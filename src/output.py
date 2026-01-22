#!/usr/bin/env python3
"""
MirrorGate Terminal Output v2.1

Demo-ready terminal formatting for video recording.
Clear visual hierarchy, color-coded decisions, timestamp precision.
"""

from datetime import datetime, timezone
from typing import Optional
import shutil

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Get terminal width
TERM_WIDTH = shutil.get_terminal_size().columns


def timestamp() -> str:
    """Return current timestamp in clean format."""
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def full_timestamp() -> str:
    """Return full ISO timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_banner():
    """Print startup banner."""
    banner = f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                                ║
║   ⟡  M I R R O R G A T E   v 2 . 1                            ║
║                                                                ║
║   Cryptographic Enforcement Layer                              ║
║   Wild Runtime • Deterministic • Tamper-Evident               ║
║                                                                ║
╚══════════════════════════════════════════════════════════════╝{RESET}
"""
    print(banner)


def log_startup():
    """Log daemon startup."""
    log_banner()
    print(f"{GRAY}[{timestamp()}]{RESET} ⟡ Daemon initialized")
    print(f"{GRAY}[{timestamp()}]{RESET} ⟡ Ed25519 keypair loaded")
    print(f"{GRAY}[{timestamp()}]{RESET} ⟡ Hash chain: ready")
    print(f"{GRAY}[{timestamp()}]{RESET} ⟡ Audit log: ~/.mirrorgate/audit_log.jsonl")
    print()


def log_watching(paths: list):
    """Log the paths being watched."""
    print(f"{GRAY}[{timestamp()}]{RESET} {CYAN}WATCHING:{RESET}")
    for path in paths:
        # Shorten home path for display
        display_path = path.replace(str(__import__('pathlib').Path.home()), "~")
        print(f"           └─ {display_path}")
    print()
    print(f"{GRAY}{'─' * 60}{RESET}")
    print(f"{GRAY}[{timestamp()}]{RESET} {GREEN}● ENFORCEMENT ACTIVE{RESET} — Waiting for writes...")
    print(f"{GRAY}{'─' * 60}{RESET}")
    print()


def log_intercept(resource: str, action_type: str = "write"):
    """Log an intercept event."""
    print(f"{GRAY}[{timestamp()}]{RESET} {YELLOW}▶ INTERCEPT{RESET}")
    print(f"           │ Agent attempting: {action_type}")
    print(f"           │ Resource: {WHITE}{resource}{RESET}")


def log_validating():
    """Log that validation is in progress."""
    print(f"           │ Status: Validating against rules...")


def log_block(resource: str, violation_code: str):
    """Log a BLOCK decision - prominent red."""
    print(f"           │")
    print(f"           ╰─▶ {RED}{BOLD}⛔ BLOCKED{RESET}")
    print(f"               {RED}├─ Violation: {violation_code}{RESET}")
    print(f"               {RED}├─ Resource: {resource}{RESET}")
    print(f"               {RED}╰─ Action: Write rejected, staging cleared{RESET}")


def log_allow(resource: str):
    """Log an ALLOW decision - clean green."""
    print(f"           │")
    print(f"           ╰─▶ {GREEN}{BOLD}✅ ALLOWED{RESET}")
    print(f"               {GREEN}├─ Resource: {resource}{RESET}")
    print(f"               {GREEN}╰─ Action: Write committed{RESET}")


def log_record_signed(event_id: str, chain_hash: str):
    """Log that a record was signed."""
    short_id = event_id[:8]
    short_hash = chain_hash[:12]
    print(f"           {GRAY}│{RESET}")
    print(f"           {GRAY}├─ Record signed: {short_id}...{RESET}")
    print(f"           {GRAY}╰─ Chain hash: {short_hash}...{RESET}")
    print()


def log_reverted(resource: str):
    """Log that a file was reverted."""
    print(f"               {YELLOW}└─ File reverted to previous state{RESET}")


def log_separator():
    """Print a visual separator."""
    print(f"\n{GRAY}{'─' * 60}{RESET}\n")


def log_shutdown():
    """Log daemon shutdown."""
    print()
    print(f"{GRAY}{'─' * 60}{RESET}")
    print(f"{GRAY}[{timestamp()}]{RESET} ⟡ MirrorGate daemon stopped")
    print(f"{GRAY}[{timestamp()}]{RESET} ⟡ Audit log preserved")
    print()


def log_error(message: str):
    """Log an error."""
    print(f"{GRAY}[{timestamp()}]{RESET} {RED}ERROR:{RESET} {message}")


def log_info(message: str):
    """Log an info message."""
    print(f"{GRAY}[{timestamp()}]{RESET} {message}")


def log_chain_status(total_records: int, last_hash: str):
    """Log chain status."""
    short_hash = last_hash[:16] if last_hash != "GENESIS" else "GENESIS"
    print(f"{GRAY}[{timestamp()}]{RESET} Chain: {total_records} records, head={short_hash}")


def log_human_absence():
    """Log that human has left (for demo recording)."""
    print()
    print(f"{GRAY}{'─' * 60}{RESET}")
    print(f"{GRAY}[{timestamp()}]{RESET} {CYAN}◉ HUMAN ABSENT{RESET} — System continues autonomously")
    print(f"{GRAY}{'─' * 60}{RESET}")
    print()
