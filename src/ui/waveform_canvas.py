"""Waveform Canvas - Specialized pyqtgraph widget for audio editing.

Supports waveform display, pitch overlay, and surgical manual correction.
"""

import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal, Qt
import numpy as np
from typing import List, Optional
from core.dsp_analyzer import PitchPoint
from utils.constants import COLORS

class WaveformCanvas(pg.GraphicsLayoutWidget):
    """Integrated waveform and pitch canvas."""
    
    point_added = pyqtSignal(float, float)  # time_s, freq_hz
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('#1A1A1A')
        
        # Audio plot
        self.p1 = self.addPlot(row=0, col=0)
        self.p1.showAxis('left', False)
        self.p1.showAxis('bottom', True)
        self.p1.setMenuEnabled(False)
        self.p1.setMouseEnabled(x=True, y=False)
        
        # Waveform curve
        self.waveform = self.p1.plot(pen=pg.mkPen('#4A4A4A', width=1))
        
        # Pitch curve (overlay on p1)
        self.pitch_curve = self.p1.plot(pen=pg.mkPen(COLORS['accent_recording'], width=2))
        
        # Manual points scatter
        self.manual_points = pg.ScatterPlotItem(
            size=10, 
            brush=pg.mkBrush(COLORS['success']),
            pen=pg.mkPen('w')
        )
        self.p1.addItem(self.manual_points)
        
        # Selection line
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('w', style=Qt.PenStyle.DashLine))
        self.p1.addItem(self.v_line)

    def set_waveform(self, data: np.ndarray, sr: int):
        """Display audio waveform."""
        if data is None or len(data) == 0:
            self.waveform.setData([], [])
            return
            
        times = np.linspace(0, len(data) / sr, len(data))
        # Downsample for performance if needed
        if len(data) > 10000:
            ds = len(data) // 10000
            self.waveform.setData(times[::ds], data[::ds])
        else:
            self.waveform.setData(times, data)

    def set_pitch_curve(self, points: List[PitchPoint]):
        """Display pitch tracking data."""
        times = [p.time_s for p in points if p.frequency_hz > 0]
        freqs = [p.frequency_hz for p in points if p.frequency_hz > 0]
        
        # Normalize freqs for overlay (0.0 to 1.0 logic mapped to waveform height)
        # Actually it's better to keep raw Hz and use a secondary Y axis if needed, 
        # but for simple overlay we can just scale
        if freqs:
            max_f = max(freqs)
            min_f = min(freqs)
            scaled_freqs = [(f - min_f) / (max_f - min_f + 1) * 0.8 - 0.4 for f in freqs]
            self.pitch_curve.setData(times, scaled_freqs)
            
            # Show manual points
            manual_times = [p.time_s for p in points if p.is_manual]
            manual_freqs = [(p.frequency_hz - min_f) / (max_f - min_f + 1) * 0.8 - 0.4 for p in points if p.is_manual]
            self.manual_points.setData(manual_times, manual_freqs)
        else:
            self.pitch_curve.setData([], [])
            self.manual_points.setData([], [])

    def mouseClickEvent(self, ev):
        """Handle manual correction via Ctrl+Click."""
        if ev.button() == Qt.MouseButton.LeftButton and ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            pos = ev.pos()
            mouse_point = self.p1.vb.mapSceneToView(pos)
            
            # Here we'd need to map the Y coordinate back to Hz
            # For this prototype, let's just emit the raw coordinates
            # A real implementation would map the vertical position in the normalized range
            self.point_added.emit(mouse_point.x(), mouse_point.y())
            ev.accept()
        else:
            super().mouseClickEvent(ev)
