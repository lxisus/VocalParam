"""Editor Widget - Visual parameter editor wrapper.

Holds the WaveformCanvas and navigation controls.
"""

from typing import Optional
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSplitter
)
from PyQt6.QtCore import pyqtSignal

from core.models import OtoEntry
from utils.constants import COLORS
from utils.logger import get_logger
from ui.waveform_canvas import WaveformCanvas

logger = get_logger(__name__)

class EditorWidget(QWidget):
    """Visual editor container."""
    
    # Re-emit signals from canvas or nav
    marker_moved = pyqtSignal(str, float)
    play_requested = pyqtSignal()
    next_requested = pyqtSignal()
    prev_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_entry: Optional[OtoEntry] = None
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title/Header
        self.label_alias = QLabel("No Alias Selected")
        self.label_alias.setStyleSheet(f"""
            font-size: 18px; 
            font-weight: bold; 
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(self.label_alias)
        
        # Canvas
        self.canvas = WaveformCanvas()
        self.canvas.marker_moved.connect(self.marker_moved.emit)
        layout.addWidget(self.canvas, stretch=1)
        
        # Navigation
        nav_layout = QHBoxLayout()
        
        self.btn_play = QPushButton("▶ Play (Space)")
        self.btn_play.setShortcut("Space")
        self.btn_play.clicked.connect(self.play_requested.emit)
        nav_layout.addWidget(self.btn_play)
        
        self.btn_prev = QPushButton("◀ Prev")
        self.btn_prev.clicked.connect(self.prev_requested.emit)
        nav_layout.addWidget(self.btn_prev)
        
        self.btn_next = QPushButton("Next ▶")
        self.btn_next.clicked.connect(self.next_requested.emit)
        nav_layout.addWidget(self.btn_next)
        
        layout.addLayout(nav_layout)
        
    def set_entry(self, entry: OtoEntry):
        """Update view with new entry."""
        self._current_entry = entry
        if entry:
            self.label_alias.setText(f"Alias: {entry.alias}")
            self.canvas.set_markers(entry)
        else:
            self.label_alias.setText("No Selection")

    def set_audio_data(self, audio: np.ndarray, sr: int, spectrogram: np.ndarray = None, rms: np.ndarray = None):
        """Pass audio data to canvas."""
        self.canvas.set_audio_data(audio, sr, spectrogram, rms)
