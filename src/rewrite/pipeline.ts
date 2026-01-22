import type { InferenceRouter } from '../inference/router.js';
import { SAFE_REFUSAL } from '../types/index.js';

const REWRITE_SYSTEM_PROMPT = `You are a rewrite assistant for MirrorGate. Your job is to take a response that violates safety/style guidelines and rewrite it to comply.

Rules:
1. Remove prescriptive language ("you should", "you must") - replace with exploratory language
2. Add uncertainty markers ("it seems", "one perspective", "depending on")
3. Remove first-person authority claims ("I decided", "I verified")
4. Keep the core meaning and helpfulness intact
5. Be concise - don't add unnecessary padding

Output ONLY the rewritten response, no explanations.`;

export interface RewriteResult {
  output: string;
  rewriteCount: number;
  fallbackUsed: boolean;
}

export async function rewritePipeline(
  originalOutput: string,
  violations: string[],
  router: InferenceRouter,
  maxRewrites: number = 2
): Promise<RewriteResult> {
  let currentOutput = originalOutput;
  let rewriteCount = 0;

  for (let i = 0; i < maxRewrites; i++) {
    try {
      const prompt = `Original response with violations (${violations.join(', ')}):\n\n${currentOutput}\n\nRewrite to comply with guidelines:`;

      const response = await router.infer({
        input: prompt,
        systemPrompt: REWRITE_SYSTEM_PROMPT,
        maxTokens: 1024,
        temperature: 0.3 // Low temperature for consistency
      });

      currentOutput = response.output;
      rewriteCount++;

      // TODO: Re-run filters to check if rewrite is compliant
      // For now, assume one rewrite is sufficient
      break;
    } catch (error) {
      console.error(`Rewrite attempt ${i + 1} failed:`, error);
    }
  }

  // If we couldn't rewrite successfully, use safe fallback
  if (rewriteCount === 0) {
    return {
      output: SAFE_REFUSAL,
      rewriteCount: 0,
      fallbackUsed: true
    };
  }

  return {
    output: currentOutput,
    rewriteCount,
    fallbackUsed: false
  };
}

// Simple inline rewrites without LLM (for minor violations)
export function quickRewrite(output: string): string {
  return output
    // Prescriptive -> exploratory
    .replace(/\byou should\b/gi, 'you might consider')
    .replace(/\byou must\b/gi, 'one approach could be to')
    .replace(/\byou need to\b/gi, 'it may help to')

    // Overconfident -> hedged
    .replace(/\bdefinitely\b/gi, 'likely')
    .replace(/\bcertainly\b/gi, 'probably')
    .replace(/\babsolutely\b/gi, 'quite possibly')

    // Identity claims -> passive
    .replace(/\bI decided\b/gi, 'based on the analysis')
    .replace(/\bI verified\b/gi, 'according to available information')
    .replace(/\bI know\b/gi, 'the information suggests');
}
