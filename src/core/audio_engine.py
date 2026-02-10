"""Audio Engine - Handles recording and playback.

Uses sounddevice for low-latency audio capture and playback.
"""

import numpy as np
import sounddevice as sd
import wave
import time
import json
from pathlib import Path
from typing import Optional, Callable
import threading
from utils.constants import (
    SAMPLE_RATE, CHANNELS, PRO_DEVICE_KEYWORDS, 
    API_PRIORITY, SUPPORTED_RATES
)
from core.persistence import AppDatabase
from utils.logger import get_logger

logger = get_logger(__name__)

class AudioEngine:
    """Core audio functionality for recording and metronome."""
    
    def __init__(self):
        self._sample_rate = SAMPLE_RATE
        self._channels = CHANNELS
        self._is_recording = False
        self._recording_data = []
        self._input_stream: Optional[sd.InputStream] = None
        self._output_stream: Optional[sd.OutputStream] = None
        
        # Device configuration
        self.input_device: Optional[int] = None
        self.output_device: Optional[int] = None
        
        # Working hardware parameters (found during scan)
        self._active_sr = SAMPLE_RATE
        self._active_channels = CHANNELS
        
        # Monitoring state
        self._monitoring_stream: Optional[sd.InputStream] = None
        self._current_level: float = 0.0
        self._is_monitoring = False
        self._is_closing = False
        self._stream_lock = threading.Lock()
        
        # Pre-generate professional metronome clicks with ADSR envelope
        self._click_sample = self._generate_professional_click(1500, 0.012, 0.25)  # Normal click
        self._click_accent = self._generate_professional_click(2000, 0.012, 0.35)  # Accent click
        self._click_countin = self._generate_professional_click(1000, 0.012, 0.20)  # Count-in click
        self._test_tone = self._generate_click(440, 0.5, 0.3)  # A4 note for test (keep simple for testing)
        
        # Oscilloscope buffer (last 2048 samples)
        self._scope_buffer_size = 2048
        self._scope_buffer = np.zeros(self._scope_buffer_size, dtype=np.float32)
        
        # Click playback state for Duplex Stream
        self._click_to_play: Optional[np.ndarray] = None
        self._click_ptr = 0
        self._click_lock = threading.Lock()
        
        # Database for config
        self.db = AppDatabase()
        self.load_config()
        
        logger.info("AudioEngine initialized")

    def save_config(self):
        """Save current device names and settings to database."""
        devices = self.get_device_list()
        input_name = None
        output_name = None
        
        for d in devices:
            if d['index'] == self.input_device:
                input_name = d['full_name']
            if d['index'] == self.output_device:
                output_name = d['full_name']
                
        config = {
            "input_device_name": input_name,
            "output_device_name": output_name,
            "sample_rate": self._sample_rate, # Persistence: Save user INTENT, not matching hardware result
            "channels": self._channels
        }
        
        self.db.set_setting("audio_config", config)
        logger.info(f"Audio config saved: {input_name} | {output_name} | {self._sample_rate}Hz")

    def load_config(self):
        """Load hardware selection by name to handle index changes."""
        config = self.db.get_setting("audio_config")
        if not config:
            return
            
        try:
            in_name = config.get("input_device_name")
            out_name = config.get("output_device_name")
            self._sample_rate = config.get("sample_rate", SAMPLE_RATE)
            self._active_sr = self._sample_rate 
            self._active_channels = config.get("channels", CHANNELS)
            self._channels = self._active_channels
            
            # Map names back to current indices
            devices = self.get_device_list()
            for d in devices:
                if d['full_name'] == in_name:
                    self.input_device = d['index']
                if d['full_name'] == out_name:
                    self.output_device = d['index']
            
            self._regenerate_clicks() # Match click SR to hardware
            logger.info("Audio config loaded from database")
        except Exception as e:
            logger.error(f"Failed to load audio config: {e}")

    def get_device_list(self):
        """Return a structured list of devices categorized by Host API."""
        try:
            devices = sd.query_devices()
            host_apis = sd.query_hostapis()
        except Exception as e:
            logger.error(f"Error querying devices: {e}")
            return []
            
        device_list = []
        for i, dev in enumerate(devices):
            api_idx = dev['hostapi']
            api_name = host_apis[api_idx]['name']
            
            # Skip virtual/useless devices that clutter the UI on Windows
            if "Streaming" in dev['name'] or "Primary" in dev['name'] or "Asignador" in dev['name']:
                # We keep them but internally mark them
                priority = 0
            else:
                priority = 1

            device_list.append({
                'index': i,
                'name': dev['name'],
                'full_name': f"{dev['name']} ({api_name})",
                'inputs': dev['max_input_channels'],
                'outputs': dev['max_output_channels'],
                'default_sr': dev['default_samplerate'],
                'api': api_name,
                'api_index': api_idx,
                'is_asio': 'ASIO' in api_name.upper(),
                'priority': priority
            })
        return device_list

    def log_hardware_status(self):
        """Debug method to print current hardware state to logs."""
        logger.info("--- HARDWARE STATUS REPORT ---")
        try:
            default_in = sd.query_devices(kind='input')
            default_out = sd.query_devices(kind='output')
            logger.info(f"Default Input: {default_in['name']} (Idx: {default_in['index']})")
            logger.info(f"Default Output: {default_out['name']} (Idx: {default_out['index']})")
        except:
            logger.warning("Could not determine default devices.")
        
        devices = self.get_device_list()
        for d in devices:
            if d['priority'] > 0:
                logger.info(f"Device [{d['index']}]: {d['full_name']} | IN: {d['inputs']} OUT: {d['outputs']} | SR: {d['default_sr']}")
        logger.info("--- END REPORT ---")

    def set_devices(self, input_idx: Optional[int], output_idx: Optional[int]):
        """Set the active input and output devices."""
        self.input_device = input_idx
        self.output_device = output_idx
        logger.info(f"Devices set - Input: {input_idx}, Output: {output_idx}")

    def set_sample_rate(self, sr: int):
        """Set the desired sample rate and trigger click regeneration."""
        self._sample_rate = sr
        self._active_sr = sr
        self._regenerate_clicks()
        logger.info(f"AudioEngine Sample Rate set to {sr}Hz")

    def check_device_capabilities(self, device_id: int) -> dict:
        """Validate sample rates for a specific device."""
        results = {}
        for sr in SUPPORTED_RATES:
            try:
                sd.check_input_settings(device=device_id, samplerate=sr, channels=self._channels)
                results[sr] = True
            except Exception:
                results[sr] = False
        return results

    class DeviceScorer:
        @staticmethod
        def score(device_info: dict) -> int:
            score = 0
            name = device_info['name']
            api = device_info['api']
            
            # API Priority
            for api_key, points in API_PRIORITY.items():
                if api_key in api:
                    score += points
                    
            # Pro Hardware Keywords
            for kw in PRO_DEVICE_KEYWORDS:
                if kw in name:
                    score += 30
                    
            # Channels
            if device_info['inputs'] >= 2:
                score += 10
                
            return score

    def _generate_click(self, freq: float, duration: float, volume: float) -> np.ndarray:
        """Generate a simple click sample (used for test tones)."""
        t = np.linspace(0, duration, int(self._sample_rate * duration), False)
        # Sine wave + fade out to avoid clicks
        click = np.sin(freq * t * 2 * np.pi) * volume
        fade_out = np.linspace(1, 0, len(click))
        return (click * fade_out).astype(np.float32)
    
    def _generate_professional_click(self, freq: float, duration: float, volume: float) -> np.ndarray:
        """Generate a professional metronome click with ADSR envelope.
        
        Creates a clean, percussive click sound suitable for musical timing.
        Uses exponential decay for natural sound and adds slight noise for character.
        
        Args:
            freq: Fundamental frequency in Hz (1000-2000 recommended)
            duration: Total duration in seconds (0.010-0.015 recommended)
            volume: Peak amplitude 0.0-1.0
            
        Returns:
            Float32 audio sample with ADSR envelope
        """
        n_samples = int(self._sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        
        # Generate base sine wave
        sine = np.sin(freq * t * 2 * np.pi)
        
        # Add slight noise component for "woodblock" character (5% mix)
        noise = np.random.randn(n_samples) * 0.05
        signal = sine + noise
        
        # ADSR Envelope
        attack_samples = int(n_samples * 0.05)   # 5% attack (very fast)
        decay_samples = int(n_samples * 0.15)    # 15% decay
        release_start = int(n_samples * 0.70)    # Release starts at 70%
        
        envelope = np.ones(n_samples)
        
        # Attack: Quick ramp up
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay: Exponential decay to sustain level (0.6)
        if decay_samples > 0:
            decay_end = attack_samples + decay_samples
            envelope[attack_samples:decay_end] = 1.0 - (1.0 - 0.6) * (1 - np.exp(-3 * np.linspace(0, 1, decay_samples)))
        
        # Sustain: Hold at 0.6
        envelope[attack_samples + decay_samples:release_start] = 0.6
        
        # Release: Exponential fade out
        release_samples = n_samples - release_start
        if release_samples > 0:
            envelope[release_start:] = 0.6 * np.exp(-5 * np.linspace(0, 1, release_samples))
        
        # Apply envelope and volume
        click = signal * envelope * volume
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(click))
        if max_val > 0:
            click = click / max_val * volume
        return click.astype(np.float32)

    def start_output_stream(self):
        """Legacy method stub. Duplex mode handles this internally during recording."""
        pass

    def stop_output_stream(self):
        """Legacy method stub."""
        pass

    def play_click(self, accent: bool = False, countin: bool = False):
        """Arm a click sound to be played with sample-level precision in the duplex callback.
        
        If not recording, uses a standard non-blocking playback fallback.
        """
        sample = self._click_countin if countin else (self._click_accent if accent else self._click_sample)
            
        with self._click_lock:
            # Arm for Duplex callback
            self._click_to_play = sample
            self._click_ptr = 0
            
        # Preview Fallback: If the duplex stream isn't active, play directly
        if not self._is_recording:
            try:
                # Use a new thread for non-blocking preview to avoid UI freeze
                sd.play(sample, self._active_sr, device=self.output_device, blocking=False)
            except Exception as e:
                logger.warning(f"Metronome preview failed (Device likely busy by another app): {e}")

    def play_audio(self, data: np.ndarray):
        """Play back audio buffer with robust device handling."""
        if data is None or len(data) == 0: return
        try:
            sr = self._active_sr if self._active_sr else SAMPLE_RATE
            sd.play(data, sr, device=self.output_device)
        except Exception as e:
            logger.error(f"Playback failed. Check if another app (YouTube/Spotify) is using the device in Exclusive Mode: {e}")

    def stop_audio(self):
        """Stop any current playback."""
        try: sd.stop()
        except: pass

    def stop_monitoring(self):
        """Stop input level monitoring and release device synchronously."""
        self._is_monitoring = False
        with self._stream_lock:
            if self._monitoring_stream:
                try:
                    self._monitoring_stream.stop()
                    self._monitoring_stream.close()
                    logger.debug("Monitoring stream released.")
                except Exception as e:
                    logger.warning(f"Error releasing monitoring stream: {e}")
                finally:
                    self._monitoring_stream = None
                    time.sleep(0.15) # Buffer for WDM-KS driver release
        self._current_level = 0.0

    def get_input_level(self) -> float:
        return self._current_level

    def start_monitoring(self, device_id: Optional[int] = None):
        """Start monitoring input levels (Oscilloscope + RMS)."""
        self.stop_monitoring()
        target_device = device_id if device_id is not None else self.input_device
        if target_device is None: return

        def callback(indata, frames, time, status):
            if status: return
            data = indata[:, 0] if indata.ndim > 1 else indata
            # Update scope
            shift = len(data)
            if shift < self._scope_buffer_size:
                self._scope_buffer = np.roll(self._scope_buffer, -shift)
                self._scope_buffer[-shift:] = data
            else:
                self._scope_buffer = data[-self._scope_buffer_size:]
            # Level
            rms = np.sqrt(np.mean(indata**2))
            self._current_level = float(np.clip(rms * 5.0, 0, 1))

        success, sr, ch = self._scan_and_open_stream(target_device, callback)
        if success:
            self._monitoring_stream = self._stream
            self._stream = None
            self._is_monitoring = True
            self._active_sr = sr
            self._active_channels = ch

    def get_scope_data(self) -> np.ndarray:
        return self._scope_buffer

    def _scan_and_open_stream(self, device_id: int, callback: Callable) -> tuple[bool, int, int]:
        """Core logic to find working audio settings, prioritizing user configuration."""
        try:
            info = sd.query_devices(device_id)
            native_sr = int(info['default_samplerate'])
            max_in = info['max_input_channels']
        except Exception as e:
            logger.error(f"Hardware scan error: {e}")
            return False, 0, 0

        # Preference: 1. User config, 2. Native hardware, 3. Standard rates
        sample_rates = []
        if self._active_sr: sample_rates.append(self._active_sr)
        if native_sr not in sample_rates: sample_rates.append(native_sr)
        for sr in [44100, 48000]:
            if sr not in sample_rates: sample_rates.append(sr)

        channel_configs = [self._channels]
        if max_in >= 2: channel_configs.append(2)

        for sr in sample_rates:
            for ch in channel_configs:
                try:
                    stream = sd.InputStream(
                        samplerate=sr, channels=ch, device=device_id, callback=callback
                    )
                    stream.start()
                    self._stream = stream
                    logger.info(f"Monitor Stream Ready: {sr}Hz | {ch}ch")
                    return True, sr, ch
                except: continue
        return False, 0, 0

    def _regenerate_clicks(self):
        """Align metronome clicks with currently active hardware sample rate."""
        sr = self._active_sr if self._active_sr else self._sample_rate
        old_sr = self._sample_rate
        self._sample_rate = sr
        self._click_sample = self._generate_professional_click(1500, 0.012, 0.25)
        self._click_accent = self._generate_professional_click(2000, 0.012, 0.35)
        self._click_countin = self._generate_professional_click(1000, 0.012, 0.20)
        self._sample_rate = old_sr

    def play_test_sound(self, device_id: Optional[int] = None):
        target_device = device_id if device_id is not None else self.output_device
        if target_device is None: return
        try:
            sd.play(self._test_tone, self._active_sr, device=target_device)
        except Exception as e:
            logger.error(f"Hardware test failed. Usually means device is busy: {e}")

    def start_recording(self):
        """Robust Full Duplex recording with aggressive hardware reset for WDM-KS stability."""
        if self._is_recording: return
        
        logger.info("Preparing hardware for recording (Hard Reset)...")
        # 1. STOP EVERYTHING: Monitoring, sounds, and active streams
        self.stop_monitoring()
        try: sd.stop()
        except: pass
        
        # Give Windows/WDM-KS time to actually release the kernel pins
        time.sleep(0.3) 
        
        self._recording_data = []
        self._is_recording = True
        
        with self._click_lock:
            self._click_to_play = None
            self._click_ptr = 0

        def duplex_callback(indata, outdata, frames, time, status):
            if status: logger.warning(f"Audio Callback Status: {status}")
            
            # 1. INPUT: Capture and visualize
            data = indata[:, 0] if indata.ndim > 1 else indata
            shift = len(data)
            if shift < self._scope_buffer_size:
                self._scope_buffer = np.roll(self._scope_buffer, -shift)
                self._scope_buffer[-shift:] = data
            else:
                self._scope_buffer = data[-self._scope_buffer_size:]
            
            if self._is_recording:
                self._recording_data.append(indata.copy())

            # 2. OUTPUT: Mix metronome click
            outdata.fill(0)
            with self._click_lock:
                if self._click_to_play is not None:
                    remaining = len(self._click_to_play) - self._click_ptr
                    to_copy = min(frames, remaining)
                    click_chunk = self._click_to_play[self._click_ptr : self._click_ptr + to_copy]
                    for c in range(outdata.shape[1]):
                        outdata[:to_copy, c] = click_chunk
                    self._click_ptr += to_copy
                    if self._click_ptr >= len(self._click_to_play):
                        self._click_to_play = None
                        self._click_ptr = 0

        # Try prioritized SRs for Duplex
        sr_to_try = []
        # Ensure unique integer sample rates
        candidates = [self._active_sr, 44100, 48000]
        try:
            output_info = sd.query_devices(self.output_device, 'output')
            candidates.insert(1, int(output_info['default_samplerate']))
        except: pass

        for s in candidates:
            if s is not None:
                sr_int = int(s)
                if sr_int not in sr_to_try: sr_to_try.append(sr_int)

        success = False
        last_error = ""
        for sr in sr_to_try:
            # IMPORTANT: Clean up from previous failed loop attempt
            if self._stream:
                try: self._stream.close()
                except: pass
                self._stream = None

            try:
                self._stream = sd.Stream(
                    samplerate=sr,
                    blocksize=1024, # Explicit blocksize improves WDM-KS stability
                    channels=(self._active_channels, 2), 
                    device=(self.input_device, self.output_device),
                    callback=duplex_callback
                )
                self._stream.start()
                self._active_sr = sr
                logger.info(f"Duplex Engine Active: {sr}Hz (Block: 1024)")
                success = True
                break
            except Exception as e:
                last_error = str(e)
                # Cleanup immediate to prevent driver hang
                if self._stream:
                    try: self._stream.close()
                    except: pass
                    self._stream = None
                logger.warning(f"Duplex attempt failed at {sr}Hz: {e}")
                time.sleep(0.1)
                continue
                
        if not success:
            self._is_recording = False
            # Re-enable monitor so app behaves normally after error
            self.start_monitoring() 
            hint = "\n\nTip: Cierra YouTube/Spotify u otras apps de audio si usas un driver WDM-KS/Exclusive."
            raise Exception(f"Error de Hardware [-9996]: El dispositivo está ocupado o no admite modo Duplex.\n{last_error}{hint}")

    def stop_recording(self) -> np.ndarray:
        """Safe shutdown of the Duplex stream."""
        if not self._is_recording: return np.array([], dtype=np.float32)
        self._is_recording = False
        with self._stream_lock:
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except: pass
                finally: self._stream = None
                time.sleep(0.1)
        if not self._recording_data: return np.array([], dtype=np.float32)
        audio = np.concatenate(self._recording_data, axis=0)
        return audio.flatten() if audio.ndim > 1 and audio.shape[1] == 1 else audio

    def save_wav(self, data: np.ndarray, filepath: str):
        """Save captured audio with original hardware fidelity."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        # 16-bit PCM conversion
        audio_pcm = (data * 32767).astype(np.int16) if data.dtype != np.int16 else data
        sr = self._active_sr if self._active_sr else SAMPLE_RATE
        ch = self._active_channels if self._active_channels else self._channels
        with wave.open(str(filepath), 'wb') as wf:
            wf.setnchannels(ch)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_pcm.tobytes())
        logger.info(f"Audio saved: {filepath.name} ({sr}Hz)")

    def load_wav(self, filepath: str) -> tuple[np.ndarray, int]:
        try:
            with wave.open(filepath, 'rb') as wf:
                params = wf.getparams()
                data = wf.readframes(params.nframes)
                audio_float = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
                if params.nchannels > 1:
                    audio_float = audio_float.reshape(-1, params.nchannels)[:, 0]
                return audio_float, params.framerate
        except Exception as e:
            logger.error(f"Failed to load WAV: {e}")
            raise

    def get_devices(self):
        return sd.query_devices()
