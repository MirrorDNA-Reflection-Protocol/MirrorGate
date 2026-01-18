"""
Gate 0: Transport & Rate Control
- Replay protection (request deduplication by hash)
- Rate limiting (configurable per-session, per-minute)
- Session binding (token validation)
"""

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Dict, List, Optional

from . import BaseGate, GateOutput, GateResult


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    ttl_seconds: int = 60  # Window for tracking
    replay_ttl_seconds: int = 300  # How long to remember request hashes


class Gate0Transport(BaseGate):
    """
    Transport layer protection:
    - Replay protection via request hashing
    - Rate limiting per session
    - Session token validation
    """
    
    name = "Gate0_Transport"
    is_blocking = True
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        
        # Request hash → timestamp for replay protection
        self._request_hashes: Dict[str, float] = {}
        
        # Session → list of request timestamps for rate limiting
        self._rate_windows: Dict[str, List[float]] = defaultdict(list)
        
        # Valid session tokens (in production, this would query a session store)
        self._valid_sessions: set = set()
        
        self._lock = Lock()
    
    def register_session(self, token: str):
        """Register a valid session token."""
        self._valid_sessions.add(token)
    
    def invalidate_session(self, token: str):
        """Invalidate a session token."""
        self._valid_sessions.discard(token)
        with self._lock:
            self._rate_windows.pop(token, None)
    
    def _compute_request_hash(self, request: dict) -> str:
        """Compute a unique hash for the request content."""
        content = request.get("content", "")
        # Include timestamp components that matter (truncate to minute for dedup)
        minute_bucket = int(time.time() / 60)
        hash_input = f"{content}:{minute_bucket}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:32]
    
    def _cleanup_expired(self, now: float):
        """Clean up expired entries."""
        # Clean request hashes
        expired_hashes = [
            h for h, ts in self._request_hashes.items()
            if now - ts > self.config.replay_ttl_seconds
        ]
        for h in expired_hashes:
            del self._request_hashes[h]
        
        # Clean rate windows
        cutoff = now - self.config.ttl_seconds
        for session, timestamps in self._rate_windows.items():
            self._rate_windows[session] = [
                ts for ts in timestamps if ts > cutoff
            ]
    
    def _check_replay(self, request: dict, now: float) -> bool:
        """Check if this is a replay attack. Returns True if replay detected."""
        request_hash = self._compute_request_hash(request)
        
        with self._lock:
            if request_hash in self._request_hashes:
                return True
            self._request_hashes[request_hash] = now
        return False
    
    def _check_rate_limit(self, session_token: str, now: float) -> bool:
        """Check if rate limit exceeded. Returns True if exceeded."""
        with self._lock:
            # Clean old entries
            cutoff = now - self.config.ttl_seconds
            self._rate_windows[session_token] = [
                ts for ts in self._rate_windows[session_token]
                if ts > cutoff
            ]
            
            # Check current count
            if len(self._rate_windows[session_token]) >= self.config.requests_per_minute:
                return True
            
            # Record this request
            self._rate_windows[session_token].append(now)
        return False
    
    def _validate_session(self, session_token: Optional[str]) -> bool:
        """Validate session token. Returns True if valid."""
        if session_token is None:
            return False
        # In production: query session store
        # For now: allow if token looks valid (non-empty, reasonable length)
        # TODO: review - integrate with actual session store
        return len(session_token) >= 8
    
    def evaluate(self, request: dict, session_token: Optional[str] = None) -> GateOutput:
        """Evaluate transport layer protections."""
        now = time.time()
        violations = []
        
        # Periodic cleanup
        self._cleanup_expired(now)
        
        # Check 1: Session validation
        if not self._validate_session(session_token):
            return GateOutput(
                gate_name=self.name,
                result=GateResult.SESSION_INVALID,
                violations=["Invalid or missing session token"],
                metadata={"session_token": session_token[:8] + "..." if session_token else None}
            )
        
        # Check 2: Replay protection
        if self._check_replay(request, now):
            return GateOutput(
                gate_name=self.name,
                result=GateResult.REPLAY_REJECTED,
                violations=["Duplicate request detected within TTL window"],
                metadata={"ttl_seconds": self.config.replay_ttl_seconds}
            )
        
        # Check 3: Rate limiting
        if self._check_rate_limit(session_token, now):
            return GateOutput(
                gate_name=self.name,
                result=GateResult.RATE_LIMITED,
                violations=[f"Rate limit exceeded: {self.config.requests_per_minute}/min"],
                metadata={
                    "limit": self.config.requests_per_minute,
                    "window_seconds": self.config.ttl_seconds
                }
            )
        
        return GateOutput(
            gate_name=self.name,
            result=GateResult.PASS,
            metadata={"session_valid": True, "rate_remaining": self._get_remaining(session_token)}
        )
    
    def _get_remaining(self, session_token: str) -> int:
        """Get remaining requests in current window."""
        with self._lock:
            current = len(self._rate_windows.get(session_token, []))
            return max(0, self.config.requests_per_minute - current)
