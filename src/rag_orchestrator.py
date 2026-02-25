"""
RAG Orchestrator - Unified Retrieval-Augmented Generation Service
Orchestrates hybrid search, MMR ranking, and context augmentation
"""

import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """
    Enterprise RAG orchestrator combining:
    - Hybrid search (BM25 + semantic)
    - MMR ranking for diversity
    - Multi-stage retrieval and augmentation
    - Contextual prompt generation
    """

    def __init__(
        self,
        hybrid_search_engine=None,
        mmr_ranker=None,
        knowledge_manager=None,
        config: Dict = None
    ):
        """
        Initialize RAG orchestrator

        Args:
            hybrid_search_engine: HybridSearchEngine instance
            mmr_ranker: MMRRanker instance
            knowledge_manager: EnterpriseKnowledgeManager instance
            config: Configuration dict with RAG parameters
        """
        self.hybrid_search = hybrid_search_engine
        self.mmr = mmr_ranker
        self.knowledge_graph = knowledge_manager

        # Default configuration
        self.config = {
            'use_hybrid_search': True,
            'use_mmr': True,
            'alpha': 0.6,  # 60% semantic, 40% keyword
            'lambda': 0.5,  # 50% relevance, 50% diversity
            'top_k': 10,
            'diversity_weight': 0.4,
            **(config or {})
        }

        logger.info(f"[RAGOrchestrator] Initialized with config: {self.config}")

    def retrieve(
        self,
        query: str,
        embedding: Optional[np.ndarray] = None,
        top_k: Optional[int] = None,
        filters: Optional[Dict] = None,
        use_mmr: Optional[bool] = None
    ) -> List[Dict]:
        """
        Retrieve most relevant documents using hybrid search + MMR

        Args:
            query: Query text
            embedding: Pre-computed query embedding (optional)
            top_k: Number of results (default from config)
            filters: Filters for metadata (platform, date, score, etc.)
            use_mmr: Whether to apply MMR ranking (default from config)

        Returns:
            List of relevant documents with scores and metadata
        """
        if top_k is None:
            top_k = self.config['top_k']

        use_mmr = use_mmr if use_mmr is not None else self.config['use_mmr']

        logger.debug(f"[RAG] Retrieving for query: '{query[:50]}...' (top_k={top_k}, MMR={use_mmr})")

        results = []

        # 1. HYBRID SEARCH (Semantic + Keyword)
        if self.hybrid_search and self.config['use_hybrid_search']:
            try:
                hybrid_results = self.hybrid_search.search(
                    query=query,
                    embedding=embedding,
                    top_k=top_k * 2,  # Get more for MMR to choose from
                    semantic_only=False,
                    keyword_only=False
                )
                results.extend(hybrid_results)
                logger.debug(f"[RAG] Hybrid search returned {len(hybrid_results)} results")
            except Exception as e:
                logger.error(f"[RAG] Hybrid search failed: {e}")
                return []

        else:
            # Fallback: semantic search only
            if embedding is not None and self.knowledge_graph:
                try:
                    semantic_results = self.knowledge_graph.search_semantic(
                        embedding, filters=filters, top_k=top_k * 2
                    )
                    results = [
                        {
                            'doc_id': r.get('node_id', r.get('id')),
                            'score': r.get('similarity_score', 0.5),
                            'metadata': {
                                'title': r.get('title', ''),
                                'platform': r.get('platform', ''),
                                'relevance_score': r.get('relevance_score', 0),
                                'memory_insight': r.get('memory_insight', '')
                            }
                        }
                        for r in semantic_results
                    ]
                    logger.debug(f"[RAG] Semantic search returned {len(results)} results")
                except Exception as e:
                    logger.error(f"[RAG] Semantic search failed: {e}")
                    return []

        # 2. APPLY FILTERS
        if filters:
            results = self._apply_filters(results, filters)
            logger.debug(f"[RAG] After filtering: {len(results)} results")

        # 3. MMR RERANKING (Diversity)
        if use_mmr and self.mmr and embedding is not None:
            try:
                # Ensure results have embeddings
                for r in results:
                    if 'embedding' not in r:
                        # Generate or retrieve embedding
                        if self.knowledge_graph and self.knowledge_graph.embedder:
                            title = r.get('metadata', {}).get('title', '')
                            if title:
                                r['embedding'] = self.knowledge_graph.embedder.encode(title)
                        else:
                            r['embedding'] = embedding  # Use query embedding as fallback

                mmr_results = self.mmr.rerank_results(embedding, results, top_k)
                logger.debug(f"[RAG] MMR reranking applied, diversity scores calculated")
                return mmr_results[:top_k]
            except Exception as e:
                logger.warning(f"[RAG] MMR reranking failed: {e}, returning hybrid results")
                return results[:top_k]

        return results[:top_k]

    def augment_context(
        self,
        query: str,
        retrieval_results: List[Dict],
        max_context_length: int = 2000
    ) -> str:
        """
        Generate augmented context from retrieval results for LLM

        Args:
            query: Original query
            retrieval_results: Results from retrieve()
            max_context_length: Maximum context length in characters

        Returns:
            Formatted context string for LLM augmentation
        """
        context = f"SEARCH RESULTS FOR: {query}\n"
        context += f"Retrieved {len(retrieval_results)} relevant papers:\n\n"

        current_length = len(context)

        for i, result in enumerate(retrieval_results, 1):
            metadata = result.get('metadata', {})
            title = metadata.get('title', 'Unknown')
            platform = metadata.get('platform', '')
            insight = metadata.get('memory_insight', '')
            score = result.get('score', 0)
            diversity = result.get('diversity_score', 0)

            # Format result entry
            entry = f"{i}. [{score:.2%} relevant, {diversity:.0%} unique] {title}\n"
            if platform:
                entry += f"   Platform: {platform}\n"
            if insight:
                entry += f"   Key Finding: {insight}\n"

            # Check if adding this entry exceeds length limit
            if current_length + len(entry) > max_context_length:
                context += f"\n... ({len(retrieval_results) - i + 1} more results available)\n"
                break

            context += entry
            current_length += len(entry)

        context += "\n--- END OF SEARCH RESULTS ---\n"
        return context

    def augment_prompt(
        self,
        query: str,
        retrieval_results: List[Dict],
        system_prompt: str = None
    ) -> str:
        """
        Create augmented prompt for LLM with retrieved context

        Args:
            query: User query
            retrieval_results: Retrieved documents
            system_prompt: Optional system prompt prefix

        Returns:
            Augmented prompt ready for LLM
        """
        if system_prompt is None:
            system_prompt = (
                "You are an expert AI research analyst specializing in on-device AI "
                "and mobile optimization. Answer questions based on the provided research context. "
                "Always cite the source papers when relevant.\n\n"
            )

        context = self.augment_context(query, retrieval_results)

        augmented_prompt = (
            f"{system_prompt}"
            f"{context}\n"
            f"USER QUESTION: {query}\n\n"
            f"Please provide a comprehensive answer based on the above research papers. "
            f"Include specific citations and findings.\n"
        )

        return augmented_prompt

    def _apply_filters(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """
        Apply metadata filters to results

        Supported filters:
        - platform: str or list (e.g., 'Mobile', 'Laptop')
        - min_score: float (minimum relevance score 0-100)
        - max_score: float (maximum relevance score 0-100)
        - date_after: str ISO date
        - date_before: str ISO date
        """
        filtered = results

        # Platform filter
        if 'platform' in filters:
            platforms = filters['platform']
            if isinstance(platforms, str):
                platforms = [platforms]
            filtered = [
                r for r in filtered
                if r.get('metadata', {}).get('platform', '').lower() in [p.lower() for p in platforms]
            ]

        # Score range filter
        if 'min_score' in filters:
            filtered = [
                r for r in filtered
                if r.get('metadata', {}).get('relevance_score', 0) >= filters['min_score']
            ]

        if 'max_score' in filters:
            filtered = [
                r for r in filtered
                if r.get('metadata', {}).get('relevance_score', 100) <= filters['max_score']
            ]

        # Date filters
        if 'date_after' in filters or 'date_before' in filters:
            for r in filtered[:]:
                try:
                    doc_date = datetime.fromisoformat(r.get('metadata', {}).get('date', ''))
                    if 'date_after' in filters:
                        after_date = datetime.fromisoformat(filters['date_after'])
                        if doc_date < after_date:
                            filtered.remove(r)
                    if 'date_before' in filters:
                        before_date = datetime.fromisoformat(filters['date_before'])
                        if doc_date > before_date:
                            filtered.remove(r)
                except (ValueError, KeyError):
                    pass

        return filtered

    def get_stats(self) -> Dict:
        """Get RAG orchestrator statistics"""
        return {
            'config': self.config,
            'hybrid_search_active': self.hybrid_search is not None,
            'mmr_active': self.mmr is not None,
            'knowledge_graph_active': self.knowledge_graph is not None,
            'timestamp': datetime.now().isoformat()
        }


class RAGConfig:
    """Configuration builder for RAG system"""

    def __init__(self):
        self.settings = {}

    def set_hybrid_search(self, alpha: float, enabled: bool = True) -> 'RAGConfig':
        """Set hybrid search parameters"""
        self.settings['use_hybrid_search'] = enabled
        self.settings['alpha'] = alpha
        return self

    def set_mmr(self, lambda_param: float, enabled: bool = True) -> 'RAGConfig':
        """Set MMR parameters"""
        self.settings['use_mmr'] = enabled
        self.settings['lambda'] = lambda_param
        return self

    def set_retrieval(self, top_k: int = 10) -> 'RAGConfig':
        """Set retrieval parameters"""
        self.settings['top_k'] = top_k
        return self

    def build(self) -> Dict:
        """Build configuration dict"""
        return self.settings
