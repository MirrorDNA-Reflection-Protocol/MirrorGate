"""
Layer 1: The Vault — Context Injection

Retrieves relevant context before the LLM is touched.
This layer is deterministic: same query + same data = same context.

Uses ChromaDB for local vector storage. No cloud dependencies.
"""

from __future__ import annotations
import os
import json
import hashlib
from pathlib import Path
from typing import Optional

from .schemas import VaultContext

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


VAULT_DIR = Path.home() / ".mirrorgate" / "vault"
CONSTRAINTS_FILE = Path.home() / ".mirrordna" / "bus" / "intent.md"


class Vault:
    """Local vector store for context injection."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or str(VAULT_DIR / "chromadb")
        self._client = None
        self._collection = None
        self._constraints_cache: list[str] = []

    def _ensure_client(self):
        if not HAS_CHROMADB:
            return
        if self._client is None:
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name="mirrorgate_context",
                metadata={"hnsw:space": "cosine"},
            )

    def ingest(self, doc_id: str, text: str, metadata: Optional[dict] = None):
        """Add a document to the vault."""
        self._ensure_client()
        if not HAS_CHROMADB:
            return
        meta = metadata or {}
        meta["content_hash"] = hashlib.sha256(text.encode()).hexdigest()[:16]
        self._collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[meta],
        )

    def ingest_file(self, filepath: str, chunk_size: int = 1000):
        """Ingest a file into the vault, chunked."""
        path = Path(filepath)
        if not path.exists():
            return
        text = path.read_text(errors="replace")
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        for i, chunk in enumerate(chunks):
            doc_id = f"{path.name}::chunk_{i}"
            self.ingest(doc_id, chunk, {"source": str(path), "chunk": i})

    def query(self, user_input: str, n_results: int = 5) -> list[str]:
        """Retrieve relevant context for a query."""
        self._ensure_client()
        if not HAS_CHROMADB or self._collection is None:
            return []
        try:
            count = self._collection.count()
            if count == 0:
                return []
            results = self._collection.query(
                query_texts=[user_input],
                n_results=min(n_results, count),
            )
            docs = results.get("documents", [[]])[0]
            return [d for d in docs if d]
        except Exception:
            return []

    def load_constraints(self) -> list[str]:
        """Load sovereignty constraints from intent.md."""
        if self._constraints_cache:
            return self._constraints_cache
        constraints = [
            "All data stays local. No cloud ingestion.",
            "No external service dependencies for core function.",
            "Cryptographic audit trail required for all decisions.",
            "Human absence does not imply autonomy.",
        ]
        if CONSTRAINTS_FILE.exists():
            try:
                raw = CONSTRAINTS_FILE.read_text()
                for line in raw.strip().splitlines():
                    line = line.strip().lstrip("- ")
                    if line and not line.startswith("#"):
                        constraints.append(line)
            except Exception:
                pass
        self._constraints_cache = constraints
        return constraints

    def load_memory(self, user_input: str) -> list[str]:
        """Load recent relevant decisions/context from conversation history."""
        history_dir = VAULT_DIR / "history"
        if not history_dir.exists():
            return []
        memories = []
        try:
            files = sorted(history_dir.glob("*.json"), reverse=True)[:20]
            for f in files:
                entry = json.loads(f.read_text())
                if isinstance(entry, dict) and "summary" in entry:
                    memories.append(entry["summary"])
        except Exception:
            pass
        return memories[:5]

    def build_context(self, user_input: str) -> VaultContext:
        """Assemble the full context object for L2."""
        facts = self.query(user_input)
        memory = self.load_memory(user_input)
        constraints = self.load_constraints()
        return VaultContext(
            facts=facts,
            memory=memory,
            constraints=constraints,
        )

    def save_exchange(self, user_input: str, summary: str):
        """Persist a conversation exchange to history for future context."""
        history_dir = VAULT_DIR / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        import time
        ts = int(time.time() * 1000)
        entry = {
            "timestamp": ts,
            "query": user_input[:200],
            "summary": summary[:500],
        }
        filepath = history_dir / f"{ts}.json"
        filepath.write_text(json.dumps(entry))
