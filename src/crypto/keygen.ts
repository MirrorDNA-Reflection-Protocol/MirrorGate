#!/usr/bin/env tsx

import { generateKeyPair, saveKeyPair, loadKeyPair } from './signer.js';
import { existsSync } from 'fs';
import { resolve } from 'path';
import { homedir } from 'os';

const DEFAULT_KEY_DIR = resolve(homedir(), '.mirrorgate', 'keys');

async function main() {
  const keyDir = process.argv[2] || DEFAULT_KEY_DIR;

  console.log('⟡ MirrorGate Key Generator');
  console.log('─'.repeat(40));
  console.log(`Key directory: ${keyDir}`);

  // Check for existing keys
  const existing = loadKeyPair(keyDir);
  if (existing) {
    console.log('\n⚠️  Keys already exist at this location.');
    console.log('   To regenerate, delete the existing keys first:');
    console.log(`   rm -rf ${keyDir}`);
    process.exit(1);
  }

  // Generate new keys
  console.log('\nGenerating Ed25519 key pair...');
  const keyPair = generateKeyPair();

  // Save keys
  saveKeyPair(keyDir, keyPair);

  console.log('\n✓ Keys generated successfully:');
  console.log(`  Private key: ${keyDir}/mirrorgate.key (mode 600)`);
  console.log(`  Public key:  ${keyDir}/mirrorgate.pub (mode 644)`);

  console.log('\n⚠️  IMPORTANT:');
  console.log('   - Keep the private key secure and never commit it to git');
  console.log('   - The public key can be shared for verification');
  console.log('   - Back up your private key - loss means audit logs cannot be verified');

  console.log('\n⟡ Done.');
}

main().catch(console.error);
