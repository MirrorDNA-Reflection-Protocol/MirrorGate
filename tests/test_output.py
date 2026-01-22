"""
Tests for Output Enforcement
Covers output_enforcement.py, schema_validator.py, and postfilters.
"""

import pytest

from src.output_enforcement import (
    OutputEnforcement,
    EnforcementResult,
    enforce_output,
    FALLBACK_RESPONSE
)
from src.schema_validator import (
    SchemaValidator,
    OutputFormat,
    validate_output
)
from src.postfilters import run_postfilters


class TestOutputEnforcement:
    """Test multi-pass output enforcement."""
    
    @pytest.fixture
    def enforcer(self):
        return OutputEnforcement()
    
    def test_clean_output_passes(self, enforcer):
        """Test that clean output passes without changes."""
        output = "Here is some helpful information about Python lists."
        result = enforcer.enforce(output)
        
        assert result.result == EnforcementResult.PASS
        assert result.output == output
        assert result.rewrites == 0
    
    def test_forbidden_pattern_blocks(self, enforcer):
        """Test that forbidden patterns cause blocking."""
        output = "Your api_key = 'sk-1234567890abcdef'"
        result = enforcer.enforce(output)
        
        assert result.result == EnforcementResult.BLOCK
        assert result.output == FALLBACK_RESPONSE
        assert "forbidden" in result.violations[0]
    
    def test_dangerous_command_blocks(self, enforcer):
        """Test that dangerous commands are blocked."""
        output = "Just run rm -rf / to clean up"
        result = enforcer.enforce(output)
        
        assert result.result == EnforcementResult.BLOCK
    
    def test_prescriptive_language_rewritten(self, enforcer):
        """Test that prescriptive language is rewritten."""
        output = "You should definitely do this first."
        result = enforcer.enforce(output)
        
        assert result.result == EnforcementResult.REWRITE
        assert "should" not in result.output.lower() or "might consider" in result.output.lower()
        assert result.rewrites > 0
    
    def test_overconfidence_rewritten(self, enforcer):
        """Test that overconfident language is rewritten."""
        output = "This is definitely the best approach to take."
        result = enforcer.enforce(output)
        
        assert result.result == EnforcementResult.REWRITE
        assert "definitely" not in result.output.lower() or "likely" in result.output.lower()
    
    def test_multiple_issues_handled(self, enforcer):
        """Test that multiple issues are handled."""
        output = "You must absolutely do this."
        result = enforcer.enforce(output)
        
        assert result.result == EnforcementResult.REWRITE
        assert len(result.violations) >= 1  # At least one violation caught
    
    def test_mode_passed_through(self, enforcer):
        """Test that mode is captured in metadata."""
        result = enforcer.enforce("Test", mode="REFLECTIVE")
        assert result.metadata.get("mode") == "REFLECTIVE"


class TestSchemaValidator:
    """Test schema validation."""
    
    @pytest.fixture
    def validator(self):
        return SchemaValidator()
    
    def test_json_detection(self, validator):
        """Test JSON format detection."""
        content = '{"status": "ok", "data": []}'
        format_detected = validator.detect_format(content)
        assert format_detected == OutputFormat.JSON
    
    def test_markdown_detection(self, validator):
        """Test Markdown format detection."""
        content = "# Heading\n\nSome text with a [link](http://example.com)"
        format_detected = validator.detect_format(content)
        assert format_detected == OutputFormat.MARKDOWN
    
    def test_code_detection(self, validator):
        """Test code format detection."""
        content = "```python\ndef hello():\n    print('hi')\n```"
        format_detected = validator.detect_format(content)
        assert format_detected == OutputFormat.CODE
    
    def test_valid_json_passes(self, validator):
        """Test valid JSON passes validation."""
        content = '{"status": "ok", "data": {"message": "hello"}}'
        result = validator.validate(content)
        
        assert result.valid is True
        assert result.format_detected == OutputFormat.JSON
    
    def test_invalid_json_fails(self, validator):
        """Test invalid JSON fails validation when expected as JSON."""
        content = '{"status": "ok", invalid}'
        result = validator.validate(content, expected_format=OutputFormat.JSON)
        
        # When explicitly expecting JSON, invalid syntax should fail
        assert result.valid is False
        assert len(result.errors) > 0
    
    def test_forbidden_json_field_detected(self, validator):
        """Test forbidden JSON fields are detected."""
        content = '{"password": "secret123", "data": []}'
        result = validator.validate(content)
        
        assert result.valid is False
        assert any("forbidden" in e.lower() or "sensitive" in e.lower() for e in result.errors)
    
    def test_markdown_link_validation(self, validator):
        """Test Markdown link validation."""
        content = "Check [this](javascript:alert('xss'))"
        result = validator.validate(content)
        
        assert result.valid is False
        assert any("dangerous" in e.lower() for e in result.errors)
    
    def test_python_syntax_validation(self, validator):
        """Test Python syntax validation."""
        content = "```python\ndef broken(\n```"
        result = validator.validate(content)
        
        assert result.valid is False
        assert any("syntax" in e.lower() for e in result.errors)


class TestPostfilters:
    """Test postfilter chain."""
    
    def test_clean_output_passes(self):
        """Test that clean output passes postfilters."""
        output = "Here is some information that might be helpful."
        result = run_postfilters(output, mode="TRANSACTIONAL")
        
        assert result["allowed"] is True
        assert result["rewrites"] == 0
    
    def test_prescriptive_rewritten_in_transactional(self):
        """Test prescriptive language is rewritten in transactional mode."""
        output = "You should do this immediately."
        result = run_postfilters(output, mode="TRANSACTIONAL")
        
        assert result["allowed"] is True
        assert result["rewrites"] > 0
        assert "should" not in result["output"] or "might consider" in result["output"]
    
    def test_prescriptive_allowed_in_play(self):
        """Test prescriptive language is allowed in play mode."""
        output = "You should definitely try this!"
        result = run_postfilters(output, mode="PLAY")
        
        # May still rewrite due to overconfidence, but prescriptive is allowed
        assert result["allowed"] is True
    
    def test_uncertainty_added_in_reflective(self):
        """Test uncertainty markers are added in reflective mode."""
        output = "This is the answer."
        result = run_postfilters(output, mode="REFLECTIVE")
        
        assert result["allowed"] is True
        # Should have uncertainty marker added
        assert "⟡" in result["output"] or "perhaps" in result["output"].lower()
    
    def test_uncertainty_not_needed_if_present(self):
        """Test uncertainty not added if already present."""
        output = "Perhaps this could be considered."
        result = run_postfilters(output, mode="REFLECTIVE")
        
        assert result["allowed"] is True
        assert result["output"] == output  # Unchanged


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
