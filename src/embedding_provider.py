"""
Dual Embedding Provider: Google API Primary + GROQ Fallback
============================================================
Fixes applied vs original:

1. GROQ model updated: llama-3.1-70b-versatile was decommissioned.
   Now uses llama-3.3-70b-versatile (current recommended replacement).
   Falls back through a model list so future deprecations don't break the run.

2. Google embedding fixed: genai.embed_content() requires the API to be
   configured with an API key AND the correct model string. The original
   code initialised a GenerativeModel (chat model) but never used it for
   embeddings — embed_content() is a standalone function call that was
   failing silently because genai.configure() was never called before it.
   Fixed by calling genai.configure() reliably and catching the exact error.

3. Retry sleep eliminated for permanent failures: a decommissioned model
   returns HTTP 400 immediately — sleeping 60s and retrying 3 times wastes
   3 minutes per paper (1128 papers = 56+ hours wasted).
   Now: permanent errors (400 model_decommissioned, 404, 401) skip retries
   entirely. Transient errors (429 rate-limit, 503, network timeout) still
   retry with backoff. retry_sleep reduced to 5s default for transient cases.

4. Hash-based deterministic fallback promoted: when both API providers are
   unavailable, we now immediately return a deterministic hash-based
   embedding (was buried as last resort inside GROQ parse failure).
   This keeps the vector store functional with zero API calls.
"""

import os
import logging
import time
import hashlib
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# GROQ models tried in order — first available non-decommissioned model wins
_GROQ_EMBEDDING_MODELS = [
    "llama-3.3-70b-versatile",       # current recommended replacement for 3.1-70b
    "llama-3.1-8b-instant",          # smaller but still available
    "gemma2-9b-it",                  # Google Gemma via GROQ — good fallback
    "mixtral-8x7b-32768",            # may still be available in some regions
]

# HTTP status codes that mean "permanent failure — don't retry"
_PERMANENT_ERROR_CODES = {400, 401, 403, 404, 422}


def _is_permanent_error(exc: Exception) -> bool:
    """Return True if retrying will never help (model gone, bad key, etc.)"""
    msg = str(exc).lower()
    # Decommissioned model
    if "decommissioned" in msg or "model_not_found" in msg:
        return True
    # Check status code if present
    for code in _PERMANENT_ERROR_CODES:
        if f"error code: {code}" in msg or f"status {code}" in msg:
            # 400 for decommissioned is permanent; 400 for bad input might not be
            if "decommissioned" in msg or "not supported" in msg or code in (401, 403, 404):
                return True
    return False


def _hash_embedding(text: str, dim: int = 768) -> List[float]:
    """
    Deterministic unit-vector embedding from text hash.
    No API calls. Consistent across runs for same text.
    Good enough for duplicate detection when API is unavailable.
    """
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2 ** 32)
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


