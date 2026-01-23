"""Reclist Parser module.

This module handles parsing of 7-Mora reclist files for VCV voicebanks.
Based on Section 6, MÓDULO 1 specification.
"""

import re
from pathlib import Path
from typing import List, Optional, Set

from core.models import PhonemeType, PhoneticLine
from utils.constants import DEFAULT_BPM, MORAS_PER_LINE, ms_per_beat


class ReclistParseError(Exception):
    """Exception raised when reclist parsing fails.
    
    Attributes:
        line_number: The line number where the error occurred
        line_content: The content of the problematic line
        message: Detailed error message
    """
    
    def __init__(self, message: str, line_number: int = 0, line_content: str = ""):
        self.line_number = line_number
        self.line_content = line_content
        self.message = message
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        if self.line_number > 0:
            return f"Error en línea {self.line_number}: {self.message}\nContenido: '{self.line_content}'"
        return self.message


class ReclistParser:
    """Parser for 7-Mora VCV reclist files.
    
    Analyzes reclist text files and converts them into structured
    PhoneticLine objects with metadata for each line.
    
    The parser identifies:
    - Pure vowels (VV): a_a_i_a_u_e_o
    - Basic consonants (CV): ba_be_bi_bo_bu_ba_b
    - Clusters (CCR/CCL): pra_pre_pri...
    - Diphthongs (DIP): kya_kyu_kyo...
    - Breaths (R): R or breath markers
    
    Example:
        >>> parser = ReclistParser(bpm=120)
        >>> lines = parser.parse_file("reclist.txt")
        >>> print(lines[0].segments)
        ['a', 'a', 'i', 'a', 'u', 'e', 'o']
    """
    
    # Spanish/Common vowels
    VOWELS: Set[str] = {"a", "e", "i", "o", "u"}
    
    # Common consonant patterns
    CONSONANTS: Set[str] = {
        "b", "c", "ch", "d", "f", "g", "h", "j", "k", "l", "ll",
        "m", "n", "ñ", "p", "q", "r", "rr", "s", "t", "v", "w",
        "x", "y", "z"
    }
    
    # Consonant clusters
    CLUSTERS: Set[str] = {
        "br", "bl", "cr", "cl", "dr", "fl", "fr", "gl", "gr",
        "kr", "pl", "pr", "tr", "tl"
    }
    
    # Breath/silence markers
    BREATH_MARKERS: Set[str] = {"R", "r", "breath", "br", "息"}
    
    def __init__(self, bpm: int = DEFAULT_BPM):
        """Initialize parser with BPM for duration calculations.
        
        Args:
            bpm: Beats per minute for timing calculations
        """
        self.bpm = bpm
        self._ms_per_mora = ms_per_beat(bpm)
    
    def parse_file(self, filepath: str) -> List[PhoneticLine]:
        """Parse a reclist file and return list of PhoneticLine objects.
        
        Args:
            filepath: Path to the reclist .txt file
            
        Returns:
            List of PhoneticLine objects with complete metadata
            
        Raises:
            ReclistParseError: If the file format is invalid
            FileNotFoundError: If the file doesn't exist
        """
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"Reclist file not found: {filepath}")
        
        if not path.suffix.lower() == ".txt":
            raise ReclistParseError(
                "Reclist must be a .txt file",
                line_content=filepath
            )
        
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with other common encodings
            try:
                content = path.read_text(encoding="shift-jis")
            except UnicodeDecodeError:
                content = path.read_text(encoding="latin-1")
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> List[PhoneticLine]:
        """Parse reclist content string.
        
        Args:
            content: Raw text content of reclist
            
        Returns:
            List of PhoneticLine objects
            
        Raises:
            ReclistParseError: If content format is invalid
        """
        lines = content.strip().split("\n")
        phonetic_lines: List[PhoneticLine] = []
        
        for line_num, raw_line in enumerate(lines, start=1):
            # Skip empty lines and comments
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue
            
            try:
                phonetic_line = self._parse_line(stripped, line_num)
                phonetic_lines.append(phonetic_line)
            except ReclistParseError:
                raise
            except Exception as e:
                raise ReclistParseError(
                    f"Error inesperado: {str(e)}",
                    line_number=line_num,
                    line_content=stripped
                )
        
        if not phonetic_lines:
            raise ReclistParseError("El archivo reclist está vacío o no contiene líneas válidas")
        
        return phonetic_lines
    
    def _parse_line(self, line: str, line_number: int) -> PhoneticLine:
        """Parse a single reclist line.
        
        Args:
            line: Raw line text (e.g., "ba_be_bi_bo_bu_ba_b")
            line_number: Line number for error reporting
            
        Returns:
            PhoneticLine with parsed segments
        """
        # Split by underscore (standard reclist format)
        segments = line.split("_")
        
        # Detect phoneme types for each segment
        phoneme_types = [self.detect_phoneme_type(seg) for seg in segments]
        
        # Generate filename from line content
        filename = f"{line}.wav"
        
        # Calculate expected duration
        expected_duration = self._ms_per_mora * len(segments)
        
        return PhoneticLine(
            index=line_number,
            raw_text=line,
            segments=segments,
            phoneme_types=phoneme_types,
            expected_duration_ms=expected_duration,
            filename=filename,
        )
    
    def validate_mora_count(self, line: str, expected: int = MORAS_PER_LINE) -> bool:
        """Verify that the line has the expected number of moras.
        
        Args:
            line: Raw line text
            expected: Expected mora count (default: 7)
            
        Returns:
            True if mora count matches expected
        """
        segments = line.split("_")
        return len(segments) == expected
    
    def detect_phoneme_type(self, segment: str) -> PhonemeType:
        """Classify a phoneme segment into its type.
        
        Args:
            segment: Individual segment (e.g., "ba", "a", "pra")
            
        Returns:
            PhonemeType classification
        """
        segment_lower = segment.lower()
        
        # Check for breath markers
        if segment_lower in self.BREATH_MARKERS or segment_lower == "":
            return PhonemeType.R
        
        # Pure vowel (single vowel character)
        if segment_lower in self.VOWELS:
            return PhonemeType.VV
        
        # Check for consonant clusters at start (CCR/CCL)
        for cluster in self.CLUSTERS:
            if segment_lower.startswith(cluster):
                return PhonemeType.CCR
        
        # Check for diphthongs (consonant + y/w + vowel)
        diphthong_pattern = re.compile(r'^[bcdfghjklmnpqrstvwxyz]+[yw][aeiou]$', re.IGNORECASE)
        if diphthong_pattern.match(segment_lower):
            return PhonemeType.DIP
        
        # Check if ends with vowel (CV pattern)
        if segment_lower and segment_lower[-1] in self.VOWELS:
            # Check if it's a VCV pattern (vowel + consonant + vowel)
            if len(segment_lower) >= 3 and segment_lower[0] in self.VOWELS:
                return PhonemeType.VCV
            return PhonemeType.CV
        
        # Ends with consonant (VC pattern or standalone consonant)
        if segment_lower and segment_lower[-1] not in self.VOWELS:
            if segment_lower[0] in self.VOWELS:
                return PhonemeType.VC
            # Standalone consonant (like "b" at end of ba_be_bi_bo_bu_ba_b)
            return PhonemeType.CV
        
        # Default to CV for unrecognized patterns
        return PhonemeType.CV
    
    def get_line_summary(self, line: PhoneticLine) -> str:
        """Generate a human-readable summary of a phonetic line.
        
        Args:
            line: PhoneticLine to summarize
            
        Returns:
            Formatted summary string
        """
        type_counts = {}
        for ptype in line.phoneme_types:
            type_counts[ptype.name] = type_counts.get(ptype.name, 0) + 1
        
        type_summary = ", ".join(f"{k}:{v}" for k, v in type_counts.items())
        
        return (
            f"Línea {line.index:03d}: {line.raw_text}\n"
            f"  Segmentos: {line.mora_count} | Duración: {line.expected_duration_ms:.1f}ms\n"
            f"  Tipos: {type_summary}"
        )
