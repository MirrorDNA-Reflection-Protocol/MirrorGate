export { filterPrescriptive, type FilterResult } from './prescriptive.js';
export { filterUncertainty } from './uncertainty.js';
export { filterIdentity } from './identity.js';
export { filterSchema, validateMirrorDNASchema } from './schema.js';

import type { PolicyProfile } from '../types/index.js';
import type { FilterResult } from './prescriptive.js';
import { filterPrescriptive } from './prescriptive.js';
import { filterUncertainty } from './uncertainty.js';
import { filterIdentity } from './identity.js';
import { filterSchema } from './schema.js';

export interface FilterChainResult {
  passed: boolean;
  filtersApplied: string[];
  allViolations: string[];
  finalOutput: string;
  rewriteCount: number;
}

export function runFilterChain(
  output: string,
  policy: PolicyProfile,
  intentMode: 'transactional' | 'reflective' | 'play'
): FilterChainResult {
  const filtersApplied: string[] = [];
  const allViolations: string[] = [];
  let currentOutput = output;
  let rewriteCount = 0;

  // Prescriptive filter (always run in reflective mode)
  if (intentMode === 'reflective' || policy.postfilters.includes('prescriptive')) {
    filtersApplied.push('prescriptive');
    const result = filterPrescriptive(currentOutput);
    allViolations.push(...result.violations);
    if (result.rewritten) {
      currentOutput = result.rewritten;
      rewriteCount++;
    }
  }

  // Uncertainty filter
  if (policy.postfilters.includes('uncertainty')) {
    filtersApplied.push('uncertainty');
    const result = filterUncertainty(currentOutput);
    allViolations.push(...result.violations);
    if (result.rewritten) {
      currentOutput = result.rewritten;
      rewriteCount++;
    }
  }

  // Identity filter
  if (policy.postfilters.includes('identity')) {
    filtersApplied.push('identity');
    const result = filterIdentity(currentOutput);
    allViolations.push(...result.violations);
    if (result.rewritten) {
      currentOutput = result.rewritten;
      rewriteCount++;
    }
  }

  // Schema filter
  if (policy.postfilters.includes('schema')) {
    filtersApplied.push('schema');
    const result = filterSchema(currentOutput, policy);
    allViolations.push(...result.violations);
    if (result.rewritten) {
      currentOutput = result.rewritten;
      rewriteCount++;
    }
  }

  return {
    passed: allViolations.length === 0,
    filtersApplied,
    allViolations,
    finalOutput: currentOutput,
    rewriteCount
  };
}
