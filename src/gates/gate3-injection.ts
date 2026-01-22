import type { GateContext } from '../types/index.js';

// Prompt injection and manipulation patterns
const INJECTION_PATTERNS = [
  // Instruction smuggling
  /\[SYSTEM\]/i,
  /\[INST\]/i,
  /<\|im_start\|>/i,
  /<<SYS>>/i,
  /###\s*(Instruction|System|Human|Assistant):/i,

  // Role confusion
  /you\s+are\s+(not\s+)?(an?\s+)?(AI|assistant|Claude|ChatGPT)/i,
  /from\s+now\s+on,?\s+(you|your)\s+(are|role|persona)/i,
  /act\s+as\s+(if\s+you\s+are|though\s+you're)/i,
  /roleplay\s+as/i,

  // Authority escalation
  /admin\s+mode/i,
  /developer\s+mode/i,
  /override\s+(safety|content|filter)/i,
  /unlock\s+(all|full)\s+(capabilities|features)/i,

  // Encoding tricks
  /base64\s*:\s*[A-Za-z0-9+/=]{20,}/i,
  /\\x[0-9a-f]{2}/i,
  /&#x?[0-9a-f]+;/i,
];

// Suspicion score patterns (accumulated)
const SUSPICION_PATTERNS: [RegExp, number][] = [
  [/ignore/i, 1],
  [/previous/i, 1],
  [/instruction/i, 2],
  [/pretend/i, 2],
  [/hypothetical/i, 1],
  [/imagine\s+you/i, 2],
  [/let's\s+play\s+a\s+game/i, 2],
  [/in\s+this\s+story/i, 1],
  [/fictional/i, 1],
];

const SUSPICION_THRESHOLD = 5;

export function gate3Injection(ctx: GateContext): GateContext {
  if (ctx.blocked) return ctx;

  const input = ctx.request.input;

  // Check hard injection patterns
  for (const pattern of INJECTION_PATTERNS) {
    if (pattern.test(input)) {
      return {
        ...ctx,
        blocked: {
          gate: '3',
          reason: 'Potential prompt injection detected',
          code: 'INJECTION_DETECTED'
        }
      };
    }
  }

  // Accumulate suspicion score
  let suspicionScore = 0;
  for (const [pattern, score] of SUSPICION_PATTERNS) {
    if (pattern.test(input)) {
      suspicionScore += score;
    }
  }

  if (suspicionScore >= SUSPICION_THRESHOLD) {
    return {
      ...ctx,
      blocked: {
        gate: '3',
        reason: 'Input exhibits manipulation patterns',
        code: 'MANIPULATION_SUSPECTED'
      }
    };
  }

  return {
    ...ctx,
    gatesPassed: [...ctx.gatesPassed, '3']
  };
}
