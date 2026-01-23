"""Recorder Widget - Recording interface with metronome.

Visual and audio metronome for synchronized recording.
Based on Section 9.3 RecorderWidget specification.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from core.models import PhoneticLine
from utils.constants import COLORS, DEFAULT_BPM, MORAS_PER_LINE
from utils.logger import get_logger

logger = get_logger(__name__)


class MoraBox(QWidget):
    """Single mora indicator box."""
    
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text = text
        self._active = False
        self.setMinimumSize(60, 60)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.label = QLabel(self.text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(self.label)
        
        self._update_style()
    
    def set_active(self, active: bool):
        """Set whether this mora is currently active."""
        self._active = active
        self._update_style()
    
    def _update_style(self):
        """Update visual style based on state."""
        if self._active:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {COLORS['accent_recording']};
                    border: 2px solid {COLORS['accent_recording']};
                    border-radius: 8px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: #2D2D2D;
                    border: 2px solid #3D3D3D;
                    border-radius: 8px;
                }}
            """)


class RecorderWidget(QWidget):
    """Recording interface with visual metronome.
    
    Displays 7 mora boxes that highlight in sequence during recording.
    
    Signals:
        recording_started: Emitted when recording begins
        recording_stopped: Emitted when recording ends (with audio data)
        recording_cancelled: Emitted when recording is cancelled
    """
    
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(object)  # audio data
    recording_cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bpm = DEFAULT_BPM
        self._current_line: PhoneticLine = None
        self._current_mora = 0
        self._is_recording = False
        
        self._setup_ui()
        self._setup_timers()
    
    def _setup_ui(self):
        """Setup widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        self.title_label = QLabel("GRABANDO")
        self.title_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {COLORS['accent_recording']};
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Line text
        self.line_label = QLabel("Seleccione una línea para grabar")
        self.line_label.setStyleSheet(f"""
            font-size: 18px;
            color: {COLORS['text_secondary']};
        """)
        self.line_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.line_label)
        
        # Instruction
        instruction = QLabel("Pronuncia cada sílaba al ritmo del metrónomo:")
        instruction.setStyleSheet(f"color: {COLORS['text_secondary']};")
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instruction)
        
        # Mora boxes container
        mora_container = QHBoxLayout()
        mora_container.setSpacing(10)
        
        self.mora_boxes: list[MoraBox] = []
        for i in range(MORAS_PER_LINE):
            box = MoraBox(f"Mora {i+1}")
            self.mora_boxes.append(box)
            mora_container.addWidget(box)
        
        layout.addLayout(mora_container)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #3D3D3D;
                border-radius: 5px;
                text-align: center;
                background-color: #252525;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent_recording']};
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Time label
        self.time_label = QLabel("0.0s / 0.0s")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.time_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        self.rerecord_btn = QPushButton("Re-grabar (R)")
        self.rerecord_btn.setShortcut("R")
        self.rerecord_btn.clicked.connect(self._on_rerecord)
        self.rerecord_btn.setStyleSheet(self._button_style("#FFB86C"))
        button_layout.addWidget(self.rerecord_btn)
        
        self.accept_btn = QPushButton("Aceptar (Enter)")
        self.accept_btn.setShortcut("Return")
        self.accept_btn.clicked.connect(self._on_accept)
        self.accept_btn.setStyleSheet(self._button_style(COLORS['success']))
        button_layout.addWidget(self.accept_btn)
        
        self.cancel_btn = QPushButton("Cancelar (Esc)")
        self.cancel_btn.setShortcut("Escape")
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.setStyleSheet(self._button_style(COLORS['error']))
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Spacer
        layout.addStretch()
    
    def _button_style(self, color: str) -> str:
        """Generate button style with given accent color."""
        return f"""
            QPushButton {{
                background-color: #3D3D3D;
                color: {COLORS['text_primary']};
                border: 2px solid {color};
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {color};
                color: #1E1E1E;
            }}
            QPushButton:pressed {{
                background-color: #2D2D2D;
            }}
        """
    
    def _setup_timers(self):
        """Setup timing system."""
        self.metronome_timer = QTimer()
        self.metronome_timer.timeout.connect(self._on_metronome_tick)
        
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
    
    def set_line(self, line: PhoneticLine):
        """Set the current line to record.
        
        Args:
            line: PhoneticLine to record
        """
        self._current_line = line
        self.line_label.setText(line.raw_text)
        
        # Update mora boxes with segment text
        for i, box in enumerate(self.mora_boxes):
            if i < len(line.segments):
                box.label.setText(line.segments[i].upper())
                box.setVisible(True)
            else:
                box.setVisible(False)
        
        self._reset_state()
    
    def set_bpm(self, bpm: int):
        """Set BPM for metronome.
        
        Args:
            bpm: Beats per minute
        """
        self._bpm = bpm
    
    def start_recording(self):
        """Start recording with metronome."""
        if not self._current_line:
            logger.warning("No line selected for recording")
            return
        
        self._is_recording = True
        self._current_mora = 0
        self._elapsed_ms = 0
        
        # Calculate interval
        ms_per_beat = int(60000 / self._bpm)
        total_duration_ms = ms_per_beat * len(self._current_line.segments)
        
        self.progress_bar.setMaximum(total_duration_ms)
        
        # Start timers
        self.metronome_timer.start(ms_per_beat)
        self.progress_timer.start(50)  # Update every 50ms
        
        self.recording_started.emit()
        logger.info(f"Recording started: {self._current_line.raw_text}")
    
    def stop_recording(self):
        """Stop recording."""
        self._is_recording = False
        self.metronome_timer.stop()
        self.progress_timer.stop()
        
        logger.info("Recording stopped")
    
    def _reset_state(self):
        """Reset recording state."""
        self._current_mora = 0
        self._elapsed_ms = 0
        self.progress_bar.setValue(0)
        self.time_label.setText("0.0s / 0.0s")
        
        for box in self.mora_boxes:
            box.set_active(False)
    
    def _on_metronome_tick(self):
        """Handle metronome tick."""
        # Deactivate current mora
        if self._current_mora < len(self.mora_boxes):
            self.mora_boxes[self._current_mora].set_active(False)
        
        self._current_mora += 1
        
        # Check if done
        if self._current_mora >= len(self._current_line.segments):
            self.stop_recording()
            return
        
        # Activate next mora
        if self._current_mora < len(self.mora_boxes):
            self.mora_boxes[self._current_mora].set_active(True)
        
        # TODO: Play click sound via AudioEngine
    
    def _update_progress(self):
        """Update progress bar and time display."""
        if not self._is_recording:
            return
        
        self._elapsed_ms += 50
        self.progress_bar.setValue(self._elapsed_ms)
        
        elapsed_s = self._elapsed_ms / 1000
        total_s = self._current_line.expected_duration_ms / 1000
        self.time_label.setText(f"{elapsed_s:.1f}s / {total_s:.1f}s")
    
    def _on_rerecord(self):
        """Handle re-record button."""
        self.stop_recording()
        self._reset_state()
        self.start_recording()
    
    def _on_accept(self):
        """Handle accept button."""
        self.stop_recording()
        # TODO: Return recorded audio
        self.recording_stopped.emit(None)
    
    def _on_cancel(self):
        """Handle cancel button."""
        self.stop_recording()
        self._reset_state()
        self.recording_cancelled.emit()
