"""Verification test for the 'Amnesia' persistence fix."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path

from ui.main_window import MainWindow
from core.audio_engine import AudioEngine
from core.models import PhoneticLine, PhonemeType, ProjectData

@pytest.fixture
def main_window(qtbot):
    """Setup MainWindow with a dummy project."""
    window = MainWindow()
    
    # Mock Audio Engine
    window.audio_engine = MagicMock(spec=AudioEngine)
    window.audio_engine._sample_rate = 44100
    window.audio_engine._active_sr = 44100
    window.audio_engine.stop_recording.return_value = np.zeros(88200, dtype=np.float32) # 2s silent audio
    window.audio_engine.load_wav.return_value = (np.zeros(88200), 44100)
    
    # Mock Project
    project = ProjectData(
        project_name="TestProject",
        bpm=120,
        reclist_path="",
        output_directory="recordings/test"
    )
    window._current_project = project
    window._current_project_path = Path("test.vocalproj")
    
    qtbot.addWidget(window)
    return window

def test_multiple_recordings_persistence(main_window, qtbot):
    """Verify that recording sample 001 and then 002 preserves both in project."""
    
    # Mock file system for recorder output GLOBALLY for this test
    with patch("pathlib.Path.exists", return_value=True), \
         patch("core.resource_manager.ResourceManager.calculate_checksum", return_value="fake_hash"):
        
        # 1. Record first sample ( ba )
        line1 = PhoneticLine(index=1, raw_text="ba", segments=["ba"], 
                             phoneme_types=[PhonemeType.CV], expected_duration_ms=1000, filename="ba.wav")
        
        main_window._on_line_selected(1, line1)
        
        # Simulate stopping recording
        audio1 = np.zeros(44100 * 2, dtype=np.float32)
        main_window._on_recording_stopped(audio1)
        
        # Verify ba is in project
        assert len(main_window._current_project.recordings) == 1
        ba_rec = next(r for r in main_window._current_project.recordings if r.line_index == 1)
        assert ba_rec.filename == "ba.wav"
        assert len(ba_rec.oto_entries) == 1
        
        first_entry = ba_rec.oto_entries[0]
        first_entry.offset = 500.0 # Modify something
        
        # 2. Record second sample ( ka )
        line2 = PhoneticLine(index=2, raw_text="ka", segments=["ka"], 
                             phoneme_types=[PhonemeType.CV], expected_duration_ms=1000, filename="ka.wav")
        
        main_window._on_line_selected(2, line2)
        
        audio2 = np.zeros(44100 * 2, dtype=np.float32)
        main_window._on_recording_stopped(audio2)
        
        # 3. VERIFICATION
        # Project should now have BOTH recordings
        assert len(main_window._current_project.recordings) == 2
        
        # Check if ba (001) still has its modified offset
        ba_rec_again = next(r for r in main_window._current_project.recordings if r.line_index == 1)
        assert ba_rec_again.oto_entries[0].offset == 500.0
        
        # Check if ka (002) is also present
        ka_rec = next(r for r in main_window._current_project.recordings if r.line_index == 2)
        assert ka_rec.filename == "ka.wav"
        assert len(ka_rec.oto_entries) == 1
        assert ka_rec.oto_entries[0].alias == "ka"
    
        ka_rec = next(r for r in main_window._current_project.recordings if r.line_index == 2)
        assert ka_rec.filename == "ka.wav"
        assert len(ka_rec.oto_entries) == 1
        assert ka_rec.oto_entries[0].alias == "ka"
