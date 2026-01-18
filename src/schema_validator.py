"""
Schema Validator — Structural Output Checks

Validates:
- JSON responses match expected schema
- Markdown responses have required sections
- Code responses are syntactically valid
"""

import json
import re
import ast
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import yaml


class OutputFormat(Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    CODE = "code"
    TEXT = "text"


@dataclass
class ValidationResult:
    """Result of schema validation."""
    valid: bool
    format_detected: OutputFormat
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


# Default schemas
DEFAULT_SCHEMAS = {
    "json_response": {
        "required_fields": ["status", "data"],
        "forbidden_fields": ["password", "api_key", "secret", "token"],
    },
    "markdown_response": {
        "max_heading_depth": 3,
        "required_markers": [],  # ["⟡"] for reflective mode
    },
    "code_response": {
        "languages": ["python", "javascript", "bash", "json", "yaml"],
        "validate_syntax": True,
    }
}

SCHEMA_FILE = Path(__file__).parent.parent / "config" / "output_schemas.yaml"


class SchemaValidator:
    """
    Validates output against structural schemas.
    """
    
    def __init__(self, schema_path: Optional[Path] = None):
        self.schema_path = schema_path or SCHEMA_FILE
        self.schemas = self._load_schemas()
    
    def _load_schemas(self) -> Dict[str, Any]:
        """Load schemas from YAML file or use defaults."""
        if self.schema_path.exists():
            try:
                with open(self.schema_path, 'r') as f:
                    data = yaml.safe_load(f) or {}
                return data.get("schemas", DEFAULT_SCHEMAS)
            except Exception as e:
                print(f"Warning: Failed to load schemas: {e}")
        return DEFAULT_SCHEMAS
    
    def detect_format(self, content: str) -> OutputFormat:
        """Detect the format of the content."""
        content = content.strip()
        
        # Check for JSON
        if content.startswith('{') or content.startswith('['):
            try:
                json.loads(content)
                return OutputFormat.JSON
            except json.JSONDecodeError:
                pass
        
        # Check for code blocks
        if content.startswith('```') or content.startswith('def ') or content.startswith('function '):
            return OutputFormat.CODE
        
        # Check for markdown
        if re.search(r'^#+\s', content, re.MULTILINE) or re.search(r'\[.+\]\(.+\)', content):
            return OutputFormat.MARKDOWN
        
        return OutputFormat.TEXT
    
    def validate(self, content: str, expected_format: Optional[OutputFormat] = None) -> ValidationResult:
        """
        Validate content against schema.
        
        Args:
            content: The content to validate
            expected_format: Expected format (auto-detected if None)
            
        Returns:
            ValidationResult with status and any errors
        """
        detected = expected_format or self.detect_format(content)
        errors = []
        warnings = []
        metadata = {"format": detected.value}
        
        if detected == OutputFormat.JSON:
            json_errors, json_warnings = self._validate_json(content)
            errors.extend(json_errors)
            warnings.extend(json_warnings)
        
        elif detected == OutputFormat.MARKDOWN:
            md_errors, md_warnings = self._validate_markdown(content)
            errors.extend(md_errors)
            warnings.extend(md_warnings)
        
        elif detected == OutputFormat.CODE:
            code_errors, code_warnings, lang = self._validate_code(content)
            errors.extend(code_errors)
            warnings.extend(code_warnings)
            metadata["detected_language"] = lang
        
        return ValidationResult(
            valid=len(errors) == 0,
            format_detected=detected,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def _validate_json(self, content: str) -> Tuple[List[str], List[str]]:
        """Validate JSON content."""
        errors = []
        warnings = []
        schema = self.schemas.get("json_response", {})
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")
            return errors, warnings
        
        if not isinstance(data, dict):
            return errors, warnings  # Array or primitive - no field checks
        
        # Check required fields
        required = schema.get("required_fields", [])
        for field in required:
            if field not in data:
                warnings.append(f"Missing recommended field: {field}")
        
        # Check forbidden fields
        forbidden = schema.get("forbidden_fields", [])
        for field in forbidden:
            if field in data:
                errors.append(f"Forbidden field present: {field}")
            # Also check nested
            for key in data:
                if field.lower() in str(key).lower():
                    errors.append(f"Potentially sensitive field: {key}")
        
        return errors, warnings
    
    def _validate_markdown(self, content: str) -> Tuple[List[str], List[str]]:
        """Validate Markdown content."""
        errors = []
        warnings = []
        schema = self.schemas.get("markdown_response", {})
        
        # Check heading depth
        max_depth = schema.get("max_heading_depth", 6)
        headings = re.findall(r'^(#+)\s', content, re.MULTILINE)
        for h in headings:
            if len(h) > max_depth:
                warnings.append(f"Heading depth {len(h)} exceeds max {max_depth}")
        
        # Check required markers
        required_markers = schema.get("required_markers", [])
        for marker in required_markers:
            if marker not in content:
                warnings.append(f"Missing required marker: {marker}")
        
        # Check for broken links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        for text, url in links:
            if not url.strip():
                errors.append(f"Empty link URL: [{text}]()")
            if url.startswith('javascript:'):
                errors.append(f"Dangerous link: {url}")
        
        return errors, warnings
    
    def _validate_code(self, content: str) -> Tuple[List[str], List[str], str]:
        """Validate code content."""
        errors = []
        warnings = []
        schema = self.schemas.get("code_response", {})
        
        # Extract code from markdown blocks if present
        code_match = re.search(r'```(\w+)?\n(.*?)```', content, re.DOTALL)
        if code_match:
            lang = code_match.group(1) or "unknown"
            code = code_match.group(2)
        else:
            lang = "python"  # Default assumption
            code = content
        
        # Check if language is allowed
        allowed_langs = schema.get("languages", [])
        if allowed_langs and lang not in allowed_langs and lang != "unknown":
            warnings.append(f"Language '{lang}' not in allowed list")
        
        # Syntax validation
        if schema.get("validate_syntax", True):
            if lang == "python":
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    errors.append(f"Python syntax error: {e}")
            
            elif lang == "json":
                try:
                    json.loads(code)
                except json.JSONDecodeError as e:
                    errors.append(f"JSON syntax error: {e}")
        
        return errors, warnings, lang


# Singleton instance
_validator: Optional[SchemaValidator] = None


def get_validator() -> SchemaValidator:
    """Get or create schema validator singleton."""
    global _validator
    if _validator is None:
        _validator = SchemaValidator()
    return _validator


def validate_output(content: str, expected_format: Optional[str] = None) -> ValidationResult:
    """Convenience function for output validation."""
    fmt = OutputFormat(expected_format) if expected_format else None
    return get_validator().validate(content, fmt)
