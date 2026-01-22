import type { FilterResult } from './prescriptive.js';

// LLM claiming authority or first-person power
const IDENTITY_VIOLATIONS: [RegExp, string][] = [
  [/\bi\s+decided\b/gi, 'I decided'],
  [/\bi\s+verified\b/gi, 'I verified'],
  [/\bi\s+confirmed\b/gi, 'I confirmed'],
  [/\bi\s+know\s+(for\s+)?(a\s+)?fact\b/gi, 'I know for a fact'],
  [/\bi\s+guarantee\b/gi, 'I guarantee'],
  [/\bi\s+promise\b/gi, 'I promise'],
  [/\btrust\s+me\b/gi, 'trust me'],
  [/\bi('m|\s+am)\s+certain\b/gi, "I'm certain"],
  [/\bi\s+have\s+determined\b/gi, 'I have determined'],
  [/\bmy\s+decision\s+is\b/gi, 'my decision is'],
  [/\bi\s+believe\s+this\s+is\s+(the\s+)?(right|correct|best)\b/gi, 'I believe this is right/correct/best'],

  // Claims of capability/existence
  [/\bi\s+can\s+see\b/gi, 'I can see'],
  [/\bi\s+can\s+hear\b/gi, 'I can hear'],
  [/\bi\s+feel\s+(that|like)\b/gi, 'I feel that'],
  [/\bi\s+want\b/gi, 'I want'],
  [/\bi\s+need\b/gi, 'I need'],

  // Claims of memory/persistence
  [/\bi\s+remember\b/gi, 'I remember'],
  [/\blast\s+time\s+(we|you)\b/gi, 'last time'],
  [/\bin\s+our\s+previous\b/gi, 'in our previous'],
];

const IDENTITY_REWRITES: Record<string, string> = {
  'I decided': 'based on the analysis',
  'I verified': 'according to available information',
  'I confirmed': 'the information suggests',
  'I know for a fact': 'the evidence indicates',
  'I guarantee': 'it appears likely that',
  'I promise': 'there is good reason to expect',
  'trust me': 'consider that',
  "I'm certain": 'it seems quite likely',
  'I have determined': 'one conclusion could be',
  'my decision is': 'one possible approach is',
};

export function filterIdentity(output: string): FilterResult {
  const violations: string[] = [];
  let rewritten = output;

  for (const [pattern, label] of IDENTITY_VIOLATIONS) {
    if (pattern.test(output)) {
      violations.push(label);
      const replacement = IDENTITY_REWRITES[label];
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
