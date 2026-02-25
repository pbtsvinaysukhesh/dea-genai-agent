"""
Qdrant Vector Store - Semantic Search & Deduplication
Stores embeddings for intelligent paper management
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# Qdrant
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
import torch
# Embeddings
try:
    from transformers import AutoTokenizer, AutoModel
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class VectorStore:
    """Qdrant vector store for semantic paper management"""
    
    def __init__(self, collection_name: str = "research_papers"):
        if not QDRANT_AVAILABLE or not EMBEDDINGS_AVAILABLE:
            raise ImportError("Install: pip install qdrant-client sentence-transformers")
        
        self.collection_name = collection_name
        
        # In-memory Qdrant for simplicity
        self.client = QdrantClient(":memory:")
        logger.info("[Qdrant] In-memory mode")
        
        # Embedding model (fast & good)
        logger.info("[Embeddings] Loading gemma-300m(offline)...")

        model_path = os.path.join("../models", "embedding-gemma-300m")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            local_files_only=True
        )

        self.model = AutoModel.from_pretrained(
            model_path,
            local_files_only=True
        )
        self.model.eval()

        self.embedding_dim = 768
        
        # Create collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE)
        )
        
        self.stats = {'added': 0, 'duplicates': 0, 'searches': 0}

    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output.last_hidden_state
        mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return (token_embeddings * mask).sum(1) / mask.sum(1)

    
    def generate_embedding(self, text: str) -> List[float]:
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )

        with torch.no_grad():
            output = self.model(**inputs)

        embedding = self._mean_pooling(output, inputs["attention_mask"])
        return embedding[0].cpu().tolist()

    
    def add_paper(self, paper: Dict) -> bool:
        """Add paper, returns False if duplicate"""
        # Create text
        text = f"{paper.get('title', '')} {paper.get('summary', '')[:500]}"
        embedding = self.generate_embedding(text)
        
        # Check duplicate (95% similarity)
        is_dup, sim, _ = self.is_duplicate(embedding)
        if is_dup:
            self.stats['duplicates'] += 1
            logger.info(f"[Qdrant] DUPLICATE ({sim:.0%})")
            return False
        
        # Add
        point_id = self._hash_id(paper)
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                'title': paper.get('title', '')[:200],
                'score': paper.get('relevance_score', 0),
                'platform': paper.get('platform', 'Unknown'),
                'added_at': datetime.now().isoformat()
            }
        )
        
        self.client.upsert(collection_name=self.collection_name, points=[point])
        self.stats['added'] += 1
        return True
    
    def is_duplicate(self, embedding: List[float], threshold=0.95) -> Tuple[bool, float, Optional[Dict]]:
        """Check if duplicate"""
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=1
            )
            
            if results and len(results) > 0 and results[0].score >= threshold:
                return True, results[0].score, results[0].payload
            return False, 0.0, None
        except Exception as e:
            logger.error(f"[Qdrant] Duplicate check error: {e}")
            return False, 0.0, None
    
    def find_similar(self, paper: Dict, top_k=3) -> List[Dict]:
        """Find similar papers"""
        text = f"{paper.get('title', '')} {paper.get('summary', '')}"
        embedding = self.generate_embedding(text)
        
        results = self.client.search_points(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=top_k,
            score_threshold=0.7
        )
        
        self.stats['searches'] += 1
        return [{'similarity': r.score, **r.payload} for r in results]
    
    def _hash_id(self, paper: Dict) -> int:
        """Generate unique ID"""
        text = f"{paper.get('title', '')}_{paper.get('url', '')}"
        return int(hashlib.md5(text.encode()).hexdigest()[:16], 16)
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        info = self.client.get_collection(self.collection_name)
        return {**self.stats, 'total_papers': info.points_count}


class VectorStoreManager:
    """High-level manager"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled and QDRANT_AVAILABLE and EMBEDDINGS_AVAILABLE
        
        if self.enabled:
            try:
                self.store = VectorStore()
                logger.info("[VectorManager] Enabled")
            
            except:
                self.enabled = False
                self.store = None
        else:
            self.store = None
    
    def check_and_add(self, paper: Dict) -> Tuple[bool, str]:
        """Check duplicate and add"""
        if not self.enabled:
            return True, "disabled"
        
        if self.store.add_paper(paper):
            return True, "new"
        return False, "duplicate"
    
    def get_context(self, paper: Dict) -> str:
        """Get similar papers context"""
        if not self.enabled:
            return ""
        
        similar = self.store.find_similar(paper, top_k=3)
        if not similar:
            return ""
        
        context = "SIMILAR PAPERS:\n"
        for s in similar:
            context += f"- {s.get('title', 'Unknown')[:60]} ({s['similarity']:.0%})\n"
        return context
    
    def get_stats(self) -> Dict:
        """Get stats"""
        if not self.enabled:
            return {'enabled': False}
        return {'enabled': True, **self.store.get_stats()}