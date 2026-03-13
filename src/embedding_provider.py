"""
Free Tier Embedding Provider: Local Gemma Primary → Hash Fallback
============================================================
Eliminates Groq/Google API costs/limits. Uses models/embeddinggemma-300m/
USE_LOCAL_EMBEDDINGS=true in .env
"""

import os
import logging
import hashlib
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


def _hash_embedding(text: str, dim: int = 768) -> List[float]:
    """
    Deterministic unit-vector embedding from text hash.
    No API calls. Good for duplicate detection.
    """
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2 ** 32)
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


class EmbeddingProvider:
    """
    Free Tier Embeddings: Local Gemma-300M → hash fallback (0 API cost).
    USE_LOCAL_EMBEDDINGS=true enables Gemma from models/embeddinggemma-300m/
    """
    
    def __init__(self):
        self.local_available = False
        self.embedding_dim = 384  # Gemma-300M dim
        
        # Local Gemma primary (free tier)
        if os.getenv("USE_LOCAL_EMBEDDINGS", "true").lower() == "true":
            try:
                from sentence_transformers import SentenceTransformer
                self.local_model = SentenceTransformer("models/embeddinggemma-300m")
                self.local_available = True
                self.embedding_dim = self.local_model.get_sentence_embedding_dimension()
                logger.info(f"✓ Local Gemma-300M loaded (dim={self.embedding_dim}, 0 cost)")
            except Exception as e:
                logger.warning(f"⚠️ Gemma-300M failed: {e} → hash only")

        logger.info("[EmbeddingProvider] Free tier ready ✓ (Local Gemma → hash)")

    def encode(self, text: str) -> List[float]:
        """Encode text → embedding vector."""
        # 1. Local Gemma
        if self.local_available:
            try:
                embedding = self.local_model.encode([text], show_progress_bar=False, convert_to_numpy=True)[0]
                logger.debug("[EmbeddingProvider] ✓ Gemma-300M")
                return embedding.tolist()
            except Exception as e:
                logger.warning(f"[Gemma] Error: {e}")

        # 2. Hash fallback (always works)
        logger.debug("[EmbeddingProvider] Hash embedding")
        return _hash_embedding(text, self.embedding_dim)

    def get_dimension(self) -> int:
        return self.embedding_dim

    def get_status(self) -> dict:
        return {
            'local_gemma': self.local_available,
            'embedding_dim': self.embedding_dim,
            'free_tier': True
        }


# Global singleton
_embedding_provider = None


def get_embedding_provider() -> EmbeddingProvider:
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = EmbeddingProvider()
    return _embedding_provider


def reset_embedding_provider():
    global _embedding_provider
    _embedding_provider = None
