import type { GateContext, PolicyProfile } from '../types/index.js';

type DomainType = 'medical' | 'legal' | 'financial' | 'crisis' | 'general';

const DOMAIN_PATTERNS: Record<DomainType, RegExp[]> = {
  medical: [
    /\b(diagnos|symptom|treatment|medication|prescription|dosage|disease|illness|cancer|diabetes|heart\s+attack)\b/i,
    /\b(doctor|physician|medical\s+advice|health\s+condition)\b/i,
    /should\s+i\s+(take|stop\s+taking|increase|decrease)\s+.*(medication|medicine|drug)/i,
  ],
  legal: [
    /\b(legal\s+advice|lawsuit|sue|court|attorney|lawyer|contract|liability)\b/i,
    /\b(divorce|custody|arrest|criminal\s+charge|prosecution)\b/i,
    /am\s+i\s+(liable|guilty|legally\s+responsible)/i,
  ],
  financial: [
    /\b(investment\s+advice|stock|crypto|trading|portfolio|retire|mortgage)\b/i,
    /should\s+i\s+(buy|sell|invest|withdraw)/i,
    /\b(financial\s+planning|tax\s+advice|estate\s+planning)\b/i,
  ],
  crisis: [
    /\b(suicid|self.harm|want\s+to\s+die|end\s+(my|it\s+all))\b/i,
    /\b(abuse|domestic\s+violence|assault|rape)\b/i,
    /\b(eating\s+disorder|anorexia|bulimia)\b/i,
    /feeling\s+(hopeless|worthless|like\s+a\s+burden)/i,
  ],
  general: [],
};

export function classifyDomain(input: string): DomainType {
  for (const [domain, patterns] of Object.entries(DOMAIN_PATTERNS)) {
    if (domain === 'general') continue;
    for (const pattern of patterns) {
      if (pattern.test(input)) {
        return domain as DomainType;
      }
    }
  }
  return 'general';
}

export function gate2Domain(ctx: GateContext, policy: PolicyProfile): GateContext {
  if (ctx.blocked) return ctx;

  const domain = classifyDomain(ctx.request.input);
  ctx.classifications.domain = domain;

  if (domain === 'general') {
    return {
      ...ctx,
      gatesPassed: [...ctx.gatesPassed, '2']
    };
  }

  const domainPolicy = policy.domains[domain as keyof typeof policy.domains];

  if (domainPolicy === 'refuse') {
    return {
      ...ctx,
      blocked: {
        gate: '2',
        reason: `${domain} domain requests are not permitted under current policy`,
        code: 'DOMAIN_REFUSED'
      }
    };
  }

  // 'reflective' mode will be enforced by downstream filters
  return {
    ...ctx,
    classifications: {
      ...ctx.classifications,
      domain,
      risk: domain === 'crisis' ? 'high' : 'medium'
    },
    gatesPassed: [...ctx.gatesPassed, '2']
  };
}
