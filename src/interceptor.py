#!/usr/bin/env python3
"""
MirrorGate File Interceptor

Manages file state for pre/post write validation.
Handles backup and revert for blocked writes.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from .crypto import compute_file_hash


class FileState:
    """Tracks state of a file for validation."""
    
    def __init__(self, path: str):
        self.path = path
        self.hash_before: Optional[str] = None
        self.hash_after: Optional[str] = None
        self.backup_path: Optional[str] = None
        self.content_before: Optional[bytes] = None


class Interceptor:
    """
    Manages file interception for MirrorGate.
    
    Captures file state before and after writes,
    enables revert on blocked writes.
    """
    
    def __init__(self):
        self.states: Dict[str, FileState] = {}
        self.backup_dir = Path(tempfile.gettempdir()) / "mirrorgate_backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def capture_before(self, path: str) -> FileState:
        """
        Capture file state before a write.
        
        Args:
            path: Path to the file
            
        Returns:
            FileState object with hash_before set
        """
        state = FileState(path)
        
        if os.path.exists(path):
            state.hash_before = compute_file_hash(path)
            # Store content for potential revert
            try:
                with open(path, 'rb') as f:
                    state.content_before = f.read()
            except:
                state.content_before = None
        else:
            state.hash_before = "NEW_FILE"
            state.content_before = None
        
        self.states[path] = state
        return state
    
    def capture_after(self, path: str) -> FileState:
        """
        Capture file state after a write.
        
        Args:
            path: Path to the file
            
        Returns:
            FileState object with hash_after set
        """
        state = self.states.get(path)
        if not state:
            state = self.capture_before(path)
        
        state.hash_after = compute_file_hash(path)
        return state
    
    def get_new_content(self, path: str) -> Optional[str]:
        """
        Get the new content of a file after write.
        
        Args:
            path: Path to the file
            
        Returns:
            File content as string, or None if unreadable
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"DEBUG Error reading {path}: {e}")
            return None
    
    def revert(self, path: str) -> bool:
        """
        Revert a file to its state before the write.
        
        Args:
            path: Path to the file
            
        Returns:
            True if revert succeeded, False otherwise
        """
        state = self.states.get(path)
        if not state:
            return False
        
        try:
            if state.hash_before == "NEW_FILE":
                # File was newly created, delete it
                if os.path.exists(path):
                    os.remove(path)
                return True
            elif state.content_before is not None:
                # Restore original content
                with open(path, 'wb') as f:
                    f.write(state.content_before)
                return True
            else:
                return False
        except Exception:
            return False
    
    def cleanup(self, path: str):
        """Remove tracked state for a path."""
        if path in self.states:
            del self.states[path]