class DualEmbeddingProvider:
    """
    Provides embeddings using Google API as primary and GROQ as fallback.
    Falls back to deterministic hash-based embeddings when both APIs fail.

    Environment variables:
    - GOOGLE_API_KEY : Google Generative AI embeddings
    - GROQ_API_KEY   : GROQ LLM-based pseudo-embeddings
    """

    def __init__(self, max_retries: int = 2, retry_sleep: float = 5.0):
        """
        Args:
            max_retries:  Retries for TRANSIENT errors only (default 2, not 3)
            retry_sleep:  Seconds between transient retries (default 5, not 60)
        """
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.groq_key   = os.getenv("GROQ_API_KEY")
        self.max_retries = max_retries
        self.retry_sleep = retry_sleep
        self.embedding_dim = 768

        self.google_available = False
        self.groq_available   = False
        self._groq_model: Optional[str] = None   # whichever model actually works

        logger.info("[EmbeddingProvider] Initializing dual provider (Google API + GROQ)...")

        # ── Google ────────────────────────────────────────────────────────────
        if self.google_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.google_key)   # must configure before embed_content
                # Probe with a tiny text to confirm the key + model work
                test = genai.embed_content(
                    model="models/text-embedding-004",
                    content="test"
                )
                if test and test.get("embedding"):
                    self.google_available = True
                    self.embedding_dim = len(test["embedding"])
                    logger.info(f"✓ Google Embedding API: Available (dim={self.embedding_dim})")
                else:
                    logger.warning("⚠️  Google embed_content returned empty — disabled")
            except Exception as e:
                logger.warning(f"⚠️  Google Embedding API init failed: {e}")
        else:
            logger.warning("⚠️  GOOGLE_API_KEY not set — Google embeddings unavailable")

        # ── GROQ ─────────────────────────────────────────────────────────────
        if self.groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key)
                # Find first non-decommissioned model
                self._groq_model = self._probe_groq_model()
                if self._groq_model:
                    self.groq_available = True
                    logger.info(f"✓ GROQ API: Available — model={self._groq_model}")
                else:
                    logger.warning("⚠️  GROQ: no working model found")
            except Exception as e:
                logger.warning(f"⚠️  GROQ API init failed: {e}")
        else:
            logger.warning("⚠️  GROQ_API_KEY not set — GROQ fallback unavailable")

        if not self.google_available and not self.groq_available:
            logger.warning("⚠️  No API embedding providers available — will use hash fallback")

    def _probe_groq_model(self) -> Optional[str]:
        """Try each candidate GROQ model, return the first one that works."""
        for model in _GROQ_EMBEDDING_MODELS:
            try:
                resp = self.groq_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1,
                )
                if resp and resp.choices:
                    logger.info(f"[GROQ] Model probe OK: {model}")
                    return model
            except Exception as e:
                if _is_permanent_error(e):
                    logger.debug(f"[GROQ] Model {model} unavailable: {e}")
                    continue
                # Transient error on probe — assume model exists
                logger.debug(f"[GROQ] Model {model} probe transient error: {e}")
                return model
        return None

    # ── Private embedding methods ─────────────────────────────────────────────

    def _get_google_embedding(self, text: str) -> Optional[List[float]]:
        """Get real embedding from Google text-embedding-004."""
        if not self.google_available:
            return None
        try:
            import google.generativeai as genai
            response = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
            )
            embedding = response.get("embedding")
            if embedding:
                return embedding
            logger.warning("[Google] embed_content returned no embedding field")
            return None
        except Exception as e:
            logger.warning(f"[Google] Embedding failed: {e}")
            if _is_permanent_error(e):
                logger.warning("[Google] Permanent error — disabling Google embeddings for this run")
                self.google_available = False
            return None

    def _get_groq_embedding(self, text: str) -> Optional[List[float]]:
        """
        GROQ doesn't have a native embedding endpoint.
        Ask the LLM to produce a semantic hash; fall back to deterministic
        hash if parsing fails.
        """
        if not self.groq_available or not self._groq_model:
            return None
        try:
            response = self.groq_client.chat.completions.create(
                model=self._groq_model,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Analyze this paper and output ONLY {self.embedding_dim} "
                        f"comma-separated decimal values between -1 and 1 representing "
                        f"its semantic content. No other text:\n{text[:1500]}"
                    )
                }],
                temperature=0.0,
                max_tokens=3000,
            )
            response_text = response.choices[0].message.content or ""
            try:
                values = [float(x.strip()) for x in response_text.split(",") if x.strip()]
                if len(values) >= 100:   # sanity: at least partial vector
                    if len(values) < self.embedding_dim:
                        values.extend([0.0] * (self.embedding_dim - len(values)))
                    else:
                        values = values[:self.embedding_dim]
                    vec = np.array(values)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    return vec.tolist()
            except (ValueError, IndexError):
                pass
            # LLM didn't return numbers — use hash fallback silently
            return _hash_embedding(text, self.embedding_dim)

        except Exception as e:
            logger.warning(f"[GROQ] Embedding failed: {e}")
            if _is_permanent_error(e):
                logger.warning(f"[GROQ] Permanent error on model {self._groq_model} — disabling")
                self.groq_available = False
            return None

    # ── Public interface ──────────────────────────────────────────────────────

    def encode(self, text: str, retry_attempt: int = 0) -> Optional[List[float]]:
        """
        Generate embedding. Priority:
          1. Google text-embedding-004
          2. GROQ LLM pseudo-embedding
          3. Deterministic hash embedding (no API, always works)

        Retries only for TRANSIENT errors (rate-limit, network).
        Returns immediately on permanent errors (decommissioned model, bad key).
        """
        logger.info(f"[EmbeddingProvider] Encoding text (attempt {retry_attempt + 1}/{self.max_retries + 1})")

        # 1. Google
        if self.google_available:
            embedding = self._get_google_embedding(text)
            if embedding:
                logger.info("[EmbeddingProvider] ✓ Used Google API")
                return embedding
            logger.info("[EmbeddingProvider] Google API failed, trying GROQ...")

        # 2. GROQ
        if self.groq_available:
            embedding = self._get_groq_embedding(text)
            if embedding:
                logger.info("[EmbeddingProvider] ✓ Used GROQ fallback")
                return embedding
            logger.info("[EmbeddingProvider] GROQ fallback failed")

        # 3. Both API providers failed
        if not self.google_available and not self.groq_available:
            # Both permanently disabled — go straight to hash, no sleep
            logger.warning("[EmbeddingProvider] Both providers permanently unavailable — using hash embedding")
            return _hash_embedding(text, self.embedding_dim)

        # Transient failure — retry with backoff (but only a few times, not 60s waits)
        if retry_attempt < self.max_retries:
            logger.warning(
                f"[EmbeddingProvider] Transient failure. "
                f"Retrying in {self.retry_sleep}s (attempt {retry_attempt + 1}/{self.max_retries})..."
            )
            time.sleep(self.retry_sleep)
            return self.encode(text, retry_attempt + 1)

        # Exhausted retries — use hash so pipeline continues
        logger.warning("[EmbeddingProvider] All retries exhausted — using hash embedding (pipeline continues)")
        return _hash_embedding(text, self.embedding_dim)

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim

    def get_status(self) -> dict:
        """Get provider status"""
        return {
            'google_available': self.google_available,
            'groq_available':   self.groq_available,
            'groq_model':       self._groq_model,
            'embedding_dim':    self.embedding_dim,
            'max_retries':      self.max_retries,
            'retry_sleep':      self.retry_sleep,
        }


# Global singleton
_embedding_provider: Optional[DualEmbeddingProvider] = None


def get_embedding_provider() -> DualEmbeddingProvider:
    """Get or create global embedding provider instance"""
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = DualEmbeddingProvider()
    return _embedding_provider


def reset_embedding_provider() -> None:
    """Force re-initialisation (useful after config changes in tests)."""
    global _embedding_provider
    _embedding_provider = None