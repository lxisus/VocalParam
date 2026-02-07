"""DSP Analyzer - Signal processing and pitch tracking.

Integrates librosa's PYIN algorithm for high-precision pitch detection
and provides tools for manual/surgical correction.
"""

import numpy as np
import librosa
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from utils.logger import get_logger
from utils.constants import SAMPLE_RATE

logger = get_logger(__name__)

@dataclass
class PitchPoint:
    """A single point in the pitch curve."""
    time_s: float
    frequency_hz: float
    confidence: float
    is_manual: bool = False

@dataclass
class AnalysisResult:
    """Complete DSP analysis for an audio file."""
    pitch_curve: List[PitchPoint]
    onsets: List[float]
    offsets: List[float]
    rms_energy: np.ndarray
    stable_vowels: List[Tuple[float, float]]  # (start_s, end_s)

class DSPAnalyzer:
    """Core DSP logic for VocalParam."""
    
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sr = sample_rate
        self.fmin = librosa.note_to_hz('C2')
        self.fmax = librosa.note_to_hz('C6')
        
    def analyze_audio(self, audio_data: np.ndarray) -> AnalysisResult:
        """Perform full automated analysis on raw audio data."""
        logger.info("Starting DSP analysis...")
        
        # Ensure mono and float32
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            if np.max(np.abs(audio_data)) > 1.0:
                audio_data /= 32768.0

        # 1. Pitch Tracking (PYIN)
        f0, voiced_flag, voiced_probs = librosa.pyin(
            audio_data, 
            fmin=self.fmin, 
            fmax=self.fmax, 
            sr=self.sr
        )
        
        times = librosa.times_like(f0, sr=self.sr)
        pitch_curve = []
        for t, freq, conf in zip(times, f0, voiced_probs):
            # Replace NaNs with 0 for frequency
            hz = freq if not np.isnan(freq) else 0.0
            pitch_curve.append(PitchPoint(float(t), float(hz), float(conf)))

        # 2. Onset detection
        onset_env = librosa.onset.onset_strength(y=audio_data, sr=self.sr)
        onsets_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=self.sr)
        onsets = librosa.frames_to_time(onsets_frames, sr=self.sr).tolist()

        # 3. RMS Energy (for offset and stable regions)
        rms = librosa.feature.rms(y=audio_data)[0]
        rms_times = librosa.times_like(rms, sr=self.sr)
        
        # Simple offset detection (where energy drops below 5% of max)
        threshold = np.max(rms) * 0.05
        offsets = []
        is_above = False
        for i, val in enumerate(rms):
            if val > threshold and not is_above:
                is_above = True
            elif val < threshold and is_above:
                offsets.append(float(rms_times[i]))
                is_above = False

        # 4. Stable Vowel Regions
        stable_vowels = self._find_stable_regions(pitch_curve, rms)

        logger.info(f"Analysis complete: {len(onsets)} onsets, {len(offsets)} offsets found")
        return AnalysisResult(
            pitch_curve=pitch_curve,
            onsets=onsets,
            offsets=offsets,
            rms_energy=rms,
            stable_vowels=stable_vowels
        )


    def compute_spectrogram(self, audio_data: np.ndarray) -> np.ndarray:
        """Compute magnitude spectrogram in dB.
        
        Using STFT with Hann window (2048) and 75% overlap.
        Hop length = 512 (approx 11.6ms at 44.1kHz).
        """
        stft = librosa.stft(
            audio_data, 
            n_fft=2048, 
            hop_length=512, 
            window='hann'
        )
        magnitude = np.abs(stft)
        return librosa.amplitude_to_db(magnitude, ref=np.max)

    def detect_transients(self, audio_data: np.ndarray) -> List[float]:
        """Detect transient attacks for initial offset positioning."""
        onset_env = librosa.onset.onset_strength(y=audio_data, sr=self.sr)
        onsets_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env, 
            sr=self.sr,
            backtrack=True
        )
        return librosa.frames_to_time(onsets_frames, sr=self.sr).tolist()

    def calculate_rms_envelope(self, audio_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate RMS envelope for power visualization.
        
        Returns:
            Tuple[times, rms_values]
        """
        rms = librosa.feature.rms(y=audio_data, frame_length=2048, hop_length=512)[0]
        times = librosa.times_like(rms, sr=self.sr, hop_length=512)
        return times, rms

    def _find_stable_regions(self, curve: List[PitchPoint], rms: np.ndarray) -> List[Tuple[float, float]]:
        """Identify regions where pitch and energy are stable (likely vowels)."""
        # Logic for identifying regions with low derivative in pitch and high energy
        # For now, a simple placeholder implementation
        return []

class SurgicalCorrection:
    """Manages manual overrides for DSP analysis."""
    
    def __init__(self):
        self.manual_points: Dict[float, float] = {}  # {time_s: freq_hz}
        
    def add_point(self, time_s: float, freq_hz: float):
        """Add or update a manual pitch point."""
        self.manual_points[time_s] = freq_hz
        
    def remove_point(self, time_s: float, tolerance: float = 0.01):
        """Remove a point near the specified time."""
        # Find closest point
        to_delete = None
        for t in self.manual_points:
            if abs(t - time_s) < tolerance:
                to_delete = t
                break
        if to_delete is not None:
            del self.manual_points[to_delete]

    def apply_to_curve(self, original_curve: List[PitchPoint]) -> List[PitchPoint]:
        """Blend manual points into the automated curve using interpolation."""
        if not self.manual_points:
            return original_curve

        new_curve = [p for p in original_curve]
        manual_times = sorted(self.manual_points.keys())
        
        # Simple override for now - find closest points in curve and set them 
        # as manual with 1.0 confidence
        for mt in manual_times:
            # Find index of closest time point
            closest_idx = min(range(len(new_curve)), key=lambda i: abs(new_curve[i].time_s - mt))
            new_curve[closest_idx].frequency_hz = self.manual_points[mt]
            new_curve[closest_idx].confidence = 1.0
            new_curve[closest_idx].is_manual = True

        return new_curve
