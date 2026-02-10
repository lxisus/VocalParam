"""Editor Controller - Manages interaction between UI and Data.

Handles synchronization between Visual Editor (Canvas) and Parameter Table.
Implements business logic for parameter validation and snapping.
"""

from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
import numpy as np
from typing import Optional

from core.models import OtoEntry
from core.dsp_analyzer import DSPAnalyzer
from ui.editor_widget import EditorWidget
from ui.parameter_table_widget import ParameterTableWidget
from utils.logger import get_logger

logger = get_logger(__name__)

class EditorController(QObject):
    """Controller for the OTO Editor module."""
    
    project_updated = pyqtSignal()
    
    def __init__(self, editor_widget: EditorWidget, table_widget: ParameterTableWidget):
        super().__init__()
        self.editor = editor_widget
        self.table = table_widget
        self.dsp = DSPAnalyzer()
        
        self.current_entry: Optional[OtoEntry] = None
        
        # Connect signals
        self.editor.marker_moved.connect(self._on_marker_moved)
        self.editor.marker_set_requested.connect(self._on_marker_set_requested)
        self.editor.search_bar.textChanged.connect(self._on_search_changed)
        
        self.table.parameter_changed.connect(self._on_table_changed)
        self.table.row_selected.connect(self._on_table_selection)
        
    def load_entry(self, entry: OtoEntry, audio_data: np.ndarray, sr: int):
        """Load a new entry and its audio into the editor."""
        self.current_entry = entry
        
        # 1. Update Table (Highlight row)
        self.table.update_entry(entry)
        
        # 2. Perform DSP Analysis
        # TODO: Run in background thread for performance
        spectrogram = self.dsp.compute_spectrogram(audio_data)
        times, rms = self.dsp.calculate_rms_envelope(audio_data)
        
        # 3. Update Editor (Canvas)
        self.editor.set_audio_data(audio_data, sr, spectrogram, rms)
        self.editor.set_entry(entry)
        
        logger.info(f"Loaded entry: {entry.alias}")

    @pyqtSlot(str, float)
    def _on_marker_moved(self, param_name: str, value_ms: float):
        """Handle marker movement from Canvas."""
        if not self.current_entry:
            return
            
        # Update model
        # Markers in Canvas are usually in ABSOLUTE ms from start of file.
        # OTO Parameters (except Offset) are RELATIVE to Offset (or absolute if positive cutoff).
        
        if param_name == 'left_blank' or param_name == 'offset':
            # Offset is absolute
            self.current_entry.offset = value_ms
        elif param_name == 'right_blank' or param_name == 'cutoff':
            if self.current_entry.cutoff < 0:
                # Value is negative from end
                duration_ms = self.editor.canvas.duration_s * 1000.0
                self.current_entry.cutoff = value_ms - duration_ms
            else:
                # Positive cutoff is relative to Offset
                self.current_entry.cutoff = value_ms - self.current_entry.offset
        elif param_name in ['overlap', 'preutter', 'fixed', 'consonant']:
            # Fixed/Consonant mapping
            actual_param = 'consonant' if param_name == 'fixed' else param_name
            # These are RELATIVE to Offset
            setattr(self.current_entry, actual_param, value_ms - self.current_entry.offset)
            
        # Update Table
        self.table.update_entry(self.current_entry)
        
        self.project_updated.emit()
        
        # TODO: Snapping logic here
        
    @pyqtSlot(OtoEntry)
    def _on_table_changed(self, entry: OtoEntry):
        """Handle value change from Table."""
        if entry is self.current_entry:
            self.editor.set_entry(entry)

    @pyqtSlot(OtoEntry)
    def _on_table_selection(self, entry: OtoEntry):
        """Handle row selection from Table."""
        # In a real app, this would load the correct audio file
        # For now, we assume the host (MainWindow) handles loading audio 
        # when a line is selected in Reclist, but here we might need to 
        # trigger a reload if selecting from the global table.
        pass

    @pyqtSlot(str)
    def _on_search_changed(self, text: str):
        """Filter table rows based on search text."""
        for i in range(self.table.rowCount()):
            alias = self.table.item(i, 0).text().lower()
            filename = self.table.item(i, 7).text().lower()
            match = text.lower() in alias or text.lower() in filename
            self.table.setRowHidden(i, not match)

    @pyqtSlot(str)
    def _on_marker_set_requested(self, param_name: str):
        """Set a marker at the current playhead or mouse position."""
        if not self.current_entry:
            return
            
        # For prototype: We'll use the center of the current view as the 'drop' target
        # Or if we had a selection/playhead, we'd use that.
        # Let's use the center of the X axis for now as a placeholder for 'active point'
        view_range = self.editor.canvas.plot_item.viewRange()
        center_s = (view_range[0][0] + view_range[0][1]) / 2.0
        center_ms = center_s * 1000.0
        
        self._on_marker_moved(param_name, center_ms)
        # Update canvas visual
        self.editor.canvas.set_markers(self.current_entry)
