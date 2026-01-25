"""Tests for DSPAnalyzer."""

import pytest
import numpy as np
from core.dsp_analyzer import DSPAnalyzer, SurgicalCorrection, PitchPoint
from utils.constants import SAMPLE_RATE

def test_analyzer_initialization():
    analyzer = DSPAnalyzer(sample_rate=44100)
    assert analyzer.sr == 44100
    assert analyzer.fmin > 0
    assert analyzer.fmax > analyzer.fmin

def test_analyze_silence():
    analyzer = DSPAnalyzer(sample_rate=44100)
    # 0.5 seconds of silence
    silence = np.zeros(22050, dtype=np.float32)
    result = analyzer.analyze_audio(silence)
    
    assert len(result.pitch_curve) > 0
    # On silence, confidence should broadly be low or 0
    average_confidence = sum(p.confidence for p in result.pitch_curve) / len(result.pitch_curve)
    assert average_confidence < 0.2

def test_analyze_sine_wave():
    analyzer = DSPAnalyzer(sample_rate=44100)
    # 1.0 second of 440Hz sine wave (A4)
    t = np.linspace(0, 1, 44100, False)
    sine_440 = np.sin(440 * t * 2 * np.pi).astype(np.float32)
    
    result = analyzer.analyze_audio(sine_440)
    
    # Check if some points correctly identified ~440Hz
    # librosa.pyin might not be perfect on a raw sine but should be close
    detected_pitches = [p.frequency_hz for p in result.pitch_curve if p.confidence > 0.8]
    assert len(detected_pitches) > 0
    
    # Mean of high confidence points should be near 440
    mean_pitch = sum(detected_pitches) / len(detected_pitches)
    assert 430 <= mean_pitch <= 450

def test_surgical_correction():
    correction = SurgicalCorrection()
    curve = [
        PitchPoint(0.0, 100.0, 0.9),
        PitchPoint(0.1, 100.0, 0.9),
        PitchPoint(0.2, 100.0, 0.9)
    ]
    
    # Correct the middle point to 200Hz
    correction.add_point(0.1, 200.0)
    new_curve = correction.apply_to_curve(curve)
    
    assert new_curve[1].frequency_hz == 200.0
    assert new_curve[1].is_manual is True
    assert new_curve[1].confidence == 1.0
    # Neighbors shouldn't change in the simple implementation
    assert new_curve[0].frequency_hz == 100.0
