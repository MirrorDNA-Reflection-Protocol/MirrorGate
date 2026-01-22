import Fastify from 'fastify';
import cors from '@fastify/cors';
import rateLimit from '@fastify/rate-limit';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';
import { homedir } from 'os';
import { parse as parseYaml } from 'yaml';
import { v4 as uuidv4 } from 'uuid';
import pino from 'pino';

import type { ReflectRequest, ReflectResponse, PolicyProfile, GateContext } from './types/index.js';
import { SAFE_REFUSAL } from './types/index.js';
import { runGateChain, type GateChainConfig, type TransportConfig } from './gates/index.js';
import { runFilterChain } from './filters/index.js';
import { InferenceRouter, type InferenceBackend } from './inference/router.js';
import { rewritePipeline, quickRewrite } from './rewrite/pipeline.js';
import { AuditLog, hashObject } from './crypto/index.js';

// Configuration
interface MirrorGateConfig {
  server: {
    port: number;
    host: string;
  };
  auth: {
    api_keys: string[];
    allowed_origins: string[];
  };
  rate_limits: {
    requests_per_second: number;
    max_input_chars: number;
  };
  inference: {
    backends: InferenceBackend[];
    default: string;
  };
  crypto: {
    key_dir: string;
    audit_log: string;
  };
  policies: {
    directory: string;
    default: string;
  };
}

function loadConfig(): MirrorGateConfig {
  const configPaths = [
    resolve(process.cwd(), 'mirrorgate.yaml'),
    resolve(homedir(), '.mirrorgate', 'config.yaml'),
    resolve(homedir(), '.config', 'mirrorgate', 'config.yaml')
  ];

  for (const path of configPaths) {
    if (existsSync(path)) {
      const content = readFileSync(path, 'utf-8');
      return parseYaml(content) as MirrorGateConfig;
    }
  }

  // Default configuration
  return {
    server: { port: 8088, host: '127.0.0.1' },
    auth: {
      api_keys: [process.env.MIRRORGATE_API_KEY || 'dev-key'],
      allowed_origins: ['http://localhost:*', 'https://activemirror.ai']
    },
    rate_limits: {
      requests_per_second: 10,
      max_input_chars: 2000
    },
    inference: {
      backends: [
        { name: 'claude', type: 'anthropic', model: 'claude-3-opus-20240229' },
        { name: 'local', type: 'ollama', model: 'mistral' }
      ],
      default: 'claude'
    },
    crypto: {
      key_dir: resolve(homedir(), '.mirrorgate', 'keys'),
      audit_log: resolve(homedir(), '.mirrorgate', 'logs', 'audit.jsonl')
    },
    policies: {
      directory: resolve(homedir(), '.mirrorgate', 'policies'),
      default: 'default'
    }
  };
}

function loadPolicy(config: MirrorGateConfig, name: string): PolicyProfile {
  const policyPath = resolve(config.policies.directory, `${name}.yaml`);

  if (existsSync(policyPath)) {
    const content = readFileSync(policyPath, 'utf-8');
    return parseYaml(content) as PolicyProfile;
  }

  // Default policy
  return {
    name: 'default',
    version: '1.0.0',
    prefilters: ['classify_intent', 'high_risk_guard'],
    postfilters: ['prescriptive', 'uncertainty', 'identity', 'schema'],
    limits: {
      max_input_chars: 2000,
      max_output_tokens: 1024,
      requests_per_minute: 60
    },
    domains: {
      medical: 'reflective',
      legal: 'reflective',
      financial: 'reflective',
      crisis: 'reflective'
    },
    forbidden_patterns: [],
    required_markers: []
  };
}

