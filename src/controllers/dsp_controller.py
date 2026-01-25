"""DSP Controller - Orchestrates analysis and manual corrections.

Connects the UI components to the DSP engine.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QThread
import numpy as np
from core.dsp_analyzer import DSPAnalyzer, AnalysisResult, SurgicalCorrection
from utils.logger import get_logger

logger = get_logger(__name__)

class AnalysisWorker(QThread):
    """Worker thread for heavy DSP analysis."""
    finished = pyqtSignal(object)  # AnalysisResult
    error = pyqtSignal(str)

    def __init__(self, analyzer: DSPAnalyzer, audio_data: np.ndarray):
        super().__init__()
        self.analyzer = analyzer
        self.audio_data = audio_data

    def run(self):
        try:
            result = self.analyzer.analyze_audio(self.audio_data)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"DSP analysis failed: {e}")
            self.error.emit(str(e))

class DSPController(QObject):
    """Controller for managing DSP state and interactions."""
    
    analysis_started = pyqtSignal()
    analysis_completed = pyqtSignal(object)  # AnalysisResult
    correction_updated = pyqtSignal(list)    # List[PitchPoint]

    def __init__(self):
        super().__init__()
        self.analyzer = DSPAnalyzer()
        self.correction = SurgicalCorrection()
        self._current_result: Optional[AnalysisResult] = None
        self._worker: Optional[AnalysisWorker] = None

    def analyze_audio(self, audio_data: np.ndarray):
        """Start asynchronous analysis of audio data."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        self.analysis_started.emit()
        self._worker = AnalysisWorker(self.analyzer, audio_data)
        self._worker.finished.connect(self._on_analysis_finished)
        self._worker.start()

    def _on_analysis_finished(self, result: AnalysisResult):
        self._current_result = result
        self.analysis_completed.emit(result)

    def add_manual_point(self, time_s: float, freq_hz: float):
        """Record a manual correction point."""
        if not self._current_result:
            return
            
        self.correction.add_point(time_s, freq_hz)
        updated_curve = self.correction.apply_to_curve(self._current_result.pitch_curve)
        self.correction_updated.emit(updated_curve)
        
    def clear_corrections(self):
        """Reset all manual points."""
        self.correction = SurgicalCorrection()
        if self._current_result:
            self.correction_updated.emit(self._current_result.pitch_curve)
