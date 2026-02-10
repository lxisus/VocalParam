"""WaveformScope - Real-time audio visualization widget.

Provides a high-performance scrolling waveform display with professional
rendering quality matching the editor's WaveformCanvas.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
from utils.constants import COLORS

class WaveformScope(QWidget):
    """
    Professional scrolling waveform visualization.
    
    Features:
    - Dual-channel waveform rendering (positive/negative)
    - Min-max envelope for accurate representation
    - Gradient fill and anti-aliased lines
    - Circular buffer for O(1) updates
    - Performance-optimized for real-time display
    """
    
    def __init__(self, buffer_size=2000, parent=None):
        super().__init__(parent)
        self._buffer_size = buffer_size
        
        # Dual buffers for min-max envelope rendering
        self._data_max = np.zeros(buffer_size)
        self._data_min = np.zeros(buffer_size)
        self._ptr = 0
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Configure PlotWidget with professional styling
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1A1A1A')
        self.plot_widget.setYRange(-1.2, 1.2)
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.getPlotItem().hideButtons()
        
        # Add reference lines
        self.plot_widget.addLine(y=0, pen=pg.mkPen('#333333', width=1))  # Center line
        self.plot_widget.addLine(y=1.0, pen=pg.mkPen('#222222', width=1, style=Qt.PenStyle.DashLine))  # +1 reference
        self.plot_widget.addLine(y=-1.0, pen=pg.mkPen('#222222', width=1, style=Qt.PenStyle.DashLine))  # -1 reference
        
        # Create waveform curves with gradient fill
        # Positive envelope (top half)
        self.curve_max = self.plot_widget.plot(
            pen=pg.mkPen(COLORS['success'], width=2),
            fillLevel=0,
            brush=pg.mkBrush(0, 255, 100, 40)  # Semi-transparent green fill
        )
        
        # Negative envelope (bottom half)
        self.curve_min = self.plot_widget.plot(
            pen=pg.mkPen(COLORS['success'], width=2),
            fillLevel=0,
            brush=pg.mkBrush(0, 255, 100, 40)
        )
        
        # X-axis data (time indices)
        self._x_data = np.arange(self._buffer_size)
        
        layout.addWidget(self.plot_widget)
        
    def update_data(self, audio_chunk: np.ndarray):
        """
        Process incoming audio data and update the display with high-quality rendering.
        
        Uses min-max envelope extraction to preserve waveform detail while
        downsampling for visualization performance.
        
        Args:
            audio_chunk: Raw float32 audio data from the engine
        """
        if len(audio_chunk) == 0:
            return
        
        # Calculate how many visual points we need from this chunk
        # We want smooth scrolling, so we process in smaller segments
        samples_per_point = max(1, len(audio_chunk) // 20)  # ~20 points per chunk
        
        max_vals = []
        min_vals = []
        
        # Extract min-max envelope for each segment
        for i in range(0, len(audio_chunk), samples_per_point):
            segment = audio_chunk[i:i + samples_per_point]
            if len(segment) > 0:
                # Get actual min and max to preserve waveform shape
                max_vals.append(np.max(segment))
                min_vals.append(np.min(segment))
        
        if not max_vals:
            return
        
        max_array = np.array(max_vals)
        min_array = np.array(min_vals)
        
        # Apply dynamic boost for better visibility (but not too aggressive)
        boost_factor = 3.0
        max_array = np.clip(max_array * boost_factor, -1.2, 1.2)
        min_array = np.clip(min_array * boost_factor, -1.2, 1.2)
        
        # Roll buffers to the left (scrolling effect)
        shift = len(max_array)
        self._data_max = np.roll(self._data_max, -shift)
        self._data_min = np.roll(self._data_min, -shift)
        
        # Insert new data at the end
        self._data_max[-shift:] = max_array
        self._data_min[-shift:] = min_array
        
        # Dynamic coloring based on signal level
        max_level = np.max(np.abs(max_array))
        
        if max_level > 1.0:  # Clipping warning
            pen_color = COLORS['error']
            brush_color = (255, 50, 50, 60)
        elif max_level < 0.05:  # Very quiet
            pen_color = COLORS['text_secondary']
            brush_color = (100, 100, 100, 30)
        else:  # Normal level
            pen_color = COLORS['success']
            brush_color = (0, 255, 100, 40)
        
        # Update curves with new data
        self.curve_max.setData(
            self._x_data, 
            self._data_max,
            pen=pg.mkPen(pen_color, width=2),
            fillLevel=0,
            brush=pg.mkBrush(*brush_color)
        )
        
        self.curve_min.setData(
            self._x_data, 
            self._data_min,
            pen=pg.mkPen(pen_color, width=2),
            fillLevel=0,
            brush=pg.mkBrush(*brush_color)
        )
        
    def clear(self):
        """Reset the waveform to silence."""
        self._data_max.fill(0)
        self._data_min.fill(0)
        self.curve_max.setData(self._x_data, self._data_max)
        self.curve_min.setData(self._x_data, self._data_min)
