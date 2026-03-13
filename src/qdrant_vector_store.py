"""
Qdrant Vector Store - Semantic Search & Deduplication
Stores embeddings for intelligent paper management
Uses Google API embeddings with GROQ fallback
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

    Mode is driven by DEA_VS_MODE env var (default: persistent).
    persistent → papers remembered across runs at DEA_VS_PATH (results/vector_db)
    memory     → resets each run (original behaviour)
    """

    def __init__(self, collection_name: str = "research_papers"):
        if not QDRANT_AVAILABLE:
            raise ImportError("Install: pip install qdrant-client")

        self.collection_name = collection_name

        # Resolve mode/path/threshold from PathConfig (env-var driven)
        try:
            from src.path_config import PathConfig
            pc = PathConfig.get_instance()
            mode = pc.get_vector_store_mode()
            db_path = str(pc.get_vector_store_path())
            self.dup_threshold = pc.get_duplicate_threshold()
        except Exception:
            mode = os.getenv("DEA_VS_MODE", "persistent")
            db_path = "results/vector_db"
            self.dup_threshold = float(os.getenv("DEA_DUP_THRESHOLD", "0.95"))

        if mode == "persistent":
            os.makedirs(db_path, exist_ok=True)
            self.client = QdrantClient(path=db_path)
            logger.info(f"[Qdrant] Persistent mode → {db_path}")
        else:
            self.client = QdrantClient(":memory:")
            logger.info("[Qdrant] In-memory mode")

        # Initialize Dual Embedding Provider (Google API + GROQ fallback)
        logger.info("[Embeddings] Initializing dual provider (Google API + GROQ)...")

        try:
            from src.embedding_provider import get_embedding_provider
            self.embedder = get_embedding_provider()
            self.embedding_dim = self.embedder.get_dimension()
            status = self.embedder.get_status()

            logger.info(f"✓ Dual embedding provider initialized")
            logger.info(f"  Google API: {'✓' if status['google_available'] else '✗'}")
            logger.info(f"  GROQ Fallback: {'✓' if status['groq_available'] else '✗'}")
            logger.info(f"  Dimension: {self.embedding_dim}")

        except Exception as e:
            logger.error(f"Failed to initialize embedding provider: {e}")
            raise

        # Create collection only if it doesn't exist yet (safe for persistent restarts)
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE)
            )
            logger.info(f"[Qdrant] Collection '{self.collection_name}' created")
        else:
            info = self.client.get_collection(self.collection_name)
            logger.info(f"[Qdrant] Collection reloaded — {info.points_count} papers already stored")

        self.stats = {'added': 0, 'duplicates': 0, 'searches': 0}

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Google API with GROQ fallback"""
        embedding = self.embedder.encode(text)
        if embedding is None:
            logger.error("Failed to generate embedding for text")
        return embedding

    def add_paper(self, paper: Dict) -> bool:
        """Add paper, returns False if duplicate"""
        text = f"{paper.get('title', '')} {paper.get('summary', '')[:500]}"
        embedding = self.generate_embedding(text)

        if embedding is None:
            # Don't crash the pipeline — let the paper through without vector check
            logger.warning("[Qdrant] Embedding failed — skipping vector check for this paper")
            return True

        is_dup, sim, _ = self.is_duplicate(embedding)
        if is_dup:
            self.stats['duplicates'] += 1
            logger.info(f"[Qdrant] DUPLICATE ({sim:.0%})")
            return False

        point_id = self._hash_id(paper)
        point = PointStruct(
            id=point_id,
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

    def is_duplicate(self, embedding: List[float], threshold: float = None) -> Tuple[bool, float, Optional[Dict]]:
        """Check if duplicate using config-driven threshold"""
        thr = threshold if threshold is not None else self.dup_threshold
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=1
            )
            if results and results[0].score >= thr:
                return True, results[0].score, results[0].payload
            return False, 0.0, None
        except Exception as e:
            logger.error(f"[Qdrant] Duplicate check error: {e}")
            return False, 0.0, None

    def find_similar(self, paper: Dict, top_k=3) -> List[Dict]:
        """Find similar papers — uses client.search (correct qdrant-client v1.x API)"""
        text = f"{paper.get('title', '')} {paper.get('summary', '')}"
        embedding = self.generate_embedding(text)
        if embedding is None:
            return []

        try:
            # FIX: search_points does not exist in qdrant-client v1.x — use search()
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=top_k,
                score_threshold=0.7
            )
        except Exception as e:
            logger.error(f"[Qdrant] find_similar error: {e}")
            return []

        self.stats['searches'] += 1
        return [{'similarity': r.score, **r.payload} for r in results]

    def _hash_id(self, paper: Dict) -> int:
        """Generate unique ID"""
        text = f"{paper.get('title', '')}_{paper.get('url', paper.get('link', ''))}"
        return int(hashlib.md5(text.encode()).hexdigest()[:16], 16)

    def get_stats(self) -> Dict:
        """Get statistics"""
        try:
            info = self.client.get_collection(self.collection_name)
            total = info.points_count
        except Exception:
            total = self.stats['added']
        return {**self.stats, 'total_papers': total}


class VectorStoreManager:
    """High-level manager"""

    def __init__(self, enabled: bool = True):
        # FIX: EMBEDDINGS_AVAILABLE was never defined — removed that reference
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
        """Check duplicate and add"""
        if not self.enabled:
            return True, "disabled"
        if self.store.add_paper(paper):
            return True, "new"
        return False, "duplicate"

    def get_context(self, paper: Dict) -> str:
        """Get similar papers context"""
        if not self.enabled:
            return ""
        similar = self.store.find_similar(paper, top_k=3)
        if not similar:
            return ""
        context = "SIMILAR PAPERS:\n"
        for s in similar:
            context += f"- {s.get('title', 'Unknown')[:60]} ({s['similarity']:.0%})\n"
        return context

    def get_stats(self) -> Dict:
        """Get stats"""
        if not self.enabled:
            return {'enabled': False}
        return {'enabled': True, **self.store.get_stats()}