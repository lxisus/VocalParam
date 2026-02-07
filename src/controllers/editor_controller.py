"""Editor Controller - Manages interaction between UI and Data.

Handles synchronization between Visual Editor (Canvas) and Parameter Table.
Implements business logic for parameter validation and snapping.
"""

from PyQt6.QtCore import QObject, pyqtSlot
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
    
    def __init__(self, editor_widget: EditorWidget, table_widget: ParameterTableWidget):
        super().__init__()
        self.editor = editor_widget
        self.table = table_widget
        self.dsp = DSPAnalyzer()
        
        self.current_entry: Optional[OtoEntry] = None
        
        # Connect signals
        self.editor.marker_moved.connect(self._on_marker_moved)
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
        # Handle Cutoff special logic (negative from end vs positive)
        # For now, just direct mapping, but 'cutoff' marker in canvas handles visual pos.
        # If user drags cutoff, value_ms is absolute position.
        # We need to convert back to relative if it was negative? 
        # The plan says "Gestión de Cutoff Negativo".
        # If original was negative, we might want to keep it negative relative to end?
        # Or just store what the user visually set.
        
        if param_name == 'cutoff' and self.current_entry.cutoff < 0:
            # Convert absolute ms back to negative relative to end
            # This requires knowing total duration. 
            # Controller should know duration or get it from editor.
            duration_ms = self.editor.canvas.duration_s * 1000.0
            new_cutoff = value_ms - duration_ms
            self.current_entry.cutoff = new_cutoff
        else:
            setattr(self.current_entry, param_name, value_ms)
            
        # Update Table
        self.table.update_entry(self.current_entry)
        
        # TODO: Snapping logic here
        
    @pyqtSlot(OtoEntry)
    def _on_table_changed(self, entry: OtoEntry):
        """Handle value change from Table."""
        if entry is self.current_entry:
            self.editor.set_entry(entry)

    @pyqtSlot(OtoEntry)
    def _on_table_selection(self, entry: OtoEntry):
        """Handle row selection from Table."""
        # TODO: Load audio for this entry
        # This requires access to the audio file manager.
        # For now, we just signal that an entry was selected.
        pass
