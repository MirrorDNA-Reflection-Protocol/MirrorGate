from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class PulseScope(str, Enum):
    # Observation Scopes
    OBSERVE_APP = "observe.app"
    OBSERVE_SCREEN = "observe.screen"
    OBSERVE_AUDIO = "observe.audio"
    OBSERVE_CAMERA = "observe.camera"
    
    # Navigation Scopes
    NAVIGATE_BASIC = "navigate.basic"
    
    # Input Scopes
    INPUT_DRAFT = "input.draft"
    INPUT_COMMIT = "input.commit"
    
    # Execution Scopes (High Risk)
    EXECUTE_CRITICAL = "execute.critical"
    
    # Admin Scopes
    ADMIN_SYSTEM = "admin.system"

class TokenConstraints(BaseModel):
    no_execute: bool = True
    no_settings: bool = True
    no_clipboard_global: bool = True
    require_visible_indicator: bool = True

class PulseToken(BaseModel):
    token_id: str
    issued_to: str
    scope: List[PulseScope]
    start: datetime
    end: datetime
    constraints: TokenConstraints = Field(default_factory=TokenConstraints)
    revocable: bool = True
    signature: Optional[str] = None

class PulseEvent(BaseModel):
    event_id: str
    ts: datetime
    type: str  # "token_issue" | "observe" | "action" | "refusal" | "vault_write"
    payload_hash: str
    prev_hash: str
    signature: Optional[str] = None
