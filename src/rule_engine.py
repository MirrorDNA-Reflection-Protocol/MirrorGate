"""
Rule Engine — Hard Boundaries

Rules are Paul-editable YAML.
Types: hard_block, soft_warn, log_only
"""

import yaml
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Any, Dict
import re


class RuleType(Enum):
    HARD_BLOCK = "hard_block"
    SOFT_WARN = "soft_warn"
    LOG_ONLY = "log_only"


class RuleConditionScope(Enum):
    ACTION = "action"
    CONTENT = "content"
    TIMING = "timing"
    FREQUENCY = "frequency"


class RuleConditionOperator(Enum):
    CONTAINS = "contains"
    MATCHES = "matches"  # Regex match
    EXCEEDS = "exceeds"
    DURING = "during"


class RuleResponseAction(Enum):
    BLOCK = "block"
    WARN = "warn"
    ESCALATE = "escalate"
    LOG = "log"


class ContextMode(Enum):
    ALL = "all"
    WORK = "work"
    REFLECT = "reflect"
    PLAY = "play"


@dataclass
class RuleCondition:
    """A condition that triggers a rule."""
    scope: RuleConditionScope
    operator: RuleConditionOperator
    value: Any
    
    def evaluate(self, action: str, content: str, context: dict) -> bool:
        """Evaluate if this condition matches."""
        if self.scope == RuleConditionScope.ACTION:
            if self.operator == RuleConditionOperator.CONTAINS:
                return self.value.lower() in action.lower()
            elif self.operator == RuleConditionOperator.MATCHES:
                return bool(re.search(self.value, action, re.IGNORECASE))
        
        elif self.scope == RuleConditionScope.CONTENT:
            if self.operator == RuleConditionOperator.CONTAINS:
                return self.value.lower() in content.lower()
            elif self.operator == RuleConditionOperator.MATCHES:
                return bool(re.search(self.value, content, re.IGNORECASE))
        
        elif self.scope == RuleConditionScope.TIMING:
            if self.operator == RuleConditionOperator.DURING:
                # value is tuple of (start_time, end_time) like ("22:00", "06:00")
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                start, end = self.value
                if start <= end:
                    return start <= current_time <= end
                else:  # Crosses midnight
                    return current_time >= start or current_time <= end
        
        elif self.scope == RuleConditionScope.FREQUENCY:
            if self.operator == RuleConditionOperator.EXCEEDS:
                # value is (count, period_minutes)
                # context should have "action_count" and "period_minutes"
                count, period = self.value
                actual_count = context.get("action_count", 0)
                return actual_count > count
        
        return False


@dataclass
class RuleResponse:
    """What happens when a rule triggers."""
    action: RuleResponseAction
    message: str


@dataclass 
class Rule:
    """A rule defining a hard boundary."""
    id: str
    name: str
    rule_type: RuleType
    priority: int  # Higher = evaluated first
    condition: RuleCondition
    response: RuleResponse
    context: ContextMode = ContextMode.ALL
    created_by: str = "system"
    rationale: str = ""
    created_at: Optional[datetime] = None
    
    def matches_context(self, current_context: str) -> bool:
        """Check if rule applies in current context."""
        if self.context == ContextMode.ALL:
            return True
        return self.context.value == current_context


RULES_FILE = Path.home() / ".mirrordna" / "oversight" / "rules.yaml"
DEFAULT_RULES_FILE = Path(__file__).parent.parent / "config" / "rules.yaml"


