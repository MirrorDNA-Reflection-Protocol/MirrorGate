import type { FilterResult } from './prescriptive.js';

// Patterns indicating appropriate uncertainty
const UNCERTAINTY_MARKERS = [
  /\bmight\b/i,
  /\bmay\b/i,
  /\bcould\b/i,
  /\bperhaps\b/i,
  /\bpossibly\b/i,
  /\bit\s+seems\b/i,
  /\bit\s+appears\b/i,
  /\bi('m|\s+am)\s+not\s+(sure|certain)\b/i,
  /\bfrom\s+my\s+understanding\b/i,
  /\bas\s+far\s+as\s+i\s+know\b/i,
  /\bone\s+perspective\b/i,
  /\bsome\s+people\s+(think|believe|feel)\b/i,
  /\bthere\s+are\s+different\s+views\b/i,
  /\bdepending\s+on\b/i,
  /\bin\s+some\s+cases\b/i,
  /\?/, // Questions inherently show uncertainty
];

// Overconfident patterns that should trigger warning
const OVERCONFIDENT_PATTERNS = [
  /\bdefinitely\b/i,
  /\bcertainly\b/i,
  /\babsolutely\b/i,
  /\bwithout\s+(a\s+)?doubt\b/i,
  /\bi('m|\s+am)\s+(100%|completely|totally)\s+(sure|certain|confident)\b/i,
  /\bthe\s+truth\s+is\b/i,
  /\bthe\s+fact\s+is\b/i,
  /\bit('s|\s+is)\s+obvious\s+that\b/i,
  /\beveryone\s+knows\b/i,
];

export function filterUncertainty(output: string): FilterResult {
  const violations: string[] = [];

  // Check for overconfident language
  for (const pattern of OVERCONFIDENT_PATTERNS) {
    const match = output.match(pattern);
    if (match) {
      violations.push(`Overconfident: "${match[0]}"`);
    }
  }

  // Check that at least one uncertainty marker is present
  const hasUncertainty = UNCERTAINTY_MARKERS.some(p => p.test(output));

  if (!hasUncertainty && output.length > 100) {
    violations.push('Missing uncertainty markers');
  }

  // Generate rewrite suggestion
  let rewritten: string | undefined;
  if (violations.length > 0) {
    rewritten = output
      .replace(/\bdefinitely\b/gi, 'likely')
      .replace(/\bcertainly\b/gi, 'probably')
      .replace(/\babsolutely\b/gi, 'quite possibly')
      .replace(/\bthe truth is\b/gi, 'one perspective is that')
      .replace(/\bthe fact is\b/gi, 'it seems that')
      .replace(/\beveryone knows\b/gi, 'many people believe');

    // Add uncertainty prefix if still missing markers
    if (!UNCERTAINTY_MARKERS.some(p => p.test(rewritten!))) {
      rewritten = 'From my understanding, ' + rewritten.charAt(0).toLowerCase() + rewritten.slice(1);
    }
  }

  return {
    passed: violations.length === 0,
    violations,
    rewritten
  };
}
