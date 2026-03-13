"""
Google Embedding Provider (Primary)
Uses GOOGLE_API_KEY → text-embedding-004 (high quality)
Fallback to deterministic hash.
No local models.
"""

import os
import logging
import time
import hashlib
from typing import List, Optional
import numpy as np
import google.generativeai as genai

logger = logging.getLogger(__name__)


def _hash_embedding(text: str, dim: int = 768) -> List[float]:
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2 ** 32)
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec.tolist()


class GoogleEmbeddingProvider:
    def __init__(self, max_retries: int = 3):
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.max_retries = max_retries
        self.embedding_dim = 768
        
        if self.google_key:
            genai.configure(api_key=self.google_key)
            logger.info("✓ Google Embedding API ready (text-embedding-004)")
        else:
            logger.warning("⚠️ GOOGLE_API_KEY missing → hash only")

    def encode(self, text: str, retry_attempt: int = 0) -> List[float]:
        if not self.google_key:
            return _hash_embedding(text)

        try:
            response = genai.embed_content(
                model="models/text-embedding-004",
                content=text[:8192],  # Max context
                task_type="retrieval_document"
            )
            embedding = response['embedding']
            logger.debug("✓ Google embedding")
            self.embedding_dim = len(embedding)
            return embedding
        except Exception as e:
            logger.warning(f"[Google Embed #{retry_attempt+1}] {str(e)[:80]}")
            
            if retry_attempt < self.max_retries - 1:
                time.sleep(2 ** retry_attempt)
                return self.encode(text, retry_attempt + 1)
            
            logger.info("→ Hash fallback")
            return _hash_embedding(text, self.embedding_dim)

    def get_dimension(self) -> int:
        return self.embedding_dim

    def get_status(self) -> dict:
        return {
            'google_api': bool(os.getenv("GOOGLE_API_KEY")),
            'embedding_dim': self.embedding_dim,
            'provider': 'Google text-embedding-004'
        }


_embedding_provider = None

def get_embedding_provider():
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = GoogleEmbeddingProvider()
    return _embedding_provider

def reset_embedding_provider():
    global _embedding_provider
    _embedding_provider = None
