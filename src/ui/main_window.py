"""Main Window - Application container.

Central widget that hosts all other UI components.
Based on Section 9.2 layout specification.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QMenuBar, QMenu, QStatusBar, QSplitter, QLabel,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence

from ui.reclist_widget import ReclistWidget
from ui.recorder_widget import RecorderWidget
from ui.editor_widget import EditorWidget
from utils.constants import COLORS
from utils.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Main application window.
    
    Layout:
    ┌────────────────────────────────────────────────────────┐
    │ VocalParam v1.0.0-proto    [Archivo] [Proyecto] [Ayuda]│
    ├────────────────────────────────────────────────────────┤
    │  ┌──────────┐  ┌────────────────────────────────────┐  │
    │  │ RECLIST  │  │   RECORDER / EDITOR                │  │
    │  │ [70 ln]  │  │                                    │  │
    │  │          │  │   (Dynamic content area)           │  │
    │  └──────────┘  └────────────────────────────────────┘  │
    ├────────────────────────────────────────────────────────┤
    │ Status: Ready | BPM: 120 | Project: [None]            │
    └────────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VocalParam v1.0.0-prototype")
        self.setMinimumSize(1200, 700)
        
        self._current_project = None
        self._current_bpm = 120
        
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._apply_dark_theme()
        
        logger.info("MainWindow initialized")
    
    def _setup_ui(self):
        """Setup main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Reclist
        self.reclist_widget = ReclistWidget()
        splitter.addWidget(self.reclist_widget)
        
        # Right panel: Content area (switches between recorder and editor)
        self.content_stack = QWidget()
        content_layout = QVBoxLayout(self.content_stack)
        
        # For now, show placeholder
        placeholder = QLabel("Cargue una reclist para comenzar")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 18px;")
        content_layout.addWidget(placeholder)
        
        splitter.addWidget(self.content_stack)
        
        # Set initial sizes (30% / 70%)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
    
    def _setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&Archivo")
        
        new_action = QAction("&Nuevo Proyecto", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Abrir Proyecto", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        load_reclist = QAction("Cargar &Reclist...", self)
        load_reclist.setShortcut("Ctrl+R")
        load_reclist.triggered.connect(self._on_load_reclist)
        file_menu.addAction(load_reclist)
        
        file_menu.addSeparator()
        
        save_action = QAction("&Guardar", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_action)
        
        export_action = QAction("&Exportar Voicebank...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Salir", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Project menu
        project_menu = menubar.addMenu("&Proyecto")
        
        generate_oto = QAction("&Generar oto.ini", self)
        generate_oto.setShortcut("Ctrl+G")
        generate_oto.triggered.connect(self._on_generate_oto)
        project_menu.addAction(generate_oto)
        
        # Help menu
        help_menu = menubar.addMenu("A&yuda")
        
        about_action = QAction("&Acerca de", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _setup_statusbar(self):
        """Setup status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.status_label = QLabel("Listo")
        self.bpm_label = QLabel(f"BPM: {self._current_bpm}")
        self.project_label = QLabel("Proyecto: [Ninguno]")
        
        self.statusbar.addWidget(self.status_label, 1)
        self.statusbar.addPermanentWidget(self.bpm_label)
        self.statusbar.addPermanentWidget(self.project_label)
    
    def _apply_dark_theme(self):
        """Apply dark mode theme from design spec."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
            }}
            QWidget {{
                background-color: {COLORS['background']};
                color: {COLORS['text_primary']};
            }}
            QMenuBar {{
                background-color: #2D2D2D;
                color: {COLORS['text_primary']};
            }}
            QMenuBar::item:selected {{
                background-color: #3D3D3D;
            }}
            QMenu {{
                background-color: #2D2D2D;
                color: {COLORS['text_primary']};
            }}
            QMenu::item:selected {{
                background-color: #3D3D3D;
            }}
            QStatusBar {{
                background-color: #2D2D2D;
                color: {COLORS['text_secondary']};
            }}
            QSplitter::handle {{
                background-color: #3D3D3D;
            }}
        """)
    
    def _on_new_project(self):
        """Handle new project action."""
        logger.info("New project requested")
        # TODO: Implement new project dialog
        self.statusbar.showMessage("Crear nuevo proyecto...", 3000)
    
    def _on_open_project(self):
        """Handle open project action."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Abrir Proyecto", "",
            "Proyectos VocalParam (*.vocalproj);;Todos los archivos (*)"
        )
        if filepath:
            logger.info(f"Opening project: {filepath}")
            # TODO: Load project
            self.statusbar.showMessage(f"Proyecto abierto: {filepath}", 3000)
    
    def _on_load_reclist(self):
        """Handle load reclist action."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Cargar Reclist", "",
            "Archivos de texto (*.txt);;Todos los archivos (*)"
        )
        if filepath:
            logger.info(f"Loading reclist: {filepath}")
            self.reclist_widget.load_reclist(filepath)
            self.statusbar.showMessage(f"Reclist cargada: {filepath}", 3000)
    
    def _on_save_project(self):
        """Handle save project action."""
        logger.info("Save project requested")
        # TODO: Implement save
        self.statusbar.showMessage("Proyecto guardado", 3000)
    
    def _on_export(self):
        """Handle export action."""
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de exportación"
        )
        if folder:
            logger.info(f"Exporting to: {folder}")
            # TODO: Implement export
            self.statusbar.showMessage(f"Exportado a: {folder}", 3000)
    
    def _on_generate_oto(self):
        """Handle generate oto.ini action."""
        logger.info("Generate oto.ini requested")
        # TODO: Implement oto generation
        self.statusbar.showMessage("Generando oto.ini...", 3000)
    
    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "Acerca de VocalParam",
            "<h2>VocalParam v1.0.0-prototype</h2>"
            "<p>Sistema Unificado de Grabación y Configuración de Voicebanks</p>"
            "<p>Licencia: MIT Open Source</p>"
            "<p><a href='https://github.com/org/vocalparam'>GitHub</a></p>"
        )
