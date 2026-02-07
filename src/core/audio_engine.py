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
        
        # Pre-generate click sound (1000Hz sine for 50ms)
        self._click_sample = self._generate_click(1000, 0.05, 0.2)
        self._click_accent = self._generate_click(1500, 0.05, 0.3)
        self._click_countin = self._generate_click(800, 0.05, 0.2) # Lower pitch for count-in
        self._test_tone = self._generate_click(440, 0.5, 0.3)  # A4 note for test
        
        # Oscilloscope buffer (last 2048 samples)
        self._scope_buffer_size = 2048
        self._scope_buffer = np.zeros(self._scope_buffer_size, dtype=np.float32)
        
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
            "sample_rate": self._active_sr,
            "channels": self._active_channels
        }
        
        self.db.set_setting("audio_config", config)
        logger.info("Audio config saved to database")

    def load_config(self):
        """Load hardware selection by name to handle index changes."""
        config = self.db.get_setting("audio_config")
        if not config:
            return
            
        try:
            in_name = config.get("input_device_name")
            out_name = config.get("output_device_name")
            self._active_sr = config.get("sample_rate", SAMPLE_RATE)
            self._active_channels = config.get("channels", CHANNELS)
            
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
        """Generate a click sample."""
        t = np.linspace(0, duration, int(self._sample_rate * duration), False)
        # Sine wave + fade out to avoid clicks
        click = np.sin(freq * t * 2 * np.pi) * volume
        fade_out = np.linspace(1, 0, len(click))
        return (click * fade_out).astype(np.float32)

    def start_output_stream(self):
        """Start a persistent output stream for low-latency metronome."""
        if self._output_stream:
            return
            
        try:
            self._output_stream = sd.OutputStream(
                samplerate=self._active_sr,
                device=self.output_device,
                channels=1 # Mono click
            )
            self._output_stream.start()
        except Exception as e:
            logger.error(f"Failed to start output stream: {e}")

    def stop_output_stream(self):
        """Stop the persistent output stream."""
        if self._output_stream:
            try:
                self._output_stream.stop()
                self._output_stream.close()
            except Exception as e:
                logger.error(f"Error closing output stream: {e}")
            finally:
                self._output_stream = None

    def play_click(self, accent: bool = False, countin: bool = False):
        """Play the metronome click sound."""
        if countin:
            sample = self._click_countin
        else:
            sample = self._click_accent if accent else self._click_sample
            
        # Use persistent stream if available for glitch-free audio
        if self._output_stream and self._output_stream.active:
            try:
                # Pad to buffer size if needed, or write directly
                # sd.OutputStream.write expects C-contiguous array
                self._output_stream.write(sample)
            except Exception as e:
                logger.error(f"Stream write error: {e}")
        else:
            # Fallback for preview/test
            try:
                sd.play(sample, self._active_sr, device=self.output_device)
            except Exception as e:
                logger.error(f"Error playing click: {e}")

    def play_audio(self, data: np.ndarray):
        """Play back a given audio buffer."""
        if data is None or len(data) == 0:
            logger.warning("Attempted to play empty audio buffer")
            return
            
        try:
            sd.play(data, self._active_sr, device=self.output_device)
        except Exception as e:
            logger.error(f"Error playing audio: {e}")

    def stop_audio(self):
        """Stop any current playback."""
        try:
            sd.stop()
        except Exception as e:
            logger.error(f"Error stopping audio: {e}")

    def play_test_sound(self, device_id: Optional[int] = None):
        """Play a short test tone to verify output."""
    def stop_monitoring(self):
        """Stop input level monitoring."""
        self._is_monitoring = False
        if self._monitoring_stream:
            self._monitoring_stream.stop()
            self._monitoring_stream.close()
            self._monitoring_stream = None
            time.sleep(0.1)  # Give HW time to release
        self._current_level = 0.0

    def get_input_level(self) -> float:
        """Return the current input level (0.0 to 1.0)."""
        return self._current_level

    def _check_device_support(self, device_id: int, stream_type: str = 'input') -> bool:
        """Verify if the device supports current settings (Sample Rate/Channels)."""
        try:
            if stream_type == 'input':
                sd.check_input_settings(device=device_id, samplerate=self._sample_rate, channels=self._channels)
            else:
                sd.check_output_settings(device=device_id, samplerate=self._sample_rate, channels=self._channels)
            return True
        except Exception as e:
            logger.warning(f"Device {device_id} check failed for {stream_type}: {e}")
            return False

    def start_monitoring(self, device_id: Optional[int] = None):
        """Start monitoring input levels with aggressive compatibility scanning."""
        self.stop_monitoring()
        target_device = device_id if device_id is not None else self.input_device
        
        if target_device is None: return

        def callback(indata, frames, time, status):
            if status: return
            
            # Update scope buffer
            data = indata[:, 0] if indata.ndim > 1 else indata
            shift = len(data)
            if shift < self._scope_buffer_size:
                self._scope_buffer = np.roll(self._scope_buffer, -shift)
                self._scope_buffer[-shift:] = data
            else:
                self._scope_buffer = data[-self._scope_buffer_size:]

            # Calculate RMS level
            rms = np.sqrt(np.mean(indata**2))
            self._current_level = float(np.clip(rms * 5.0, 0, 1))

        success, sr, ch = self._scan_and_open_stream(target_device, callback)
        
        if success:
            self._monitoring_stream = self._stream
            self._stream = None # Move to monitoring slot
            self._is_monitoring = True
            self._active_sr = sr # Save for recording
            self._active_channels = ch
        else:
            self._current_level = 0.0

    def get_scope_data(self) -> np.ndarray:
        """Return the current oscilloscope buffer."""
        return self._scope_buffer

    def _scan_and_open_stream(self, device_id: int, callback: Callable) -> tuple[bool, int, int]:
        """Core logic to find a working SR/Channel combo for a device."""
        try:
            info = sd.query_devices(device_id)
            native_sr = int(info['default_samplerate'])
            max_in = info['max_input_channels']
        except Exception as e:
            logger.error(f"Device error {device_id}: {e}")
            return False, 0, 0

        sample_rates = sorted(list(set([native_sr, self._sample_rate, 48000, 44100])), reverse=True)
        channel_configs = [self._channels]
        if max_in >= 2: channel_configs.append(2)

        for sr in sample_rates:
            for ch in channel_configs:
                try:
                    stream = sd.InputStream(
                        samplerate=sr,
                        channels=ch,
                        device=device_id,
                        callback=callback
                    )
                    stream.start()
                    self._stream = stream
                    logger.info(f"Stream Open: Dev {device_id} | {sr}Hz | {ch}ch")
                    return True, sr, ch
                except Exception:
                    continue
        
        return False, 0, 0

    def _regenerate_clicks(self):
        """Regenerate click samples at the specific active sample rate."""
        sr = self._active_sr if self._active_sr else self._sample_rate
        self._click_sample = self._generate_click_at_sr(1000, 0.05, 0.2, sr)
        self._click_accent = self._generate_click_at_sr(1500, 0.05, 0.3, sr)
        logger.debug(f"Clicks regenerated for {sr}Hz")

    def _generate_click_at_sr(self, freq: float, duration: float, volume: float, sr: int) -> np.ndarray:
        """Generate a click sample at specified sample rate."""
        t = np.linspace(0, duration, int(sr * duration), False)
        click = np.sin(freq * t * 2 * np.pi) * volume
        fade_out = np.linspace(1, 0, len(click))
        return (click * fade_out).astype(np.float32)

    def play_test_sound(self, device_id: Optional[int] = None):
        """Play test tone with fallback and safer error catching."""
        target_device = device_id if device_id is not None else self.output_device
        if target_device is None: return
        
        try:
            # First try default
            sd.play(self._test_tone, self._sample_rate, device=target_device)
        except Exception:
            try:
                # Try common fallback SR
                sd.play(self._test_tone, 48000, device=target_device)
            except Exception as e:
                logger.error(f"Fatal Output Error: Dispositivo {target_device} no responde. {e}")

    def start_recording(self):
        """Start capturing audio into memory using pre-validated settings."""
        if self._is_recording:
            return
        
        # Safety: ensure any level monitoring is off
        self.stop_monitoring()
        
        self._recording_data = []
        self._is_recording = True
        
        def callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio status: {status}")
            
            # Update scope buffer during recording too
            data = indata[:, 0] if indata.ndim > 1 else indata
            shift = len(data)
            if shift < self._scope_buffer_size:
                self._scope_buffer = np.roll(self._scope_buffer, -shift)
                self._scope_buffer[-shift:] = data
            
            if self._is_recording:
                self._recording_data.append(indata.copy())

        if self.input_device is None:
            raise Exception("No se ha seleccionado un dispositivo de entrada.")

        # Try to open with the settings that worked for monitoring
        try:
            self._stream = sd.InputStream(
                samplerate=self._active_sr,
                channels=self._active_channels,
                device=self.input_device,
                callback=callback
            )
            self._stream.start()
            logger.info(f"Recording: Dev {self.input_device} @ {self._active_sr}Hz ({self._active_channels}ch)")
        except Exception:
            # Full scan fallback if previous settings fail now
            success, sr, ch = self._scan_and_open_stream(self.input_device, callback)
            if not success:
                self._is_recording = False
                raise Exception(f"El dispositivo {self.input_device} no responde.")
            self._active_sr = sr
            self._active_channels = ch

    def stop_recording(self) -> np.ndarray:
        """Stop capturing and return the audio data."""
        if not self._is_recording:
            return np.array([], dtype=np.float32)
        
        self._is_recording = False
        
        # Safe stream closing
        with self._stream_lock:
            if self._stream:
                self._is_closing = True
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.error(f"Error closing stream: {e}")
                finally:
                    self._stream = None
                    self._is_closing = False
                time.sleep(0.1)  # Give HW time to release on Windows
            
        if not self._recording_data:
            return np.array([], dtype=np.float32)

        # Concatenate all chunks
        audio = np.concatenate(self._recording_data, axis=0)
        
        # Flatten for mono (N, 1) -> (N,)
        if audio.ndim > 1 and audio.shape[1] == 1:
            audio = audio.flatten()
            
        logger.info(f"Recording stopped, captured {len(audio)} samples")
        return audio

    def save_wav(self, data: np.ndarray, filepath: str):
        """Save numpy array as a WAV file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure 16-bit PCM for UTAU compatibility
        if data.dtype != np.int16:
            # Convert float32 to int16
            data = (data * 32767).astype(np.int16)
            
        # Validate parameters - Fallback to defaults if not set
        sr = self._active_sr if self._active_sr else SAMPLE_RATE
        ch = self._active_channels if self._active_channels else self._channels
            
        with wave.open(str(filepath), 'wb') as wf:
            wf.setnchannels(ch)
            wf.setsampwidth(2)  # 2 bytes for 16-bit
            wf.setframerate(sr)
            wf.writeframes(data.tobytes())
            
        logger.info(f"Saved audio: {filepath} | {sr}Hz | {ch}ch")

    def get_devices(self):
        """Return list of available audio devices."""
        return sd.query_devices()
