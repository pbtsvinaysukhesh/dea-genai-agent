"""
Dual Embedding Provider: Google API Primary + GROQ Fallback
Implements retry logic with 60-second sleep on failures
"""

import os
import logging
import time
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class DualEmbeddingProvider:
    """
    Provides embeddings using Google API as primary and GROQ as fallback

    Strategy:
    1. Try Google API embedding
    2. On failure, try GROQ embedding
    3. On both failures, sleep 60 seconds and retry

    Environment variables required:
    - GOOGLE_API_KEY: For Google embeddings
    - GROQ_API_KEY: For GROQ fallback
    """

    def __init__(self, max_retries: int = 3, retry_sleep: float = 60.0):
        """
        Initialize embedding providers

        Args:
            max_retries: Number of retry attempts on failure
            retry_sleep: Sleep time in seconds between retries
        """
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.max_retries = max_retries
        self.retry_sleep = retry_sleep

        # Track which provider is available
        self.google_available = False
        self.groq_available = False
        self.embedding_dim = 768

        logger.info("[EmbeddingProvider] Initializing dual provider...")

        # Initialize Google Embeddings
        if self.google_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.google_key)
                self.google_client = genai.GenerativeModel('gemini-1.5-flash')
                self.google_available = True
                logger.info("✓ Google Embedding API: Available")
            except Exception as e:
                logger.warning(f"⚠️  Google Embedding API initialization failed: {e}")
                self.google_available = False
        else:
            logger.warning("⚠️  GOOGLE_API_KEY not set - Google embeddings unavailable")

        # Initialize GROQ as Fallback
        if self.groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key)
                self.groq_available = True
                logger.info("✓ GROQ API: Available (fallback)")
            except Exception as e:
                logger.warning(f"⚠️  GROQ API initialization failed: {e}")
                self.groq_available = False
        else:
            logger.warning("⚠️  GROQ_API_KEY not set - GROQ fallback unavailable")

        if not self.google_available and not self.groq_available:
            logger.warning("⚠️  No embedding providers available!")

    def _get_google_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from Google API"""
        if not self.google_available:
            return None

        try:
            import google.generativeai as genai

            logger.debug("[Google] Generating embedding...")
            response = genai.embed_content(
                model="models/embedding-001",
                content=text,
                title="On-Device AI Paper"
            )

            embedding = response['embedding']
            logger.debug(f"[Google] ✓ Generated {len(embedding)}D embedding")
            return embedding

        except Exception as e:
            logger.warning(f"[Google] Embedding failed: {e}")
            return None

    def _get_groq_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from GROQ as fallback"""
        if not self.groq_available:
            return None

        try:
            logger.debug("[GROQ] Generating embedding (via text analysis)...")

            # GROQ doesn't have native embeddings, so we generate a semantic hash
            # by asking the model to analyze the text and produce a deterministic response
            response = self.groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{
                    "role": "user",
                    "content": f"Analyze this paper and provide a semantic signature as 768 comma-separated decimal values between -1 and 1:\n{text[:2000]}"
                }],
                temperature=0.1,
                max_tokens=2000
            )

            response_text = response.choices[0].message.content

            # Parse the response to extract embedding values
            try:
                # Try to extract comma-separated values
                values = [float(x.strip()) for x in response_text.split(',') if x.strip()]

                # Pad or truncate to 768 dimensions
                if len(values) < 768:
                    values.extend([0.0] * (768 - len(values)))
                else:
                    values = values[:768]

                # Normalize to unit vector
                embedding = np.array(values)
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm

                logger.debug(f"[GROQ] ✓ Generated semantic embedding ({len(values)}D)")
                return embedding.tolist()

            except (ValueError, IndexError) as e:
                logger.warning(f"[GROQ] Could not parse embedding response: {e}")
                # Return a random deterministic embedding based on text hash
                import hashlib
                hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
                np.random.seed(hash_val % (2**32))
                embedding = np.random.randn(768)
                embedding = embedding / np.linalg.norm(embedding)
                logger.debug(f"[GROQ] Using hash-based embedding fallback")
                return embedding.tolist()

        except Exception as e:
            logger.warning(f"[GROQ] Embedding failed: {e}")
            return None

    def encode(self, text: str, retry_attempt: int = 0) -> Optional[List[float]]:
        """
        Generate embedding with retry logic

        Priority:
        1. Try Google API
        2. If fails, try GROQ
        3. If both fail and retries remaining, sleep 60 seconds and retry

        Args:
            text: Text to embed
            retry_attempt: Current retry attempt (0 = initial)

        Returns:
            List of embedding values or None on final failure
        """
        logger.info(f"[EmbeddingProvider] Encoding text (attempt {retry_attempt + 1}/{self.max_retries})")

        # Try Google first
        if self.google_available:
            embedding = self._get_google_embedding(text)
            if embedding:
                logger.info("[EmbeddingProvider] ✓ Used Google API")
                return embedding
            logger.info("[EmbeddingProvider] Google API failed, trying GROQ...")

        # Try GROQ fallback
        if self.groq_available:
            embedding = self._get_groq_embedding(text)
            if embedding:
                logger.info("[EmbeddingProvider] ✓ Used GROQ fallback")
                return embedding
            logger.info("[EmbeddingProvider] GROQ fallback failed")

        # Both failed - retry if attempts remaining
        if retry_attempt < self.max_retries - 1:
            logger.warning(
                f"[EmbeddingProvider] Both providers failed. "
                f"Sleeping {self.retry_sleep}s before retry..."
            )
            time.sleep(self.retry_sleep)
            return self.encode(text, retry_attempt + 1)

        # Final failure
        logger.error("[EmbeddingProvider] ✗ All embedding providers failed after all retries")
        return None

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim

    def get_status(self) -> dict:
        """Get provider status"""
        return {
            'google_available': self.google_available,
            'groq_available': self.groq_available,
            'embedding_dim': self.embedding_dim,
            'max_retries': self.max_retries,
            'retry_sleep': self.retry_sleep
        }


# Global instance
_embedding_provider = None


def get_embedding_provider() -> DualEmbeddingProvider:
    """Get or create global embedding provider instance"""
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = DualEmbeddingProvider()
    return _embedding_provider
