"""Global constants for VocalParam."""

# Audio settings
SAMPLE_RATE = 44100  # Hz
BIT_DEPTH = 16
CHANNELS = 1  # Mono
BUFFER_SIZE = 512  # samples (~11.6ms at 44.1kHz)
PRO_DEVICE_KEYWORDS = ["ASIO", "UMC", "Focusrite", "Yamaha", "Steinberg", "RME", "Audient"]
API_PRIORITY = {"ASIO": 100, "Windows WDM-KS": 80, "Windows WASAPI": 60, "MME": 20}
SUPPORTED_RATES = [44100, 48000, 88200, 96000]

# Default project settings
DEFAULT_BPM = 120
MORAS_PER_LINE = 7

# UI Colors (Dark Mode - Section 9.5)
COLORS = {
    "background": "#1E1E1E",
    "text_primary": "#E0E0E0",
    "text_secondary": "#A0A0A0",
    "accent_recording": "#FF5555",
    "success": "#50FA7B",
    "warning": "#FFB86C",
    "error": "#FF5555",
    # oto.ini parameter lines (Section RF-05.7)
    "offset": "#00FFFF",      # Cyan
    "consonant": "#00008B",   # Dark blue
    "cutoff": "#FF69B4",      # Pink/Magenta
    "preutter": "#FF0000",    # Red
    "overlap": "#00FF00",     # Green
}

# File extensions
RECLIST_EXTENSIONS = [".txt"]
AUDIO_EXTENSION = ".wav"
PROJECT_EXTENSION = ".vocalproj"

# Timing calculations
def ms_per_beat(bpm: int) -> float:
    """Calculate milliseconds per beat from BPM."""
    return 60000 / bpm

def expected_duration_ms(bpm: int, moras: int = MORAS_PER_LINE) -> float:
    """Calculate expected duration for a recording."""
    return ms_per_beat(bpm) * moras
