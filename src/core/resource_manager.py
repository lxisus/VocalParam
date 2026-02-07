"""Resource Management for VocalParam.

Handles integrity, hashing, and discovery of audio assets (WAV files).
"""

import os
import hashlib
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from core.persistence import AppDatabase
from utils.logger import get_logger

logger = get_logger(__name__)

class ResourceIntegrityError(Exception):
    """Raised when resource integrity checks fail."""
    pass

class ResourceManager:
    """Manages audio assets and ensures their integrity."""

    def __init__(self, project_root: Optional[Path] = None, db: Optional[AppDatabase] = None):
        self.project_root = project_root
        self.db = db or AppDatabase()
        self._checksum_cache: Dict[str, str] = {}
        self._stop_scrubbing = threading.Event()
        self._scrub_thread: Optional[threading.Thread] = None

    def set_project_root(self, path: Path):
        """Update the base directory for resource lookup."""
        self.project_root = Path(path)

    def calculate_checksum(self, filepath: Path, partial: bool = True) -> str:
        """Calculate a SHA-256 hash of the file.
        
        Args:
            filepath: Path to the file.
            partial: If True, only hashes the first 1MB to speed up large files.
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Cannot hash missing file: {filepath}")

        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            if partial:
                # Read at most 1MB
                sha256.update(f.read(1024 * 1024))
            else:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256.update(byte_block)
        
        return sha256.hexdigest()

    def verify_resource(self, filepath: Path, expected_hash: Optional[str] = None) -> bool:
        """Check if a resource exists and optionally verify its hash."""
        if not filepath.exists():
            return False
        
        current_hash = self.calculate_checksum(filepath)
        
        # Update ledger
        self.db.update_resource_ledger(current_hash, str(filepath))
        
        if expected_hash:
            return current_hash == expected_hash
            
        return True

    def start_background_scrubbing(self, interval_seconds: int = 300):
        """Start a background thread to check resource integrity."""
        if self._scrub_thread and self._scrub_thread.is_alive():
            return

        self._stop_scrubbing.clear()
        self._scrub_thread = threading.Thread(
            target=self._scrub_worker, 
            args=(interval_seconds,),
            daemon=True,
            name="ResourceScrubber"
        )
        self._scrub_thread.start()
        logger.info("Background resource scrubbing started")

    def stop_background_scrubbing(self):
        """Signal the scrub thread to stop."""
        self._stop_scrubbing.set()
        if self._scrub_thread:
            self._scrub_thread.join(timeout=1.0)

    def _scrub_worker(self, interval: int):
        """Periodic integrity check of all files in project_root."""
        while not self._stop_scrubbing.is_set():
            if self.project_root and self.project_root.exists():
                logger.debug(f"Starting integrity scrub in {self.project_root}")
                # We only scrub WAV files to avoid heavy IO
                for wav_path in self.project_root.rglob("*.wav"):
                    if self._stop_scrubbing.is_set():
                        break
                    try:
                        self.verify_resource(wav_path)
                    except Exception as e:
                        logger.error(f"Scrub failed for {wav_path}: {e}")
            
            # Wait for interval or stop signal
            self._stop_scrubbing.wait(interval)

    def find_missing_resource(self, original_path: Path, search_dirs: List[Path]) -> Optional[Path]:
        """Heuristically find a moved asset.
        
        Args:
            original_path: The filename and original directory we are looking for.
            search_dirs: List of directories to search recursively.
        """
        filename = original_path.name
        
        for root in search_dirs:
            if not root.exists():
                continue
                
            # Recursive check
            for path in root.rglob(filename):
                # For now, just return the first match by name
                # In advanced mode, we'd verify metadata or hash here
                logger.info(f"Resource recovered: {filename} found at {path}")
                return path
                
        return None

    def create_lock_file(self, project_path: Path) -> bool:
        """Create a .lock file to prevent concurrent access."""
        lock_path = project_path.with_suffix(project_path.suffix + ".lock")
        if lock_path.exists():
            # Check if stale (older than X hours?) - for now just fail
            return False
            
        try:
            with open(lock_path, "w") as f:
                f.write(f"Locked by VocalParam at {os.getpid()}")
            return True
        except Exception as e:
            logger.error(f"Failed to create lock file: {e}")
            return False

    def release_lock(self, project_path: Path):
        """Remove the .lock file."""
        lock_path = project_path.with_suffix(project_path.suffix + ".lock")
        if lock_path.exists():
            try:
                lock_path.unlink()
            except Exception as e:
                logger.error(f"Failed to release lock: {e}")
