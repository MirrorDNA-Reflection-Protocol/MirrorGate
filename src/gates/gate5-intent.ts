import type { GateContext } from '../types/index.js';

type IntentMode = 'transactional' | 'reflective' | 'play';

const TRANSACTIONAL_PATTERNS = [
  /^(what|when|where|who|how\s+many|how\s+much)\s+is/i,
  /convert\s+\d+/i,
  /calculate/i,
  /translate/i,
  /define\s+/i,
  /syntax\s+(for|of)/i,
  /format\s+(this|the)/i,
  /fix\s+(this|the)\s+(code|bug|error)/i,
  /regex\s+for/i,
];

const REFLECTIVE_PATTERNS = [
  /should\s+i/i,
  /what\s+do\s+you\s+think/i,
  /help\s+me\s+(decide|choose|understand)/i,
  /i('m|\s+am)\s+(feeling|confused|uncertain|worried|anxious)/i,
  /advice\s+(on|about|for)/i,
  /how\s+(should|would|could)\s+i/i,
  /is\s+it\s+(right|wrong|good|bad)\s+to/i,
  /what\s+would\s+you\s+(do|suggest|recommend)/i,
];

const PLAY_PATTERNS = [
  /write\s+(a|me\s+a)\s+(story|poem|song|joke)/i,
  /imagine\s+(if|a\s+world)/i,
  /creative\s+writing/i,
  /let's\s+(brainstorm|explore|imagine)/i,
  /what\s+if/i,
  /for\s+fun/i,
  /just\s+curious/i,
];

export function classifyIntent(input: string): IntentMode {
  // Check transactional first (most constrained)
  for (const pattern of TRANSACTIONAL_PATTERNS) {
    if (pattern.test(input)) return 'transactional';
  }

  // Check play mode
  for (const pattern of PLAY_PATTERNS) {
    if (pattern.test(input)) return 'play';
  }

  // Check reflective
  for (const pattern of REFLECTIVE_PATTERNS) {
    if (pattern.test(input)) return 'reflective';
  }

  // Default to reflective (safer)
  return 'reflective';
}

export function gate5Intent(ctx: GateContext): GateContext {
  if (ctx.blocked) return ctx;

  const intent = classifyIntent(ctx.request.input);

  // If domain was high-risk, force reflective mode
  const forcedIntent = ctx.classifications.risk === 'high' ? 'reflective' : intent;

  return {
    ...ctx,
    classifications: {
      ...ctx.classifications,
      intent: forcedIntent
    },
    gatesPassed: [...ctx.gatesPassed, '5']
  };
}
