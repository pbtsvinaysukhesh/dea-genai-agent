"""
MMR (Maximum Marginal Relevance) Ranker
Ensures retrieved documents are diverse and non-redundant
Formula: MMR = λ × relevance(d) - (1-λ) × max(similarity(d, selected))
"""

import logging
from typing import List, Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class MMRRanker:
    """
    Maximum Marginal Relevance (MMR) re-ranker
    Balances relevance to query with diversity among selected documents
    Prevents getting similar/redundant results
    """

    def __init__(self, lambda_param: float = 0.5):
        """
        Initialize MMR ranker

        Args:
            lambda_param: Trade-off parameter (0-1)
                - λ=1.0: Pure relevance (no diversity)
                - λ=0.5: Balanced relevance and diversity (recommended)
                - λ=0.0: Pure diversity
        """
        if not (0 <= lambda_param <= 1):
            raise ValueError("lambda_param must be between 0 and 1")

        self.lambda_param = lambda_param
        logger.info(f"[MMR] Initialized with lambda={lambda_param} (relevance={lambda_param*100:.0f}%, diversity={(1-lambda_param)*100:.0f}%)")

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        if norm_product == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / norm_product)

    def rank(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: Dict[str, np.ndarray],
        relevance_scores: Dict[str, float],
        top_k: int = 10
    ) -> List[Tuple[str, float, float, float]]:
        """
        Rank documents using MMR algorithm

        Args:
            query_embedding: Query vector embedding
            candidate_embeddings: Dict of {doc_id: embedding_vector}
            relevance_scores: Dict of {doc_id: relevance_score}
            top_k: Number of diverse results to return

        Returns:
            List of (doc_id, mmr_score, relevance, diversity) tuples
        """
        if not candidate_embeddings:
            return []

        selected_docs = []
        remaining_docs = set(candidate_embeddings.keys())
        results = []

        # Greedy selection of top_k most diverse+relevant documents
        for _ in range(min(top_k, len(remaining_docs))):
            best_doc = None
            best_mmr_score = -float('inf')
            best_relevance = 0
            best_diversity = 0

            for doc_id in remaining_docs:
                # 1. Calculate relevance (similarity to query)
                doc_embedding = candidate_embeddings[doc_id]
                relevance = self._cosine_similarity(query_embedding, doc_embedding)

                # If relevance_scores provided, weight by that
                if doc_id in relevance_scores:
                    relevance = relevance * (relevance_scores[doc_id] / 100.0)

                # 2. Calculate diversity (dissimilarity to already selected)
                diversity = 1.0  # Start with max diversity for first item
                if selected_docs:
                    # Find max similarity to any selected document
                    max_similarity = max([
                        self._cosine_similarity(doc_embedding, candidate_embeddings[selected])
                        for selected in selected_docs
                    ])
                    diversity = 1.0 - max_similarity  # Higher = more diverse

                # 3. Calculate MMR score
                mmr_score = (self.lambda_param * relevance) - (
                    (1 - self.lambda_param) * (1 - diversity)
                )

                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_doc = doc_id
                    best_relevance = relevance
                    best_diversity = diversity

            if best_doc is not None:
                selected_docs.append(best_doc)
                remaining_docs.remove(best_doc)
                results.append((best_doc, best_mmr_score, best_relevance, best_diversity))

        logger.debug(f"[MMR] Selected {len(results)} documents with average MMR score: {np.mean([r[1] for r in results]):.3f}")

        return results

    def rerank_results(
        self,
        query_embedding: np.ndarray,
        results: List[Dict],
        top_k: int = 10
    ) -> List[Dict]:
        """
        Re-rank search results using MMR

        Args:
            query_embedding: Query embedding vector
            results: List of result dicts with 'doc_id', 'embedding', 'score', 'metadata'
            top_k: Number of re-ranked results to return

        Returns:
            Re-ranked results with MMR scores
        """
        # Extract embeddings and scores
        embeddings = {}
        scores = {}

        for result in results:
            doc_id = result.get('doc_id') or result.get('id')
            if 'embedding' not in result:
                logger.warning(f"Result {doc_id} missing embedding, skipping")
                continue

            embeddings[str(doc_id)] = np.array(result['embedding'])
            scores[str(doc_id)] = result.get('score', 0.5)

        if not embeddings:
            logger.warning("[MMR] No embeddings found in results")
            return results[:top_k]

        # Rank with MMR
        mmr_ranked = self.rank(query_embedding, embeddings, scores, top_k)

        # Merge MMR scores back into original results
        result_dict = {str(r.get('doc_id') or r.get('id')): r for r in results}
        reranked = []

        for doc_id, mmr_score, relevance, diversity in mmr_ranked:
            if str(doc_id) in result_dict:
                result = result_dict[str(doc_id)].copy()
                result['mmr_score'] = float(mmr_score)
                result['relevance_score'] = float(relevance)
                result['diversity_score'] = float(diversity)
                reranked.append(result)

        return reranked


class FakeEmbedding:
    """Placeholder for results without embeddings during testing"""

    @staticmethod
    def create_dummy(doc_id: str, dim: int = 768) -> np.ndarray:
        """Create deterministic dummy embedding for testing"""
        np.random.seed(hash(doc_id) % (2**32))
        return np.random.randn(dim).astype(np.float32)


def compare_ranking_strategies(
    query_embedding: np.ndarray,
    results: List[Dict],
    top_k: int = 5
) -> Dict:
    """
    Compare different ranking strategies for learning purposes

    Args:
        query_embedding: Query vector
        results: Result list with embeddings
        top_k: Number to return from each strategy

    Returns:
        Dict with rankings from different strategies
    """
    strategies = {}

    # 1. Pure relevance ranking
    strategies['relevance_only'] = sorted(
        results,
        key=lambda x: x.get('score', 0),
        reverse=True
    )[:top_k]

    # 2. Pure diversity ranking (no query consideration)
    embeddings = {str(r.get('id')): np.array(r['embedding']) for r in results if 'embedding' in r}
    diverse = []
    remaining = set(embeddings.keys())

    for _ in range(min(top_k, len(remaining))):
        if not diverse:
            # First item: pick highest scoring
            best = max(remaining, key=lambda x: float([r['score'] for r in results if str(r.get('id')) == x][0]))
        else:
            # Pick most different from selected
            best = max(remaining, key=lambda doc: min([
                1 - abs(np.dot(
                    embeddings[doc] / (np.linalg.norm(embeddings[doc]) + 1e-8),
                    embeddings[sel] / (np.linalg.norm(embeddings[sel]) + 1e-8)
                )) for sel in diverse
            ]))
        diverse.append(best)
        remaining.remove(best)

    strategies['diversity_only'] = [r for r in results if str(r.get('id')) in diverse][:top_k]

    # 3. Balanced MMR ranking
    mmr = MMRRanker(lambda_param=0.5)
    embeddings_dict = {str(r.get('doc_id') or r.get('id')): np.array(r['embedding'])
                       for r in results if 'embedding' in r}
    scores_dict = {str(r.get('doc_id') or r.get('id')): r.get('score', 0.5) for r in results}

    mmr_ranked = mmr.rank(query_embedding, embeddings_dict, scores_dict, top_k)
    strategies['mmr_alpha=0.5'] = [
        r for r in results
        if str(r.get('doc_id') or r.get('id')) in [m[0] for m in mmr_ranked]
    ][:top_k]

    return strategies
