#!/usr/bin/env python3
"""
MirrorGate Terminal Output

Clean, demo-ready terminal formatting.
Color-coded BLOCK/ALLOW with timestamps.
"""

from datetime import datetime, timezone
from typing import Optional

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def timestamp() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_watching(paths: list):
    """Log the paths being watched."""
    paths_str = ", ".join(paths)
    print(f"[{timestamp()}] {BLUE}WATCHING:{RESET} {paths_str}")


def log_intercept(resource: str, action_type: str = "write"):
    """Log an intercept event."""
    print(f"[{timestamp()}] {YELLOW}INTERCEPT:{RESET} agent attempting {action_type} to {resource}")


def log_validating():
    """Log that validation is in progress."""
    print(f"[{timestamp()}] VALIDATING...")


def log_block(resource: str, violation_code: str):
    """Log a BLOCK decision."""
    print(f"[{timestamp()}] {RED}{BOLD}⛔ BLOCK{RESET} | VIOLATION: {violation_code} | resource: {resource}")


def log_allow(resource: str):
    """Log an ALLOW decision."""
    print(f"[{timestamp()}] {GREEN}{BOLD}✅ ALLOW{RESET} | resource: {resource} | no violations detected")


def log_record_signed(event_id: str, chain_hash: str):
    """Log that a record was signed."""
    short_id = event_id[:12] + "..."
    short_hash = chain_hash[:8] + "..."
    print(f"[{timestamp()}] RECORD SIGNED: event_id={short_id} chain_hash={short_hash}")


def log_reverted(resource: str):
    """Log that a file was reverted."""
    print(f"[{timestamp()}] REVERTED: {resource} restored to hash_before state")


def log_separator():
    """Print a visual separator."""
    print("---")


def log_startup():
    """Log daemon startup."""
    print(f"\n{BOLD}⟡ MirrorGate Daemon v2.0{RESET}")
    print(f"[{timestamp()}] Cryptographic enforcement active")
    print(f"[{timestamp()}] Press Ctrl+C to stop\n")


def log_shutdown():
    """Log daemon shutdown."""
    print(f"\n[{timestamp()}] MirrorGate daemon stopped")


def log_error(message: str):
    """Log an error."""
    print(f"[{timestamp()}] {RED}ERROR:{RESET} {message}")


def log_info(message: str):
    """Log an info message."""
    print(f"[{timestamp()}] {message}")
