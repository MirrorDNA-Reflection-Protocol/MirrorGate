export interface PolicyProfile {
  name: string;
  version: string;
  prefilters: string[];
  postfilters: string[];
  limits: {
    max_input_chars: number;
    max_output_tokens: number;
    requests_per_minute: number;
  };
  domains: {
    medical: 'refuse' | 'reflective' | 'allow';
    legal: 'refuse' | 'reflective' | 'allow';
    financial: 'refuse' | 'reflective' | 'allow';
    crisis: 'refuse' | 'reflective' | 'allow';
  };
  forbidden_patterns: string[];
  required_markers: string[];
}

export interface AuditRecord {
  event_id: string;
  timestamp: string;
  actor: 'user' | 'agent' | 'system';
  action: 'ALLOW' | 'BLOCK';
  request_id: string;
  gates_passed: string[];
  filters_applied: string[];
  rewrite_count: number;
  violation_code?: string;
  hash_input: string;
  hash_output: string;
  policy_hash: string;
  prev_record_hash: string;
  mirrorgate_version: string;
  signature?: string;
}
