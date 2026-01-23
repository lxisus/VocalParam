"""Unit tests for ReclistParser module.

Tests both successful parsing and error conditions.
Coverage target: 100% for parser as specified in Sprint 0.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.models import PhonemeType, PhoneticLine
from core.reclist_parser import ReclistParser, ReclistParseError


class TestReclistParserBasic:
    """Basic parsing functionality tests."""
    
    @pytest.fixture
    def parser(self):
        """Create parser with default BPM."""
        return ReclistParser(bpm=120)
    
    @pytest.fixture
    def sample_reclist_path(self):
        """Path to sample reclist fixture."""
        return Path(__file__).parent / "fixtures" / "sample_reclist.txt"
    
    def test_parse_valid_file(self, parser, sample_reclist_path):
        """Test parsing a valid reclist file."""
        lines = parser.parse_file(str(sample_reclist_path))
        
        assert len(lines) > 0
        assert all(isinstance(line, PhoneticLine) for line in lines)
    
    def test_parse_vowel_line(self, parser):
        """Test parsing pure vowel lines."""
        content = "a_a_i_a_u_e_o"
        lines = parser.parse_content(content)
        
        assert len(lines) == 1
        line = lines[0]
        assert line.segments == ["a", "a", "i", "a", "u", "e", "o"]
        assert line.mora_count == 7
        assert all(pt == PhonemeType.VV for pt in line.phoneme_types)
    
    def test_parse_cv_line(self, parser):
        """Test parsing consonant-vowel lines."""
        content = "ba_be_bi_bo_bu_ba_b"
        lines = parser.parse_content(content)
        
        line = lines[0]
        assert line.segments == ["ba", "be", "bi", "bo", "bu", "ba", "b"]
        # First 6 are CV, last one is standalone consonant
        assert line.phoneme_types[0] == PhonemeType.CV
        assert line.phoneme_types[5] == PhonemeType.CV
    
    def test_parse_cluster_line(self, parser):
        """Test parsing consonant cluster lines."""
        content = "pra_pre_pri_pro_pru_pra_pr"
        lines = parser.parse_content(content)
        
        line = lines[0]
        assert line.segments[0] == "pra"
        assert line.phoneme_types[0] == PhonemeType.CCR
    
    def test_parse_diphthong_line(self, parser):
        """Test parsing diphthong lines."""
        content = "kya_kyu_kyo_kya_kyu_kyo_ky"
        lines = parser.parse_content(content)
        
        line = lines[0]
        assert line.phoneme_types[0] == PhonemeType.DIP
    
    def test_parse_breath_line(self, parser):
        """Test parsing breath/respiration lines."""
        content = "R_R_R_R_R_R_R"
        lines = parser.parse_content(content)
        
        line = lines[0]
        assert all(pt == PhonemeType.R for pt in line.phoneme_types)
    
    def test_skip_comments(self, parser):
        """Test that comments are skipped."""
        content = """# This is a comment
// This is also a comment
ba_be_bi_bo_bu_ba_b
"""
        lines = parser.parse_content(content)
        assert len(lines) == 1
    
    def test_skip_empty_lines(self, parser):
        """Test that empty lines are skipped."""
        content = """

ba_be_bi_bo_bu_ba_b

da_de_di_do_du_da_d

"""
        lines = parser.parse_content(content)
        assert len(lines) == 2


class TestReclistParserValidation:
    """Validation and mora count tests."""
    
    @pytest.fixture
    def parser(self):
        return ReclistParser(bpm=120)
    
    def test_validate_mora_count_correct(self, parser):
        """Test mora count validation with correct count."""
        assert parser.validate_mora_count("ba_be_bi_bo_bu_ba_b", expected=7)
    
    def test_validate_mora_count_incorrect(self, parser):
        """Test mora count validation with incorrect count."""
        assert not parser.validate_mora_count("ba_be_bi", expected=7)
    
    def test_expected_duration_calculation(self, parser):
        """Test that expected duration is calculated correctly."""
        content = "ba_be_bi_bo_bu_ba_b"
        lines = parser.parse_content(content)
        
        # At 120 BPM: 60000/120 = 500ms per beat
        # 7 moras = 7 * 500 = 3500ms
        assert lines[0].expected_duration_ms == 3500.0
    
    def test_filename_generation(self, parser):
        """Test that filenames are generated correctly."""
        content = "ba_be_bi_bo_bu_ba_b"
        lines = parser.parse_content(content)
        
        assert lines[0].filename == "ba_be_bi_bo_bu_ba_b.wav"


class TestReclistParserErrors:
    """Error handling tests."""
    
    @pytest.fixture
    def parser(self):
        return ReclistParser(bpm=120)
    
    def test_file_not_found(self, parser):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file("nonexistent_file.txt")
    
    def test_empty_content(self, parser):
        """Test error with empty content."""
        with pytest.raises(ReclistParseError) as exc_info:
            parser.parse_content("")
        
        assert "vacío" in str(exc_info.value).lower()
    
    def test_only_comments(self, parser):
        """Test error when file only contains comments."""
        content = """# Comment 1
// Comment 2
# Comment 3
"""
        with pytest.raises(ReclistParseError):
            parser.parse_content(content)


class TestPhonemeTypeDetection:
    """Phoneme type detection tests."""
    
    @pytest.fixture
    def parser(self):
        return ReclistParser()
    
    def test_detect_vowel(self, parser):
        """Test detection of pure vowels."""
        for vowel in ["a", "e", "i", "o", "u"]:
            assert parser.detect_phoneme_type(vowel) == PhonemeType.VV
    
    def test_detect_cv(self, parser):
        """Test detection of CV patterns."""
        for segment in ["ba", "ka", "sa", "ta", "na"]:
            assert parser.detect_phoneme_type(segment) == PhonemeType.CV
    
    def test_detect_cluster(self, parser):
        """Test detection of consonant clusters."""
        for segment in ["pra", "bra", "tra", "dra", "fra"]:
            assert parser.detect_phoneme_type(segment) == PhonemeType.CCR
    
    def test_detect_diphthong(self, parser):
        """Test detection of diphthongs."""
        for segment in ["kya", "kyu", "gya", "rya"]:
            assert parser.detect_phoneme_type(segment) == PhonemeType.DIP
    
    def test_detect_breath(self, parser):
        """Test detection of breath markers."""
        for marker in ["R", "r", "breath"]:
            assert parser.detect_phoneme_type(marker) == PhonemeType.R


class TestBPMVariations:
    """Test different BPM settings."""
    
    def test_bpm_60(self):
        """Test parsing at 60 BPM."""
        parser = ReclistParser(bpm=60)
        lines = parser.parse_content("ba_be_bi_bo_bu_ba_b")
        
        # At 60 BPM: 60000/60 = 1000ms per beat
        # 7 moras = 7000ms
        assert lines[0].expected_duration_ms == 7000.0
    
    def test_bpm_150(self):
        """Test parsing at 150 BPM."""
        parser = ReclistParser(bpm=150)
        lines = parser.parse_content("ba_be_bi_bo_bu_ba_b")
        
        # At 150 BPM: 60000/150 = 400ms per beat
        # 7 moras = 2800ms
        assert lines[0].expected_duration_ms == 2800.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
