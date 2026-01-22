export { gate0Transport, type TransportConfig } from './gate0-transport.js';
export { gate1Refusal } from './gate1-refusal.js';
export { gate2Domain, classifyDomain } from './gate2-domain.js';
export { gate3Injection } from './gate3-injection.js';
export { gate4Size } from './gate4-size.js';
export { gate5Intent, classifyIntent } from './gate5-intent.js';

import type { GateContext, PolicyProfile } from '../types/index.js';
import { gate0Transport, type TransportConfig } from './gate0-transport.js';
import { gate1Refusal } from './gate1-refusal.js';
import { gate2Domain } from './gate2-domain.js';
import { gate3Injection } from './gate3-injection.js';
import { gate4Size } from './gate4-size.js';
import { gate5Intent } from './gate5-intent.js';

export interface GateChainConfig {
  transport: TransportConfig;
  policy: PolicyProfile;
}

export function runGateChain(
  ctx: GateContext,
  config: GateChainConfig,
  apiKey?: string,
  origin?: string
): GateContext {
  let result = ctx;

  // Gate 0: Transport & Auth
  result = gate0Transport(result, config.transport, apiKey, origin);
  if (result.blocked) return result;

  // Gate 1: Hard Refusal
  result = gate1Refusal(result);
  if (result.blocked) return result;

  // Gate 2: Domain Risk
  result = gate2Domain(result, config.policy);
  if (result.blocked) return result;

  // Gate 3: Injection Detection
  result = gate3Injection(result);
  if (result.blocked) return result;

  // Gate 4: Size & Complexity
  result = gate4Size(result, config.policy);
  if (result.blocked) return result;

  // Gate 5: Intent Classification
  result = gate5Intent(result);

  return result;
}
