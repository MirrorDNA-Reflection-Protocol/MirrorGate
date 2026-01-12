#!/usr/bin/env python3
"""
MirrorGate Daemon — File System Watcher

Watches configured paths for file changes.
Intercepts writes, validates against rules, signs decisions.
"""

import os
import sys
import time
import signal
from pathlib import Path
from typing import List

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from .rules import check_content, get_violation_description
from .crypto import generate_decision_record, append_to_audit_log, ensure_directories
from .interceptor import Interceptor
from .output import (
    log_watching, log_intercept, log_validating, log_block, log_allow,
    log_record_signed, log_reverted, log_separator, log_startup, 
    log_shutdown, log_error
)

# Default watch paths
DEFAULT_WATCH_PATHS = [
    str(Path.home() / ".mirrordna"),
    str(Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"),
]

# File extensions to monitor
MONITORED_EXTENSIONS = {'.md', '.txt', '.json', '.yaml', '.yml'}

# Ignore patterns
IGNORE_PATTERNS = {'.git', '__pycache__', '.DS_Store', 'node_modules'}


class MirrorGateHandler(FileSystemEventHandler):
    """Handles file system events for MirrorGate."""
    
    def __init__(self):
        super().__init__()
        self.interceptor = Interceptor()
        self._processing = set()  # Prevent re-entry
    
    def _should_process(self, path: str) -> bool:
        """Check if this file should be processed."""
        # Skip directories
        if os.path.isdir(path):
            return False
        
        # Skip ignored patterns
        for pattern in IGNORE_PATTERNS:
            if pattern in path:
                return False
        
        # Only process monitored extensions
        ext = os.path.splitext(path)[1].lower()
        if ext not in MONITORED_EXTENSIONS:
            return False
        
        return True
    
    def _process_write(self, path: str):
        """Process a file write event."""
        # Prevent re-entry
        if path in self._processing:
            return
        self._processing.add(path)
        
        try:
            resource = os.path.basename(path)
            
            log_separator()
            log_intercept(resource)
            log_validating()
            
            # Capture state after write
            state = self.interceptor.capture_after(path)
            
            # If we don't have before state, capture it now (first time seeing this file)
            if state.hash_before is None:
                state.hash_before = "UNKNOWN"
            
            # Get content for validation
            content = self.interceptor.get_new_content(path)
            if content is None:
                # Retry once to handle race conditions
                time.sleep(0.1)
                content = self.interceptor.get_new_content(path)
                if content is None:
                    log_error(f"Could not read content of {resource}")
                    return
            
            # Check against rules
            action, violation_code = check_content(content, path)
            
            # Generate decision record
            record = generate_decision_record(
                action=action,
                resource=path,
                violation_code=violation_code,
                hash_before=state.hash_before,
                hash_after=state.hash_after,
                actor="agent"
            )
            
            # Append to audit log
            append_to_audit_log(record)
            
            if action == "BLOCK":
                log_block(resource, violation_code)
                log_record_signed(record["event_id"], record["chain_hash"])
                
                # Revert the write
                if self.interceptor.revert(path):
                    log_reverted(resource)
                else:
                    log_error(f"Could not revert {resource}")
            else:
                log_allow(resource)
                log_record_signed(record["event_id"], record["chain_hash"])
            
            # Cleanup state
            self.interceptor.cleanup(path)
            
        finally:
            self._processing.discard(path)
    
    def on_created(self, event):
        """Handle file creation."""
        if not isinstance(event, FileCreatedEvent):
            return
        if self._should_process(event.src_path):
            # Explicitly mark as new file to ensure revert works (deletes it)
            # regardless of whether content has already been written to disk
            from .interceptor import FileState
            state = FileState(event.src_path)
            state.hash_before = "NEW_FILE"
            state.content_before = None
            self.interceptor.states[event.src_path] = state
            
            # Small delay to ensure file is written before we validate
            time.sleep(0.1)
            self._process_write(event.src_path)
    
    def on_modified(self, event):
        """Handle file modification."""
        if not isinstance(event, FileModifiedEvent):
            return
        if self._should_process(event.src_path):
            self._process_write(event.src_path)


class MirrorGateDaemon:
    """Main daemon class for MirrorGate."""
    
    def __init__(self, watch_paths: List[str] = None):
        self.watch_paths = watch_paths or DEFAULT_WATCH_PATHS
        self.observer = None
        self.running = False
    
    def start(self):
        """Start the daemon."""
        ensure_directories()
        log_startup()
        
        # Filter to existing paths
        valid_paths = []
        for path in self.watch_paths:
            if os.path.exists(path):
                valid_paths.append(path)
            else:
                # Create if it doesn't exist
                try:
                    os.makedirs(path, exist_ok=True)
                    valid_paths.append(path)
                except:
                    pass
        
        if not valid_paths:
            log_error("No valid watch paths found")
            return
        
        log_watching(valid_paths)
        
        # Setup observer
        self.observer = Observer()
        handler = MirrorGateHandler()
        
        for path in valid_paths:
            self.observer.schedule(handler, path, recursive=True)
        
        # Handle shutdown signals
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start watching
        self.observer.start()
        self.running = True
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """Stop the daemon."""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
        log_shutdown()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.running = False


def main():
    """Entry point for the daemon."""
    # Parse command line args for custom paths
    watch_paths = None
    if len(sys.argv) > 1:
        watch_paths = sys.argv[1:]
    
    daemon = MirrorGateDaemon(watch_paths)
    daemon.start()


if __name__ == "__main__":
    main()
