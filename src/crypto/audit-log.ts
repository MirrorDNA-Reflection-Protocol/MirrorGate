import { appendFileSync, readFileSync, existsSync, mkdirSync } from 'fs';
import { dirname } from 'path';
import { v4 as uuidv4 } from 'uuid';
import type { AuditRecord } from '../types/index.js';
import { HashChain, sha256 } from './hasher.js';
import { signAuditRecord, loadKeyPair } from './signer.js';

export class AuditLog {
  private logPath: string;
  private keyDir: string;
  private chain: HashChain;

  constructor(logPath: string, keyDir: string) {
    this.logPath = logPath;
    this.keyDir = keyDir;

    // Ensure directory exists
    const dir = dirname(logPath);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    // Initialize chain from last record or genesis
    const lastHash = this.getLastChainHash();
    this.chain = new HashChain(lastHash);
  }

  private getLastChainHash(): string | undefined {
    if (!existsSync(this.logPath)) return undefined;

    const content = readFileSync(this.logPath, 'utf-8');
    const lines = content.trim().split('\n').filter(Boolean);

    if (lines.length === 0) return undefined;

    try {
      const lastRecord = JSON.parse(lines[lines.length - 1]) as AuditRecord;
      return sha256(JSON.stringify(lastRecord));
    } catch {
      return undefined;
    }
  }

  log(params: {
    action: 'ALLOW' | 'BLOCK';
    request_id: string;
    gates_passed: string[];
    filters_applied: string[];
    rewrite_count: number;
    violation_code?: string;
    input: string;
    output: string;
    policyHash: string;
  }): AuditRecord {
    const keyPair = loadKeyPair(this.keyDir);

    const baseRecord = {
      event_id: uuidv4(),
      timestamp: new Date().toISOString(),
      actor: 'user' as const,
      action: params.action,
      request_id: params.request_id,
      gates_passed: params.gates_passed,
      filters_applied: params.filters_applied,
      rewrite_count: params.rewrite_count,
      violation_code: params.violation_code,
      hash_input: sha256(params.input),
      hash_output: sha256(params.output),
      policy_hash: params.policyHash,
      mirrorgate_version: '1.0.0'
    };

    // Add to chain
    const { chainHash, prevHash } = this.chain.addRecord(baseRecord);

    const record: AuditRecord = {
      ...baseRecord,
      prev_record_hash: prevHash
    };

    // Sign if key available
    if (keyPair) {
      record.signature = signAuditRecord(
        {
          event_id: record.event_id,
          timestamp: record.timestamp,
          action: record.action,
          hash_output: record.hash_output,
          prev_record_hash: record.prev_record_hash
        },
        keyPair.privateKey
      );
    }

    // Append to log
    appendFileSync(this.logPath, JSON.stringify(record) + '\n');

    return record;
  }

  verify(): { valid: boolean; errors: string[] } {
    if (!existsSync(this.logPath)) {
      return { valid: true, errors: [] };
    }

    const content = readFileSync(this.logPath, 'utf-8');
    const lines = content.trim().split('\n').filter(Boolean);
    const errors: string[] = [];

    let prevHash: string | null = null;

    for (let i = 0; i < lines.length; i++) {
      try {
        const record = JSON.parse(lines[i]) as AuditRecord;

        // Verify chain continuity
        if (i > 0 && record.prev_record_hash !== prevHash) {
          errors.push(`Record ${i}: Chain broken - expected prev_hash ${prevHash}, got ${record.prev_record_hash}`);
        }

        prevHash = sha256(JSON.stringify(record));
      } catch (e) {
        errors.push(`Record ${i}: Invalid JSON`);
      }
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }
}
