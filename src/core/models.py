"""Data models for VocalParam.

This module contains all dataclasses and enums used throughout the application.
Following the specification in Section 6-7 of the design document.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Optional


class PhonemeType(Enum):
    """Classification of phoneme segments.
    
    Based on RF-02.1 specification:
    - VV: Pure vowels
    - CV: Consonant + Vowel (basic)
    - VCV: Vowel-Consonant-Vowel transitions
    - VC: Vowel + Consonant (coda)
    - CCR: Consonant clusters (right)
    - CCL: Consonant clusters (left)
    - DIP: Diphthongs (palatization/labialization)
    - R: Breaths/respirations
    """
    VV = auto()   # Pure vowels (a_a_i_a_u_e_o)
    CV = auto()   # Consonant-Vowel (ba, ka, sa...)
    VCV = auto()  # Vowel-Consonant-Vowel transitions
    VC = auto()   # Vowel-Consonant codas
    CCR = auto()  # Consonant clusters (pr, tr, kr...)
    CCL = auto()  # Consonant clusters left
    DIP = auto()  # Diphthongs
    R = auto()    # Breaths/respirations


class RecordingStatus(Enum):
    """Status of a recording line."""
    PENDING = "pending"
    RECORDED = "recorded"
    VALIDATED = "validated"


@dataclass
class PhoneticLine:
    """Represents a single line from the Reclist.
    
    As specified in Section 6, MÓDULO 1.
    
    Attributes:
        index: Line number (001, 002...)
        raw_text: Original text from reclist (e.g., "ba_be_bi_bo_bu_ba_b")
        segments: List of individual segments (e.g., ["ba", "be", "bi"...])
        phoneme_types: Classification of each segment
        expected_duration_ms: Calculated duration based on BPM
        filename: Generated WAV filename
    """
    index: int
    raw_text: str
    segments: List[str]
    phoneme_types: List[PhonemeType]
    expected_duration_ms: float
    filename: str
    
    @property
    def mora_count(self) -> int:
        """Number of moras (segments) in this line."""
        return len(self.segments)


@dataclass
class OtoEntry:
    """Represents a single entry in oto.ini file.
    
    Format: filename.wav=alias,offset,consonant,cutoff,preutter,overlap
    
    Attributes:
        filename: WAV file name
        alias: Phonetic alias (e.g., "- ba" or "a be")
        offset: Start position in ms (cian/cyan line)
        consonant: Fixed consonant region in ms (dark blue line)
        cutoff: End position in ms, negative = from end (pink/magenta line)
        preutter: Pre-utterance point in ms (red line)
        overlap: Overlap region in ms (green line)
    """
    filename: str
    alias: str
    offset: float
    consonant: float
    cutoff: float
    preutter: float
    overlap: float
    
    def to_oto_line(self) -> str:
        """Convert to oto.ini format string."""
        return (
            f"{self.filename}={self.alias},"
            f"{self.offset:.1f},{self.consonant:.1f},"
            f"{self.cutoff:.1f},{self.preutter:.1f},{self.overlap:.1f}"
        )
    
    @classmethod
    def from_oto_line(cls, line: str) -> "OtoEntry":
        """Parse an oto.ini format line."""
        # Split filename from parameters
        filename_part, params_part = line.strip().split("=", 1)
        parts = params_part.split(",")
        
        return cls(
            filename=filename_part,
            alias=parts[0],
            offset=float(parts[1]),
            consonant=float(parts[2]),
            cutoff=float(parts[3]),
            preutter=float(parts[4]),
            overlap=float(parts[5]),
        )


@dataclass
class Recording:
    """Represents a single recording with its oto entries."""
    line_index: int
    filename: str
    status: RecordingStatus = RecordingStatus.PENDING
    duration_ms: float = 0.0
    oto_entries: List[OtoEntry] = field(default_factory=list)


@dataclass
class ProjectData:
    """Complete project state for serialization (JSON).
    
    Based on Section 7 data model specification.
    """
    project_name: str
    bpm: int
    reclist_path: str
    output_directory: str
    recordings: List[Recording] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_name": self.project_name,
            "bpm": self.bpm,
            "reclist_path": self.reclist_path,
            "output_directory": self.output_directory,
            "recordings": [
                {
                    "line_index": r.line_index,
                    "filename": r.filename,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "oto_entries": [
                        {
                            "alias": e.alias,
                            "offset": e.offset,
                            "consonant": e.consonant,
                            "cutoff": e.cutoff,
                            "preutter": e.preutter,
                            "overlap": e.overlap,
                        }
                        for e in r.oto_entries
                    ],
                }
                for r in self.recordings
            ],
            "metadata": {
                "created_at": self.created_at.isoformat(),
                "last_modified": self.last_modified.isoformat(),
                "version": self.version,
            },
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectData":
        """Create ProjectData from dictionary."""
        recordings = []
        for r in data.get("recordings", []):
            oto_entries = [
                OtoEntry(
                    filename=r["filename"],
                    alias=e["alias"],
                    offset=e["offset"],
                    consonant=e["consonant"],
                    cutoff=e["cutoff"],
                    preutter=e["preutter"],
                    overlap=e["overlap"],
                )
                for e in r.get("oto_entries", [])
            ]
            recordings.append(Recording(
                line_index=r["line_index"],
                filename=r["filename"],
                status=RecordingStatus(r["status"]),
                duration_ms=r.get("duration_ms", 0.0),
                oto_entries=oto_entries,
            ))
        
        metadata = data.get("metadata", {})
        return cls(
            project_name=data["project_name"],
            bpm=data["bpm"],
            reclist_path=data["reclist_path"],
            output_directory=data["output_directory"],
            recordings=recordings,
            created_at=datetime.fromisoformat(metadata.get("created_at", datetime.now().isoformat())),
            last_modified=datetime.fromisoformat(metadata.get("last_modified", datetime.now().isoformat())),
            version=metadata.get("version", "1.0.0"),
        )
