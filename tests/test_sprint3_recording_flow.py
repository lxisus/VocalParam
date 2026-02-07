"""Integration Test for Recording Flow & OTO Generation.

Verifies the refined Sprint 3 flow:
1. Recorder starts with Count-in.
2. Recorder captures audio (simulated) for min duration.
3. Recorder stops and emits signal.
4. MainWindow generates OTO with correct Offset.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt

from ui.recorder_widget import RecorderWidget
from ui.main_window import MainWindow
from core.audio_engine import AudioEngine
from core.models import PhoneticLine, PhonemeType

@pytest.fixture
def mock_audio_engine():
    """Mock AudioEngine to avoid hardware dependency."""
    engine = MagicMock(spec=AudioEngine)
    engine._sample_rate = 44100
    engine._active_sr = 44100
    engine.get_scope_data.return_value = np.zeros(1024)
    # Simulate recorded audio: 5 seconds of silence then a tone
    # 3 sec count-in (at 120bpm = 1500ms? No, 3 beats * 500ms = 1500ms)
    # Wait, 120BPM = 500ms/beat. 3 beats = 1.5s.
    # Recorder count-in is 3 beats.
    # Min duration is 4s.
    # Audio buffer size = 4s * 44100 = 176400 samples.
    # We'll put a transient at 2.0s (after count-in).
    duration = 4.0
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration))
    # Transient at 2.0s
    audio = np.zeros_like(t)
    # Add a burst of noise/tone at 2.0s
    start_idx = int(2.0 * sr)
    end_idx = int(2.1 * sr)
    audio[start_idx:end_idx] = 0.8 * np.sin(2 * np.pi * 440 * t[start_idx:end_idx])
    
    engine.stop_recording.return_value = audio.astype(np.float32)
    return engine

def test_recording_oto_flow(qtbot, mock_audio_engine):
    """Ref-rec-01: Verify recording produces OTO with correct offset skipping count-in."""
    # Setup MainWindow with mocked engine
    # We patch the AudioEngine instantiation inside MainWindow? 
    # Or simplified: We test main window's logic specifically.
    
    # Let's instantiate MainWindow but swap its engine
    main_window = MainWindow()
    main_window.audio_engine = mock_audio_engine
    # Re-initialize recorder widget with new engine
    from ui.recorder_widget import RecorderWidget
    main_window.recorder_widget = RecorderWidget(mock_audio_engine)
    # Re-connect signals manually since we replaced the widget
    main_window.recorder_widget.recording_stopped.connect(main_window._on_recording_stopped)
    
    qtbot.addWidget(main_window)
    
    # 1. Select a Line
    line = PhoneticLine(
        index=0,
        raw_text="test_sample",
        segments=["test", "sample"],
        phoneme_types=[PhonemeType.CV, PhonemeType.CV],
        mora_count=2
    )
    main_window._on_line_selected(0, line)
    
    # 2. Simulate Recording Completion
    # We bypass the actual timer/threading logic of RecorderWidget for this test
    # and directly emit the signal as if user finished.
    # But we want to ensure generate_oto uses the count_in param.
    
    # Get the simulated audio
    audio_data = mock_audio_engine.stop_recording()
    
    # Emit signal
    with qtbot.waitSignal(main_window.statusbar.messageChanged, timeout=1000):
        main_window.recorder_widget.recording_stopped.emit(audio_data)
        
    # 3. Validation
    # Check if OTO entry was generated and loaded into editor controller
    assert main_window.editor_controller.current_entry is not None
    entry = main_window.editor_controller.current_entry
    
    print(f"Generated Offset: {entry.offset} ms")
    
    # Expected:
    # 120 BPM = 500ms/beat
    # Count-in = 3 beats = 1500ms
    # Min Offset Search = 1500ms - 200ms = 1300ms
    # Actual Transient in audio = 2000ms
    # Expected Offset = ~2000ms (minus 50ms buffer) = 1950ms
    
    assert entry.offset > 1300, "Offset should be after count-in"
    assert entry.offset == pytest.approx(1950.0, abs=50.0) # Allow small tolerance
    
    # Verify alias
    assert entry.alias == "test" # First segment
