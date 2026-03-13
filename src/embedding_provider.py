"""
Production Google Embedding Provider
====================================
Google text-embedding-004 primary with:
- Init probe/health check
- Permanent error disable (401/403/404)
- Token accounting/quota guard
- Rich observability metrics
- Exponential retry/backoff
"""

import os
import logging
import time
import hashlib
import json
from typing import List, Optional, Dict
import numpy as np
from google import genai as genai
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingStats:
    session_tokens: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    token_budget: int = 1_000_000  # Daily free tier
    google_available: bool = True

_stats = EmbeddingStats()


def _is_permanent_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    codes = {400, 401, 403, 404, 422}
    for code in codes:
        if f' {code} ' in msg or f'status {code}' in msg:
            return True
    if any(kw in msg for kw in ['invalid api key', 'quota exceeded', 'decommissioned']):
        return True
    return False


def _hash_embedding(text: str, dim: int = 768) -> List[float]:
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim)
    norm = np.linalg.norm(vec)
    return (vec / norm if norm > 0 else vec).tolist()


class ProductionEmbeddingProvider:
    def __init__(self, daily_budget: int = 1_000_000):
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.daily_budget = daily_budget
        self.embedding_dim = 768
        self.google_available = False
        self._backoff_factor = 1.5
        
        if self.google_key:
            genai.configure(api_key=self.google_key)
            self.google_available = self._health_check()
        else:
            logger.error("❌ GOOGLE_API_KEY missing → hash only")
        
        logger.info(f"[EmbeddingProvider] Ready: Google={'✓' if self.google_available else '✗'} "
                   f"Budget={_stats.token_budget:,} Probe={_stats.total_requests}")

    def _health_check(self) -> bool:
        """Probe init to fail-fast bad keys."""
        try:
            test = genai.embed_content(
                model="models/text-embedding-004",
                content="health check"
            )
            emb = test.get('embedding')
            if emb and len(emb) > 0:
                self.embedding_dim = len(emb)
                _stats.session_tokens += len("health check")
                logger.info(f"✓ Google healthy (dim={self.embedding_dim})")
                return True
        except Exception as e:
            logger.error(f"[Health Check] FAIL: {e}")
            if _is_permanent_error(e):
                logger.error("❌ Google permanently disabled")
        return False

    def _estimate_tokens(self, text: str) -> int:
        return min(len(text.encode()) * 4 // 3, 8192)  # Conservative UTF-8 estimate

    def encode(self, text: str, quota_check: bool = True) -> List[float]:
        _stats.total_requests += 1
        
        if quota_check:
            if _stats.session_tokens > self.daily_budget * 0.9:
                logger.warning("⚠️  90% quota → hash fallback")
                return _hash_embedding(text, self.embedding_dim)
        
        if self.google_available:
            attempt = 0
            while attempt < 3:
                try:
                    tokens = self._estimate_tokens(text)
                    _stats.session_tokens += tokens
                    
                    resp = genai.embed_content(
                        model="models/text-embedding-004",
                        content=text[:8192],
                        task_type="retrieval_document"
                    )
                    emb = resp['embedding']
                    logger.debug(f"✓ Google ({tokens} tokens)")
                    return emb
                except Exception as e:
                    logger.warning(f"[Google #{attempt+1}] {str(e)[:60]}")
                    if _is_permanent_error(e):
                        logger.error("❌ Google permanently disabled")
                        self.google_available = False
                        break
                    attempt += 1
                    time.sleep(self._backoff_factor ** attempt)
        
        logger.debug("→ Hash fallback")
        return _hash_embedding(text, self.embedding_dim)

    def get_dimension(self) -> int:
        return self.embedding_dim

    def get_status(self) -> Dict:
        quota_pct = min(_stats.session_tokens / _stats.token_budget * 100, 100)
        return {
            'google_available': self.google_available,
            'embedding_dim': self.embedding_dim,
            'session_tokens': _stats.session_tokens,
            'quota_used': f"{quota_pct:.1f}% ({_stats.session_tokens:,}/{_stats.token_budget:,})",
            'requests': _stats.total_requests,
            'provider': 'Google text-embedding-004 + hash'
        }

    def reset_session(self):
        """Reset daily counters (call on app restart)."""
        global _stats
        _stats = EmbeddingStats()


# Singleton
_provider = None

def get_embedding_provider() -> ProductionEmbeddingProvider:
    global _provider
    if _provider is None:
        _provider = ProductionEmbeddingProvider()
    return _provider

def reset_embedding_provider():
    global _provider
    _provider = None
