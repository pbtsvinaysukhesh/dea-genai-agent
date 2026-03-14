"""
Google Embedding Provider — google-genai SDK (>=1.0)
=====================================================
Uses the NEW google-genai package (from google import genai).
GROQ is NOT used for embeddings — reserved for AI Council scoring.

Old SDK (google-generativeai):         New SDK (google-genai):
  import google.generativeai as genai    from google import genai
  genai.configure(api_key=key)           client = genai.Client(api_key=key)
  genai.embed_content(model, content)    client.models.embed_content(model, contents)
  genai.GenerativeModel(name)            client.models.generate_content(model, contents)

Environment:
    GOOGLE_API_KEY          Google API key
    DEA_EMBED_TOKEN_BUDGET  Session token budget (default 1_000_000)
"""

import os
import logging
import time
import hashlib
from typing import List, Optional, Dict
import numpy as np

logger = logging.getLogger(__name__)

_EMBED_MODEL         = "text-embedding-004"   # no "models/" prefix in new SDK
_EMBED_DIM           = 768
_TOKENS_PER_REQUEST  = 150                    # conservative estimate per call


def _is_permanent_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    for phrase in ("api key not valid", "invalid api key", "permission denied",
                   "not found", "decommissioned", "quota exceeded"):
        if phrase in msg:
            return True
    for code in (400, 401, 403, 404, 422):
        if f" {code} " in msg or f"status {code}" in msg:
            return True
    return False


def _hash_embedding(text: str, dim: int = _EMBED_DIM) -> List[float]:
    """Deterministic unit-vector from MD5 hash. Zero API cost. Always works."""
    seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % (2 ** 32)
    rng  = np.random.default_rng(seed)
    vec  = rng.standard_normal(dim).astype(np.float32)
    norm = np.linalg.norm(vec)
    return (vec / norm if norm > 0 else vec).tolist()


class DualEmbeddingProvider:
    """
    Google text-embedding-004 (new SDK) with hash fallback.
    Class name kept as DualEmbeddingProvider for drop-in compatibility.
    """

    def __init__(self, max_retries: int = 2, retry_sleep: float = 3.0):
        self.max_retries   = max_retries
        self.retry_sleep   = retry_sleep
        self.embedding_dim = _EMBED_DIM
        self.google_available = False
        self.groq_available   = False      # kept for status compat; always False here
        self._session_tokens  = 0
        self._token_budget    = int(os.getenv("DEA_EMBED_TOKEN_BUDGET", "1000000"))
        self._client          = None

        logger.info("[EmbeddingProvider] Initializing (google-genai SDK + hash fallback)")

        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            logger.warning("⚠️  GOOGLE_API_KEY not set — hash-only embeddings")
            return

        try:
            from google import genai                          # NEW SDK
            self._client = genai.Client(api_key=google_key)  # replaces configure()

            # Real probe — confirms key + model work
            result = self._client.models.embed_content(
                model=_EMBED_MODEL,
                contents="health check",
            )
            emb = result.embeddings[0].values if result.embeddings else None
            if emb:
                self.embedding_dim    = len(emb)
                self._session_tokens += _TOKENS_PER_REQUEST
                self.google_available = True
                logger.info(f"✓ Google text-embedding-004: Available (dim={self.embedding_dim})")
            else:
                logger.warning("⚠️  Google embed returned empty — disabled")

        except Exception as e:
            logger.warning(f"⚠️  Google Embedding init failed: {e}")

    # ── private ───────────────────────────────────────────────────────────────

    def _google_embed(self, text: str) -> Optional[List[float]]:
        if not self.google_available or self._client is None:
            return None
        if self._session_tokens >= self._token_budget:
            logger.warning("[Google] Token budget reached — switching to hash mode")
            self.google_available = False
            return None
        try:
            result = self._client.models.embed_content(
                model=_EMBED_MODEL,
                contents=text[:8192],
            )
            emb = result.embeddings[0].values if result.embeddings else None
            if emb:
                self._session_tokens += _TOKENS_PER_REQUEST
                return list(emb)
            return None
        except Exception as e:
            logger.warning(f"[Google] Embedding failed: {e}")
            if _is_permanent_error(e):
                logger.warning("[Google] Permanent error — disabling for this run")
                self.google_available = False
            return None

    # ── public ────────────────────────────────────────────────────────────────

    def encode(self, text: str, retry_attempt: int = 0) -> List[float]:
        """
        Generate embedding. Always returns a vector — never None.
        1. Google text-embedding-004 (real semantic, free tier)
        2. Hash fallback (zero cost, deterministic, instant)
        """
        logger.info(
            f"[EmbeddingProvider] Encoding text "
            f"(attempt {retry_attempt + 1}/{self.max_retries + 1})"
        )

        if self.google_available:
            emb = self._google_embed(text)
            if emb:
                logger.info("[EmbeddingProvider] ✓ Used Google text-embedding-004")
                return emb
            # Still available → transient error, retry with backoff
            if self.google_available and retry_attempt < self.max_retries:
                logger.warning(
                    f"[EmbeddingProvider] Transient failure. "
                    f"Retrying in {self.retry_sleep}s "
                    f"(attempt {retry_attempt + 1}/{self.max_retries})..."
                )
                time.sleep(self.retry_sleep)
                return self.encode(text, retry_attempt + 1)

        logger.debug("[EmbeddingProvider] Using hash embedding (Google unavailable)")
        return _hash_embedding(text, self.embedding_dim)

    def get_dimension(self) -> int:
        return self.embedding_dim

    def get_status(self) -> dict:
        return {
            "google_available": self.google_available,
            "groq_available":   False,
            "embedding_dim":    self.embedding_dim,
            "session_tokens":   self._session_tokens,
            "token_budget":     self._token_budget,
            "max_retries":      self.max_retries,
            "retry_sleep":      self.retry_sleep,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
_embedding_provider: Optional[DualEmbeddingProvider] = None

def get_embedding_provider() -> DualEmbeddingProvider:
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = DualEmbeddingProvider()
    return _embedding_provider

def reset_embedding_provider() -> None:
    global _embedding_provider
    _embedding_provider = None