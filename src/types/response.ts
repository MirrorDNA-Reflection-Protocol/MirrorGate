export type SafetyOutcome = 'allowed' | 'rewritten' | 'refused';

export interface ReflectResponse {
  request_id: string;
  session_id: string;
  output: string;
  safety_outcome: SafetyOutcome;
  model_used: string;
  mode_used: string;
  rule_version: string;
  policy_profile: string;
  stats: {
    processing_time_ms: number;
    gates_passed: string[];
    filters_applied: string[];
    rewrite_count: number;
  };
  signature?: string;
  audit_hash?: string;
}

export interface ErrorResponse {
  request_id: string;
  session_id: string;
  output: string;
  safety_outcome: 'refused';
  error_code: string;
  rule_version: string;
  policy_profile: string;
}

export const SAFE_REFUSAL = "I can't respond safely at this time.";