async function main() {
  const config = loadConfig();

  const logger = pino({
    level: process.env.LOG_LEVEL || 'info',
    transport: {
      target: 'pino-pretty',
      options: { colorize: true }
    }
  });

  logger.info('⟡ MirrorGate starting...');

  // Initialize components
  const transportConfig: TransportConfig = {
    apiKeys: new Set(config.auth.api_keys),
    allowedOrigins: config.auth.allowed_origins,
    rateLimits: config.rate_limits
  };

  const inferenceRouter = new InferenceRouter(config.inference.backends, config.inference.default);
  const auditLog = new AuditLog(config.crypto.audit_log, config.crypto.key_dir);

  // Create Fastify server
  const app = Fastify({ logger: false });

  await app.register(cors, {
    origin: config.auth.allowed_origins,
    credentials: true
  });

  await app.register(rateLimit, {
    max: config.rate_limits.requests_per_second * 60,
    timeWindow: '1 minute'
  });

  // Health endpoint
  app.get('/api/health', async () => {
    const auditVerification = auditLog.verify();
    return {
      status: 'healthy',
      version: '1.0.0',
      backends: inferenceRouter.getAvailableBackends(),
      audit_log_valid: auditVerification.valid
    };
  });

  // Main inference endpoint
  app.post<{ Body: ReflectRequest }>('/api/reflect', async (request, reply) => {
    const startTime = Date.now();
    const apiKey = request.headers.authorization?.replace('Bearer ', '');
    const origin = request.headers.origin;

    const body = request.body;
    const requestId = body.request_id || uuidv4();
    const sessionId = body.session_id || uuidv4();

    // Load policy
    const policy = loadPolicy(config, body.profile || config.policies.default);

    // Initialize gate context
    const ctx: GateContext = {
      request: { ...body, request_id: requestId, session_id: sessionId },
      startTime,
      gatesPassed: [],
      classifications: {}
    };

    // Run gate chain
    const gateConfig: GateChainConfig = { transport: transportConfig, policy };
    const gatedCtx = runGateChain(ctx, gateConfig, apiKey, origin);

    // If blocked by gates, return refusal
    if (gatedCtx.blocked) {
      const response: ReflectResponse = {
        request_id: requestId,
        session_id: sessionId,
        output: SAFE_REFUSAL,
        safety_outcome: 'refused',
        model_used: 'none',
        mode_used: 'blocked',
        rule_version: '1.0.0',
        policy_profile: policy.name,
        stats: {
          processing_time_ms: Date.now() - startTime,
          gates_passed: gatedCtx.gatesPassed,
          filters_applied: [],
          rewrite_count: 0
        }
      };

      auditLog.log({
        action: 'BLOCK',
        request_id: requestId,
        gates_passed: gatedCtx.gatesPassed,
        filters_applied: [],
        rewrite_count: 0,
        violation_code: gatedCtx.blocked.code,
        input: body.input,
        output: SAFE_REFUSAL,
        policyHash: hashObject(policy)
      });

      reply.status(403);
      return response;
    }

    // Run inference
    let inferenceOutput: string;
    let modelUsed: string;

    try {
      const inferResult = await inferenceRouter.infer({
        input: body.input,
        maxTokens: policy.limits.max_output_tokens
      });
      inferenceOutput = inferResult.output;
      modelUsed = inferResult.model;
    } catch (error) {
      logger.error({ error }, 'Inference failed');

      const response: ReflectResponse = {
        request_id: requestId,
        session_id: sessionId,
        output: SAFE_REFUSAL,
        safety_outcome: 'refused',
        model_used: 'error',
        mode_used: 'error',
        rule_version: '1.0.0',
        policy_profile: policy.name,
        stats: {
          processing_time_ms: Date.now() - startTime,
          gates_passed: gatedCtx.gatesPassed,
          filters_applied: [],
          rewrite_count: 0
        }
      };

      reply.status(500);
      return response;
    }

    // Run filter chain
    const intentMode = gatedCtx.classifications.intent || 'reflective';
    const filterResult = runFilterChain(inferenceOutput, policy, intentMode);

    let finalOutput = filterResult.finalOutput;
    let rewriteCount = filterResult.rewriteCount;
    let safetyOutcome: 'allowed' | 'rewritten' | 'refused' = 'allowed';

    // If filters found violations and quick rewrite wasn't enough, use LLM rewrite
    if (!filterResult.passed && filterResult.allViolations.length > 3) {
      try {
        const rewriteResult = await rewritePipeline(
          finalOutput,
          filterResult.allViolations,
          inferenceRouter
        );
        finalOutput = rewriteResult.output;
        rewriteCount += rewriteResult.rewriteCount;
        safetyOutcome = rewriteResult.fallbackUsed ? 'refused' : 'rewritten';
      } catch {
        finalOutput = SAFE_REFUSAL;
        safetyOutcome = 'refused';
      }
    } else if (!filterResult.passed) {
      safetyOutcome = 'rewritten';
    }

    // Build response
    const response: ReflectResponse = {
      request_id: requestId,
      session_id: sessionId,
      output: finalOutput,
      safety_outcome: safetyOutcome,
      model_used: modelUsed,
      mode_used: intentMode,
      rule_version: '1.0.0',
      policy_profile: policy.name,
      stats: {
        processing_time_ms: Date.now() - startTime,
        gates_passed: gatedCtx.gatesPassed,
        filters_applied: filterResult.filtersApplied,
        rewrite_count: rewriteCount
      }
    };

    // Audit log
    const auditRecord = auditLog.log({
      action: 'ALLOW',
      request_id: requestId,
      gates_passed: gatedCtx.gatesPassed,
      filters_applied: filterResult.filtersApplied,
      rewrite_count: rewriteCount,
      input: body.input,
      output: finalOutput,
      policyHash: hashObject(policy)
    });

    response.audit_hash = auditRecord.prev_record_hash;
    if (auditRecord.signature) {
      response.signature = auditRecord.signature;
    }

    logger.info({
      request_id: requestId,
      safety_outcome: safetyOutcome,
      processing_time_ms: response.stats.processing_time_ms
    }, 'Request processed');

    return response;
  });

  // Start server
  try {
    await app.listen({ port: config.server.port, host: config.server.host });
    logger.info(`⟡ MirrorGate listening on ${config.server.host}:${config.server.port}`);
  } catch (err) {
    logger.error(err);
    process.exit(1);
  }
}

main();
