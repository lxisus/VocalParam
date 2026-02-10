"""Waveform Canvas - Multi-layer audio visualizer.

Supports:
- Spectrogram (Heatmap)
- Waveform Overlay
- RMS Envelope
- Interactive OTO Markers
"""

import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal, Qt
import numpy as np
from typing import List, Dict

from core.models import OtoEntry
from utils.constants import COLORS

class WaveformCanvas(pg.GraphicsLayoutWidget):
    """Surgical audio editor with spectrogram and OTO markers."""
    
    marker_moved = pyqtSignal(str, float)  # param_name, new_value_ms
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('#1A1A1A')
        
        # Main Plot
        self.plot_item = self.addPlot(row=0, col=0)
        self.plot_item.showAxis('left', False)
        self.plot_item.showAxis('bottom', True)
        self.plot_item.setMouseEnabled(x=True, y=False)
        self.plot_item.hideButtons()
        
        # 1. Spectrogram Layer (Background)
        self.img_item = pg.ImageItem()
        self.plot_item.addItem(self.img_item)
        
        # Colormap for spectrogram (Viridis-like)
        pos = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        color = np.array([
            [0, 0, 0, 255],       # Black
            [30, 0, 60, 255],     # Dark Purple
            [120, 0, 120, 255],   # Purple
            [255, 100, 0, 255],   # Orange
            [255, 255, 0, 255]    # Yellow
        ], dtype=np.ubyte)
        cmap = pg.ColorMap(pos, color)
        self.img_item.setLookupTable(cmap.getLookupTable())
        
        # 2. Waveform Layer (Overlay)
        self.waveform_curve = self.plot_item.plot(
            pen=pg.mkPen(color=(255, 255, 255, 100), width=1)
        )
        
        # 3. RMS Envelope (Overlay)
        self.rms_curve = self.plot_item.plot(
            pen=pg.mkPen(color=(255, 215, 0, 150), width=2)
        )
        
        # 4. OTO Markers
        self.markers: Dict[str, pg.InfiniteLine] = {}
        marker_config = {
            'offset': ("#858585", 'LeftBlank'),
            'overlap': ("#1FFF00", 'Overlap'),
            'preutter': ("#FF0000", 'Preutter'),
            'consonant': ("#00C8FF", 'Consonant'),
            'cutoff': ("#858585", 'RightBlank')
        }
        
        for name, (color, label) in marker_config.items():
            line = pg.InfiniteLine(
                pos=0, 
                angle=90, 
                movable=True, 
                pen=pg.mkPen(color, width=2, style=Qt.PenStyle.SolidLine),
                hoverPen=pg.mkPen(color, width=3),
                label=label,
                labelOpts={'color': color, 'position': 0.9, 'rotateAxis': [1, 0]}
            )
            line.sigPositionChanged.connect(
                lambda p, n=name: self._on_marker_drag(n, p)
            )
            self.plot_item.addItem(line)
            self.markers[name] = line

        self.sr = 44100
        self.duration_s = 0.0
        self._prev_preutter_pos = 0.0
        self._is_updating_markers = False
        
        # 5. Root Indicator (Red Triangle)
        self.root_indicator = pg.ScatterPlotItem(
            size=15, 
            brush=pg.mkBrush(255, 0, 0),
            pen=pg.mkPen(None),
            symbol='t'  # Inverted triangle
        )
        self.plot_item.addItem(self.root_indicator)

    def set_audio_data(self, audio: np.ndarray, sr: int, spectrogram: np.ndarray = None, rms: np.ndarray = None):
        """Update visualization data."""
        self.sr = sr
        self.duration_s = len(audio) / sr
        
        # Spectrogram
        if spectrogram is not None:
            # Transpose: Time x Freq
            self.img_item.setImage(spectrogram.T, autoLevels=True)
            # Scale image to match time (x) and freq bins (y)
            # We map 0..duration_s on X
            tr = pg.QtGui.QTransform()
            tr.scale(self.duration_s / spectrogram.shape[1], 1)
            self.img_item.setTransform(tr)
        
        # Waveform
        times = np.linspace(0, self.duration_s, len(audio))
        # Downsample for performance (max 10k points)
        step = max(1, len(audio) // 10000)
        # Normalize waveform to fit over spectrogram (e.g., 0 to 100 vertical range?)
        # Actually spectrogram Y is freq bins. ImageItem fills defined rect.
        # We need to scale waveform Y to overlay nicely.
        # Let's assume standardized view range. 0..100? or 0..FreqBins?
        # Spectrogram shape[0] is frequency bins (1025 for n_fft=2048).
        max_y = spectrogram.shape[0] if spectrogram is not None else 1.0
        
        # Center waveform at mid-height
        norm_audio = audio / np.max(np.abs(audio) + 1e-6)  # -1..1
        scaled_audio = (norm_audio * (max_y / 4)) + (max_y / 2)
        
        self.waveform_curve.setData(times[::step], scaled_audio[::step])
        
        # RMS Envelope
        if rms is not None:
             # RMS is usually small, scale it
            norm_rms = rms / np.max(rms + 1e-6)
            scaled_rms = norm_rms * (max_y / 2)
            self.rms_curve.setData(np.linspace(0, self.duration_s, len(rms)), scaled_rms)

        # Reset view
        self.plot_item.setXRange(0, self.duration_s)
        self.plot_item.setYRange(0, max_y)

    def set_markers(self, entry: OtoEntry):
        """Position markers based on OTO entry."""
        if not entry:
            return
            
        # BLOCK SIGNALS: Prevent recursive loops between Canvas -> Controller -> Table -> Canvas
        self._is_updating_markers = True
        
        try:
            m = self.markers
            # Convert ms to seconds
            base_offset = entry.offset / 1000.0
            
            m['offset'].setPos(base_offset)
            m['overlap'].setPos(base_offset + entry.overlap / 1000.0)
            
            m['preutter'].setPos(base_offset + entry.preutter / 1000.0)
            self._prev_preutter_pos = m['preutter'].value()
            
            m['consonant'].setPos(base_offset + entry.consonant / 1000.0)
            
            # Cutoff: if negative, from end. if positive, from offset
            if entry.cutoff < 0:
                cut_pos = self.duration_s + (entry.cutoff / 1000.0)
            else:
                cut_pos = base_offset + (entry.cutoff / 1000.0)
            m['cutoff'].setPos(cut_pos)
            
            # Update Root Indicator position
            self._update_root_indicator(m['preutter'].value())
        finally:
            self._is_updating_markers = False

    def _update_root_indicator(self, x_pos: float):
        """Update the position of the Pre-utterance root triangle."""
        # Position triangle at the top of the plot area
        view_range = self.plot_item.viewRange()
        y_max = view_range[1][1]
        self.root_indicator.setData(x=[x_pos], y=[y_max])

    def _on_marker_drag(self, name: str, line: pg.InfiniteLine):
        """Handle marker movement and convert to ms."""
        if self._is_updating_markers:
            return

        pos_s = line.value()
        
        # Root Dragging Mechanic: If Pre-utterance moves, move EVERYTHING
        if name == 'preutter':
            delta = pos_s - self._prev_preutter_pos
            self._prev_preutter_pos = pos_s
            
            self._is_updating_markers = True
            
            # 1. Update all positions visually
            for m_name, m_line in self.markers.items():
                if m_name != 'preutter':
                    new_pos = m_line.value() + delta
                    m_line.setPos(new_pos)
            
            # 2. Emit 'offset' FIRST. This is critical because others are relative to it in the model.
            self.marker_moved.emit('offset', self.markers['offset'].value() * 1000.0)
            
            # 3. Emit others
            for m_name in ['overlap', 'preutter', 'consonant', 'cutoff']:
                self.marker_moved.emit(m_name, self.markers[m_name].value() * 1000.0)
            
            self._is_updating_markers = False
            self._update_root_indicator(pos_s)
            return # Avoid double-emitting for preutter at the end

        # Validation: Overlap <= Preutterance (Gold Rule)
        # Only enforced if not multi-dragging or if specifically dragging overlap/preutter
        if not self._is_updating_markers:
            if name == 'overlap':
                preutter_pos = self.markers['preutter'].value()
                if pos_s > preutter_pos:
                    line.setPos(preutter_pos)
                    pos_s = preutter_pos
            elif name == 'preutter':
                overlap_pos = self.markers['overlap'].value()
                if pos_s < overlap_pos:
                    line.setPos(overlap_pos)
                    pos_s = overlap_pos
                    # Re-sync if clamped
                    self._update_root_indicator(pos_s)
                    self._prev_preutter_pos = pos_s
                
        # Convert to ms
        pos_ms = pos_s * 1000.0
        self.marker_moved.emit(name, pos_ms)
