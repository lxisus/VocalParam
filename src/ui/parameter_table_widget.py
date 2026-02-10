"""Parameter Table Widget - Editor for OTO parameters.

Displays and edits numerical values for the current recording's OTO entries.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QAbstractItemView, QStyledItemDelegate
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from core.models import OtoEntry
from utils.constants import COLORS

class FloatDelegate(QStyledItemDelegate):
    """Delegate to handle float formatting and validation."""
    
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        return editor

    def setEditorData(self, editor, index):
        super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        super().setModelData(editor, model, index)

class ParameterTableWidget(QTableWidget):
    """Table widget for OTO parameters."""
    
    parameter_changed = pyqtSignal(OtoEntry)  # Emitted when a value changes
    row_selected = pyqtSignal(OtoEntry)       # Emitted when a row is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: List[OtoEntry] = []
        self._is_updating = False
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Configure table structure."""
        columns = [
            "Alias", 
            "Left Blank", 
            "Overlap", 
            "Pre-Utterance", 
            "Fixed", 
            "Right Blank",
            "Comment",
            "Filename"
        ]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        # Behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        
        # Header resize
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) 
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Comment stretches
        
        # Item changed signal
        self.itemChanged.connect(self._on_item_changed)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Styling
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: #1E1E1E;
                color: {COLORS['text_primary']};
                gridline-color: #3D3D3D;
                selection-background-color: {COLORS['accent_primary']};
                border: none;
            }}
            QHeaderView::section {{
                background-color: #2D2D2D;
                color: {COLORS['text_secondary']};
                padding: 4px;
                border: 1px solid #3D3D3D;
            }}
        """)

    def set_entries(self, entries: List[OtoEntry]):
        """Populate the table with OTO entries."""
        self._is_updating = True
        self.setRowCount(0)
        self._entries = entries
        
        self.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            # Alias
            self.setItem(row, 0, QTableWidgetItem(entry.alias))
            
            # Params (Formatted 123.4)
            self._set_float_item(row, 1, entry.offset)
            self._set_float_item(row, 2, entry.overlap)
            self._set_float_item(row, 3, entry.preutter)
            self._set_float_item(row, 4, entry.consonant)
            self._set_float_item(row, 5, entry.cutoff)
            
            # Comment
            self.setItem(row, 6, QTableWidgetItem(entry.comment))
            
            # Filename (Read-only)
            fn_item = QTableWidgetItem(entry.filename)
            fn_item.setFlags(fn_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            fn_item.setForeground(QColor(COLORS['text_secondary']))
            self.setItem(row, 7, fn_item)
            
        self._is_updating = False

    def _set_float_item(self, row: int, col: int, value: float):
        """Helper to set float item."""
        item = QTableWidgetItem(f"{value:.1f}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setItem(row, col, item)

    def _on_item_changed(self, item: QTableWidgetItem):
        """Handle manual edits in the table."""
        if self._is_updating:
            return
            
        row = item.row()
        col = item.column()
        entry = self._entries[row]
        
        # Column 0: Alias
        if col == 0:
            entry.alias = item.text()
            self.parameter_changed.emit(entry)
            
        # Columns 1-5 are parameters
        elif 1 <= col <= 5:
            try:
                new_val = float(item.text())
                
                # Update model
                if col == 1: entry.offset = new_val
                elif col == 2: entry.overlap = new_val
                elif col == 3: entry.preutter = new_val
                elif col == 4: entry.consonant = new_val
                elif col == 5: entry.cutoff = new_val
                
                self.parameter_changed.emit(entry)
                
            except ValueError:
                # Revert if invalid
                self.update_entry(entry)
        
        # Column 6: Comment
        elif col == 6:
            entry.comment = item.text()
            self.parameter_changed.emit(entry)

    def _on_selection_changed(self):
        """Emit signal when user selects a row."""
        rows = self.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            if row < len(self._entries):
                self.row_selected.emit(self._entries[row])

    def update_entry(self, entry: OtoEntry):
        """Update or add a single entry in the table."""
        try:
            row = self._entries.index(entry)
        except ValueError:
            # If not in the list, add it
            row = self.rowCount()
            self.insertRow(row)
            self._entries.append(entry)
            
            # Initial setup for new row (Alias and Filename)
            self._is_updating = True
            self.setItem(row, 0, QTableWidgetItem(entry.alias))
            self.setItem(row, 6, QTableWidgetItem(entry.comment))
            
            fn_item = QTableWidgetItem(entry.filename)
            fn_item.setFlags(fn_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            fn_item.setForeground(QColor(COLORS['text_secondary']))
            self.setItem(row, 7, fn_item)
            self._is_updating = False

        # Update params
        self._is_updating = True
        self._set_float_item(row, 1, entry.offset)
        self._set_float_item(row, 2, entry.overlap)
        self._set_float_item(row, 3, entry.preutter)
        self._set_float_item(row, 4, entry.consonant)
        self._set_float_item(row, 5, entry.cutoff)
        self._is_updating = False
