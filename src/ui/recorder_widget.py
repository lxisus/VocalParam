"""Recorder Widget - Recording interface with metronome.

Visual and audio metronome for synchronized recording.
Based on Section 9.3 RecorderWidget specification.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QLineEdit, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
import time
import numpy as np

from core.models import PhoneticLine
from ui.waveform_scope import WaveformScope
from core.audio_engine import AudioEngine
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
    
    MIN_RECORDING_DURATION_MS = 4000
    COUNT_IN_BEATS = 3
    
    def __init__(self, audio_engine: AudioEngine, parent=None):
        super().__init__(parent)
        self.engine = audio_engine
        self._bpm = DEFAULT_BPM
        self._current_line: PhoneticLine = None
        self._current_mora = 0
        self._count_in_counter = 0 # Negative during count-in
        self._is_recording = False
        self._last_audio = None
        
        # Determine default save path
        project_root = Path(__file__).parent.parent.parent
        self._dest_path = project_root / "recordings" / "test_samples"
        self._dest_path.mkdir(parents=True, exist_ok=True)
        
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
            color: {COLORS['text_secondary']};
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
        
        # Path Destination Selector
        path_layout = QHBoxLayout()
        path_label = QLabel("Destino:")
        path_label.setFixedWidth(50)
        path_layout.addWidget(path_label)
        
        self.path_edit = QLineEdit(str(self._dest_path))
        self.path_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: #252525;
                color: {COLORS['text_primary']};
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                padding: 5px;
            }}
        """)
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("...")
        self.browse_btn.setFixedWidth(40)
        self.browse_btn.clicked.connect(self._on_browse_destination)
        self.browse_btn.setStyleSheet(self._button_style("#6272A4"))
        path_layout.addWidget(self.browse_btn)
        
        layout.addLayout(path_layout)
        
        # Mora boxes container
        mora_container = QHBoxLayout()
        mora_container.setSpacing(10)
        
        self.mora_boxes: list[MoraBox] = []
        for i in range(MORAS_PER_LINE):
            box = MoraBox(f"Mora {i+1}")
            self.mora_boxes.append(box)
            mora_container.addWidget(box)
        
        layout.addLayout(mora_container)
        
        # Oscilloscope / Waveform
        self.wave_scope = WaveformScope()
        self.wave_scope.setFixedHeight(120)
        layout.addWidget(self.wave_scope)
        
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
        
        self.rerecord_btn = QPushButton("Iniciar/Re-grabar (Espacio/R)")
        self.rerecord_btn.setShortcut("Space")
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
        
        # Listen Button (Extra controls)
        extra_layout = QHBoxLayout()
        self.listen_btn = QPushButton("▶ Escuchar / Listen")
        self.listen_btn.clicked.connect(self._on_listen_clicked)
        self.listen_btn.setStyleSheet(self._button_style("#BD93F9"))
        self.listen_btn.setEnabled(False)
        self.listen_btn.setMinimumWidth(200)
        extra_layout.addStretch()
        extra_layout.addWidget(self.listen_btn)
        extra_layout.addStretch()
        layout.addLayout(extra_layout)
        
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
        
        self.scope_timer = QTimer()
        self.scope_timer.timeout.connect(self._update_scope)
        # Slower updates for UI to prevent metronome jitter (trabado sound)
        self.progress_interval = 100 # ms
        self.scope_interval = 60 # ms
    
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
        self._count_in_counter = -self.COUNT_IN_BEATS # Start at -3
        self._current_mora = 0
        self._elapsed_ms = 0
        self._start_time = time.time()
        self._last_audio = None
        self.listen_btn.setEnabled(False)
        self._update_recording_status(True, "PREPARAR")
        
        # Calculate interval and duration
        ms_per_beat = int(60000 / self._bpm)
        self.tail_beats = 1
        
        # Total duration must cover count-in + segments + tail, AND satisfy min duration
        # Actually count-in is part of the recorded file, so it counts towards duration?
        # User said: "Grabación se inicia desde el segundo 1... tiempo muerto para 3 clicks"
        # So yes, count-in is recorded.
        
        notes_beats = len(self._current_line.segments) + self.tail_beats
        notes_duration = notes_beats * ms_per_beat
        countin_duration = self.COUNT_IN_BEATS * ms_per_beat
        
        # Ensure total duration is at least MIN_RECORDING_DURATION_MS
        calculated_total = countin_duration + notes_duration
        self._target_duration_ms = max(self.MIN_RECORDING_DURATION_MS, calculated_total)
        
        self.progress_bar.setMaximum(self._target_duration_ms)
        
        # Start persistent output stream for metronome FIRST
        self.engine.start_output_stream()
        
        # Start hardware recording
        try:
            self.engine.start_recording()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error de Audio", 
                               f"No se pudo iniciar la grabación:\n{str(e)}\n\n"
                               "Verifica tu configuración de audio en Proyecto > Configuración.")
            self._reset_state()
            self._is_recording = False
            self.engine.stop_output_stream()
            return

        # Start timers
        self.metronome_timer.start(ms_per_beat)
        self.progress_timer.start(self.progress_interval)
        self.scope_timer.start(self.scope_interval)
        
        # Play first count-in click immediately
        self._play_count_in()
        
        self.recording_started.emit()
        logger.info(f"Recording sequence started: {self._current_line.raw_text}")
    
    def _play_count_in(self):
        """Play count-in logic."""
        self.engine.play_click(countin=True)
        # Visual feedback for count-in
        count = abs(self._count_in_counter)
        if count > 0:
            self._update_recording_status(True, f"PREPARAR: {count}...")
    
    def _reset_state(self):
        """Reset recording state."""
        self._current_mora = 0
        self._count_in_counter = 0
        self._elapsed_ms = 0
        self.progress_bar.setValue(0)
        self.time_label.setText("0.0s / 0.0s")
        self.listen_btn.setEnabled(False)
        self._last_audio = None
        self.wave_scope.clear()
        
        for box in self.mora_boxes:
            box.set_active(False)
            
        self._update_recording_status(False)

    def _update_recording_status(self, is_recording: bool, text_override: str = None):
        """Update the recording title style."""
        if is_recording:
            color = COLORS['accent_recording']
            text = text_override if text_override else "GRABANDO..."
        else:
            color = COLORS['text_secondary']
            text = "GRABANDO"
            
        self.title_label.setText(text)
        self.title_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {color};
        """)
    
    def _on_metronome_tick(self):
        """Handle metronome tick."""
        # Handle Count-in phase
        if self._count_in_counter < 0:
            self._count_in_counter += 1
            if self._count_in_counter < 0:
                 self._play_count_in()
                 return
            else:
                 # Count-in finished, start actual recording metrics
                 self._update_recording_status(True, "GRABANDO...")
                 # Start normal loop below (fall through to index 0)
        
        # --- Normal Metronome Logic ---
        
        # Deactivate previous mora visually
        if self._current_mora > 0 and self._current_mora - 1 < len(self.mora_boxes):
             self.mora_boxes[self._current_mora - 1].set_active(False)
        
        # Check if we should stop (based on TIME, not just beats, to enforce min duration)
        # But we align stopping with beats to be rhythmic.
        # We stop if we are past the target duration.
        
        ms_per_beat = int(60000 / self._bpm)
        current_beat_time = (self._current_mora + self.COUNT_IN_BEATS) * ms_per_beat
        
        if self._elapsed_ms >= self._target_duration_ms:
            logger.info("Target duration reached, stopping.")
            self.stop_recording()
            return
            
        # Determine if we are in "mora" phase or "tail/padding" phase
        num_segments = len(self._current_line.segments) if self._current_line else 0
        
        if self._current_mora < num_segments:
             # Activate box
             if self._current_mora < len(self.mora_boxes):
                 self.mora_boxes[self._current_mora].set_active(True)
             # Play accent/normal click
             is_first = (self._current_mora == 0)
             self.engine.play_click(accent=is_first)
        else:
             # Tail/Padding phase
             self.engine.play_click(accent=False)
             
        self._current_mora += 1
    
    def _update_scope(self):
        """Update the scrolling waveform plot (DSP)."""
        data = self.engine.get_scope_data()
        self.wave_scope.update_data(data)
    
    def _update_progress(self):
        """Update progress bar and time display."""
        if not self._is_recording:
            return
        
        # Real-time sync (M5.2)
        elapsed_real = (time.time() - self._start_time) * 1000
        self._elapsed_ms = int(elapsed_real)
        self.progress_bar.setValue(self._elapsed_ms)
        
        elapsed_s = self._elapsed_ms / 1000
        total_s = self._target_duration_ms / 1000
        
        self.time_label.setText(f"{elapsed_s:.1f}s / {total_s:.1f}s")
    
    def _on_rerecord(self):
        """Handle re-record button."""
        self.stop_recording()
        self._reset_state()
        self.start_recording()
    
    def _on_accept(self):
        """Handle accept button."""
        # Fix 44-byte bug (M5.1): Don't stop if already stopped, just save what we have
        if self._is_recording:
            self.stop_recording()
        
        # Save audio if a line is selected and we have a path
        if self._current_line and self._last_audio is not None and len(self._last_audio) > 0:
             wav_name = f"{self._current_line.raw_text}.wav"
             save_file = Path(self.path_edit.text()) / wav_name
             try:
                 self.engine.save_wav(self._last_audio, str(save_file))
                 logger.info(f"Auto-saved recording to: {save_file}")
             except Exception as e:
                 logger.error(f"Failed to auto-save recording: {e}")

        # Return recorded audio
        self.recording_stopped.emit(self._last_audio)
    
    def _on_cancel(self):
        """Handle cancel button."""
        self.stop_recording()
        self._reset_state()
        self.recording_cancelled.emit()

    def _on_browse_destination(self):
        """Open dialog to select destination folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de destino", str(self._dest_path)
        )
        if folder:
            self._dest_path = Path(folder)
            self.path_edit.setText(folder)
            logger.info(f"Destination path changed to: {folder}")

    def _on_listen_clicked(self):
        """Play back the last recorded audio."""
        if self._last_audio is not None:
            self.engine.play_audio(self._last_audio)
        else:
            logger.warning("No audio to play")

    def stop_recording(self):
        """Stop recording."""
        self._is_recording = False
        self.metronome_timer.stop()
        self.progress_timer.stop()
        self.scope_timer.stop()
        
        # Stop hardware recording AND output stream
        self._last_audio = self.engine.stop_recording()
        self.engine.stop_output_stream()
        
        if self._last_audio is not None and len(self._last_audio) > 0:
            self.listen_btn.setEnabled(True)
        
        self._update_recording_status(False)
        logger.info("Recording stopped")
