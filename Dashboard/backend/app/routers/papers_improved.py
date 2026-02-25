"""
Papers Router with RAG Integration
Provides semantic search, filtering, and CRUD operations
"""

import logging
import sys
import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
import numpy as np

logger = logging.getLogger(__name__)

# Add project root to path
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from Dashboard.backend.app.services.data import DataService

router = APIRouter()


class PaperUpdate(BaseModel):
    """Paper update request"""
    title: Optional[str] = None
    memory_insight: Optional[str] = None
    engineering_takeaway: Optional[str] = None
    platform: Optional[str] = None
    relevance_score: Optional[int] = None


class SemanticSearchRequest(BaseModel):
    """Semantic search request"""
    query: str
    top_k: Optional[int] = 5
    platform: Optional[str] = None
    min_score: Optional[int] = 0


class RAGSearchRequest(BaseModel):
    """RAG search request with hybrid search"""
    query: str
    top_k: Optional[int] = 5
    use_mmr: Optional[bool] = True
    hybrid: Optional[bool] = True


# Initialize services
data_service = DataService()
rag_orchestrator = None
knowledge_manager = None


def _init_rag():
    """Initialize RAG components"""
    global rag_orchestrator, knowledge_manager

    try:
        from src.rag_orchestrator import RAGOrchestrator
        from src.knowledge_graph import EnterpriseKnowledgeManager

        knowledge_manager = EnterpriseKnowledgeManager(data_dir="data")
        rag_orchestrator = RAGOrchestrator(
            knowledge_manager=knowledge_manager,
            config={'top_k': 10, 'use_mmr': True}
        )
        logger.info("[PapersRouter] RAG initialized")
        return True
    except Exception as e:
        logger.warning(f"[PapersRouter] RAG initialization failed: {e}")
        return False


# Initialize on import
_init_rag()


@router.get("/papers")
async def list_papers(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    platform: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    search: Optional[str] = None
):
    """
    List papers with optional filtering

    Query params:
    - limit: Number of results (1-1000)
    - offset: Pagination offset
    - platform: Filter by platform (Mobile/Laptop)
    - min_score: Minimum relevance score
    - search: Text search in title/insight/takeaway
    """
    try:
        papers = data_service.get_papers(
            limit=limit,
            offset=offset,
            platform=platform,
            min_score=min_score,
            search=search
        )
        return {"papers": papers, "count": len(papers)}
    except Exception as e:
        logger.error(f"[Papers] List failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/papers/{paper_id}")
async def get_paper(paper_id: str):
    """Get specific paper by ID"""
    try:
        paper = data_service.get_paper_by_id(paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")
        return paper
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Papers] Get failed: {e}")
        raise HTTPException(500, str(e))


@router.put("/papers/{paper_id}")
async def update_paper(paper_id: str, update: PaperUpdate):
    """Update paper metadata"""
    try:
        updates = update.dict(exclude_unset=True)
        if not updates:
            raise HTTPException(400, "No updates provided")

        paper = data_service.update_paper(paper_id, updates)
        if not paper:
            raise HTTPException(404, "Paper not found")

        logger.info(f"[Papers] Updated paper {paper_id}")
        return paper

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Papers] Update failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """Delete paper"""
    try:
        success = data_service.delete_paper(paper_id)
        if not success:
            raise HTTPException(404, "Paper not found")

        logger.info(f"[Papers] Deleted paper {paper_id}")
        return {"status": "deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Papers] Delete failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/papers/semantic-search")
async def semantic_search(request: SemanticSearchRequest):
    """
    Semantic search using embeddings
    Finds papers semantically similar to query (not just keyword matching)
    """
    try:
        if not rag_orchestrator or not knowledge_manager:
            raise HTTPException(503, "RAG system not initialized")

        # Generate query embedding
        query_embedding = None
        if knowledge_manager.embedder:
            query_embedding = knowledge_manager.embedder.encode(request.query)

        # Search
        results = rag_orchestrator.retrieve(
            query=request.query,
            embedding=query_embedding,
            top_k=request.top_k,
            filters={'platform': request.platform} if request.platform else None,
            use_mmr=True
        )

        logger.info(f"[Papers] Semantic search for '{request.query[:30]}' returned {len(results)} results")
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Papers] Semantic search failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/papers/rag-search")
async def rag_search(request: RAGSearchRequest):
    """
    Advanced RAG search combining keyword + semantic search with diversity
    """
    try:
        if not rag_orchestrator or not knowledge_manager:
            raise HTTPException(503, "RAG system not initialized")

        # Generate query embedding
        query_embedding = None
        if knowledge_manager.embedder:
            try:
                query_embedding = knowledge_manager.embedder.encode(request.query)
            except Exception as e:
                logger.warning(f"[Papers] Embedding generation failed: {e}")

        # Retrieve with RAG
        results = rag_orchestrator.retrieve(
            query=request.query,
            embedding=query_embedding,
            top_k=request.top_k,
            use_mmr=request.use_mmr
        )

        # Generate augmented context
        context = rag_orchestrator.augment_context(request.query, results)

        logger.info(f"[Papers] RAG search returned {len(results)} papers with context")
        return {
            "query": request.query,
            "results": results,
            "context": context,
            "count": len(results)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Papers] RAG search failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/papers/{paper_id}/similar")
async def get_similar_papers(
    paper_id: str,
    top_k: int = Query(5, ge=1, le=20)
):
    """
    Find papers similar to given paper
    """
    try:
        if not knowledge_manager or not knowledge_manager.embedder:
            raise HTTPException(503, "Embedding service not available")

        # Get the paper
        paper = data_service.get_paper_by_id(paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")

        # Generate embedding for the paper
        title = paper.get('title', '')
        summary = paper.get('summary', '')[:500]
        text = f"{title} {summary}"

        embedding = knowledge_manager.embedder.encode(text)

        # Find similar papers
        similar = knowledge_manager.search_semantic(embedding, top_k=top_k)

        # Filter out the paper itself
        similar = [p for p in similar if p.get('node_id') != paper_id]

        logger.info(f"[Papers] Found {len(similar)} papers similar to {paper_id}")
        return {
            "paper_id": paper_id,
            "paper_title": title,
            "similar_papers": similar,
            "count": len(similar)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Papers] Similar search failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/papers/health")
async def health_check():
    """Health check for papers API"""
    return {
        "service": "PapersAPI",
        "rag_available": rag_orchestrator is not None,
        "data_service": "ok" if data_service else "failed",
        "embeddings": knowledge_manager and knowledge_manager.embedder is not None
    }
