"""
Hybrid Search Implementation: BM25 Keyword + Semantic Search
Combines keyword-based ranking (BM25) with semantic similarity for better retrieval
"""

import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from collections import Counter
import math

logger = logging.getLogger(__name__)


class BM25Ranker:
    """
    BM25 (Best Matching 25) - Industry standard for keyword search
    Ranks documents based on term frequency and inverse document frequency
    """

    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 ranker

        Args:
            corpus: List of documents to index
            k1: Term frequency saturation parameter (default: 1.5)
            b: Length normalization parameter (default: 0.75)
        """
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.corpus_size = len(corpus)

        # Build inverted index
        self.doc_freqs: Dict[str, List[int]] = {}  # term → [doc_ids containing term]
        self.idf: Dict[str, float] = {}  # term → IDF value
        self.doc_lengths = []  # Length of each document (word count)
        self.avg_doc_length = 0

        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization - convert to lowercase and split"""
        return text.lower().split()

    def _build_index(self):
        """Build inverted index and calculate IDF values"""
        for doc_id, doc in enumerate(self.corpus):
            tokens = self._tokenize(doc)
            self.doc_lengths.append(len(tokens))

            # Track unique terms in document
            unique_terms = set(tokens)
            for term in unique_terms:
                if term not in self.doc_freqs:
                    self.doc_freqs[term] = []
                self.doc_freqs[term].append(doc_id)

        # Calculate average document length
        self.avg_doc_length = sum(self.doc_lengths) / self.corpus_size if self.corpus_size > 0 else 0

        # Calculate IDF for each term
        for term, doc_list in self.doc_freqs.items():
            # IDF = log((N - n + 0.5) / (n + 0.5))
            n = len(doc_list)
            self.idf[term] = math.log((self.corpus_size - n + 0.5) / (n + 0.5))

        logger.info(f"[BM25] Indexed {self.corpus_size} documents with {len(self.idf)} unique terms")

    def rank(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Rank documents by relevance to query

        Args:
            query: Query text
            top_k: Number of top results to return

        Returns:
            List of (doc_id, score) tuples
        """
        query_tokens = self._tokenize(query)
        scores = [0.0] * self.corpus_size

        for term in query_tokens:
            if term not in self.idf:
                continue

            idf_score = self.idf[term]
            term_freqs = Counter(self._tokenize(self.corpus[doc_id])) if hasattr(self, 'corpus') else {}

            # Calculate BM25 score for each document
            for doc_id in self.doc_freqs.get(term, []):
                doc_tokens = self._tokenize(self.corpus[doc_id])
                term_freq = doc_tokens.count(term)
                doc_length = self.doc_lengths[doc_id]

                # BM25 formula
                norm_factor = 1 - self.b + self.b * (doc_length / self.avg_doc_length)
                bm25_score = idf_score * (
                    (self.k1 + 1) * term_freq) / (
                    self.k1 * norm_factor + term_freq
                )
                scores[doc_id] += bm25_score

        # Sort and return top_k
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


class HybridSearchEngine:
    """
    Hybrid Search combining BM25 (keyword) and semantic (vector) search
    Uses weighted combination: score = α × semantic_score + (1-α) × keyword_score
    """

    def __init__(self, vector_store, bm25_ranker: BM25Ranker, alpha: float = 0.6):
        """
        Initialize hybrid search engine

        Args:
            vector_store: Semantic vector store (with similarity_search method)
            bm25_ranker: BM25 keyword ranker
            alpha: Weight for semantic search (0-1). Default 0.6 = 60% semantic, 40% keyword
        """
        self.vector_store = vector_store
        self.bm25 = bm25_ranker
        self.alpha = alpha

        if not (0 <= alpha <= 1):
            raise ValueError("Alpha must be between 0 and 1")

        logger.info(f"[HybridSearch] Initialized with alpha={alpha} (semantic={alpha*100:.0f}%, keyword={(1-alpha)*100:.0f}%)")

    def search(
        self,
        query: str,
        embedding: Optional[np.ndarray] = None,
        top_k: int = 10,
        semantic_only: bool = False,
        keyword_only: bool = False
    ) -> List[Dict]:
        """
        Perform hybrid search combining keyword and semantic methods

        Args:
            query: Query text
            embedding: Pre-computed query embedding (if available)
            top_k: Number of results to return
            semantic_only: Skip BM25, use only semantic search
            keyword_only: Skip semantic, use only BM25

        Returns:
            Ranked list of result dicts with 'doc_id', 'score', 'metadata'
        """
        results = {}  # doc_id → combined_score

        # 1. Semantic search (if embedding available and not keyword_only)
        if embedding is not None and not keyword_only:
            semantic_results = self.vector_store.similarity_search(embedding, top_k * 2)

            # Normalize semantic scores to [0, 1]
            max_semantic_score = max([s[1] for s in semantic_results]) if semantic_results else 1.0

            for doc_id, similarity, metadata in semantic_results:
                normalized_score = similarity / max_semantic_score if max_semantic_score > 0 else 0
                results[doc_id] = {
                    'semantic_score': similarity,
                    'normalized_semantic': normalized_score,
                    'metadata': metadata,
                    'combined_score': 0  # Will be set below
                }

        # 2. Keyword search BM25 (if not semantic_only)
        if not semantic_only:
            keyword_results = self.bm25.rank(query, top_k * 2)

            # Normalize BM25 scores to [0, 1]
            max_keyword_score = max([s[1] for s in keyword_results]) if keyword_results else 1.0

            for doc_id, bm25_score in keyword_results:
                normalized_score = bm25_score / max_keyword_score if max_keyword_score > 0 else 0

                if doc_id in results:
                    results[doc_id]['keyword_score'] = bm25_score
                    results[doc_id]['normalized_keyword'] = normalized_score
                else:
                    results[doc_id] = {
                        'semantic_score': 0,
                        'normalized_semantic': 0,
                        'keyword_score': bm25_score,
                        'normalized_keyword': normalized_score,
                        'metadata': {},
                        'combined_score': 0
                    }

        # 3. Combine scores using weighted sum
        for doc_id, result_dict in results.items():
            semantic_part = result_dict.get('normalized_semantic', 0) * self.alpha
            keyword_part = result_dict.get('normalized_keyword', 0) * (1 - self.alpha)
            result_dict['combined_score'] = semantic_part + keyword_part

        # 4. Sort by combined score and return top_k
        ranked = sorted(
            [(doc_id, data) for doc_id, data in results.items()],
            key=lambda x: x[1]['combined_score'],
            reverse=True
        )

        return [
            {
                'doc_id': doc_id,
                'score': data['combined_score'],
                'semantic_score': data.get('semantic_score', 0),
                'keyword_score': data.get('keyword_score', 0),
                'metadata': data.get('metadata', {})
            }
            for doc_id, data in ranked[:top_k]
        ]


class SearchConfig:
    """Configuration for hybrid search parameters"""

    def __init__(
        self,
        alpha: float = 0.6,
        top_k: int = 10,
        similarity_threshold: float = 0.3,
        bm25_k1: float = 1.5,
        bm25_b: float = 0.75
    ):
        """
        Initialize search configuration

        Args:
            alpha: Weight for semantic search (0-1)
            top_k: Default number of results
            similarity_threshold: Minimum similarity score to include
            bm25_k1: BM25 k1 parameter
            bm25_b: BM25 b parameter
        """
        self.alpha = alpha
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.bm25_k1 = bm25_k1
        self.bm25_b = bm25_b

    def __repr__(self):
        return (
            f"SearchConfig(alpha={self.alpha}, top_k={self.top_k}, "
            f"threshold={self.similarity_threshold}, bm25_k1={self.bm25_k1}, "
            f"bm25_b={self.bm25_b})"
        )
