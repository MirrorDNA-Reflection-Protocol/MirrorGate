"""
Consent Manager — Permission Model with Decay

Permissions have:
- Scope (device, filesystem, network, vault, messaging)
- Action (read, write, delete, execute, send)
- Target (path pattern or resource)
- Expiry (timestamp or session-only)
- Escalation triggers
- Context lock (work/reflect/play/null)
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
import json


class PermissionScope(Enum):
    DEVICE = "device"
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    VAULT = "vault"
    MESSAGING = "messaging"


class PermissionAction(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    SEND = "send"


class ContextMode(Enum):
    WORK = "work"
    REFLECT = "reflect"
    PLAY = "play"
    NULL = "null"  # No context lock


@dataclass
class EscalationTrigger:
    """Condition that triggers escalation."""
    trigger_type: str  # "action_count", "target_contains", "time_of_day"
    threshold: Any  # Depends on trigger_type
    
    def to_dict(self) -> dict:
        return {"type": self.trigger_type, "threshold": self.threshold}
    
    @classmethod
    def from_dict(cls, data: dict) -> "EscalationTrigger":
        return cls(trigger_type=data["type"], threshold=data["threshold"])


@dataclass
class Permission:
    """A permission grant with decay."""
    id: str
    scope: PermissionScope
    action: PermissionAction
    target: str  # Path pattern or resource identifier
    granted_at: datetime
    expires_at: Optional[datetime]  # None = session-only
    renewable: bool = False
    escalation_triggers: List[EscalationTrigger] = field(default_factory=list)
    context_lock: ContextMode = ContextMode.NULL
    granted_by: str = "system"
    reason: str = ""


DB_PATH = Path.home() / ".mirrordna" / "oversight" / "permissions.db"


class ConsentManager:
    """
    Manages permissions with expiry and escalation.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS permissions (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    granted_at TEXT NOT NULL,
                    expires_at TEXT,
                    renewable INTEGER DEFAULT 0,
                    escalation_triggers TEXT,
                    context_lock TEXT DEFAULT 'null',
                    granted_by TEXT DEFAULT 'system',
                    reason TEXT DEFAULT ''
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS permission_usage (
                    permission_id TEXT,
                    used_at TEXT,
                    action_count INTEGER DEFAULT 1,
                    FOREIGN KEY (permission_id) REFERENCES permissions(id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_permissions_scope_action 
                ON permissions(scope, action)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_permissions_expires 
                ON permissions(expires_at)
            """)
            conn.commit()
    
    def grant_permission(
        self,
        scope: PermissionScope,
        action: PermissionAction,
        target: str,
        expires_at: Optional[datetime] = None,
        renewable: bool = False,
        escalation_triggers: Optional[List[EscalationTrigger]] = None,
        context_lock: ContextMode = ContextMode.NULL,
        granted_by: str = "system",
        reason: str = ""
    ) -> Permission:
        """Grant a new permission."""
        perm_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        permission = Permission(
            id=perm_id,
            scope=scope,
            action=action,
            target=target,
            granted_at=now,
            expires_at=expires_at,
            renewable=renewable,
            escalation_triggers=escalation_triggers or [],
            context_lock=context_lock,
            granted_by=granted_by,
            reason=reason
        )
        
        triggers_json = json.dumps([t.to_dict() for t in permission.escalation_triggers])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO permissions 
                (id, scope, action, target, granted_at, expires_at, renewable,
                 escalation_triggers, context_lock, granted_by, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                permission.id,
                permission.scope.value,
                permission.action.value,
                permission.target,
                permission.granted_at.isoformat(),
                permission.expires_at.isoformat() if permission.expires_at else None,
                1 if permission.renewable else 0,
                triggers_json,
                permission.context_lock.value,
                permission.granted_by,
                permission.reason
            ))
            conn.commit()
        
        return permission
    
    def revoke_permission(self, permission_id: str) -> bool:
        """Revoke a permission by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM permissions WHERE id = ?",
                (permission_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def check_permission(
        self,
        scope: PermissionScope,
        action: PermissionAction,
        target: str,
        context: Optional[ContextMode] = None
    ) -> bool:
        """
        Check if a permission exists for the given scope/action/target.
        Returns True if allowed, False otherwise.
        """
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Find matching permissions (not expired, matching context or no context lock)
            cursor = conn.execute("""
                SELECT id, target, context_lock FROM permissions
                WHERE scope = ? AND action = ?
                AND (expires_at IS NULL OR expires_at > ?)
            """, (scope.value, action.value, now))
            
            for row in cursor:
                perm_id, perm_target, context_lock = row
                
                # Check target pattern match
                if self._match_target(target, perm_target):
                    # Check context lock
                    if context_lock == "null" or (context and context.value == context_lock):
                        # Record usage
                        self._record_usage(perm_id)
                        return True
        
        return False
    
    def _match_target(self, actual: str, pattern: str) -> bool:
        """Check if actual target matches pattern (supports * wildcard)."""
        if pattern == "*":
            return True
        if pattern.endswith("/*"):
            prefix = pattern[:-1]
            return actual.startswith(prefix)
        return actual == pattern
    
    def _record_usage(self, permission_id: str):
        """Record permission usage for escalation tracking."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO permission_usage (permission_id, used_at, action_count)
                VALUES (?, ?, 1)
            """, (permission_id, now))
            conn.commit()
    
    def get_permission(self, permission_id: str) -> Optional[Permission]:
        """Get a permission by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM permissions WHERE id = ?",
                (permission_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_permission(row)
        return None
    
    def list_permissions(
        self,
        scope: Optional[PermissionScope] = None,
        include_expired: bool = False
    ) -> List[Permission]:
        """List all permissions, optionally filtered by scope."""
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            if scope:
                if include_expired:
                    cursor = conn.execute(
                        "SELECT * FROM permissions WHERE scope = ?",
                        (scope.value,)
                    )
                else:
                    cursor = conn.execute("""
                        SELECT * FROM permissions 
                        WHERE scope = ? AND (expires_at IS NULL OR expires_at > ?)
                    """, (scope.value, now))
            else:
                if include_expired:
                    cursor = conn.execute("SELECT * FROM permissions")
                else:
                    cursor = conn.execute("""
                        SELECT * FROM permissions 
                        WHERE expires_at IS NULL OR expires_at > ?
                    """, (now,))
            
            return [self._row_to_permission(row) for row in cursor]
    
    def _row_to_permission(self, row) -> Permission:
        """Convert a database row to a Permission object."""
        return Permission(
            id=row[0],
            scope=PermissionScope(row[1]),
            action=PermissionAction(row[2]),
            target=row[3],
            granted_at=datetime.fromisoformat(row[4]),
            expires_at=datetime.fromisoformat(row[5]) if row[5] else None,
            renewable=bool(row[6]),
            escalation_triggers=[
                EscalationTrigger.from_dict(t) 
                for t in json.loads(row[7]) if row[7]
            ] if row[7] else [],
            context_lock=ContextMode(row[8]) if row[8] else ContextMode.NULL,
            granted_by=row[9] if len(row) > 9 else "system",
            reason=row[10] if len(row) > 10 else ""
        )
    
    def decay_expired(self) -> int:
        """Remove expired permissions. Returns count of removed."""
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # First, handle renewable permissions
            cursor = conn.execute("""
                SELECT id FROM permissions 
                WHERE expires_at IS NOT NULL 
                AND expires_at <= ? 
                AND renewable = 1
            """, (now,))
            
            # For now, just log renewable ones (could extend expiry)
            renewable_count = len(cursor.fetchall())
            
            # Delete non-renewable expired permissions
            cursor = conn.execute("""
                DELETE FROM permissions 
                WHERE expires_at IS NOT NULL 
                AND expires_at <= ? 
                AND renewable = 0
            """, (now,))
            deleted = cursor.rowcount
            
            # Clean up usage records for deleted permissions
            conn.execute("""
                DELETE FROM permission_usage 
                WHERE permission_id NOT IN (SELECT id FROM permissions)
            """)
            
            conn.commit()
            return deleted
    
    def check_escalation_triggers(self, permission_id: str) -> List[str]:
        """
        Check if any escalation triggers have fired for a permission.
        Returns list of triggered conditions.
        """
        triggered = []
        permission = self.get_permission(permission_id)
        if not permission:
            return triggered
        
        # Get usage count in last hour
        one_hour_ago = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM permission_usage
                WHERE permission_id = ?
            """, (permission_id,))
            usage_count = cursor.fetchone()[0]
        
        for trigger in permission.escalation_triggers:
            if trigger.trigger_type == "action_count":
                if usage_count >= trigger.threshold:
                    triggered.append(f"action_count >= {trigger.threshold}")
            
            elif trigger.trigger_type == "target_contains":
                if any(kw in permission.target for kw in trigger.threshold):
                    triggered.append(f"target_contains: {trigger.threshold}")
            
            elif trigger.trigger_type == "time_of_day":
                now = datetime.now()
                start, end = trigger.threshold  # e.g., ("22:00", "06:00")
                # Simplified check - could be more robust
                current_time = now.strftime("%H:%M")
                if start <= current_time or current_time <= end:
                    triggered.append(f"time_of_day: {start}-{end}")
        
        return triggered
