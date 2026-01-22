import type { GateContext, PolicyProfile } from '../types/index.js';

// Rough token estimation (4 chars per token average for English)
function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

// Complexity heuristics
function calculateComplexity(input: string): number {
  let score = 0;

  // Nested structures
  const bracketDepth = (input.match(/[\[\{\(]/g) || []).length;
  score += bracketDepth * 0.5;

  // Code blocks
  const codeBlocks = (input.match(/```/g) || []).length / 2;
  score += codeBlocks * 2;

  // Lists (potential for expansive responses)
  const listItems = (input.match(/^[\s]*[-*\d.]+\s/gm) || []).length;
  score += listItems * 0.3;

  // Questions (each may require substantial response)
  const questions = (input.match(/\?/g) || []).length;
  score += questions * 1;

  // "Explain", "describe", "list all" - expansion triggers
  if (/explain\s+(in\s+detail|thoroughly|completely)/i.test(input)) score += 3;
  if (/list\s+(all|every|each)/i.test(input)) score += 2;
  if (/describe\s+(everything|all)/i.test(input)) score += 2;

  return score;
}

const COMPLEXITY_THRESHOLD = 15;

export function gate4Size(ctx: GateContext, policy: PolicyProfile): GateContext {
  if (ctx.blocked) return ctx;

  const input = ctx.request.input;
  const tokens = estimateTokens(input);
  const maxTokens = Math.ceil(policy.limits.max_input_chars / 4);

  if (tokens > maxTokens) {
    return {
      ...ctx,
      blocked: {
        gate: '4',
        reason: `Input too large: ~${tokens} tokens exceeds limit of ~${maxTokens}`,
        code: 'INPUT_TOO_COMPLEX'
      }
    };
  }

  const complexity = calculateComplexity(input);
  if (complexity > COMPLEXITY_THRESHOLD) {
    return {
      ...ctx,
      blocked: {
        gate: '4',
        reason: `Input complexity score ${complexity.toFixed(1)} exceeds threshold`,
        code: 'COMPLEXITY_EXCEEDED'
      }
    };
  }

  return {
    ...ctx,
    gatesPassed: [...ctx.gatesPassed, '4']
  };
}
