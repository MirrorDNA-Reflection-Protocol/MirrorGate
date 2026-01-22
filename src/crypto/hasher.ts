import { createHash } from 'crypto';

export function sha256(data: string | Buffer): string {
  return createHash('sha256').update(data).digest('hex');
}

export function hashObject(obj: object): string {
  const json = JSON.stringify(obj, Object.keys(obj).sort());
  return sha256(json);
}

// Hash chain for tamper-evident log
export class HashChain {
  private prevHash: string;

  constructor(genesisHash?: string) {
    this.prevHash = genesisHash || sha256('mirrorgate-genesis-' + Date.now());
  }

  // Add a record and return its chain hash
  addRecord(record: object): { recordHash: string; chainHash: string; prevHash: string } {
    const recordHash = hashObject(record);
    const prevHash = this.prevHash;
    const chainHash = sha256(recordHash + prevHash);

    this.prevHash = chainHash;

    return { recordHash, chainHash, prevHash };
  }

  // Verify a record in the chain
  static verifyRecord(
    record: object,
    expectedRecordHash: string,
    expectedChainHash: string,
    prevHash: string
  ): boolean {
    const recordHash = hashObject(record);
    if (recordHash !== expectedRecordHash) return false;

    const chainHash = sha256(recordHash + prevHash);
    return chainHash === expectedChainHash;
  }

  getCurrentHash(): string {
    return this.prevHash;
  }
}
