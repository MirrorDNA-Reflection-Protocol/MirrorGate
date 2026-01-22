import type { FilterResult } from './prescriptive.js';
import type { PolicyProfile } from '../types/index.js';

// MirrorDNA glyphs that indicate reflective output
const REFLECTION_GLYPHS = ['⟡', '⧈', '⧉', '🜃', '🜔'];

export function filterSchema(output: string, policy: PolicyProfile): FilterResult {
  const violations: string[] = [];

  // Check for required markers (if policy specifies them)
  if (policy.required_markers && policy.required_markers.length > 0) {
    const hasRequiredMarker = policy.required_markers.some(marker =>
      output.includes(marker)
    );

    if (!hasRequiredMarker) {
      violations.push(`Missing required marker (one of: ${policy.required_markers.join(', ')})`);
    }
  }

  // Check for forbidden patterns
  if (policy.forbidden_patterns) {
    for (const patternStr of policy.forbidden_patterns) {
      try {
        const pattern = new RegExp(patternStr, 'gi');
        if (pattern.test(output)) {
          violations.push(`Contains forbidden pattern: ${patternStr}`);
        }
      } catch {
        // Invalid regex in policy, skip
      }
    }
  }

  // Reflective mode checks
  const hasGlyph = REFLECTION_GLYPHS.some(g => output.includes(g));

  // Generate rewrite if needed
  let rewritten: string | undefined;
  if (violations.length > 0) {
    rewritten = output;

    // Add glyph prefix if missing and required
    if (!hasGlyph && policy.required_markers?.some(m => REFLECTION_GLYPHS.includes(m))) {
      rewritten = '⟡ ' + rewritten;
    }
  }

  return {
    passed: violations.length === 0,
    violations,
    rewritten
  };
}

// Validate entire output against MirrorDNA schema
export function validateMirrorDNASchema(output: string): {
  valid: boolean;
  issues: string[];
} {
  const issues: string[] = [];

  // No empty responses
  if (!output || output.trim().length === 0) {
    issues.push('Empty output');
  }

  // No raw JSON dumps
  if (/^\s*\{[\s\S]*\}\s*$/.test(output) && output.length > 500) {
    issues.push('Raw JSON dump detected');
  }

  // No code-only responses to non-code questions
  const codeRatio = (output.match(/```/g) || []).length / 2;
  const textLength = output.replace(/```[\s\S]*?```/g, '').trim().length;
  if (codeRatio > 0 && textLength < 50) {
    issues.push('Code-heavy response with insufficient explanation');
  }

  return {
    valid: issues.length === 0,
    issues
  };
}
