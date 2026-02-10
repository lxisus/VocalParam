"""Main Window - Application container.

Central widget that hosts all other UI components.
Based on Section 9.2 layout specification.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QMenuBar, QMenu, QStatusBar, QSplitter, QLabel,
    QFileDialog, QMessageBox, QStackedWidget, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from pathlib import Path
from datetime import datetime

from ui.reclist_widget import ReclistWidget
from ui.recorder_widget import RecorderWidget
from ui.editor_widget import EditorWidget
from ui.parameter_table_widget import ParameterTableWidget
from ui.audio_settings_dialog import AudioSettingsDialog
from controllers.editor_controller import EditorController
from core.audio_engine import AudioEngine
from core.persistence import ProjectRepository, AppDatabase, PersistenceError
from core.resource_manager import ResourceManager
from core.models import ProjectData, OtoEntry
from core.oto_generator import OtoGenerator
from ui.project_dialog import ProjectDialog
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
    │  │ RECLIST  │  │   RECORDER / EDITOR SEQ            │  │
    │  │ [70 ln]  │  │  ┌──────────────────────────────┐  │  │
    │  │          │  │  │       Visual Editor          │  │  │
    │  │          │  │  ├──────────────────────────────┤  │  │
    │  │          │  │  │      Parameter Table         │  │  │
    │  └──────────┘  └────────────────────────────────────┘  │
    ├────────────────────────────────────────────────────────┤
    │ Status: Ready | BPM: 120 | Project: [None]            │
    └────────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VocalParam v1.0.0-prototype")
        self.setMinimumSize(1200, 800)
        
        self._current_project: ProjectData = None
        self._current_project_path = None
        self._current_line: PhoneticLine = None
        self._current_bpm = 120
        self.audio_engine = AudioEngine()
        self.resource_manager = ResourceManager()
        self.oto_generator = OtoGenerator(self._current_bpm)
        
        # Initialize Database
        try:
            self.db = AppDatabase()
            self._load_recent_projects()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.db = None
        
        self._setup_ui()
        
        # Initialize Controller
        self.editor_controller = EditorController(self.editor_widget, self.parameter_table)
        
        self._setup_menu()
        self._setup_statusbar()
        self._setup_connections()
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
        
        # Right panel: Content area using QStackedWidget
        self.content_stack = QStackedWidget()
        
        # 0: Placeholder
        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_label = QLabel("Cargue una reclist para comenzar")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 18px;")
        placeholder_layout.addWidget(placeholder_label)
        self.content_stack.addWidget(self.placeholder_widget)
        
        # 1: Recorder
        self.recorder_widget = RecorderWidget(self.audio_engine)
        self.content_stack.addWidget(self.recorder_widget)
        
        # 2: Editor Split View (Visual + Table)
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        editor_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.editor_widget = EditorWidget()
        self.parameter_table = ParameterTableWidget()
        
        editor_splitter.addWidget(self.editor_widget)
        editor_splitter.addWidget(self.parameter_table)
        editor_splitter.setSizes([500, 200]) # Favor visual editor
        
        editor_layout.addWidget(editor_splitter)
        self.content_stack.addWidget(editor_container)
        
        splitter.addWidget(self.content_stack)
        
        # Set initial sizes (25% / 75%)
        splitter.setSizes([300, 900])
        
        layout.addWidget(splitter)
    
    def _setup_connections(self):
        """Connect signals and slots."""
        self.reclist_widget.line_selected.connect(self._on_line_selected)
        self.recorder_widget.recording_stopped.connect(self._on_recording_stopped)
        
        # Connection from Editor Table to loading audio
        self.parameter_table.row_selected.connect(self._on_editor_row_selected)
        
        # New: Auto-save on edits (non-explicit)
        self.editor_controller.project_updated.connect(lambda: self._on_save_project(explicit=False))
        
        # New: Direct Editor Access
        self.btn_goto_editor = QPushButton("✏ Editor Global")
        self.btn_goto_editor.setStyleSheet(f"background-color: {COLORS['accent_primary']}; font-weight: bold; padding: 5px;")
        self.btn_goto_editor.clicked.connect(self._on_goto_editor)
        self.reclist_widget.layout().addWidget(self.btn_goto_editor)
    
    def _on_line_selected(self, index, line):
        """Handle line selection from reclist."""
        logger.info(f"Line selected: {line.raw_text}")
        self._current_line = line
        self.recorder_widget.set_line(line)
        self.recorder_widget.set_bpm(self._current_bpm)
        
        # Set default output path for recorded audio if project exists
        if self._current_project:
            project_dir = self._current_project_path.parent if self._current_project_path else Path(".")
            output_dir = Path(self._current_project.output_directory)
            if not output_dir.is_absolute():
                output_dir = project_dir / output_dir
            self.recorder_widget.path_edit.setText(str(output_dir))
            
        self.content_stack.setCurrentIndex(1)  # Show recorder
    
    def _on_recording_stopped(self, audio_data):
        """Handle recording completion."""
        if audio_data is not None and self._current_line:
             logger.info(f"Received audio data for line: {self._current_line.raw_text}")
             
             # 1. Check for Project
             if not self._current_project:
                 res = QMessageBox.question(self, "Proyecto Requerido", 
                     "La grabación se ha guardado localmente, pero no hay un proyecto abierto para organizar la metadata.\n\n"
                     "¿Desea crear un proyecto nuevo ahora?",
                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                 if res == QMessageBox.StandardButton.Yes:
                     self._on_new_project()
             
             # 2. Update Project (if it was created or already existed)
             recording = None
             if self._current_project:
                 recording = self._update_project_recording(self._current_line, audio_data)
             
             # 2. Generate Initial OTO
             # Use the first segment as the alias for now (prototype limitation)
             # TODO: Handle multi-segment logic
             alias = self._current_line.segments[0] if self._current_line.segments else self._current_line.raw_text
             
             entry = self.oto_generator.generate_oto(
                 filename=f"{self._current_line.raw_text}.wav",
                 audio_data=audio_data,
                 alias=alias,
                 count_in_beats=self.recorder_widget.COUNT_IN_BEATS
             )
             
             # Link entry to recording for persistence
             if recording:
                 # Check if this alias already exists in this recording
                 existing_entry = next((e for e in recording.oto_entries if e.alias == entry.alias), None)
                 if existing_entry:
                     # Update existing
                     existing_entry.offset = entry.offset
                     existing_entry.consonant = entry.consonant
                     existing_entry.cutoff = entry.cutoff
                     existing_entry.preutter = entry.preutter
                     existing_entry.overlap = entry.overlap
                     entry = existing_entry # Use the reference in the project
                 else:
                     recording.oto_entries.append(entry)
             
             # 3. Load into Editor
             self.editor_controller.load_entry(
                 entry, 
                 audio_data, 
                 self.audio_engine._sample_rate
             )
             
             # 4. Switch View
             self.content_stack.setCurrentIndex(2) # Show Editor Container
             
             # Refresh the GLOBAL table to show all recorded samples
             self._on_goto_editor() 
             
             self.statusbar.showMessage(f"Grabación '{alias}' lista para editar.", 3000)

    def _on_goto_editor(self):
        """Switch to editor view manually."""
        # Load all project recordings into the table if project exists
        if self._current_project:
            all_entries = []
            for rec in self._current_project.recordings:
                all_entries.extend(rec.oto_entries)
            self.parameter_table.set_entries(all_entries)
            self.statusbar.showMessage("Cargadas todas las grabaciones en el Editor.", 3000)
        else:
            self.parameter_table.set_entries([])
            self.statusbar.showMessage("Abierto Editor (Sin Proyecto)", 3000)
            
        self.content_stack.setCurrentIndex(2)

    def _on_editor_row_selected(self, entry: OtoEntry):
        """Handle selection of a row in the global parameter table."""
        if not self._current_project:
            return
            
        # Find the recording that contains this entry
        recording = next((r for r in self._current_project.recordings if entry in r.oto_entries), None)
        if not recording:
            logger.warning(f"No recording found for alias: {entry.alias}")
            return
            
        # Load audio file
        project_dir = self._current_project_path.parent if self._current_project_path else Path(".")
        output_dir = Path(self._current_project.output_directory)
        if not output_dir.is_absolute():
            output_dir = project_dir / output_dir
            
        wav_path = output_dir / recording.filename
        
        if wav_path.exists():
            try:
                audio_data, sr = self.audio_engine.load_wav(str(wav_path))
                self.editor_controller.load_entry(entry, audio_data, sr)
                self.statusbar.showMessage(f"Cargado: {entry.alias}", 2000)
            except Exception as e:
                logger.error(f"Failed to load audio for editor: {e}")
                self.statusbar.showMessage(f"Error al cargar audio: {recording.filename}", 3000)
        else:
            self.statusbar.showMessage(f"Archivo no encontrado: {recording.filename}", 3000)

    def _update_project_recording(self, line, audio_data):
        """Update or add a recording entry to the current project."""
        if not self._current_project:
            return
            
        wav_name = f"{line.raw_text}.wav"
        save_path = Path(self.recorder_widget.path_edit.text()) / wav_name
        
        # Calculate hash for integrity
        try:
            # We hash the file after it's saved by RecorderWidget
            # (Wait, actually RecorderWidget._on_accept saves it)
            # Let's verify it exists
            if save_path.exists():
                file_hash = self.resource_manager.calculate_checksum(save_path)
                
                from core.models import Recording, RecordingStatus
                # Find existing or create new
                existing = next((r for r in self._current_project.recordings if r.line_index == line.index), None)
                
                if existing:
                    existing.filename = wav_name
                    existing.status = RecordingStatus.RECORDED
                    existing.duration_ms = len(audio_data) / self.audio_engine._active_sr * 1000
                    existing.hash = file_hash
                else:
                    new_rec = Recording(
                        line_index=line.index,
                        filename=wav_name,
                        status=RecordingStatus.RECORDED,
                        duration_ms=len(audio_data) / self.audio_engine._active_sr * 1000,
                        hash=file_hash
                    )
                    self._current_project.recordings.append(new_rec)
                
                # Update Reclist UI
                self.reclist_widget.set_line_status(line.index, RecordingStatus.RECORDED)
                    
                logger.info(f"Project updated with recording: {wav_name} (Hash: {file_hash[:8]}...)")
                return existing or new_rec
        except Exception as e:
            logger.error(f"Failed to update project recording: {e}")
        return None
    
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
        
        project_menu.addSeparator()
        
        audio_setup = QAction("⚙ Configuración de Audio", self)
        audio_setup.triggered.connect(self._on_audio_settings)
        project_menu.addAction(audio_setup)
        
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
        dialog = ProjectDialog(self)
        if dialog.exec() == ProjectDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data: return
            
            # Create Project Model
            project = ProjectData(
                project_name=data["name"],
                bpm=data["bpm"],
                reclist_path=data["reclist"],
                output_directory=data["output"]
            )
            
            try:
                # Save immediately
                ProjectRepository.save_project(project, data["save_path"])
                self._current_project_path = Path(data["save_path"])
                self._load_project_ui(project)
                
                # Setup Resource Manager
                self.resource_manager.set_project_root(self._current_project_path.parent)
                
                QMessageBox.information(self, "Proyecto Creado", f"El proyecto '{project.project_name}' ha sido creado exitosamente.")
            except Exception as e:
                logger.error(f"Failed to create project: {e}")
                QMessageBox.critical(self, "Error", f"No se pudo crear el proyecto:\n{e}")
    
    def _on_open_project(self):
        """Handle open project action."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Abrir Proyecto", "",
            "Proyectos VocalParam (*.vocalproj);;Todos los archivos (*)"
        )
        if filepath:
            filepath = Path(filepath)
            logger.info(f"Opening project: {filepath}")
            
            # Check locking
            if not self.resource_manager.create_lock_file(filepath):
                QMessageBox.warning(self, "Proyecto Bloqueado", 
                                  "El proyecto ya parece estar abierto en otra instancia o está bloqueado.")
                return

            try:
                project = ProjectRepository.load_project(filepath)
                self._current_project_path = filepath
                
                # Verify resources and Integrity
                self._verify_project_resources(project, filepath.parent)
                self._load_project_ui(project)
                
                # Start background integrity checks
                self.resource_manager.set_project_root(filepath.parent)
                self.resource_manager.start_background_scrubbing()
                
                self.statusbar.showMessage(f"Proyecto cargado: {project.project_name}", 3000)
            except PersistenceError as e:
                self.resource_manager.release_lock(filepath)
                QMessageBox.critical(self, "Error al abrir", str(e))
                logger.error(f"Error opening project: {e}")
    
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

    def _load_recent_projects(self):
        """Update recent projects menu (placeholder for full implementation)."""
        if not self.db:
            return
        # In a real app, this would populate a submenu. 
        # For now, we just log it to verify DB connectivity.
        recent = self.db.get_recent_projects(limit=5)
        logger.info(f"Loaded {len(recent)} recent projects from DB")
    
    def _on_save_project(self, explicit=True):
        """Handle save project action.
        
        Args:
            explicit: If True, show dialogs and errors. If False (auto-save), be silent 
                     unless a critical error occurs and only if a path is already set.
        """
        if not self._current_project:
            if explicit:
                QMessageBox.warning(self, "Guardar", "Primero debe crear o abrir un proyecto.")
            return

        # Get existing path
        filepath = self._current_project_path
        
        # If no path and user clicked Save, ask for one
        if not filepath and explicit:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Guardar Proyecto", "",
                "Proyectos VocalParam (*.vocalproj)"
            )
            if filepath:
                self._current_project_path = Path(filepath)
            else:
                return # User cancelled

        # Only proceed if we have a path
        if self._current_project_path:
            try:
                # Update metadata
                self._current_project.last_modified = datetime.now()
                
                ProjectRepository.save_project(self._current_project, self._current_project_path)
                
                if explicit:
                    self.statusbar.showMessage("Proyecto guardado correctamente", 3000)
                else:
                    self.statusbar.showMessage("Proyecto auto-guardado", 1000)
            except PersistenceError as e:
                logger.error(f"Error saving project: {e}")
                if explicit:
                    QMessageBox.critical(self, "Error al guardar", str(e))
    
    def _verify_project_resources(self, project: ProjectData, project_dir: Path):
        """Check if all recordings exist and verify integrity."""
        missing = []
        corrupted = []
        
        output_dir = Path(project.output_directory)
        if not output_dir.is_absolute():
            output_dir = project_dir / output_dir
            
        for rec in project.recordings:
            wav_path = output_dir / rec.filename
            if not wav_path.exists():
                # Try smart relinking
                recovered = self.resource_manager.find_missing_resource(wav_path, [project_dir])
                if recovered:
                    rec.filename = os.path.relpath(recovered, output_dir)
                    logger.info(f"Relinked {rec.filename} to {recovered}")
                else:
                    missing.append(rec.filename)
            elif rec.hash:
                # Verify integrity
                current_hash = self.resource_manager.calculate_checksum(wav_path)
                if current_hash != rec.hash:
                    corrupted.append(rec.filename)
                    
        if missing or corrupted:
            msg = "Problemas detectados en los recursos:\n"
            if missing:
                msg += f"\nFaltantes ({len(missing)}):\n" + "\n".join(missing[:5])
                if len(missing) > 5: msg += "\n..."
            if corrupted:
                msg += f"\nCorruptos/Modificados ({len(corrupted)}):\n" + "\n".join(corrupted[:5])
                if len(corrupted) > 5: msg += "\n..."
                
            QMessageBox.warning(self, "Integridad de Recursos", msg)

    def _load_project_ui(self, project: ProjectData):
        """Update UI with project data."""
        self._current_project = project
        # Note: self._current_project_path must be set before calling this 
        # as ProjectData doesn't store its own file path.
        self._current_bpm = project.bpm
        
        self.project_label.setText(f"Proyecto: {project.project_name}")
        self.bpm_label.setText(f"BPM: {project.bpm}")
        
        # Load reclist if path exists
        if project.reclist_path:
             self.reclist_widget.load_reclist(project.reclist_path)
             
        # Load recording statuses into Reclist UI
        from core.models import RecordingStatus
        for rec in project.recordings:
            self.reclist_widget.set_line_status(rec.line_index, rec.status)
             
        self.statusbar.showMessage(f"Proyecto {project.project_name} cargado", 3000)
        """Load recent projects specific logic (placeholder for menu update)."""
        # This would update the "Open Recent" menu
        pass
    
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
    
    def _on_audio_settings(self):
        """Show audio hardware configuration and apply settings."""
        dialog = AudioSettingsDialog(self.audio_engine, self)
        if dialog.exec() == AudioSettingsDialog.DialogCode.Accepted:
            input_idx, output_idx, sr = dialog.get_selected_devices()
            self.audio_engine.set_devices(input_idx, output_idx)
            self.audio_engine.set_sample_rate(sr) # This also regenerates clicks
            self.audio_engine.save_config() 
            self.statusbar.showMessage(f"Configuración actualizada: {sr}Hz", 3000)
    
    def closeEvent(self, event):
        """Cleanup on close."""
        self.resource_manager.stop_background_scrubbing()
        if self._current_project_path:
            self.resource_manager.release_lock(Path(self._current_project_path))
        if hasattr(self, 'db') and self.db:
            self.db.close()
        super().closeEvent(event)

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
