"""
Gate 5: Intent Classification & Routing
Routes to: TRANSACTIONAL | REFLECTIVE | PLAY
Determines processing mode BEFORE inference.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import BaseGate, GateOutput, GateResult, IntentMode


@dataclass
class IntentSignal:
    """A signal that indicates intent type."""
    pattern: str  # Regex pattern
    mode: IntentMode
    weight: float  # Contribution to classification (0.0-1.0)


# Intent classification signals
INTENT_SIGNALS = [
    # TRANSACTIONAL: Facts, math, syntax, lookups, code execution
    IntentSignal(r"(?i)(what\s+is|define|explain|how\s+does)", IntentMode.TRANSACTIONAL, 0.7),
    IntentSignal(r"(?i)(calculate|compute|solve|evaluate)", IntentMode.TRANSACTIONAL, 0.9),
    IntentSignal(r"(?i)(convert|translate\s+(from|to)|format)", IntentMode.TRANSACTIONAL, 0.8),
    IntentSignal(r"(?i)(list|enumerate|show\s+(me\s+)?(all|the))", IntentMode.TRANSACTIONAL, 0.6),
    IntentSignal(r"(?i)(code|implement|write\s+a?\s*(function|class|script))", IntentMode.TRANSACTIONAL, 0.85),
    IntentSignal(r"(?i)(fix|debug|error|bug|exception)", IntentMode.TRANSACTIONAL, 0.8),
    IntentSignal(r"(?i)(syntax|compile|run|execute)", IntentMode.TRANSACTIONAL, 0.75),
    IntentSignal(r"(?i)(api|endpoint|request|response)", IntentMode.TRANSACTIONAL, 0.7),
    IntentSignal(r"(?i)\b\d+\s*[\+\-\*\/\^]\s*\d+\b", IntentMode.TRANSACTIONAL, 0.9),  # Math expressions
    IntentSignal(r"```\w*\n", IntentMode.TRANSACTIONAL, 0.8),  # Code blocks
    
    # REFLECTIVE: Ambiguity, decisions, emotion, ethics, "should I"
    IntentSignal(r"(?i)(should\s+i|should\s+we|ought\s+to)", IntentMode.REFLECTIVE, 0.9),
    IntentSignal(r"(?i)(what\s+do\s+you\s+think|your\s+opinion)", IntentMode.REFLECTIVE, 0.85),
    IntentSignal(r"(?i)(is\s+it\s+(right|wrong|ethical|moral))", IntentMode.REFLECTIVE, 0.9),
    IntentSignal(r"(?i)(help\s+me\s+(decide|choose|think))", IntentMode.REFLECTIVE, 0.85),
    IntentSignal(r"(?i)(dilemma|trade-?off|pros?\s+and\s+cons?)", IntentMode.REFLECTIVE, 0.8),
    IntentSignal(r"(?i)(feel(s|ing)?|emotion(al)?|stress|anxious|worried)", IntentMode.REFLECTIVE, 0.7),
    IntentSignal(r"(?i)(meaning|purpose|value|matter)", IntentMode.REFLECTIVE, 0.6),
    IntentSignal(r"(?i)(advice|guidance|recommend)", IntentMode.REFLECTIVE, 0.75),
    IntentSignal(r"(?i)(confused|uncertain|unsure|don'?t\s+know)", IntentMode.REFLECTIVE, 0.7),
    IntentSignal(r"(?i)(relationship|friend|family|colleague)", IntentMode.REFLECTIVE, 0.5),
    
    # PLAY: Creative, exploratory, hypothetical, "what if"
    IntentSignal(r"(?i)(what\s+if|imagine|suppose|pretend)", IntentMode.PLAY, 0.9),
    IntentSignal(r"(?i)(creative|story|poem|fiction|novel)", IntentMode.PLAY, 0.85),
    IntentSignal(r"(?i)(fun|funny|joke|humor)", IntentMode.PLAY, 0.7),
    IntentSignal(r"(?i)(brainstorm|ideas?|possibilities)", IntentMode.PLAY, 0.65),
    IntentSignal(r"(?i)(game|play|challenge|puzzle)", IntentMode.PLAY, 0.75),
    IntentSignal(r"(?i)(hypothetic(al)?|thought\s+experiment)", IntentMode.PLAY, 0.8),
    IntentSignal(r"(?i)(explore|experiment|try\s+out)", IntentMode.PLAY, 0.6),
    IntentSignal(r"(?i)(wild|crazy|outlandish|absurd)", IntentMode.PLAY, 0.7),
    IntentSignal(r"(?i)(dream|fantasy|magical)", IntentMode.PLAY, 0.75),
    IntentSignal(r"(?i)(write\s+(me\s+)?a\s+(story|poem|song))", IntentMode.PLAY, 0.9),
]


class Gate5Intent(BaseGate):
    """
    Intent classification gate.
    Routes requests to appropriate processing mode before inference.
    
    This is a non-blocking gate - it always passes but provides routing info.
    """
    
    name = "Gate5_Intent"
    is_blocking = False  # Non-blocking: provides routing, doesn't reject
    
    def __init__(self, signals: Optional[List[IntentSignal]] = None):
        self.signals = signals or INTENT_SIGNALS
        
        # Pre-compile patterns
        self._compiled = [
            (signal, re.compile(signal.pattern))
            for signal in self.signals
        ]
    
    def _classify(self, content: str) -> Tuple[IntentMode, float, Dict[IntentMode, float]]:
        """
        Classify content into intent mode.
        Returns (mode, confidence, score_breakdown).
        """
        scores: Dict[IntentMode, float] = {
            IntentMode.TRANSACTIONAL: 0.0,
            IntentMode.REFLECTIVE: 0.0,
            IntentMode.PLAY: 0.0,
        }
        match_counts: Dict[IntentMode, int] = {m: 0 for m in IntentMode}
        
        # Score each signal
        for signal, compiled in self._compiled:
            if compiled.search(content):
                scores[signal.mode] += signal.weight
                match_counts[signal.mode] += 1
        
        # Normalize scores
        total_score = sum(scores.values())
        if total_score == 0:
            # No clear signals - default to TRANSACTIONAL with low confidence
            return IntentMode.TRANSACTIONAL, 0.3, scores
        
        normalized = {mode: score / total_score for mode, score in scores.items()}
        
        # Determine winner
        winner = max(normalized.items(), key=lambda x: x[1])
        mode = winner[0]
        
        # Calculate confidence based on margin over second place
        sorted_scores = sorted(normalized.values(), reverse=True)
        if len(sorted_scores) > 1:
            margin = sorted_scores[0] - sorted_scores[1]
            # Confidence = winner's share + margin bonus
            confidence = min(1.0, winner[1] + margin * 0.5)
        else:
            confidence = winner[1]
        
        return mode, confidence, normalized
    
    def _get_structural_hints(self, content: str) -> Dict[str, any]:
        """Get structural hints about the content."""
        hints = {}
        
        # Question detection
        hints["is_question"] = bool(re.search(r'\?(\s|$)', content))
        
        # Code presence
        hints["has_code"] = bool(re.search(r'```|`[^`]+`', content))
        
        # Length category
        word_count = len(content.split())
        if word_count < 20:
            hints["length"] = "short"
        elif word_count < 100:
            hints["length"] = "medium"
        else:
            hints["length"] = "long"
        
        # Urgency signals
        hints["urgent"] = bool(re.search(r'(?i)(urgent|asap|immediately|quick(ly)?)', content))
        
        return hints
    
    def evaluate(self, request: dict, session_token: Optional[str] = None) -> GateOutput:
        """Classify intent and provide routing information."""
        content = request.get("content", "")
        
        if not content:
            return GateOutput(
                gate_name=self.name,
                result=GateResult.PASS,
                metadata={
                    "mode": IntentMode.TRANSACTIONAL.value,
                    "confidence": 0.5,
                    "reason": "Empty content - defaulting to TRANSACTIONAL"
                }
            )
        
        mode, confidence, scores = self._classify(content)
        structural_hints = self._get_structural_hints(content)
        
        # Adjust based on structural hints
        if structural_hints.get("has_code") and mode != IntentMode.TRANSACTIONAL:
            # Code presence is a strong transactional signal
            if confidence < 0.7:
                mode = IntentMode.TRANSACTIONAL
                confidence = 0.6
        
        return GateOutput(
            gate_name=self.name,
            result=GateResult.PASS,
            metadata={
                "mode": mode.value,
                "confidence": round(confidence, 3),
                "score_breakdown": {m.value: round(s, 3) for m, s in scores.items()},
                "structural_hints": structural_hints
            }
        )
