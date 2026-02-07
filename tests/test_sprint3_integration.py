"""Integration Test for Sprint 3: Visual Editor.

Validates the complete flow from loading audio to parameter editing.
"""

import pytest
import time
import numpy as np
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PyQt6.QtCore import Qt
from core.models import OtoEntry
from ui.editor_widget import EditorWidget
from ui.parameter_table_widget import ParameterTableWidget
from controllers.editor_controller import EditorController

@pytest.fixture
def sample_audio():
    """Create a dummy 5s audio signal (sine wave)."""
    sr = 44100
    duration = 5.0
    t = np.linspace(0, duration, int(sr * duration)).astype(np.float32)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    return audio, sr

@pytest.fixture
def oto_entry():
    """Create a default OtoEntry."""
    return OtoEntry(
        filename="test.wav",
        alias="test_alias",
        offset=50.0,
        consonant=100.0,
        cutoff=-100.0,
        preutter=80.0,
        overlap=40.0
    )

def test_spectrogram_performance(qtbot, sample_audio, oto_entry):
    """Ref-01: Validate spectrogram generation < 500ms for 5s audio (DSP only)."""
    audio, sr = sample_audio
    
    # Measure DSP calculation time only
    # UI rendering time depends heavily on hardware/drivers in test env
    from core.dsp_analyzer import DSPAnalyzer
    analyzer = DSPAnalyzer()
    
    # Warmup (librosa/numba compilation overhead)
    _ = analyzer.compute_spectrogram(audio[:1024])
    
    start_time = time.time()
    _ = analyzer.compute_spectrogram(audio)
    end_time = time.time()
    
    duration_ms = (end_time - start_time) * 1000
    
    print(f"Spectrogram generation time (DSP): {duration_ms:.2f}ms")
    assert duration_ms < 500, f"Spectrogram too slow: {duration_ms}ms"

def test_data_sync(qtbot, sample_audio, oto_entry):
    """Ref-03: Validate marker movement updates model correctly."""
    audio, sr = sample_audio
    
    editor = EditorWidget()
    table = ParameterTableWidget()
    
    # Initialize table with entry (Simulate project load)
    table.set_entries([oto_entry])
    
    controller = EditorController(editor, table)
    qtbot.addWidget(editor)
    
    controller.load_entry(oto_entry, audio, sr)
    
    # Simulate moving overlap marker
    new_overlap_ms = 60.0 # Valid move (< preutter 80.0)
    
    # Emit signal directly from canvas to simulate drag
    editor.marker_moved.emit('overlap', new_overlap_ms)
         
    # Check model update
    assert controller.current_entry.overlap == pytest.approx(new_overlap_ms)
    
    # Check table UI update (row 0, col 2 is Overlap)
    # Note: Table does NOT emit parameter_changed when updated programmatically
    item = table.item(0, 2)
    assert float(item.text()) == pytest.approx(new_overlap_ms)

def test_overlap_constraint(qtbot, sample_audio, oto_entry):
    """Ref-02: Validate Gold Rule constraint (overlap <= preutter)."""
    audio, sr = sample_audio
    
    editor = EditorWidget()
    table = ParameterTableWidget() # Not strictly needed for this test but part of controller
    controller = EditorController(editor, table) # Instantiation
    
    # We test WaveformCanvas method directly
    canvas = editor.canvas
    canvas.set_audio_data(audio, sr) # Init duration
    canvas.set_markers(oto_entry) # Set initial markers
    
    # Fixture: offset=50ms (0.05s), preutter=80ms (0.08s)
    # Preutter Marker Pos = 0.05 + 0.08 = 0.13s
    preutter_pos_s = 0.13
    
    # Try to drag Overlap past Preutter -> to 0.14s
    target_pos_s = 0.14
    
    # Find overlap line
    overlap_line = canvas.markers['overlap']
    
    # Trigger move
    overlap_line.setValue(target_pos_s)
    
    # Should snap back to Preutter pos (0.13s)
    current_pos_s = overlap_line.value()
    
    assert current_pos_s <= preutter_pos_s + 1e-6, "Overlap constraint failed"
    assert current_pos_s == pytest.approx(preutter_pos_s, abs=1e-4)
