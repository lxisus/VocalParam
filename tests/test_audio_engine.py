import pytest
import numpy as np
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.audio_engine import AudioEngine

def test_engine_initialization():
    engine = AudioEngine()
    assert engine._is_recording is False
    assert engine._sample_rate == 44100
    assert engine.input_device is None or isinstance(engine.input_device, int)

def test_click_generation():
    engine = AudioEngine()
    # Click should be a non-empty float32 array
    assert len(engine._click_sample) > 0
    assert engine._click_sample.dtype == np.float32
    assert np.max(np.abs(engine._click_sample)) <= 1.0

def test_device_listing():
    engine = AudioEngine()
    devices = engine.get_device_list()
    assert isinstance(devices, list)
    if len(devices) > 0:
        dev = devices[0]
        assert "name" in dev
        assert "api" in dev
        assert "inputs" in dev

def test_config_persistence():
    engine = AudioEngine()
    engine.input_device = 0
    engine.output_device = 0
    # Create fake device list for saving
    engine.save_config()
    
    # Reload in a new engine
    engine2 = AudioEngine()
    # If the file exists, it should have loaded something
    assert engine2.config_path.exists()

def test_scope_buffer_updates():
    engine = AudioEngine()
    # Initial buffer should be zeros
    buf = engine.get_scope_data()
    assert len(buf) == 2048
    assert np.all(buf == 0)
