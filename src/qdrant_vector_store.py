"""
Qdrant Vector Store - Semantic Search & Deduplication
======================================================
Version-agnostic: works with qdrant-client 0.x, 1.0-1.6, and 1.7+.

The qdrant-client API changed across versions:
  v0.x / 1.0-1.6 : (collection_name, query_vector, limit)
  v1.7+ local mode: client.query_points(collection_name, query=..., limit)
                    (search() only works against a remote HTTP/gRPC server)

_qdrant_search() detects which API is available at runtime and uses it.
"""

import os
import logging
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Qdrant imports ────────────────────────────────────────────────────────────
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


def _qdrant_search(client, collection_name: str, vector: List[float],
                   limit: int, score_threshold: float = None) -> list:
    """
    Version-agnostic Qdrant vector search.

    Tries APIs in order until one succeeds:
      1. query_points()  — qdrant-client >= 1.7 (local + remote)
      2. search()        — qdrant-client < 1.7 (remote only in 1.7+)
      3. scroll()        — last resort: fetch all, sort by cosine similarity

    Returns a list of scored points compatible with both APIs.
    """
    # ── Strategy 1: query_points (v1.7+) ─────────────────────────────────────
    if hasattr(client, "query_points"):
        try:
            kwargs = dict(
                collection_name=collection_name,
                query=vector,
                limit=limit,
            )
            if score_threshold is not None:
                kwargs["score_threshold"] = score_threshold
            result = client.query_points(**kwargs)
            # query_points returns a QueryResponse with .points list
            points = result.points if hasattr(result, "points") else result
            return points
        except Exception as e:
            logger.debug(f"[Qdrant] query_points failed: {e}, trying search()")

    # ── Strategy 2: search (v0.x – v1.6) ────────────────────────────────────
    if hasattr(client, "search"):
        try:
            kwargs = dict(
                collection_name=collection_name,
                query_vector=vector,
                limit=limit,
            )
            if score_threshold is not None:
                kwargs["score_threshold"] = score_threshold
            return client.search(**kwargs)
        except Exception as e:
            logger.debug(f"[Qdrant] search() failed: {e}, trying scroll()")

    # ── Strategy 3: scroll + manual cosine (last resort) ────────────────────
    try:
        import numpy as np
        all_points, _ = client.scroll(
            collection_name=collection_name,
            with_vectors=True,
            with_payload=True,
            limit=10000,
        )
        if not all_points:
            return []

        q = np.array(vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        scored = []
        for pt in all_points:
            v = np.array(pt.vector, dtype=np.float32)
            norm = np.linalg.norm(v)
            cos = float(np.dot(q, v) / (q_norm * norm)) if (q_norm * norm) > 0 else 0.0
            if score_threshold is None or cos >= score_threshold:
                # Attach a .score attribute so callers work uniformly
                pt.score = cos
                scored.append(pt)

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    except Exception as e:
        logger.error(f"[Qdrant] All search strategies failed: {e}")
        return []


class VectorStore:
    """
    Qdrant vector store for semantic paper management.

    Storage mode (DEA_VS_MODE env var):
      persistent  — survives restarts, saved to DEA_VS_PATH (default: results/vector_db)
      memory      — resets each run (original behaviour)
    """

    def __init__(self, collection_name: str = "research_papers"):
        if not QDRANT_AVAILABLE:
            raise ImportError("Install: pip install qdrant-client")

        self.collection_name = collection_name

        # ── Resolve mode / path / threshold from PathConfig or env vars ───────
        try:
            from src.path_config import PathConfig
            pc = PathConfig.get_instance()
            mode            = pc.get_vector_store_mode()
            db_path         = str(pc.get_vector_store_path())
            self.dup_threshold = pc.get_duplicate_threshold()
        except Exception:
            mode            = os.getenv("DEA_VS_MODE", "persistent")
            db_path         = os.getenv("DEA_VS_PATH", "results/vector_db")
            self.dup_threshold = float(os.getenv("DEA_DUP_THRESHOLD", "0.95"))

        # ── Init Qdrant client ────────────────────────────────────────────────
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_key = os.getenv("QDRANT_API_KEY")
        
        if qdrant_url and qdrant_key:
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=60)
            logger.info(f"[Qdrant] Cloud ✓ {qdrant_url[:30]}...")
        elif mode == "persistent":
            os.makedirs(db_path, exist_ok=True)
            self.client = QdrantClient(path=db_path)
            logger.info(f"[Qdrant] Local → {db_path}")
        else:
            self.client = QdrantClient(":memory:")
            logger.info("[Qdrant] Memory")

        # Log which search API is available
        if hasattr(self.client, "query_points"):
            logger.info("[Qdrant] Search API: query_points (v1.7+)")
        elif hasattr(self.client, "search"):
            logger.info("[Qdrant] Search API: search (v0.x–v1.6)")
        else:
            logger.warning("[Qdrant] Search API: scroll+cosine fallback")

        # ── Embedding provider ────────────────────────────────────────────────
        try:
            from src.embedding_provider import get_embedding_provider
            self.embedder = get_embedding_provider()
            self.embedding_dim = self.embedder.get_dimension()
            status = self.embedder.get_status()
            logger.info(f"✓ Embedding provider ready (dim={self.embedding_dim})")
            logger.info(f"  Google: {'✓' if status['google_available'] else '✗'}  "
                        f"GROQ: {'✓' if status['groq_available'] else '✗'}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding provider: {e}")
            raise

        # ── Create collection (skip if already exists in persistent mode) ─────
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE)
            )
            logger.info(f"[Qdrant] Collection '{self.collection_name}' created")
        else:
            try:
                info = self.client.get_collection(self.collection_name)
                logger.info(f"[Qdrant] Collection reloaded — {info.points_count} papers stored")
            except Exception:
                logger.info(f"[Qdrant] Collection '{self.collection_name}' reloaded")

        self.stats = {'added': 0, 'duplicates': 0, 'searches': 0}

    # ── Embedding ─────────────────────────────────────────────────────────────

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding — always returns a vector (hash fallback in provider)."""
        return self.embedder.encode(text)

    # ── Core operations ───────────────────────────────────────────────────────

    def add_paper(self, paper: Dict) -> bool:
        """Add paper. Returns False if duplicate, True if added."""
        text = f"{paper.get('title', '')} {paper.get('summary', '')[:500]}"
        embedding = self.generate_embedding(text)

        if embedding is None:
            logger.warning("[Qdrant] Embedding returned None — skipping vector check")
            return True  # don't block the pipeline

        is_dup, sim, _ = self.is_duplicate(embedding)
        if is_dup:
            self.stats['duplicates'] += 1
            logger.info(f"[Qdrant] DUPLICATE ({sim:.0%}) — skipped")
            return False

        point = PointStruct(
            id=self._hash_id(paper),
            vector=embedding,
            payload={
                'title':       paper.get('title', '')[:200],
                'score':       paper.get('relevance_score', 0),
                'platform':    paper.get('platform', 'Unknown'),
                'source':      paper.get('source', 'Unknown'),
                'link':        paper.get('link', paper.get('url', '')),
                'dram_impact': paper.get('dram_impact', 'Unknown'),
                'added_at':    datetime.now().isoformat(),
            }
        )
        self.client.upsert(collection_name=self.collection_name, points=[point])
        self.stats['added'] += 1
        return True

    def is_duplicate(self, embedding: List[float],
                     threshold: float = None) -> Tuple[bool, float, Optional[Dict]]:
        """Check semantic duplicate using version-agnostic search."""
        thr = threshold if threshold is not None else self.dup_threshold
        try:
            results = _qdrant_search(self.client, self.collection_name, embedding, limit=1)
            if results and results[0].score >= thr:
                payload = results[0].payload if hasattr(results[0], 'payload') else {}
                return True, results[0].score, payload
            return False, 0.0, None
        except Exception as e:
            logger.error(f"[Qdrant] Duplicate check error: {e}")
            return False, 0.0, None

    def find_similar(self, paper: Dict, top_k: int = 3) -> List[Dict]:
        """Find semantically similar papers."""
        text = f"{paper.get('title', '')} {paper.get('summary', '')}"
        embedding = self.generate_embedding(text)
        if embedding is None:
            return []
        try:
            results = _qdrant_search(
                self.client, self.collection_name, embedding,
                limit=top_k, score_threshold=0.7
            )
            self.stats['searches'] += 1
            return [{'similarity': r.score,
                     **(r.payload if hasattr(r, 'payload') else {})}
                    for r in results]
        except Exception as e:
            logger.error(f"[Qdrant] find_similar error: {e}")
            return []

    def _hash_id(self, paper: Dict) -> int:
        """Deterministic int ID from paper title + url."""
        text = f"{paper.get('title', '')}_{paper.get('url', paper.get('link', ''))}"
        return int(hashlib.md5(text.encode()).hexdigest()[:16], 16)

    def get_stats(self) -> Dict:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(self.collection_name)
            total = info.points_count
        except Exception:
            total = self.stats['added']
        return {**self.stats, 'total_papers': total}


class VectorStoreManager:
    """High-level manager — safe to construct even when qdrant is not installed."""

    def __init__(self, enabled: bool = True):
        # EMBEDDINGS_AVAILABLE was never defined — removed that reference
        self.enabled = enabled and QDRANT_AVAILABLE

        if self.enabled:
            try:
                self.store = VectorStore()
                logger.info("[VectorManager] Enabled")
            except Exception as e:
                logger.warning(f"[VectorManager] Init failed: {e}")
                self.enabled = False
                self.store = None
        else:
            self.store = None

    def check_and_add(self, paper: Dict) -> Tuple[bool, str]:
        """Deduplicate and add. Returns (should_process, reason)."""
        if not self.enabled:
            return True, "disabled"
        return (True, "new") if self.store.add_paper(paper) else (False, "duplicate")

    def get_context(self, paper: Dict) -> str:
        """Return similar-papers context string for RAG."""
        if not self.enabled:
            return ""
        similar = self.store.find_similar(paper, top_k=3)
        if not similar:
            return ""
        lines = ["SIMILAR PAPERS:"]
        for s in similar:
            lines.append(f"- {s.get('title', 'Unknown')[:60]} ({s['similarity']:.0%})")
        return "\n".join(lines)

    def get_stats(self) -> Dict:
        if not self.enabled:
            return {'enabled': False}
        return {'enabled': True, **self.store.get_stats()}