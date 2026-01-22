export interface FilterResult {
  passed: boolean;
  violations: string[];
  rewritten?: string;
}

// Patterns that indicate prescriptive/directive language
const PRESCRIPTIVE_PATTERNS: [RegExp, string][] = [
  [/\byou\s+should\b/gi, 'you should'],
  [/\byou\s+must\b/gi, 'you must'],
  [/\byou\s+need\s+to\b/gi, 'you need to'],
  [/\byou\s+have\s+to\b/gi, 'you have to'],
  [/\bdo\s+this\b/gi, 'do this'],
  [/\bdon't\s+do\b/gi, "don't do"],
  [/\bthe\s+best\s+(option|choice|way)\s+is\b/gi, 'the best X is'],
  [/\bhere's\s+what\s+you\s+(must|should|need\s+to)\s+do\b/gi, "here's what you must do"],
  [/\bthe\s+right\s+(answer|choice|decision)\s+is\b/gi, 'the right X is'],
  [/\balways\s+do\b/gi, 'always do'],
  [/\bnever\s+do\b/gi, 'never do'],
  [/\bi\s+recommend\s+that\s+you\b/gi, 'I recommend that you'],
  [/\bmy\s+advice\s+is\s+to\b/gi, 'my advice is to'],
];

// Replacement suggestions for rewrites
const REWRITES: Record<string, string> = {
  'you should': 'you might consider',
  'you must': 'one approach could be to',
  'you need to': 'it may help to',
  'you have to': 'one option is to',
  'the best X is': 'one possibility is',
  'the right X is': 'depending on your situation,',
  'always do': 'in many cases,',
  'never do': 'it may be worth reconsidering',
  'I recommend that you': 'some people find it helpful to',
  'my advice is to': 'one perspective is that',
};

export function filterPrescriptive(output: string): FilterResult {
  const violations: string[] = [];
  let rewritten = output;

  for (const [pattern, label] of PRESCRIPTIVE_PATTERNS) {
    if (pattern.test(output)) {
      violations.push(label);
      // Apply rewrite if available
      const replacement = REWRITES[label];
      if (replacement) {
        rewritten = rewritten.replace(pattern, replacement);
      }
    }
  }

  return {
    passed: violations.length === 0,
    violations,
    rewritten: violations.length > 0 ? rewritten : undefined
  };
}
