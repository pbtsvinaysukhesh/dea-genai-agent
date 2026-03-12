"""
Enhanced RAG Orchestrator with Query Expansion and Advanced Reranking
Alternative mechanism to standard RAG for improved paper discovery
Combines: Query Expansion + Semantic Search + Reranking + Knowledge Graph traversal
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
import numpy as np
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class QueryExpander:
    """Expands queries to find more relevant papers"""

    def __init__(self, llm_orchestrator=None):
        """
        Initialize query expander

        Args:
            llm_orchestrator: MultiModelOrchestrator instance for query generation
        """
        self.llm = llm_orchestrator

    def expand_query(self, query: str, expansion_count: int = 3) -> List[str]:
        """
        Expand single query into multiple search queries

        Args:
            query: Original query
            expansion_count: Number of expanded queries to generate

        Returns:
            List of expanded queries
        """
        if not self.llm:
            return [query]  # Fallback: just original query

        expanded = [query]  # Include original

        try:
            # Generate semantically similar queries
            prompt = f"""Given the research query: "{query}"

Generate {expansion_count} alternative ways to search for the same concept.
Focus on synonyms, related terms, and different perspectives.
Return only the queries, one per line, no numbering."""

            response = self.llm.generate(prompt)

            if response:
                new_queries = [
                    q.strip()
                    for q in response.split('\n')
                    if q.strip() and len(q.strip()) > 5
                ]
                expanded.extend(new_queries[:expansion_count])
                logger.debug(f"[QueryExpander] Generated {len(new_queries)} expansions for: '{query}'")

            return expanded

        except Exception as e:
            logger.warning(f"[QueryExpander] Expansion failed: {e}, using original query")
            return [query]


class AdvancedReranker:
    """Reranks results using multiple signals"""

    def __init__(self, knowledge_graph=None):
        """
        Initialize reranker

        Args:
            knowledge_graph: EnterpriseKnowledgeManager instance
        """
        self.kg = knowledge_graph

    def rerank(
        self,
        results: List[Dict],
        query_embedding: Optional[np.ndarray] = None,
        top_k: int = 10,
        weights: Dict = None
    ) -> List[Dict]:
        """
        Rerank results using multiple signals

        Signals used:
        - Relevance score (from analysis)
        - Semantic similarity (embedding)
        - Citation count (knowledge graph)
        - Recency (publication date)
        - Diversity (topic coverage)

        Args:
            results: Search results to rerank
            query_embedding: Query embedding for similarity
            top_k: Top results to return
            weights: Weights for each signal (default: equal weight)

        Returns:
            Reranked results with composite scores
        """
        if not results:
            return []

        # Default weights (each signal 20%)
        signal_weights = weights or {
            'relevance': 0.25,
            'similarity': 0.25,
            'citations': 0.15,
            'recency': 0.15,
            'diversity': 0.20
        }

        # Normalize weights
        total = sum(signal_weights.values())
        signal_weights = {k: v / total for k, v in signal_weights.items()}

        # Calculate scores
        for result in results:
            scores = {}

            # 1. Relevance signal (0-100 normalized to 0-1)
            relevance = result.get('metadata', {}).get('relevance_score', 50) / 100
            scores['relevance'] = relevance

            # 2. Semantic similarity (if available)
            if 'embedding' in result and query_embedding is not None:
                similarity = np.dot(result['embedding'], query_embedding) / (
                    np.linalg.norm(result['embedding']) * np.linalg.norm(query_embedding) + 1e-10
                )
                scores['similarity'] = max(0, min(1, similarity))
            else:
                scores['similarity'] = result.get('score', 0.5)

            # 3. Citation count (if available in KG)
            citations = result.get('metadata', {}).get('citation_count', 0)
            # Normalize: assume max 1000 citations
            scores['citations'] = min(1, citations / 1000)

            # 4. Recency (recent papers score higher)
            try:
                created_at = result.get('metadata', {}).get('created_at', '')
                if created_at:
                    paper_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    days_old = (datetime.now(paper_date.tzinfo) - paper_date).days
                    # Papers from last 2 years get higher score
                    recency = max(0, 1 - (days_old / 730))
                    scores['recency'] = recency
                else:
                    scores['recency'] = 0.5
            except:
                scores['recency'] = 0.5

            # 5. Diversity (placeholder - can be calculated against already-selected papers)
            scores['diversity'] = 0.5  # Default neutral

            # Composite score
            composite = sum(
                scores.get(signal, 0) * weight
                for signal, weight in signal_weights.items()
            )

            result['rerank_score'] = composite
            result['signal_scores'] = scores

        # Sort by composite score
        reranked = sorted(
            results,
            key=lambda x: x.get('rerank_score', 0),
            reverse=True
        )

        logger.debug(f"[AdvancedReranker] Reranked {len(results)} results")
        return reranked[:top_k]


class KnowledgeGraphTraversal:
    """Traverses knowledge graph to find related papers"""

    def __init__(self, knowledge_graph=None):
        """
        Initialize graph traversal

        Args:
            knowledge_graph: EnterpriseKnowledgeManager instance
        """
        self.kg = knowledge_graph

    def find_related_papers(
        self,
        paper_id: str,
        max_depth: int = 2,
        relation_types: List[str] = None
    ) -> List[Dict]:
        """
        Find papers related to a given paper via knowledge graph

        Relation types:
        - 'cites' - papers that cite this paper
        - 'cited_by' - papers cited by this paper
        - 'same_topic' - papers with same topic/platform
        - 'similar_method' - papers with similar methodology

        Args:
            paper_id: Starting paper ID
            max_depth: Maximum graph traversal depth
            relation_types: Types of relations to follow

        Returns:
            List of related papers with relevance scores
        """
        if not self.kg:
            return []

        related = []
        visited = {paper_id}
        queue = [(paper_id, 0)]  # (paper_id, depth)

        if relation_types is None:
            relation_types = ['cites', 'cited_by', 'same_topic', 'similar_method']

        try:
            while queue:
                current_id, depth = queue.pop(0)

                if depth >= max_depth:
                    continue

                # Get related papers from KG
                neighbors = self.kg.get_related_nodes(
                    current_id,
                    relation_types=relation_types
                ) if hasattr(self.kg, 'get_related_nodes') else []

                for neighbor in neighbors:
                    neighbor_id = neighbor.get('node_id', neighbor.get('id'))

                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, depth + 1))

                        # Score by depth and relation type
                        relation = neighbor.get('relation_type', 'unknown')
                        score = 1 - (depth / max_depth) * 0.5  # Closer relations score higher

                        related.append({
                            'paper_id': neighbor_id,
                            'title': neighbor.get('title', ''),
                            'relation_type': relation,
                            'graph_score': score,
                            'depth': depth,
                            'metadata': neighbor.get('metadata', {})
                        })

            logger.debug(f"[KnowledgeGraphTraversal] Found {len(related)} related papers")
            return related

        except Exception as e:
            logger.warning(f"[KnowledgeGraphTraversal] Traversal failed: {e}")
            return []


class EnhancedRAGOrchestrator:
    """
    Enhanced RAG orchestrator with query expansion and advanced reranking

    Pipeline:
    1. Query Expansion - Generate alternative search queries
    2. Multi-Query Search - Search with all expanded queries
    3. Result Fusion - Combine results from multiple queries
    4. Advanced Reranking - Rerank using multiple signals
    5. Knowledge Graph Enhancement - Add related papers from graph
    6. Final Deduplication - Remove duplicates
    """

    def __init__(
        self,
        hybrid_search_engine=None,
        llm_orchestrator=None,
        knowledge_manager=None,
        config: Dict = None
    ):
        """
        Initialize enhanced RAG orchestrator

        Args:
            hybrid_search_engine: HybridSearchEngine for semantic+keyword search
            llm_orchestrator: MultiModelOrchestrator for query expansion
            knowledge_manager: EnterpriseKnowledgeManager for graph operations
            config: Configuration dict
        """
        self.hybrid_search = hybrid_search_engine
        self.llm = llm_orchestrator
        self.kg = knowledge_manager

        self.query_expander = QueryExpander(llm_orchestrator)
        self.reranker = AdvancedReranker(knowledge_manager)
        self.graph_traversal = KnowledgeGraphTraversal(knowledge_manager)

        self.config = {
            'use_query_expansion': True,
            'expansion_count': 3,
            'use_multi_query_fusion': True,
            'use_graph_enhancement': True,
            'use_advanced_reranking': True,
            'top_k': 10,
            'max_graph_depth': 2,
            **(config or {})
        }

        logger.info(f"[EnhancedRAG] Initialized with config: {self.config}")

    def retrieve(
        self,
        query: str,
        embedding: Optional[np.ndarray] = None,
        top_k: Optional[int] = None,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Enhanced retrieval with query expansion and reranking

        Args:
            query: Original query
            embedding: Query embedding
            top_k: Number of results
            filters: Metadata filters

        Returns:
            List of ranked documents with metadata
        """
        if top_k is None:
            top_k = self.config['top_k']

        logger.info(f"[EnhancedRAG] Starting enhanced retrieval for: '{query}'")

        all_results = {}  # Deduplicate by ID

        # STEP 1: Query Expansion
        queries_to_search = [query]
        if self.config['use_query_expansion']:
            expanded = self.query_expander.expand_query(
                query,
                self.config['expansion_count']
            )
            queries_to_search = expanded
            logger.info(f"[EnhancedRAG] Expanded to {len(queries_to_search)} queries")

        # STEP 2: Multi-Query Search
        for search_query in queries_to_search:
            if not self.hybrid_search:
                logger.warning("[EnhancedRAG] No hybrid search engine available")
                continue

            try:
                results = self.hybrid_search.search(
                    query=search_query,
                    embedding=embedding,
                    top_k=top_k * 3,  # Get more for reranking
                    semantic_only=False,
                    keyword_only=False
                )

                for result in results:
                    doc_id = result.get('doc_id', result.get('id'))
                    if doc_id not in all_results:
                        all_results[doc_id] = result
                    else:
                        # Merge scores (take max)
                        all_results[doc_id]['score'] = max(
                            all_results[doc_id]['score'],
                            result.get('score', 0)
                        )

                logger.debug(f"[EnhancedRAG] Search '{search_query}' yielded {len(results)} results")
            except Exception as e:
                logger.warning(f"[EnhancedRAG] Search failed for '{search_query}': {e}")

        # Convert back to list
        results = list(all_results.values())
        logger.info(f"[EnhancedRAG] Total unique results after multi-query: {len(results)}")

        # STEP 3: Apply Filters
        if filters:
            results = self._apply_filters(results, filters)
            logger.debug(f"[EnhancedRAG] After filtering: {len(results)} results")

        # STEP 4: Advanced Reranking
        if self.config['use_advanced_reranking']:
            results = self.reranker.rerank(
                results,
                query_embedding=embedding,
                top_k=len(results)
            )
            logger.debug(f"[EnhancedRAG] Advanced reranking applied")

        # STEP 5: Knowledge Graph Enhancement
        enhanced_results = results.copy()
        if self.config['use_graph_enhancement'] and self.kg:
            try:
                # For top papers, find related ones
                for top_result in results[:3]:
                    doc_id = top_result.get('doc_id', top_result.get('id'))
                    related = self.graph_traversal.find_related_papers(
                        doc_id,
                        max_depth=self.config['max_graph_depth']
                    )

                    # Add related papers with boost for relevance
                    for rel_paper in related[:2]:  # Add top 2 related per paper
                        rel_id = rel_paper.get('paper_id')
                        if rel_id not in all_results:
                            enhanced_results.append({
                                'doc_id': rel_id,
                                'score': rel_paper.get('graph_score', 0.6),
                                'metadata': rel_paper.get('metadata', {}),
                                'source': 'knowledge_graph',
                                'relation': rel_paper.get('relation_type')
                            })

                logger.info(f"[EnhancedRAG] Graph enhancement added {len(enhanced_results) - len(results)} papers")
            except Exception as e:
                logger.warning(f"[EnhancedRAG] Graph enhancement failed: {e}")

        # STEP 6: Final deduplication and top-k selection
        final_dedup = {}
        for result in enhanced_results:
            doc_id = result.get('doc_id', result.get('id'))
            if doc_id not in final_dedup:
                final_dedup[doc_id] = result

        final_results = sorted(
            final_dedup.values(),
            key=lambda x: x.get('rerank_score', x.get('score', 0)),
            reverse=True
        )[:top_k]

        logger.info(f"[EnhancedRAG] Final results: {len(final_results)} papers")
        return final_results

    def _apply_filters(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """Apply metadata filters to results"""
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

        # Date filters
        if 'date_after' in filters or 'date_before' in filters:
            for r in filtered[:]:
                try:
                    doc_date = datetime.fromisoformat(
                        r.get('metadata', {}).get('created_at', '')
                    )
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
        """Get extended RAG statistics"""
        return {
            'config': self.config,
            'components': {
                'query_expansion': self.query_expander is not None,
                'advanced_reranking': self.reranker is not None,
                'graph_traversal': self.graph_traversal is not None,
                'hybrid_search': self.hybrid_search is not None,
                'llm_available': self.llm is not None,
                'kg_available': self.kg is not None
            },
            'timestamp': datetime.now().isoformat()
        }
