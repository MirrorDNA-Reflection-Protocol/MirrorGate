import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { randomBytes, sign, verify, generateKeyPairSync } from 'crypto';
import { dirname } from 'path';

export interface KeyPair {
  privateKey: string;
  publicKey: string;
}

export function generateKeyPair(): KeyPair {
  const { privateKey, publicKey } = generateKeyPairSync('ed25519', {
    privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
    publicKeyEncoding: { type: 'spki', format: 'pem' }
  });

  return { privateKey, publicKey };
}

export function saveKeyPair(keyDir: string, keyPair: KeyPair): void {
  if (!existsSync(keyDir)) {
    mkdirSync(keyDir, { recursive: true, mode: 0o700 });
  }

  writeFileSync(`${keyDir}/mirrorgate.key`, keyPair.privateKey, { mode: 0o600 });
  writeFileSync(`${keyDir}/mirrorgate.pub`, keyPair.publicKey, { mode: 0o644 });
}

export function loadKeyPair(keyDir: string): KeyPair | null {
  const privPath = `${keyDir}/mirrorgate.key`;
  const pubPath = `${keyDir}/mirrorgate.pub`;

  if (!existsSync(privPath) || !existsSync(pubPath)) {
    return null;
  }

  return {
    privateKey: readFileSync(privPath, 'utf-8'),
    publicKey: readFileSync(pubPath, 'utf-8')
  };
}

export function signData(data: string, privateKey: string): string {
  const signature = sign(null, Buffer.from(data), privateKey);
  return signature.toString('base64');
}

export function verifySignature(data: string, signature: string, publicKey: string): boolean {
  try {
    return verify(null, Buffer.from(data), publicKey, Buffer.from(signature, 'base64'));
  } catch {
    return false;
  }
}

// Sign an audit record
export function signAuditRecord(record: {
  event_id: string;
  timestamp: string;
  action: string;
  hash_output: string;
  prev_record_hash: string;
}, privateKey: string): string {
  const payload = [
    record.event_id,
    record.timestamp,
    record.action,
    record.hash_output,
    record.prev_record_hash
  ].join('||');

  return signData(payload, privateKey);
}