class RuleEngine:
    """
    Evaluates rules against actions and content.
    Rules are immutable once created (versioning, not editing).
    """
    
    def __init__(self, rules_path: Optional[Path] = None):
        self.rules_path = rules_path or RULES_FILE
        self.rules: List[Rule] = []
        self._load_rules()
    
    def _load_rules(self):
        """Load rules from YAML file."""
        # Try user rules first, fall back to defaults
        rules_file = self.rules_path
        if not rules_file.exists():
            rules_file = DEFAULT_RULES_FILE
            if not rules_file.exists():
                self.rules = self._get_default_rules()
                return
        
        try:
            with open(rules_file, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            self.rules = []
            for rule_data in data.get("rules", []):
                rule = self._parse_rule(rule_data)
                if rule:
                    self.rules.append(rule)
            
            # Sort by priority (higher first)
            self.rules.sort(key=lambda r: r.priority, reverse=True)
        except Exception as e:
            print(f"Warning: Failed to load rules from {rules_file}: {e}")
            self.rules = self._get_default_rules()
    
    def _parse_rule(self, data: dict) -> Optional[Rule]:
        """Parse a rule from dictionary."""
        try:
            condition_data = data.get("condition", {})
            condition = RuleCondition(
                scope=RuleConditionScope(condition_data.get("scope", "action")),
                operator=RuleConditionOperator(condition_data.get("operator", "contains")),
                value=condition_data.get("value")
            )
            
            response_data = data.get("response", {})
            response = RuleResponse(
                action=RuleResponseAction(response_data.get("action", "log")),
                message=response_data.get("message", "")
            )
            
            return Rule(
                id=data.get("id", str(hash(data.get("name", "")))),
                name=data.get("name", "Unnamed Rule"),
                rule_type=RuleType(data.get("type", "log_only")),
                priority=data.get("priority", 0),
                condition=condition,
                response=response,
                context=ContextMode(data.get("context", "all")),
                created_by=data.get("created_by", "paul"),
                rationale=data.get("rationale", "")
            )
        except Exception as e:
            print(f"Warning: Failed to parse rule: {e}")
            return None
    
    def _get_default_rules(self) -> List[Rule]:
        """Get built-in default rules."""
        return [
            Rule(
                id="default-1",
                name="No late-night file deletion",
                rule_type=RuleType.HARD_BLOCK,
                priority=100,
                condition=RuleCondition(
                    scope=RuleConditionScope.TIMING,
                    operator=RuleConditionOperator.DURING,
                    value=("22:00", "06:00")
                ),
                response=RuleResponse(
                    action=RuleResponseAction.BLOCK,
                    message="File deletions blocked during night hours (22:00-06:00)"
                ),
                context=ContextMode.ALL,
                created_by="system",
                rationale="Prevent accidental destructive actions during low-alertness hours"
            ),
            Rule(
                id="default-2",
                name="High-frequency tool call warning",
                rule_type=RuleType.SOFT_WARN,
                priority=50,
                condition=RuleCondition(
                    scope=RuleConditionScope.FREQUENCY,
                    operator=RuleConditionOperator.EXCEEDS,
                    value=(20, 5)  # >20 calls in 5 minutes
                ),
                response=RuleResponse(
                    action=RuleResponseAction.WARN,
                    message="High frequency of tool calls detected - possible runaway"
                ),
                context=ContextMode.ALL,
                created_by="system",
                rationale="Detect potential infinite loops or runaway behavior"
            ),
            Rule(
                id="default-3",
                name="Block credential access",
                rule_type=RuleType.HARD_BLOCK,
                priority=100,
                condition=RuleCondition(
                    scope=RuleConditionScope.CONTENT,
                    operator=RuleConditionOperator.MATCHES,
                    value=r"(?i)(password|api[_\s]?key|secret[_\s]?key|private[_\s]?key|credentials?)"
                ),
                response=RuleResponse(
                    action=RuleResponseAction.BLOCK,
                    message="Access to credential-related content blocked"
                ),
                context=ContextMode.ALL,
                created_by="system",
                rationale="Prevent accidental exposure of sensitive credentials"
            ),
        ]
    
    def evaluate_rules(
        self,
        action: str,
        content: str,
        context: str = "all",
        frequency_context: Optional[dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all rules against the given action/content.
        
        Returns list of triggered rules with their responses.
        """
        triggered = []
        eval_context = frequency_context or {}
        
        for rule in self.rules:
            # Check context
            if not rule.matches_context(context):
                continue
            
            # Evaluate condition
            if rule.condition.evaluate(action, content, eval_context):
                triggered.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "type": rule.rule_type.value,
                    "response_action": rule.response.action.value,
                    "message": rule.response.message,
                    "priority": rule.priority
                })
        
        return triggered
    
    def add_rule(self, rule: Rule) -> bool:
        """
        Add a new rule. Rules are immutable - this creates a new version.
        Saves to rules file.
        """
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        return self._save_rules()
    
    def _save_rules(self) -> bool:
        """Save rules to YAML file."""
        try:
            self.rules_path.parent.mkdir(parents=True, exist_ok=True)
            
            rules_data = {
                "version": "1.0",
                "last_modified": datetime.now().isoformat(),
                "rules": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "type": r.rule_type.value,
                        "priority": r.priority,
                        "condition": {
                            "scope": r.condition.scope.value,
                            "operator": r.condition.operator.value,
                            "value": r.condition.value
                        },
                        "response": {
                            "action": r.response.action.value,
                            "message": r.response.message
                        },
                        "context": r.context.value,
                        "created_by": r.created_by,
                        "rationale": r.rationale
                    }
                    for r in self.rules
                ]
            }
            
            with open(self.rules_path, 'w') as f:
                yaml.dump(rules_data, f, default_flow_style=False, sort_keys=False)
            
            return True
        except Exception as e:
            print(f"Failed to save rules: {e}")
            return False
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
    
    def list_rules(self, rule_type: Optional[RuleType] = None) -> List[Rule]:
        """List all rules, optionally filtered by type."""
        if rule_type:
            return [r for r in self.rules if r.rule_type == rule_type]
        return self.rules.copy()
