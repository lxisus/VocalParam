"""WaveformScope - Real-time audio visualization widget.

Provides a high-performance scrolling waveform display with professional
rendering quality matching the editor's WaveformCanvas.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
from utils.constants import COLORS, ms_per_beat

class WaveformScope(QWidget):
    """
    Professional scrolling waveform visualization.
    
    Features:
    - Dual-channel waveform rendering (positive/negative)
    - Min-max envelope for accurate representation
    - Gradient fill and anti-aliased lines
    - Circular buffer for O(1) updates (scrolling mode)
    - Fixed timeline mode for linear recording/playback
    - Synchronized playhead (Timeline Guide)
    - Integrated Timeline Ruler
    - Mora illumination regions
    """
    
    def __init__(self, buffer_size=2000, parent=None):
        super().__init__(parent)
        self._buffer_size = buffer_size
        self._mode = 'scrolling'  # 'scrolling' or 'fixed'
        self._duration_ms = 0
        
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
        
        # Configure Axis (Ruler)
        self.plot_widget.showAxis('bottom')
        self.plot_widget.hideAxis('left')
        bottom_axis = self.plot_widget.getAxis('bottom')
        bottom_axis.setPen(pg.mkPen(COLORS['text_secondary']))
        bottom_axis.setLabel('Tiempo (s)')
        
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
        
        # Timeline Guide (Playhead)
        self.playhead = pg.InfiniteLine(
            pos=0, 
            angle=90, 
            pen=pg.mkPen('#FFFFFF', width=2),
            movable=False
        )
        self.plot_widget.addItem(self.playhead)
        self.playhead.hide()
        
        # Mora Highlight (Moving Spotlight)
        self.active_region = pg.LinearRegionItem(
            [0, 0], 
            movable=False, 
            brush=pg.mkBrush(255, 85, 85, 80),
            pen=pg.mkPen(None)
        )
        # Remove lines and hover effects that cause trails
        for line in self.active_region.lines:
            line.setPen(pg.mkPen(None))
            line.setHoverPen(pg.mkPen(None))
        self.plot_widget.addItem(self.active_region)
        self.active_region.hide()
        
        # Static Background Regions (Container)
        self.static_regions = []
        
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
        
    def set_mode(self, mode: str, duration_ms: float = 0):
        """
        Switch between 'scrolling' and 'fixed' modes.
        
        Args:
            mode: 'scrolling' (oscilloscope) or 'fixed' (linear timeline)
            duration_ms: Total duration for 'fixed' mode
        """
        self._mode = mode
        self._duration_ms = duration_ms
        
        if mode == 'fixed':
            self.plot_widget.setXRange(0, duration_ms / 1000)
            self.playhead.show()
            self.playhead.setPos(0)
            self.active_region.show()
            # Hide curves and clear their data to prevent any residual 'trail'
            self.curve_max.setData([], [])
            self.curve_min.setData([], [])
            self.curve_max.hide()
            self.curve_min.hide()
        else:
            self.plot_widget.setXRange(0, self._buffer_size)
            self.playhead.hide()
            self.active_region.hide()
            self._data_max.fill(0)
            self._data_min.fill(0)
            self.curve_max.setData(self._x_data, self._data_max) 
            self.curve_min.setData(self._x_data, self._data_min)
            self.curve_max.show()
            self.curve_min.show()
            self._clear_regions()

    def set_playhead(self, time_ms: float):
        """Update the Timeline Guide position and Mora spotlight."""
        if self._mode == 'fixed':
            time_s = time_ms / 1000
            self.playhead.setPos(time_s)
            
            # Find which static region we are in and move the spotlight
            for region_data in self.static_regions:
                start, end = region_data['range']
                if start <= time_s <= end:
                    # Only update if the spotlight actually needs to move
                    current_start, current_end = self.active_region.getRegion()
                    if current_start != start or current_end != end:
                        self.active_region.setRegion([start, end])
                    break

    def setup_mora_regions(self, bpm: int, num_moras: int, count_in_beats: int):
        """Create visual static regions and prepare spotlight."""
        self._clear_regions()
        beat_ms = ms_per_beat(bpm)
        
        # Total beats to show
        total_beats = count_in_beats + num_moras
        for i in range(total_beats):
            start = (i * beat_ms) / 1000
            end = (i + 1) * beat_ms / 1000
            
            # Use a single static background item (efficiency)
            # Instead of LinearRegionItem for static ones, we use simpler items if possible
            # but for now, we'll use non-movable LinearRegions with very low alpha
            brush = pg.mkBrush(150, 150, 150, 15) if i < count_in_beats else pg.mkBrush(255, 255, 255, 10)
            
            region = pg.LinearRegionItem(
                [start, end], 
                movable=False, 
                brush=brush,
                pen=pg.mkPen(None)
            )
            for line in region.lines:
                line.setPen(pg.mkPen(None))
                
            self.plot_widget.addItem(region)
            self.static_regions.append({'item': region, 'range': (start, end)})
            
        # Reset spotlight
        self.active_region.setRegion([0, beat_ms/1000 if total_beats > 0 else 0])

    def _clear_regions(self):
        """Remove all static mora regions from the plot."""
        for rd in self.static_regions:
            try:
                self.plot_widget.removeItem(rd['item'])
            except: pass
        self.static_regions = []
        self.active_region.setRegion([0, 0])
        self.active_region.hide()

    def set_waveform(self, audio_data: np.ndarray, sr: int):
        """Set a static waveform for fixed duration mode (playback)."""
        if len(audio_data) == 0:
            return
            
        # Compute envelope for visualization
        # We'll use a fixed number of samples to represent the waveform
        num_points = 2000
        step = max(1, len(audio_data) // num_points)
        
        max_vals = []
        min_vals = []
        x_vals = []
        
        for i in range(0, len(audio_data), step):
            segment = audio_data[i:i+step]
            if len(segment) > 0:
                max_vals.append(np.max(segment))
                min_vals.append(np.min(segment))
                x_vals.append(i / sr)
        
        # Apply boost
        max_vals = np.clip(np.array(max_vals) * 2.0, -1.2, 1.2)
        min_vals = np.clip(np.array(min_vals) * 2.0, -1.2, 1.2)
        x_vals = np.array(x_vals)
        
        self.curve_max.setData(x_vals, max_vals)
        self.curve_min.setData(x_vals, min_vals)
        self.curve_max.show()
        self.curve_min.show()

    def clear(self):
        """Reset the waveform to silence."""
        self._data_max.fill(0)
        self._data_min.fill(0)
        self.curve_max.setData(self._x_data, self._data_max)
        self.curve_min.setData(self._x_data, self._data_min)
        if self._mode == 'fixed':
            self.playhead.setPos(0)
            self._clear_regions()
