"""
Qdrant Vector Store - Semantic Search, Deduplication & Clustering
Stores embeddings for intelligent paper management.

Enhancements over original:
  • Config-driven thresholds (duplicate, similarity) via PathConfig / DEA_CONFIG
  • Persistence mode: "memory" (default) or "persistent" (survives restarts)
  • Semantic cluster tagging: auto-assigns topic clusters to papers
  • Fixed: search_points → search (correct qdrant-client v1.x API)
  • Richer payload: cluster_id, link, model_type stored for RAG context
  • get_cluster_summary(): returns per-cluster topic distribution
  • All hardcoded magic numbers replaced with config lookups
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# Qdrant
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


class VectorStore:
    """
    Qdrant vector store for semantic paper management.

    Reads thresholds and mode from PathConfig / DEA_CONFIG so no values
    need to be changed here when tuning the system.
    """

    def __init__(
        self,
        collection_name: str = "research_papers",
        mode: Optional[str] = None,
        persistence_path: Optional[str] = None,
        duplicate_threshold: Optional[float] = None,
        similarity_threshold: Optional[float] = None,
        top_k_similar: Optional[int] = None,
        enable_clustering: Optional[bool] = None,
        cluster_count: Optional[int] = None,
    ):
        if not QDRANT_AVAILABLE:
            raise ImportError("Install: pip install qdrant-client")

        # Resolve config — prefer explicit args, then PathConfig, then DEA_CONFIG defaults
        try:
            from src.path_config import PathConfig
            pc = PathConfig.get_instance()
            cfg_vs = pc.get_dea_config().get("vector_store", {})
            _mode       = mode              or pc.get_vector_store_mode()
            _path       = persistence_path  or str(pc.get_vector_store_path())
            _dup_thr    = duplicate_threshold   or cfg_vs.get("duplicate_threshold", 0.95)
            _sim_thr    = similarity_threshold  or cfg_vs.get("similarity_threshold", 0.70)
            _top_k      = top_k_similar         or cfg_vs.get("top_k_similar", 3)
            _clustering = enable_clustering if enable_clustering is not None else pc.get_clustering_enabled()
            _clusters   = cluster_count         or cfg_vs.get("cluster_count", 8)
        except Exception:
            _mode       = mode              or "memory"
            _path       = persistence_path  or "results/vector_db"
            _dup_thr    = duplicate_threshold   or 0.95
            _sim_thr    = similarity_threshold  or 0.70
            _top_k      = top_k_similar         or 3
            _clustering = enable_clustering if enable_clustering is not None else True
            _clusters   = cluster_count         or 8

        self.collection_name    = collection_name
        self.duplicate_threshold = _dup_thr
        self.similarity_threshold = _sim_thr
        self.top_k_similar      = _top_k
        self.enable_clustering  = _clustering
        self.cluster_count      = _clusters

        # Initialize client based on mode
        if _mode == "persistent":
            import os as _os
            _os.makedirs(_path, exist_ok=True)
            self.client = QdrantClient(path=_path)
            logger.info(f"[Qdrant] Persistent mode → {_path}")
        else:
            self.client = QdrantClient(":memory:")
            logger.info("[Qdrant] In-memory mode")

        # Initialize embedding provider
        logger.info("[Embeddings] Initializing dual provider (Google API + GROQ)...")
        try:
            from src.embedding_provider import get_embedding_provider
            self.embedder = get_embedding_provider()
            self.embedding_dim = self.embedder.get_dimension()
            status = self.embedder.get_status()
            logger.info("✓ Dual embedding provider initialized")
            logger.info(f"  Google API: {'✓' if status['google_available'] else '✗'}")
            logger.info(f"  GROQ Fallback: {'✓' if status['groq_available'] else '✗'}")
            logger.info(f"  Dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding provider: {e}")
            raise

        # Create collection if not exists (safe for persistent mode restarts)
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim, distance=Distance.COSINE
                )
            )
            logger.info(f"[Qdrant] Collection '{self.collection_name}' created")
        else:
            logger.info(f"[Qdrant] Collection '{self.collection_name}' reloaded (persistent)")

        # Cluster centroids: cluster_id → centroid embedding (running mean)
        self._cluster_centroids: Dict[int, List[float]] = {}
        self._cluster_counts: Dict[int, int] = {}
        self._cluster_topics: Dict[int, Dict[str, int]] = {}   # cluster_id → {platform: count}

        self.stats = {
            'added': 0, 'duplicates': 0, 'searches': 0,
            'cluster_assignments': 0
        }

    # ── Embedding ─────────────────────────────────────────────────────────────

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using Google API with GROQ fallback."""
        embedding = self.embedder.encode(text)
        if embedding is None:
            logger.error("[Qdrant] Failed to generate embedding")
        return embedding

    # ── Core operations ───────────────────────────────────────────────────────

    def add_paper(self, paper: Dict) -> bool:
        """Add paper to store. Returns False if semantic duplicate detected."""
        text = f"{paper.get('title', '')} {paper.get('summary', '')[:500]}"
        embedding = self.generate_embedding(text)
        if embedding is None:
            logger.warning("[Qdrant] Skipping paper — no embedding generated")
            return True  # don't block pipeline on embedding failure

        is_dup, sim, _ = self.is_duplicate(embedding)
        if is_dup:
            self.stats['duplicates'] += 1
            logger.info(f"[Qdrant] DUPLICATE ({sim:.0%}) — skipped")
            return False

        # Assign to semantic cluster
        cluster_id = self._assign_cluster(embedding, paper)

        point_id = self._hash_id(paper)
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                'title':      paper.get('title', '')[:200],
                'score':      paper.get('relevance_score', 0),
                'platform':   paper.get('platform', 'Unknown'),
                'model_type': paper.get('model_type', 'Unknown'),
                'link':       paper.get('link', ''),
                'source':     paper.get('source', 'Unknown'),
                'cluster_id': cluster_id,
                'added_at':   datetime.now().isoformat(),
            }
        )

        self.client.upsert(collection_name=self.collection_name, points=[point])
        self.stats['added'] += 1
        return True

    def is_duplicate(
        self, embedding: List[float], threshold: Optional[float] = None
    ) -> Tuple[bool, float, Optional[Dict]]:
        """Check if a semantically similar paper already exists."""
        thr = threshold if threshold is not None else self.duplicate_threshold
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=1,
            )
            if results and results[0].score >= thr:
                return True, results[0].score, results[0].payload
            return False, 0.0, None
        except Exception as e:
            logger.error(f"[Qdrant] Duplicate check error: {e}")
            return False, 0.0, None

    def find_similar(self, paper: Dict, top_k: Optional[int] = None) -> List[Dict]:
        """Return top-k semantically similar papers from the store."""
        k = top_k if top_k is not None else self.top_k_similar
        text = f"{paper.get('title', '')} {paper.get('summary', '')}"
        embedding = self.generate_embedding(text)
        if embedding is None:
            return []

        try:
            # Correct qdrant-client v1.x API: client.search (not search_points)
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=k,
                score_threshold=self.similarity_threshold,
            )
        except Exception as e:
            logger.error(f"[Qdrant] find_similar error: {e}")
            return []

        self.stats['searches'] += 1
        return [{'similarity': r.score, **r.payload} for r in results]

    def search_by_cluster(self, cluster_id: int, top_k: int = 10) -> List[Dict]:
        """
        NEW: Return papers belonging to a specific semantic cluster.
        Useful for RAG context enrichment and trend analysis.
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(
                        key="cluster_id",
                        match=MatchValue(value=cluster_id)
                    )]
                ),
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )
            return [r.payload for r in results]
        except Exception as e:
            logger.error(f"[Qdrant] Cluster search error: {e}")
            return []

    def get_cluster_summary(self) -> Dict[int, Dict]:
        """
        NEW: Returns per-cluster statistics — paper count, top platform, top source.
        Enables trend spotting across the collected corpus.
        """
        summary = {}
        for cid, topics in self._cluster_topics.items():
            top_platform = max(topics, key=topics.get) if topics else "Unknown"
            summary[cid] = {
                "paper_count":  self._cluster_counts.get(cid, 0),
                "top_platform": top_platform,
                "platform_breakdown": topics,
            }
        return summary

    # ── Semantic clustering ───────────────────────────────────────────────────

    def _assign_cluster(self, embedding: List[float], paper: Dict) -> int:
        """
        Assign paper to nearest existing cluster, or start a new one.
        Uses online k-means (running centroid update) — no sklearn required.
        Returns cluster_id (0-based integer).
        """
        if not self.enable_clustering:
            return 0

        import numpy as np
        vec = np.array(embedding)

        if not self._cluster_centroids:
            # First paper — create cluster 0
            self._cluster_centroids[0] = embedding
            self._cluster_counts[0] = 1
            self._cluster_topics[0] = {}
            self._update_cluster_topics(0, paper)
            self.stats['cluster_assignments'] += 1
            return 0

        # Find nearest centroid by cosine similarity
        best_cid = -1
        best_sim = -1.0
        for cid, centroid in self._cluster_centroids.items():
            c = np.array(centroid)
            sim = float(np.dot(vec, c) / (np.linalg.norm(vec) * np.linalg.norm(c) + 1e-8))
            if sim > best_sim:
                best_sim = sim
                best_cid = cid

        # If similarity is high enough, join existing cluster
        join_threshold = self.similarity_threshold
        if best_sim >= join_threshold:
            cid = best_cid
        elif len(self._cluster_centroids) < self.cluster_count:
            # Start new cluster
            cid = len(self._cluster_centroids)
            self._cluster_centroids[cid] = embedding
            self._cluster_counts[cid] = 0
            self._cluster_topics[cid] = {}
        else:
            # All clusters full, join nearest anyway
            cid = best_cid

        # Update centroid with running mean
        n = self._cluster_counts.get(cid, 0)
        old_c = np.array(self._cluster_centroids[cid])
        new_c = (old_c * n + vec) / (n + 1)
        # Re-normalize
        norm = np.linalg.norm(new_c)
        if norm > 0:
            new_c = new_c / norm
        self._cluster_centroids[cid] = new_c.tolist()
        self._cluster_counts[cid] = n + 1
        self._update_cluster_topics(cid, paper)
        self.stats['cluster_assignments'] += 1
        return cid

    def _update_cluster_topics(self, cid: int, paper: Dict) -> None:
        """Track platform distribution per cluster for trend summaries."""
        platform = paper.get("platform", "Unknown")
        self._cluster_topics.setdefault(cid, {})
        self._cluster_topics[cid][platform] = self._cluster_topics[cid].get(platform, 0) + 1

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _hash_id(self, paper: Dict) -> int:
        """Generate stable integer ID from title + url."""
        text = f"{paper.get('title', '')}_{paper.get('url', paper.get('link', ''))}"
        return int(hashlib.md5(text.encode()).hexdigest()[:16], 16)

    def get_stats(self) -> Dict:
        """Return operational statistics including cluster summary."""
        try:
            info = self.client.get_collection(self.collection_name)
            total = info.points_count
        except Exception:
            total = self.stats['added']

        return {
            **self.stats,
            'total_papers':    total,
            'duplicate_threshold': self.duplicate_threshold,
            'cluster_count':   len(self._cluster_centroids),
            'cluster_summary': self.get_cluster_summary(),
        }


class VectorStoreManager:
    """
    High-level manager — drop-in replacement for the original.

    New behaviours:
      • Reads mode/threshold from PathConfig (no hardcoding)
      • Exposes get_cluster_context() for RAG enrichment
      • get_stats() now includes cluster breakdown
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled and QDRANT_AVAILABLE

        if self.enabled:
            try:
                self.store = VectorStore()
                logger.info("[VectorManager] Enabled with config-driven settings")
            except Exception as e:
                logger.warning(f"[VectorManager] Init failed: {e}")
                self.enabled = False
                self.store = None
        else:
            self.store = None

    def check_and_add(self, paper: Dict) -> Tuple[bool, str]:
        """Check for semantic duplicate and add if new."""
        if not self.enabled:
            return True, "disabled"
        if self.store.add_paper(paper):
            return True, "new"
        return False, "duplicate"

    def get_context(self, paper: Dict) -> str:
        """Get similar papers context string for AGI analysis prompt."""
        if not self.enabled or not self.store:
            return ""
        similar = self.store.find_similar(paper)
        if not similar:
            return ""
        context = "SIMILAR PAPERS IN STORE:\n"
        for s in similar:
            context += f"- {s.get('title', 'Unknown')[:60]} ({s['similarity']:.0%}) [{s.get('platform', '?')}]\n"
        return context

    def get_cluster_context(self, paper: Dict) -> str:
        """
        NEW: Returns cluster-mate papers for the given paper.
        Provides richer RAG context than pure similarity search.
        """
        if not self.enabled or not self.store:
            return ""
        similar = self.store.find_similar(paper, top_k=1)
        if not similar:
            return ""
        cluster_id = similar[0].get("cluster_id", 0)
        cluster_papers = self.store.search_by_cluster(cluster_id, top_k=5)
        if not cluster_papers:
            return ""
        context = f"TOPIC CLUSTER {cluster_id} — related papers:\n"
        for cp in cluster_papers:
            context += f"- {cp.get('title', 'Unknown')[:60]} [{cp.get('source', '?')}]\n"
        return context

    def get_stats(self) -> Dict:
        """Return stats including cluster breakdown."""
        if not self.enabled or not self.store:
            return {'enabled': False}
        return {'enabled': True, **self.store.get_stats()}