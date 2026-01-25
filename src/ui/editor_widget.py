"""Editor Widget - Visual parameter editor for oto.ini.

Displays waveform with draggable parameter lines.
Based on Section 9.4 EditorWidget specification and RF-05 requirements.
"""

from typing import List, Optional
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QDoubleSpinBox, QGroupBox,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.models import OtoEntry, PhoneticLine
from utils.constants import COLORS
from utils.logger import get_logger

logger = get_logger(__name__)


class EditorWidget(QWidget):
    """Visual editor for oto.ini parameters.
    
    Displays waveform with color-coded draggable parameter lines:
    - Offset: Cyan (#00FFFF)
    - Consonant: Dark Blue (#00008B)
    - Cutoff: Pink/Magenta (#FF69B4)
    - Preutter: Red (#FF0000)
    - Overlap: Green (#00FF00)
    
    Signals:
        parameters_changed: Emitted when any parameter is modified
    """
    
    parameters_changed = pyqtSignal(object)  # OtoEntry
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_entry: Optional[OtoEntry] = None
        self._current_line: Optional[PhoneticLine] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        self.title_label = QLabel("EDITOR")
        self.title_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(self.title_label)
        
        # Alias label
        self.alias_label = QLabel("Alias: [ninguno]")
        self.alias_label.setStyleSheet(f"""
            font-size: 16px;
            color: {COLORS['text_secondary']};
        """)
        layout.addWidget(self.alias_label)
        
        # Waveform Canvas
        from ui.waveform_canvas import WaveformCanvas
        from controllers.dsp_controller import DSPController
        
        self.dsp_controller = DSPController()
        self.canvas = WaveformCanvas()
        self.canvas.setMinimumHeight(250)
        
        # Connect signals
        self.dsp_controller.analysis_completed.connect(self._on_analysis_done)
        self.dsp_controller.correction_updated.connect(self.canvas.set_pitch_curve)
        self.canvas.point_added.connect(self._on_manual_point)
        
        layout.addWidget(self.canvas)
        
        # Parameter controls
        params_group = QGroupBox("Parámetros")
        params_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text_primary']};
                font-weight: bold;
                border: 1px solid #3D3D3D;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        params_layout = QVBoxLayout(params_group)
        
        # Create spinbox for each parameter
        self.param_spinboxes = {}
        param_info = [
            ("offset", "Offset (ms)", COLORS['offset'], 0, 10000),
            ("consonant", "Consonant (ms)", COLORS['consonant'], 0, 500),
            ("cutoff", "Cutoff (ms)", COLORS['cutoff'], -5000, 0),
            ("preutter", "Preutter (ms)", COLORS['preutter'], 0, 500),
            ("overlap", "Overlap (ms)", COLORS['overlap'], 0, 200),
        ]
        
        for param_name, label_text, color, min_val, max_val in param_info:
            row = QHBoxLayout()
            
            # Color indicator
            color_box = QLabel()
            color_box.setFixedSize(20, 20)
            color_box.setStyleSheet(f"""
                background-color: {color};
                border-radius: 4px;
            """)
            row.addWidget(color_box)
            
            # Label
            label = QLabel(label_text)
            label.setStyleSheet(f"color: {COLORS['text_primary']};")
            label.setMinimumWidth(120)
            row.addWidget(label)
            
            # Spinbox
            spinbox = QDoubleSpinBox()
            spinbox.setRange(min_val, max_val)
            spinbox.setDecimals(1)
            spinbox.setSingleStep(1.0)
            spinbox.setStyleSheet(f"""
                QDoubleSpinBox {{
                    background-color: #2D2D2D;
                    color: {COLORS['text_primary']};
                    border: 1px solid #3D3D3D;
                    border-radius: 4px;
                    padding: 4px;
                }}
            """)
            spinbox.valueChanged.connect(
                lambda val, p=param_name: self._on_param_changed(p, val)
            )
            self.param_spinboxes[param_name] = spinbox
            row.addWidget(spinbox)
            
            # Adjust buttons
            minus_btn = QPushButton("←")
            minus_btn.setFixedSize(30, 30)
            minus_btn.clicked.connect(lambda _, s=spinbox: s.stepDown())
            row.addWidget(minus_btn)
            
            plus_btn = QPushButton("→")
            plus_btn.setFixedSize(30, 30)
            plus_btn.clicked.connect(lambda _, s=spinbox: s.stepUp())
            row.addWidget(plus_btn)
            
            row.addStretch()
            params_layout.addLayout(row)
        
        layout.addWidget(params_group)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(20)
        
        self.play_btn = QPushButton("Reproducir (Space)")
        self.play_btn.setShortcut("Space")
        self.play_btn.clicked.connect(self._on_play)
        self.play_btn.setStyleSheet(self._button_style(COLORS['success']))
        nav_layout.addWidget(self.play_btn)
        
        self.prev_btn = QPushButton("← Anterior")
        self.prev_btn.setShortcut("Left")
        self.prev_btn.clicked.connect(self._on_previous)
        self.prev_btn.setStyleSheet(self._button_style(COLORS['text_secondary']))
        nav_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Siguiente →")
        self.next_btn.setShortcut("Right")
        self.next_btn.clicked.connect(self._on_next)
        self.next_btn.setStyleSheet(self._button_style(COLORS['text_secondary']))
        nav_layout.addWidget(self.next_btn)
        
        layout.addLayout(nav_layout)
        
        layout.addStretch()
    
    def _button_style(self, color: str) -> str:
        """Generate button style."""
        return f"""
            QPushButton {{
                background-color: #3D3D3D;
                color: {COLORS['text_primary']};
                border: 2px solid {color};
                border-radius: 8px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {color};
                color: #1E1E1E;
            }}
        """
    
    def set_entry(self, entry: OtoEntry):
        """Set the current oto entry to edit.
        
        Args:
            entry: OtoEntry to edit
        """
        self._current_entry = entry
        self.alias_label.setText(f"Alias: {entry.alias}")
        
        # Update spinboxes
        self.param_spinboxes["offset"].setValue(entry.offset)
        self.param_spinboxes["consonant"].setValue(entry.consonant)
        self.param_spinboxes["cutoff"].setValue(entry.cutoff)
        self.param_spinboxes["preutter"].setValue(entry.preutter)
        self.param_spinboxes["overlap"].setValue(entry.overlap)
        
        logger.info(f"Editing entry: {entry.alias}")
    
    def _on_param_changed(self, param_name: str, value: float):
        """Handle parameter value change."""
        if not self._current_entry:
            return
        
        setattr(self._current_entry, param_name, value)
        self.parameters_changed.emit(self._current_entry)
        logger.debug(f"Parameter {param_name} changed to {value}")
    
    def set_audio_data(self, data: np.ndarray, sr: int):
        """Load audio data into the editor and start analysis."""
        self.canvas.set_waveform(data, sr)
        self.dsp_controller.analyze_audio(data)

    def _on_analysis_done(self, result):
        """Handle completion of DSP analysis."""
        self.canvas.set_pitch_curve(result.pitch_curve)
        logger.info("DSP analysis results displayed")

    def _on_manual_point(self, time_s: float, rel_pos: float):
        """Handle manual pitch point addition."""
        # For prototype: map rel_pos (-0.4 to 0.4) back to a reasonable freq range
        # C2 (65Hz) to C6 (1046Hz)
        fmin = 65.0
        fmax = 1046.0
        normalized = (rel_pos + 0.4) / 0.8
        freq = fmin + normalized * (fmax - fmin)
        self.dsp_controller.add_manual_point(time_s, freq)

    def _on_play(self):
        """Handle play button."""
        logger.info("Play audio preview")
        # TODO: Implement audio playback
    
    def _on_previous(self):
        """Handle previous button."""
        logger.info("Previous entry")
        # TODO: Navigate to previous entry
    
    def _on_next(self):
        """Handle next button."""
        logger.info("Next entry")
        # TODO: Navigate to next entry
