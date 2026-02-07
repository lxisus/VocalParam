"""Persistence Layer for VocalParam.

Implements robust data storage patterns including:
- Atomic writes for project files
- SQLite with WAL mode for global application state
- Rolling backups for project safety
"""

import json
import shutil
import sqlite3
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager
import hashlib
import threading
from core.models import ProjectData
from utils.logger import get_logger

logger = get_logger(__name__)

class PersistenceError(Exception):
    """Base exception for persistence errors."""
    pass

class ProjectRepository:
    """Handles storage and retrieval of ProjectData with atomic safety."""
    
    BACKUP_COUNT = 3
    CURRENT_VERSION = "1.0.0"
    
    @staticmethod
    def save_project(project: ProjectData, filepath: Union[str, Path]) -> None:
        """Save project atomically with rolling backups.
        
        Args:
            project: ProjectData instance to save
            filepath: Target path for the .vocalproj file
            
        Raises:
            PersistenceError: If saving fails
        """
        filepath = Path(filepath)
        
        # 1. Rotate Backups if file exists
        if filepath.exists():
            ProjectRepository._rotate_backups(filepath)
            
        # 2. Serialize data
        try:
            data = project.to_dict()
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            raise PersistenceError(f"Serialization failed: {e}")
            
        # 3. Atomic Write (Write to temp -> Rename)
        tmp_path = None
        try:
            # Create temp file in the same directory to ensure atomic rename works
            # (rename across filesystems might not be atomic)
            fd, tmp_path_str = tempfile.mkstemp(
                prefix=f".{filepath.name}.", 
                dir=filepath.parent,
                text=True
            )
            tmp_path = Path(tmp_path_str)
            
            with open(fd, 'w', encoding='utf-8') as f:
                f.write(json_str)
                f.flush()
                # fsync to ensure data is physically written to disk
                import os
                os.fsync(fd)
                
            # Atomic rename
            tmp_path.replace(filepath)
            
            # Update recent projects in DB
            db = AppDatabase()
            db.add_recent_project(str(filepath), project.project_name)
            
            logger.info(f"Project saved successfully: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save project to {filepath}: {e}")
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()
            raise PersistenceError(f"Atomic write failed: {e}")

    @staticmethod
    def load_project(filepath: Union[str, Path]) -> ProjectData:
        """Load project from file.
        
        Args:
            filepath: Path to .vocalproj file
            
        Returns:
            ProjectData instance
            
        Raises:
            PersistenceError: If loading or parsing fails
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise PersistenceError(f"File not found: {filepath}")
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Schema version migration hooks
            version = data.get('version', '0.0.0')
            if version != ProjectRepository.CURRENT_VERSION:
                data = ProjectRepository._migrate_data(data, version)
            
            project = ProjectData.from_dict(data)
            
            # Update recent projects in DB
            db = AppDatabase()
            db.add_recent_project(str(filepath), project.project_name)
            
            return project
        except json.JSONDecodeError as e:
            raise PersistenceError(f"Corrupted project file: {e}")
        except Exception as e:
            raise PersistenceError(f"Failed to load project: {e}")

    @staticmethod
    def _migrate_data(data: Dict, from_version: str) -> Dict:
        """Transform data from older versions to current schema."""
        logger.info(f"Migrating project from {from_version} to {ProjectRepository.CURRENT_VERSION}")
        # Placeholder for future migrations
        # if from_version == "0.9.0": ...
        data['version'] = ProjectRepository.CURRENT_VERSION
        return data

    @staticmethod
    def _rotate_backups(filepath: Path):
        """Rotate .bak files (file.vocalproj -> .bak1 -> .bak2 -> ...)."""
        try:
            # Remove oldest backup
            last_backup = filepath.with_suffix(f"{filepath.suffix}.bak{ProjectRepository.BACKUP_COUNT}")
            if last_backup.exists():
                last_backup.unlink()
            
            # Shift existing backups
            for i in range(ProjectRepository.BACKUP_COUNT - 1, 0, -1):
                src = filepath.with_suffix(f"{filepath.suffix}.bak{i}")
                dst = filepath.with_suffix(f"{filepath.suffix}.bak{i+1}")
                if src.exists():
                    src.replace(dst)
            
            # Create new backup from current file
            first_backup = filepath.with_suffix(f"{filepath.suffix}.bak1")
            shutil.copy2(filepath, first_backup)
            
        except Exception as e:
            logger.warning(f"Backup rotation failed: {e}")


class AppDatabase:
    """Global application SQLite database manager."""
    
    DB_NAME = "vocalparam.db"
    
    def __init__(self):
        # Store DB in user home directory
        self.db_path = Path.home() / ".vocalparam" / self.DB_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns the active connection, creating it if needed."""
        with self._lock:
            if self._connection is None:
                self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
                self._connection.row_factory = sqlite3.Row
                # Enable WAL mode once per session
                self._connection.execute("PRAGMA journal_mode=WAL;")
                self._connection.execute("PRAGMA synchronous=NORMAL;")
            return self._connection

    def _init_db(self):
        """Initialize database schema."""
        try:
            conn = self._get_connection()
            with conn:
                # Create tables
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS recent_projects (
                        path TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS app_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        type TEXT DEFAULT 'string'
                    );
                    
                    CREATE TABLE IF NOT EXISTS telemetry_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT,
                        message TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS resource_ledger (
                        hash TEXT PRIMARY KEY,
                        path TEXT NOT NULL,
                        first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_verified DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT -- JSON blob for extra info
                    );
                    
                    CREATE TABLE IF NOT EXISTS op_journal (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        operation TEXT NOT NULL,
                        status TEXT DEFAULT 'PENDING',
                        data TEXT, -- JSON payload
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        completed_at DATETIME
                    );
                """)
                logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise PersistenceError(f"DB Init Failed: {e}")

    def add_recent_project(self, path: str, name: str):
        """Add or update a project in recent list."""
        try:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO recent_projects (path, name, last_accessed)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(path) DO UPDATE SET
                        name=excluded.name,
                        last_accessed=CURRENT_TIMESTAMP
                """, (str(path), name))
        except Exception as e:
            logger.error(f"Failed to update recent projects: {e}")

    def get_recent_projects(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent projects."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT path, name, last_accessed 
                FROM recent_projects 
                ORDER BY last_accessed DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch recent projects: {e}")
            return []

    def log_event(self, level: str, message: str):
        """Log an internal event for telemetry."""
        try:
            conn = self._get_connection()
            with conn:
                conn.execute(
                    "INSERT INTO telemetry_log (level, message) VALUES (?, ?)",
                    (level, message)
                )
        except Exception as e:
            # Don't recurse if logging fails
            print(f"Telemetry write failed: {e}")

    def update_resource_ledger(self, file_hash: str, path: str, metadata: Optional[Dict] = None):
        """Record or update a resource's status in the ledger."""
        try:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO resource_ledger (hash, path, last_verified, metadata)
                    VALUES (?, ?, CURRENT_TIMESTAMP, ?)
                    ON CONFLICT(hash) DO UPDATE SET
                        path=excluded.path,
                        last_verified=CURRENT_TIMESTAMP,
                        metadata=COALESCE(excluded.metadata, resource_ledger.metadata)
                """, (file_hash, str(path), json.dumps(metadata) if metadata else None))
        except Exception as e:
            logger.error(f"Failed to update resource ledger: {e}")

    def get_resource_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve resource info by its hash."""
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM resource_ledger WHERE hash = ?", (file_hash,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to fetch resource by hash: {e}")
            return None

    def set_setting(self, key: str, value: Any):
        """Save a typed setting to the database."""
        try:
            val_type = type(value).__name__
            val_str = json.dumps(value) if not isinstance(value, str) else value
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO app_settings (key, value, type)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value=excluded.value,
                        type=excluded.type
                """, (key, val_str, val_type))
        except Exception as e:
            logger.error(f"Failed to save setting {key}: {e}")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieve a typed setting from the database."""
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT value, type FROM app_settings WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            if not row:
                return default
            
            val_str, val_type = row['value'], row['type']
            if val_type == 'str':
                return val_str
            try:
                return json.loads(val_str)
            except:
                return val_str
        except Exception as e:
            logger.error(f"Failed to fetch setting {key}: {e}")
            return default

    def start_journal_entry(self, operation: str, data: Optional[Dict] = None) -> int:
        """Create a journal entry for a multi-step operation."""
        try:
            conn = self._get_connection()
            with conn:
                cursor = conn.execute(
                    "INSERT INTO op_journal (operation, data) VALUES (?, ?)",
                    (operation, json.dumps(data) if data else None)
                )
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to start journal: {e}")
            return -1

    def complete_journal_entry(self, entry_id: int, status: str = 'COMPLETED'):
        """Mark a journal entry as finished."""
        try:
            conn = self._get_connection()
            with conn:
                conn.execute(
                    "UPDATE op_journal SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, entry_id)
                )
        except Exception as e:
            logger.error(f"Failed to complete journal: {e}")

    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
