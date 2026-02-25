"""
RAG-Integrated Chat Service
Provides paper-aware chat with context retrieval and citations
"""

import logging
import sys
import os
from typing import List, Dict, Optional, AsyncGenerator
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Add project root to path for imports
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class ChatService:
    """
    Chat service with RAG integration
    Retrieves relevant papers and augments LLM responses with context
    """

    def __init__(self):
        """Initialize chat service with RAG components"""
        self.rag_orchestrator = None
        self.llm_client = None
        self.knowledge_manager = None

        try:
            # Initialize RAG components
            self._init_rag()
            logger.info("[ChatService] Initialized with RAG support")
        except Exception as e:
            logger.warning(f"[ChatService] RAG initialization failed: {e}, falling back to basic chat")

    def _init_rag(self):
        """Initialize RAG orchestrator and knowledge manager"""
        try:
            from src.rag_orchestrator import RAGOrchestrator
            from src.knowledge_graph import EnterpriseKnowledgeManager
            from src.hybrid_search import HybridSearchEngine, BM25Ranker, SearchConfig
            from src.mmr_ranker import MMRRanker
            from src.qdrant_vector_store import VectorStore

            # Initialize knowledge manager
            self.knowledge_manager = EnterpriseKnowledgeManager(data_dir="data")

            # Initialize vector store for hybrid search
            try:
                vector_store = VectorStore()
                logger.info("[ChatService] Vector store initialized")
            except Exception as e:
                logger.warning(f"[ChatService] Vector store init failed: {e}")
                vector_store = None

            # Build BM25 index from history
            corpus = self._build_corpus()
            bm25 = BM25Ranker(corpus) if corpus else None

            # Initialize hybrid search
            hybrid_engine = None
            if vector_store and bm25:
                hybrid_engine = HybridSearchEngine(
                    vector_store=vector_store,
                    bm25_ranker=bm25,
                    alpha=0.6
                )

            # Initialize MMR ranker
            mmr = MMRRanker(lambda_param=0.5)

            # Create RAG orchestrator
            self.rag_orchestrator = RAGOrchestrator(
                hybrid_search_engine=hybrid_engine,
                mmr_ranker=mmr,
                knowledge_manager=self.knowledge_manager,
                config={
                    'use_hybrid_search': hybrid_engine is not None,
                    'use_mmr': True,
                    'alpha': 0.6,
                    'lambda': 0.5,
                    'top_k': 5
                }
            )

            # Initialize LLM client
            self._init_llm()

        except Exception as e:
            logger.error(f"[ChatService] RAG initialization failed: {e}")
            raise

    def _init_llm(self):
        """Initialize LLM client (Groq/Ollama/Gemini)"""
        try:
            from src.multimodal_orchestrator import MultiModelOrchestrator

            self.llm_client = MultiModelOrchestrator()
            logger.info("[ChatService] LLM client initialized")
        except Exception as e:
            logger.warning(f"[ChatService] LLM client init failed: {e}")
            self.llm_client = None

    def _build_corpus(self) -> List[str]:
        """Build corpus from history.json for BM25 indexing"""
        try:
            history_path = os.path.join(_PROJECT_ROOT, "data", "history.json")
            if os.path.exists(history_path):
                with open(history_path, 'r', encoding='utf-8') as f:
                    papers = json.load(f)

                corpus = []
                for paper in papers:
                    # Combine title and summary for indexing
                    text = f"{paper.get('title', '')} {paper.get('summary', '')}"
                    if text.strip():
                        corpus.append(text)

                logger.info(f"[ChatService] Built corpus from {len(papers)} papers")
                return corpus
        except Exception as e:
            logger.warning(f"[ChatService] Failed to build corpus: {e}")
            return []

    async def stream(
        self,
        query: str,
        paper_id: Optional[str] = None,
        context: Optional[List[Dict]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Chat stream endpoint with RAG augmentation

        Args:
            query: User query
            paper_id: Optional specific paper to focus on
            context: Optional additional context

        Yields:
            Streamed response tokens
        """
        try:
            # Step 1: Retrieve relevant context using RAG
            retrieval_results = []
            augmented_prompt = query

            if self.rag_orchestrator and self.knowledge_manager:
                try:
                    # Generate query embedding
                    query_embedding = None
                    if self.knowledge_manager.embedder:
                        query_embedding = self.knowledge_manager.embedder.encode(query)

                    # Retrieve with hybrid search + MMR
                    retrieval_results = self.rag_orchestrator.retrieve(
                        query=query,
                        embedding=query_embedding,
                        top_k=5,
                        filters={'platform': ['Mobile', 'Laptop']} if not paper_id else None
                    )

                    # Augment prompt with context
                    augmented_prompt = self.rag_orchestrator.augment_prompt(
                        query=query,
                        retrieval_results=retrieval_results,
                        system_prompt=(
                            "You are an expert AI research analyst specializing in on-device AI. "
                            "Answer questions based on the provided research papers. "
                            "Always cite sources and be specific about findings.\n\n"
                        )
                    )

                    logger.info(f"[ChatService] Retrieved {len(retrieval_results)} papers for query")

                except Exception as e:
                    logger.warning(f"[ChatService] RAG retrieval failed: {e}")
                    augmented_prompt = query

            # Step 2: Generate response using LLM
            if self.llm_client:
                try:
                    async for token in self.llm_client.stream_response(augmented_prompt):
                        yield token
                except Exception as e:
                    logger.error(f"[ChatService] LLM streaming failed: {e}")
                    yield f"Error: {str(e)}"
            else:
                # Fallback: return basic response
                yield "Chat service not configured. Please check configuration."

        except Exception as e:
            logger.error(f"[ChatService] Stream failed: {e}")
            yield f"Error: {str(e)}"

    def get_retrieval_context(
        self,
        query: str
    ) -> Dict:
        """
        Get retrieval context without streaming LLM response
        Useful for debugging and analytics

        Args:
            query: Query text

        Returns:
            Dict with retrieval results and stats
        """
        try:
            if not self.rag_orchestrator:
                return {'error': 'RAG not initialized', 'results': []}

            query_embedding = None
            if self.knowledge_manager and self.knowledge_manager.embedder:
                query_embedding = self.knowledge_manager.embedder.encode(query)

            results = self.rag_orchestrator.retrieve(
                query=query,
                embedding=query_embedding,
                top_k=5
            )

            return {
                'query': query,
                'results': results,
                'count': len(results),
                'rag_stats': self.rag_orchestrator.get_stats()
            }

        except Exception as e:
            logger.error(f"[ChatService] Get context failed: {e}")
            return {'error': str(e), 'results': []}

    def health_check(self) -> Dict:
        """Check service health"""
        return {
            'service': 'ChatService',
            'rag_enabled': self.rag_orchestrator is not None,
            'llm_enabled': self.llm_client is not None,
            'knowledge_manager': self.knowledge_manager is not None
        }


# For testing/debugging
async def test_chat_service():
    """Test chat service with sample query"""
    service = ChatService()

    query = "What are the latest techniques for quantization on mobile devices?"
    print(f"Query: {query}")
    print("\nResponse:")

    async for token in service.stream(query):
        print(token, end='', flush=True)

    print("\n\nContext used:")
    context = service.get_retrieval_context(query)
    print(json.dumps(context, indent=2))

    print("\n\nHealth check:")
    health = service.health_check()
    print(json.dumps(health, indent=2))


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_chat_service())
