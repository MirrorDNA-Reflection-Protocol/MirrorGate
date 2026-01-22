import type { GateContext } from '../types/index.js';

export interface TransportConfig {
  apiKeys: Set<string>;
  allowedOrigins: string[];
  rateLimits: {
    requestsPerSecond: number;
    maxInputChars: number;
  };
}

const requestCounts = new Map<string, { count: number; resetAt: number }>();

export function gate0Transport(ctx: GateContext, config: TransportConfig, apiKey?: string, origin?: string): GateContext {
  // API Key validation
  if (!apiKey || !config.apiKeys.has(apiKey)) {
    return {
      ...ctx,
      blocked: {
        gate: '0',
        reason: 'Invalid or missing API key',
        code: 'AUTH_FAILED'
      }
    };
  }

  // Origin validation
  if (origin && config.allowedOrigins.length > 0) {
    const originAllowed = config.allowedOrigins.some(allowed => {
      if (allowed.includes('*')) {
        const pattern = new RegExp('^' + allowed.replace('*', '.*') + '$');
        return pattern.test(origin);
      }
      return allowed === origin;
    });

    if (!originAllowed) {
      return {
        ...ctx,
        blocked: {
          gate: '0',
          reason: `Origin ${origin} not allowed`,
          code: 'CORS_VIOLATION'
        }
      };
    }
  }

  // Rate limiting
  const now = Date.now();
  const keyState = requestCounts.get(apiKey) || { count: 0, resetAt: now + 1000 };

  if (now > keyState.resetAt) {
    keyState.count = 0;
    keyState.resetAt = now + 1000;
  }

  keyState.count++;
  requestCounts.set(apiKey, keyState);

  if (keyState.count > config.rateLimits.requestsPerSecond) {
    return {
      ...ctx,
      blocked: {
        gate: '0',
        reason: 'Rate limit exceeded',
        code: 'RATE_LIMITED'
      }
    };
  }

  // Input size check
  if (ctx.request.input.length > config.rateLimits.maxInputChars) {
    return {
      ...ctx,
      blocked: {
        gate: '0',
        reason: `Input exceeds ${config.rateLimits.maxInputChars} characters`,
        code: 'INPUT_TOO_LARGE'
      }
    };
  }

  return {
    ...ctx,
    gatesPassed: [...ctx.gatesPassed, '0']
  };
}
