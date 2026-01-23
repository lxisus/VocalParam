"""VocalParam - Main Entry Point.

Sistema Unificado de Grabación y Configuración de Voicebanks.
"""

import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Application entry point."""
    logger.info("Starting VocalParam...")
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("VocalParam")
    app.setApplicationVersion("1.0.0-prototype")
    app.setOrganizationName("VocalParam")
    
    # Apply dark theme
    app.setStyle("Fusion")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    logger.info("Application started successfully")
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
