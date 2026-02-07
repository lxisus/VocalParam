"""OTO Generator - Automatic parameter estimation.

Uses hybrid approach:
1. BPM-based calculation (Grid)
2. DSP-based refinement (Transients/RMS)
"""

from typing import List, Tuple
import numpy as np
import librosa
from core.models import OtoEntry, ProjectData
from core.dsp_analyzer import DSPAnalyzer

class OtoGenerator:
    """Generates initial OTO parameters."""
    
    def __init__(self, bpm: int):
        self.bpm = bpm
        self.dsp = DSPAnalyzer()

    def generate_oto(self, filename: str, audio_data: np.ndarray, alias: str, count_in_beats: int = 3) -> OtoEntry:
        """Generate a single OTO entry with smart positioning.
        
        Args:
            filename: Name of the wav file.
            audio_data: Audio samples.
            alias: Alias for the OTO entry.
            count_in_beats: Number of beats to skip (silence/prep) before detection.
        """
        # 1. Calculate grid and expected start time
        beat_ms = 60000 / self.bpm
        min_start_ms = beat_ms * count_in_beats
        
        # 2. DSP Analysis
        # Detect all transients
        onsets_s = self.dsp.detect_transients(audio_data)
        onsets_ms = [t * 1000.0 for t in onsets_s]
        
        # Filter onsets that are too early (during count-in)
        # We allow a small tolerance (e.g., 200ms before expected start) for early attacks
        search_start = max(0, min_start_ms - 200)
        valid_onsets = [t for t in onsets_ms if t >= search_start]
        
        # Default offset logic
        if valid_onsets:
            # Pick the first valid onset as the start of the sample
            offset = valid_onsets[0]
            # Fine-tune: Offset corresponds to the START of the consonant/vowel
            # Usually we want a bit of "Left Blank" before the actual sound starts.
            # But in UTAU, "Offset" IS the start of the used audio.
            # Often, we want Offset to be slightly before the transient peak.
            offset = max(0, offset - 50.0) # 50ms buffer before transient
        else:
            # Fallback if no transient found: use grid expectation
            offset = min_start_ms
            
        # 3. Parameter Heuristics (Standard CV/VCV values)
        # Consonant (Fixed/Pink): Duration of the consonant part
        consonant = 80.0
        
        # Preutterance (Red): From Offset to the Vowel onset
        # If we set Offset 50ms before transient, and transient is vowel start...
        # Then preutter should be around 50-60ms?
        # Let's align Preutter with the transient peak we found
        preutter = 60.0 # Standard-ish
        
        # Overlap (Green): Crossfade area
        # Must be <= Preutter (Gold Rule)
        overlap = 30.0
        
        # Cutoff (Blue): Negative value from end
        # Default to include decent tail, or use RMS to find silence?
        cutoff = -100.0
        
        return OtoEntry(
            filename=filename,
            alias=alias,
            offset=offset,
            consonant=consonant,
            cutoff=cutoff,
            preutter=preutter,
            overlap=overlap
        )
