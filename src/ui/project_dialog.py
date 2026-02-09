"""Project Dialog - New project configuration.

Allows setting project name, reclist, output directory, and BPM.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QSpinBox,
    QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from utils.constants import COLORS, DEFAULT_BPM
from utils.logger import get_logger

logger = get_logger(__name__)

class ProjectDialog(QDialog):
    """Dialog for creating a new VocalParam project."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Proyecto VocalParam")
        self.setMinimumWidth(500)
        
        self.result_data = None
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['background']}; color: {COLORS['text_primary']}; }}
            QLabel {{ color: {COLORS['text_primary']}; font-weight: bold; }}
            QLineEdit {{
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                padding: 8px;
                color: {COLORS['text_primary']};
            }}
            QSpinBox {{
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
        """)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Project Name
        self.name_edit = QLineEdit("MiNuevoVoicebank")
        form_layout.addRow("Nombre del Proyecto:", self.name_edit)
        
        # Reclist Selection
        reclist_layout = QHBoxLayout()
        self.reclist_edit = QLineEdit()
        self.reclist_edit.setPlaceholderText("Seleccionar archivo .txt...")
        self.btn_browse_reclist = QPushButton("...")
        self.btn_browse_reclist.setFixedWidth(40)
        self.btn_browse_reclist.clicked.connect(self._on_browse_reclist)
        reclist_layout.addWidget(self.reclist_edit)
        reclist_layout.addWidget(self.btn_browse_reclist)
        form_layout.addRow("Archivo Reclist:", reclist_layout)
        
        # Output Directory
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Carpeta donde se guardarán los audios...")
        self.btn_browse_output = QPushButton("...")
        self.btn_browse_output.setFixedWidth(40)
        self.btn_browse_output.clicked.connect(self._on_browse_output)
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.btn_browse_output)
        form_layout.addRow("Directorio de Salida:", output_layout)
        
        # Project File Path
        save_layout = QHBoxLayout()
        self.save_edit = QLineEdit()
        self.save_edit.setPlaceholderText("Dónde guardar el archivo .vocalproj...")
        self.btn_browse_save = QPushButton("...")
        self.btn_browse_save.setFixedWidth(40)
        self.btn_browse_save.clicked.connect(self._on_browse_save)
        save_layout.addWidget(self.save_edit)
        save_layout.addWidget(self.btn_browse_save)
        form_layout.addRow("Guardar Proyecto como:", save_layout)
        
        # BPM
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(40, 300)
        self.bpm_spin.setValue(DEFAULT_BPM)
        form_layout.addRow("BPM Base:", self.bpm_spin)
        
        layout.addLayout(form_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton("Crear Proyecto")
        self.btn_ok.setStyleSheet(f"background-color: {COLORS['success']}; color: black; font-weight: bold;")
        self.btn_ok.clicked.connect(self._on_accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

    def _on_browse_reclist(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Reclist", "", "Text Files (*.txt);;All Files (*)")
        if path:
            self.reclist_edit.setText(path)
            
    def _on_browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Audios")
        if path:
            self.output_edit.setText(path)
            
    def _on_browse_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Proyecto", "", "VocalParam Project (*.vocalproj)")
        if path:
            self.save_edit.setText(path)

    def _on_accept(self):
        # Validation
        name = self.name_edit.text().strip()
        reclist = self.reclist_edit.text().strip()
        output = self.output_edit.text().strip()
        save_path = self.save_edit.text().strip()
        
        if not name or not reclist or not output or not save_path:
            QMessageBox.warning(self, "Validación", "Todos los campos son obligatorios.")
            return
            
        if not Path(reclist).exists():
            QMessageBox.warning(self, "Validación", "El archivo reclist no existe.")
            return
            
        if not Path(output).is_dir():
            QMessageBox.warning(self, "Validación", "El directorio de salida no es válido.")
            return

        self.result_data = {
            "name": name,
            "reclist": reclist,
            "output": output,
            "save_path": save_path,
            "bpm": self.bpm_spin.value()
        }
        self.accept()

    def get_data(self):
        return self.result_data
