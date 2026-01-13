import json
import hashlib
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any, Dict
from .types import PulseEvent

# MirrorGate Standard Paths
MIRRORGATE_DIR = Path.home() / ".mirrorgate"
PULSE_LOG = MIRRORGATE_DIR / "pulse_audit.jsonl"
PULSE_CHAIN_STATE = MIRRORGATE_DIR / "pulse_chain_state.json"

try:
    from ..crypto import load_private_key
except (ImportError, ValueError):
    try:
        from crypto import load_private_key
    except ImportError:
        def load_private_key(): raise NotImplementedError("Crypto not found")


def ensure_directories():
    MIRRORGATE_DIR.mkdir(exist_ok=True)

def get_previous_hash() -> str:
    if not PULSE_CHAIN_STATE.exists():
        return "GENESIS"
    try:
        state = json.loads(PULSE_CHAIN_STATE.read_text())
        return state.get("last_hash", "GENESIS")
    except:
        return "GENESIS"

def save_chain_state(last_hash: str):
    ensure_directories()
    PULSE_CHAIN_STATE.write_text(json.dumps({
        "last_hash": last_hash,
        "updated": datetime.now(timezone.utc).isoformat()
    }))

def log_pulse_event(
    event_type: str,
    payload: Dict[str, Any],
    actor: str = "mac_mini_pulse"
) -> PulseEvent:
    """
    Log a generic Pulse event with hash chaining.
    """
    ensure_directories()
    
    # 1. Prepare Basic Event
    # We use a simplified payload hash for the event body?
    # Or just put payload in the record? Protocol says "payload_hash" in the log struct.
    # "payload_hash": "sha256"
    
    payload_str = json.dumps(payload, sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
    
    prev_hash = get_previous_hash()
    
    # Create Event Object (Unsigned first)
    # Note: PulseEvent has 'event_id', 'ts', 'type', 'payload_hash', 'prev_hash', 'signature'
    
    # We need an ID.
    try:
        import uuid6
        eid = str(uuid6.uuid7())
    except:
        import uuid
        eid = str(uuid.uuid4())
        
    event = PulseEvent(
        event_id=eid,
        ts=datetime.now(timezone.utc),
        type=event_type,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        signature=None
    )
    
    # 2. Compute Chain Hash (this serves as the "content to be signed")
    # serialization for hashing
    event_json = event.model_dump_json(exclude={'signature'}, exclude_none=True)
    
    # Chain Input = EventJSON + PrevHash?
    # The 'prev_hash' is already INSIDE the EventJSON.
    # So hashing the EventJSON is sufficient to bind it to the chain.
    chain_hash = hashlib.sha256(event_json.encode()).hexdigest()
    
    # 3. Sign the Chain Hash
    private_key = load_private_key()
    signature_bytes = private_key.sign(chain_hash.encode())
    event.signature = base64.b64encode(signature_bytes).decode()
    
    # 4. Persist
    # We append the FULL event (including signature) to the log
    with open(PULSE_LOG, 'a') as f:
        f.write(event.model_dump_json() + '\n')
        
    # 5. Update State
    save_chain_state(chain_hash)
    
    return event
