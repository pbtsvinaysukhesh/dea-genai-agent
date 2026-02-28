"""
Configuration to switch between Standard RAG and Enhanced RAG mechanisms
"""

# Standard RAG: Hybrid Search + MMR Ranking (current)
# - Fast semantic + keyword search
# - Maximum Marginal Relevance reranking for diversity
# - Best for: Quick relevant results
# Config: use_standard_rag = True

# Enhanced RAG: Query Expansion + Advanced Reranking + Graph Enhancement (new)
# - Query expansion to find more papers
# - Multi-query fusion combining results
# - 5-signal reranking (relevance, similarity, citations, recency, diversity)
# - Knowledge graph traversal for related papers
# - Best for: Comprehensive paper discovery
# Config: use_standard_rag = False

RAG_CONFIG = {
    # Choose which RAG implementation to use
    "use_standard_rag": False,  # Set to True to use original RAG, False to use Enhanced RAG

    # Standard RAG Settings (if use_standard_rag=True)
    "standard_rag": {
        "use_hybrid_search": True,  # BM25 + Semantic
        "use_mmr": True,            # Diversity reranking
        "alpha": 0.6,               # 60% semantic, 40% keyword
        "lambda": 0.5,              # 50% relevance, 50% diversity
        "top_k": 10,
        "diversity_weight": 0.4
    },

    # Enhanced RAG Settings (if use_standard_rag=False)
    "enhanced_rag": {
        "use_query_expansion": True,        # Generate alternative searches
        "expansion_count": 3,               # Number of expanded queries
        "use_multi_query_fusion": True,    # Combine results from all queries
        "use_advanced_reranking": True,    # Multi-signal reranking
        "use_graph_enhancement": True,     # Add related papers from knowledge graph
        "top_k": 10,
        "max_graph_depth": 2,              # How deep to traverse knowledge graph

        # Reranking signal weights (sum should equal 1.0)
        "rerank_weights": {
            "relevance": 0.25,      # Paper analysis score
            "similarity": 0.25,     # Semantic similarity to query
            "citations": 0.15,      # Citation count
            "recency": 0.15,        # Date (recent = higher)
            "diversity": 0.20       # Topic/method diversity
        }
    }
}

def get_rag_implementation(rag_orchestrator_module, llm_orchestrator, knowledge_manager, hybrid_search):
    """
    Factory function to get configured RAG implementation

    Usage:
        from src.rag_config import get_rag_implementation
        rag = get_rag_implementation(src, llm, km, hs)
    """
    use_standard = RAG_CONFIG.get("use_standard_rag", True)

    if use_standard:
        # Use standard RAG
        from src.rag_orchestrator import RAGOrchestrator
        return RAGOrchestrator(
            hybrid_search_engine=hybrid_search,
            mmr_ranker=None,  # Will be created internally
            knowledge_manager=knowledge_manager,
            config=RAG_CONFIG["standard_rag"]
        )
    else:
        # Use enhanced RAG
        from src.rag_orchestrator_enhanced import EnhancedRAGOrchestrator
        return EnhancedRAGOrchestrator(
            hybrid_search_engine=hybrid_search,
            llm_orchestrator=llm_orchestrator,
            knowledge_manager=knowledge_manager,
            config=RAG_CONFIG["enhanced_rag"]
        )

if __name__ == "__main__":
    import json
    print("RAG Configuration:")
    print(json.dumps(RAG_CONFIG, indent=2))
    print("\nTo switch RAG implementations, modify: use_standard_rag setting")
