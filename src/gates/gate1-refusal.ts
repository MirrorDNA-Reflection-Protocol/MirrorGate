import type { GateContext } from '../types/index.js';

// Hard refusal patterns - immediate block, no exceptions
const HARD_REFUSAL_PATTERNS = [
  // Illegal activity
  /how\s+to\s+(make|create|build)\s+(a\s+)?(bomb|explosive|weapon)/i,
  /synthesize\s+(meth|fentanyl|heroin)/i,
  /child\s+(porn|abuse|exploitation)/i,

  // Self-harm facilitation
  /how\s+to\s+(kill|harm)\s+(myself|yourself)/i,
  /suicide\s+methods/i,
  /most\s+painless\s+way\s+to\s+die/i,

  // System compromise
  /ignore\s+(previous|all)\s+instructions/i,
  /you\s+are\s+now\s+(DAN|jailbroken|unrestricted)/i,
  /pretend\s+you\s+(have\s+no|don't\s+have)\s+(limits|restrictions|rules)/i,
  /bypass\s+(your|the)\s+(safety|content)\s+(filters?|rules?)/i,

  // Explicit exploitation
  /hack\s+into\s+(someone's|their)\s+(account|system)/i,
  /steal\s+(credit\s+card|identity|credentials)/i,
];

export function gate1Refusal(ctx: GateContext): GateContext {
  if (ctx.blocked) return ctx;

  const input = ctx.request.input;

  for (const pattern of HARD_REFUSAL_PATTERNS) {
    if (pattern.test(input)) {
      return {
        ...ctx,
        blocked: {
          gate: '1',
          reason: 'Content violates hard safety constraints',
          code: 'HARD_REFUSAL'
        }
      };
    }
  }

  return {
    ...ctx,
    gatesPassed: [...ctx.gatesPassed, '1']
  };
}
