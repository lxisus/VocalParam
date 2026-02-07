"""WaveformScope - Real-time audio visualization widget.

Provides a high-performance scrolling waveform display with dynamic
level coloring and smooth rendering using PyQtGraph/OpenGL.
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
    - Circular buffer for O(1) updates
    - Downsampling for rendering performance
    - Dynamic color gradient based on signal amplitude
    """
    
    def __init__(self, buffer_size=1000, parent=None):
        super().__init__(parent)
        self._buffer_size = buffer_size
        self._data = np.zeros(buffer_size)
        self._ptr = 0
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Configure PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1A1A1A')
        self.plot_widget.setYRange(-1, 1)
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.getPlotItem().hideButtons()
        
        # Add a center line for reference
        self.plot_widget.addLine(y=0, pen=pg.mkPen('#333333', width=1))
        
        # Create the curve item with gradient fill
        # Note: PyQtGraph doesn't support complex gradients easily on a single curve
        # We use a solid recognizable color for the "Professional" look (e.g. Cyan/Green)
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(COLORS['success'], width=2),
            fillLevel=0, 
            brush=(0, 255, 0, 30) # Semi-transparent green fill
        )
        
        layout.addWidget(self.plot_widget)
        
    def update_data(self, audio_chunk: np.ndarray):
        """
        Process incoming audio data and update the display.
        
        Args:
            audio_chunk: Raw float32 audio data from the engine
        """
        if len(audio_chunk) == 0:
            return
            
        # Calculate RMS or Peak for the chunk to downsample for visualization
        # Visualizing 44100 points/sec is wasteful. We just need the envelope.
        
        # Taking a max peak every N samples works well for visual impact
        step = max(1, len(audio_chunk) // 10) # 10 points per chunk update
        
        # Simple rolling update
        peaks = []
        for i in range(0, len(audio_chunk), step):
            segment = audio_chunk[i:i+step]
            if len(segment) > 0:
                # Dynamic Boost (M5.3 Refined): Use 5.0x for visualization
                peaks.append(np.max(np.abs(segment)) * 5.0)
                
        if not peaks:
            return
            
        peak_array = np.array(peaks)
        
        # Roll buffer
        shift = len(peak_array)
        self._data = np.roll(self._data, -shift)
        self._data[-shift:] = peak_array
        
        # Dynamic coloring logic (optional optimization: update pen color based on max peak)
        max_val = np.max(peak_array)
        if max_val > 0.95:
            self.curve.setPen(pg.mkPen(COLORS['error'], width=2))
        elif max_val < 0.05:
            self.curve.setPen(pg.mkPen(COLORS['text_secondary'], width=2))
        else:
            self.curve.setPen(pg.mkPen(COLORS['success'], width=2))
            
        # Update curve
        # We mirror the data for a "symmetric" waveform look if desired, 
        # but standard scrolling graph is usually just +amplitude
        self.curve.setData(self._data)
        
    def clear(self):
        """Reset the waveform to silence."""
        self._data.fill(0)
        self.curve.setData(self._data)
