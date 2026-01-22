export interface ReflectRequest {
  session_id: string;
  request_id: string;
  timestamp: string;
  mode: 'local' | 'cloud';
  profile: string;
  metadata?: {
    origin?: string;
    user_agent?: string;
    client_tag?: string;
  };
  intent?: string;
  input: string;
  consent: {
    save_to_vault: boolean;
    log_opt_in: boolean;
  };
}

export interface GateContext {
  request: ReflectRequest;
  startTime: number;
  gatesPassed: string[];
  classifications: {
    domain?: string;
    intent?: 'transactional' | 'reflective' | 'play';
    risk?: 'low' | 'medium' | 'high';
  };
  blocked?: {
    gate: string;
    reason: string;
    code: string;
  };
}
