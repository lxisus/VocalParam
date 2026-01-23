"""Reclist Widget - List of phonetic lines to record.

Displays all lines from the loaded reclist with status indicators.
Based on Section 9.2 ReclistWidget specification.
"""

from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from core.reclist_parser import ReclistParser, ReclistParseError
from core.models import PhoneticLine, RecordingStatus
from utils.constants import COLORS
from utils.logger import get_logger

logger = get_logger(__name__)


class ReclistWidget(QWidget):
    """Widget displaying list of reclist lines with status.
    
    Signals:
        line_selected: Emitted when a line is selected (index, PhoneticLine)
    """
    
    line_selected = pyqtSignal(int, object)  # index, PhoneticLine
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser = ReclistParser()
        self._lines: List[PhoneticLine] = []
        self._statuses: dict[int, RecordingStatus] = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header
        header = QLabel("RECLIST")
        header.setStyleSheet(f"""
            font-weight: bold;
            font-size: 14px;
            color: {COLORS['text_primary']};
            padding: 5px;
        """)
        layout.addWidget(header)
        
        # Line count label
        self.count_label = QLabel("0 líneas")
        self.count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.count_label)
        
        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: #252525;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #3D3D3D;
            }}
            QListWidget::item:selected {{
                background-color: #3D3D3D;
            }}
            QListWidget::item:hover {{
                background-color: #353535;
            }}
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Cargar...")
        self.load_btn.setStyleSheet(self._button_style())
        self.load_btn.clicked.connect(self._on_load_clicked)
        button_layout.addWidget(self.load_btn)
        
        layout.addLayout(button_layout)
    
    def _button_style(self) -> str:
        """Return button stylesheet."""
        return f"""
            QPushButton {{
                background-color: #3D3D3D;
                color: {COLORS['text_primary']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: #4D4D4D;
            }}
            QPushButton:pressed {{
                background-color: #2D2D2D;
            }}
        """
    
    def load_reclist(self, filepath: str) -> bool:
        """Load and parse a reclist file.
        
        Args:
            filepath: Path to reclist .txt file
            
        Returns:
            True if loaded successfully
        """
        try:
            self._lines = self.parser.parse_file(filepath)
            self._statuses = {line.index: RecordingStatus.PENDING for line in self._lines}
            self._populate_list()
            logger.info(f"Loaded reclist with {len(self._lines)} lines")
            return True
        except ReclistParseError as e:
            logger.error(f"Failed to parse reclist: {e}")
            return False
        except FileNotFoundError as e:
            logger.error(f"Reclist file not found: {e}")
            return False
    
    def _populate_list(self):
        """Populate list widget with loaded lines."""
        self.list_widget.clear()
        
        for line in self._lines:
            status = self._statuses.get(line.index, RecordingStatus.PENDING)
            item = QListWidgetItem(self._format_line(line, status))
            item.setData(Qt.ItemDataRole.UserRole, line.index)
            
            # Color based on status
            if status == RecordingStatus.RECORDED:
                item.setForeground(QBrush(QColor(COLORS['success'])))
            elif status == RecordingStatus.VALIDATED:
                item.setForeground(QBrush(QColor("#50FA7B")))  # Brighter green
            else:
                item.setForeground(QBrush(QColor(COLORS['text_secondary'])))
            
            self.list_widget.addItem(item)
        
        self.count_label.setText(f"{len(self._lines)} líneas")
    
    def _format_line(self, line: PhoneticLine, status: RecordingStatus) -> str:
        """Format line for display."""
        status_icon = {
            RecordingStatus.PENDING: "☐",
            RecordingStatus.RECORDED: "☑",
            RecordingStatus.VALIDATED: "✓"
        }.get(status, "☐")
        
        return f"{status_icon} {line.index:03d} {line.raw_text}"
    
    def set_line_status(self, index: int, status: RecordingStatus):
        """Update status of a specific line.
        
        Args:
            index: Line index
            status: New status
        """
        self._statuses[index] = status
        self._populate_list()  # Refresh display
    
    def get_line(self, index: int) -> Optional[PhoneticLine]:
        """Get PhoneticLine by index."""
        for line in self._lines:
            if line.index == index:
                return line
        return None
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle item click."""
        index = item.data(Qt.ItemDataRole.UserRole)
        line = self.get_line(index)
        if line:
            self.line_selected.emit(index, line)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle item double click - start recording."""
        # TODO: Trigger recording mode
        pass
    
    def _on_load_clicked(self):
        """Handle load button click."""
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Cargar Reclist", "",
            "Archivos de texto (*.txt);;Todos los archivos (*)"
        )
        if filepath:
            self.load_reclist(filepath)
