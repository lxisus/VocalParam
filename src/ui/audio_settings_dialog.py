"""Audio Settings Dialog - Hardware configuration.

Allows selection of Input/Output devices and Host API (ASIO/MME/etc).
Includes Real-time monitoring and sound test functionality.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QGroupBox, QMessageBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from core.audio_engine import AudioEngine
from utils.constants import COLORS
from utils.logger import get_logger

logger = get_logger(__name__)

class AudioSettingsDialog(QDialog):
    """Dialog for configuring audio hardware with smart linking and monitoring."""
    
    def __init__(self, audio_engine: AudioEngine, parent=None):
        super().__init__(parent)
        self.engine = audio_engine
        self.all_devices = []
        
        self.setWindowTitle("Configuración de Audio Pro")
        self.setMinimumWidth(550)
        
        self._setup_ui()
        self._load_all_devices()
        self._populate_inputs()
        
        # UI update timer for level meter
        self.level_timer = QTimer(self)
        self.level_timer.timeout.connect(self._update_level_meter)
        
        # Connect signals
        self.input_combo.currentIndexChanged.connect(self._on_input_changed)
        self.test_btn.clicked.connect(self._on_test_sound)
        
        # Select current devices
        self._select_current_on_load()
        
        # Start monitoring with current selection
        self.level_timer.start(50)
        self._restart_monitoring()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Style
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['background']}; color: {COLORS['text_primary']}; }}
            QLabel {{ color: {COLORS['text_primary']}; }}
            QGroupBox {{
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 20px;
                color: #A0A0A0;
                font-weight: bold;
                font-size: 11px;
            }}
            QComboBox {{
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                padding: 8px;
                color: {COLORS['text_primary']};
            }}
            QPushButton {{
                background-color: #3D3D3D;
                color: {COLORS['text_primary']};
                border-radius: 4px;
                padding: 10px;
            }}
            QPushButton:hover {{ background-color: #4D4D4D; }}
            QProgressBar {{
                border: 1px solid #3D3D3D;
                border-radius: 3px;
                background-color: #1A1A1A;
                height: 12px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['success']};
            }}
        """)

        # Input Group
        input_group = QGroupBox("CONFIGURACIÓN DE ENTRADA")
        input_layout = QVBoxLayout(input_group)
        
        self.input_combo = QComboBox()
        input_layout.addWidget(self.input_combo)
        
        # Level Meter Layout
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Nivel:"))
        self.level_meter = QProgressBar()
        self.level_meter.setRange(0, 100)
        self.level_meter.setValue(0)
        self.level_meter.setTextVisible(False)
        level_layout.addWidget(self.level_meter)
        input_layout.addLayout(level_layout)
        
        layout.addWidget(input_group)

        # Output Group
        output_group = QGroupBox("CONFIGURACIÓN DE SALIDA")
        output_layout = QVBoxLayout(output_group)
        
        out_select_layout = QHBoxLayout()
        self.output_combo = QComboBox()
        out_select_layout.addWidget(self.output_combo, 1)
        
        self.test_btn = QPushButton("🔊 Probar")
        self.test_btn.setFixedWidth(80)
        out_select_layout.addWidget(self.test_btn)
        output_layout.addLayout(out_select_layout)
        
        layout.addWidget(output_group)

        # Help
        self.help_lbl = QLabel("Seleccione dispositivos compatibles.")
        self.help_lbl.setStyleSheet(f"color: {COLORS['warning']}; font-size: 10px;")
        layout.addWidget(self.help_lbl)

        # Footer Buttons
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refrescar")
        self.refresh_btn.clicked.connect(self._refresh_all)
        
        self.ok_btn = QPushButton("Confirmar y Cerrar")
        self.ok_btn.setStyleSheet(f"background-color: {COLORS['success']}; color: black; font-weight: bold;")
        self.ok_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def _load_all_devices(self):
        self.all_devices = self.engine.get_device_list()

    def _populate_inputs(self):
        self.input_combo.blockSignals(True)
        self.input_combo.clear()
        
        sorted_devs = sorted(
            [d for d in self.all_devices if d['inputs'] > 0],
            key=lambda x: (not x['is_asio'], -x['priority'], x['api'], x['name'])
        )
        
        for dev in sorted_devs:
            prefix = "⚡ [ASIO]" if dev['is_asio'] else f"[{dev['api']}]"
            self.input_combo.addItem(f"{prefix} {dev['name']}", dev)
            
        self.input_combo.blockSignals(False)

    def _on_input_changed(self):
        current_input = self.input_combo.currentData()
        if not current_input: return

        # Restart monitoring for visual feedback
        self._restart_monitoring()

        # Update outputs list
        api_index = current_input['api_index']
        self.output_combo.clear()
        
        compatible_outputs = [
            d for d in self.all_devices 
            if d['outputs'] > 0 and d['api_index'] == api_index
        ]

        for dev in compatible_outputs:
            prefix = "⚡ [ASIO]" if dev['is_asio'] else f"[{dev['api']}]"
            self.output_combo.addItem(f"{prefix} {dev['name']}", dev)

        self.help_lbl.setText(f"✓ Driver {current_input['api']} activo.")
        
        # Auto-match names
        self._smart_select_output(current_input['name'])

    def _restart_monitoring(self):
        """Start monitoring on the currently selected input item."""
        input_data = self.input_combo.currentData()
        if input_data:
            self.engine.start_monitoring(input_data['index'])

    def _update_level_meter(self):
        """Get level from engine and update progress bar."""
        level = self.engine.get_input_level() # 0.0 to 1.0
        self.level_meter.setValue(int(level * 100))
        
        # Dynamic color for peak
        if level > 0.8:
            self.level_meter.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLORS['error']}; }}")
        elif level > 0.6:
            self.level_meter.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLORS['warning']}; }}")
        else:
            self.level_meter.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLORS['success']}; }}")

    def _on_test_sound(self):
        """Play test tone on current output choice."""
        out_data = self.output_combo.currentData()
        if out_data:
            self.engine.play_test_sound(out_data['index'])

    def _smart_select_output(self, target_name):
        terms = ["BEHRINGER", "REALTEK", "USB", "UMC", "FOCUSRITE"]
        target_upper = target_name.upper()
        for t in terms:
            if t in target_upper:
                for i in range(self.output_combo.count()):
                    if t in self.output_combo.itemData(i)['name'].upper():
                        self.output_combo.setCurrentIndex(i)
                        return

    def _select_current_on_load(self):
        if self.engine.input_device is not None:
            for i in range(self.input_combo.count()):
                if self.input_combo.itemData(i)['index'] == self.engine.input_device:
                    self.input_combo.setCurrentIndex(i)
                    break
        self._on_input_changed()
        if self.engine.output_device is not None:
            for i in range(self.output_combo.count()):
                if self.output_combo.itemData(i)['index'] == self.engine.output_device:
                    self.output_combo.setCurrentIndex(i)
                    break

    def _refresh_all(self):
        self._load_all_devices()
        self._populate_inputs()
        self._on_input_changed()

    def closeEvent(self, event):
        """Stop monitoring when dialog closes."""
        self.level_timer.stop()
        self.engine.stop_monitoring()
        super().closeEvent(event)

    def get_selected_devices(self):
        in_data = self.input_combo.currentData()
        out_data = self.output_combo.currentData()
        return (in_data['index'] if in_data else None, out_data['index'] if out_data else None)
