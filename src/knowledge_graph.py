"""
Enterprise-Grade Knowledge Graph & Vector Store for On-Device AI Intelligence
Uses Graph RAG, embeddings, and structured knowledge extraction for scalable research intelligence
"""

import json
import os
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict
import logging
import hashlib

# Core dependencies
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum
logger = logging.getLogger(__name__)

# Safe Import for Embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not installed. Vector search will be disabled.")
    EMBEDDINGS_AVAILABLE = False



logger = logging.getLogger(__name__)


class ResearchEntity(Enum):
    """Entity types in research knowledge graph"""
    PAPER = "paper"
    TECHNIQUE = "technique"
    PLATFORM = "platform"
    MODEL_TYPE = "model_type"
    OPTIMIZATION = "optimization"
    METRIC = "metric"
    COMPANY = "company"
    AUTHOR = "author"


@dataclass
class ResearchNode:
    """Node in knowledge graph"""
    id: str
    entity_type: ResearchEntity
    name: str
    attributes: Dict
    embedding: Optional[np.ndarray] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass
class ResearchEdge:
    """Edge connecting nodes in knowledge graph"""
    source_id: str
    target_id: str
    relationship: str  # uses, improves, compares_to, builds_on, contradicts
    weight: float
    metadata: Dict
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class KnowledgeGraph:
    """
    Graph database for research papers and their relationships
    Enables Graph RAG for contextual retrieval
    """
    
    def __init__(self, graph_path: str = "data/knowledge_graph.pkl"):
        self.graph_path = graph_path
        self.nodes: Dict[str, ResearchNode] = {}
        self.edges: List[ResearchEdge] = []
        self.entity_index: Dict[ResearchEntity, Set[str]] = defaultdict(set)
        self.adjacency: Dict[str, List[str]] = defaultdict(list)
        self.load()
    
    def add_node(self, node: ResearchNode) -> str:
        """Add node to graph"""
        self.nodes[node.id] = node
        self.entity_index[node.entity_type].add(node.id)
        logger.debug(f"Added node: {node.id} ({node.entity_type.value})")
        return node.id
    
    def add_edge(self, edge: ResearchEdge):
        """Add edge to graph"""
        self.edges.append(edge)
        self.adjacency[edge.source_id].append(edge.target_id)
        self.adjacency[edge.target_id].append(edge.source_id)  # Bidirectional
        logger.debug(f"Added edge: {edge.source_id} -> {edge.target_id} ({edge.relationship})")
    
    def get_neighbors(self, node_id: str, relationship: Optional[str] = None) -> List[ResearchNode]:
        """Get neighboring nodes"""
        neighbors = []
        for edge in self.edges:
            if edge.source_id == node_id:
                if relationship is None or edge.relationship == relationship:
                    if edge.target_id in self.nodes:
                        neighbors.append(self.nodes[edge.target_id])
        return neighbors
    
    def find_paths(self, start_id: str, end_id: str, max_depth: int = 3) -> List[List[str]]:
        """Find paths between two nodes (for relationship discovery)"""
        paths = []
        
        def dfs(current: str, target: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            if current == target:
                paths.append(path[:])
                return
            
            for neighbor in self.adjacency.get(current, []):
                if neighbor not in path:
                    path.append(neighbor)
                    dfs(neighbor, target, path, depth + 1)
                    path.pop()
        
        dfs(start_id, end_id, [start_id], 0)
        return paths
    
    def get_subgraph(self, center_id: str, radius: int = 2) -> Tuple[Dict, List]:
        """Get subgraph around a node (for context)"""
        visited = set()
        queue = [(center_id, 0)]
        subgraph_nodes = {}
        subgraph_edges = []
        
        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited or depth > radius:
                continue
            
            visited.add(node_id)
            if node_id in self.nodes:
                subgraph_nodes[node_id] = self.nodes[node_id]
            
            for neighbor_id in self.adjacency.get(node_id, []):
                if neighbor_id not in visited:
                    queue.append((neighbor_id, depth + 1))
                
                # Add edges in subgraph
                for edge in self.edges:
                    if (edge.source_id == node_id and edge.target_id == neighbor_id) or \
                       (edge.source_id == neighbor_id and edge.target_id == node_id):
                        if edge not in subgraph_edges:
                            subgraph_edges.append(edge)
        
        return subgraph_nodes, subgraph_edges
    
    def get_entities_by_type(self, entity_type: ResearchEntity) -> List[ResearchNode]:
        """Get all nodes of a specific type"""
        node_ids = self.entity_index.get(entity_type, set())
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]
    
    def save(self):
        """Persist graph to disk"""
        try:
            os.makedirs(os.path.dirname(self.graph_path), exist_ok=True)
            with open(self.graph_path, 'wb') as f:
                pickle.dump({
                    'nodes': self.nodes,
                    'edges': self.edges,
                    'entity_index': self.entity_index,
                    'adjacency': self.adjacency
                }, f)
            logger.info(f"Saved graph: {len(self.nodes)} nodes, {len(self.edges)} edges")
        except Exception as e:
            logger.error(f"Failed to save graph: {e}")
    
    def load(self):
        """Load graph from disk"""
        try:
            if os.path.exists(self.graph_path):
                with open(self.graph_path, 'rb') as f:
                    data = pickle.load(f)
                    self.nodes = data['nodes']
                    self.edges = data['edges']
                    self.entity_index = data['entity_index']
                    self.adjacency = data['adjacency']
                logger.info(f"Loaded graph: {len(self.nodes)} nodes, {len(self.edges)} edges")
        except Exception as e:
            logger.warning(f"Could not load graph: {e}")


class VectorStore:
    """
    Local Vector Database using Numpy for math and Pickle for storage.
    """
    def __init__(self, store_path: str = "data/vector_store.pkl"):
        self.store_path = store_path
        self.embeddings: Dict[str, np.ndarray] = {} # This holds the vectors
        self.metadata: Dict[str, Dict] = {}
        self.load() # Load existing vectors from disk on startup

    def add_embedding(self, doc_id: str, embedding: np.ndarray, metadata: Dict):
        """Stores the vector in the local dictionary"""
        self.embeddings[doc_id] = embedding
        self.metadata[doc_id] = metadata

    def similarity_search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """Performs Cosine Similarity math to find the closest research papers"""
        if not self.embeddings: return []
        
        similarities = []
        for doc_id, emb in self.embeddings.items():
            # Math: Cosine Similarity
            sim = np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
            similarities.append((doc_id, float(sim), self.metadata.get(doc_id, {})))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def save(self):
        """Persists all vectors to a local file"""
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        with open(self.store_path, 'wb') as f:
            pickle.dump({'embeddings': self.embeddings, 'metadata': self.metadata}, f)

    def load(self):
        """Loads vectors from the .pkl file"""
        if os.path.exists(self.store_path):
            with open(self.store_path, 'rb') as f:
                data = pickle.load(f)
                self.embeddings = data.get('embeddings', {})
                self.metadata = data.get('metadata', {})

class ChainOfThoughtReasoner:
    """
    Chain-of-Thought reasoning for better context generation and trend analysis
    """
    
    @staticmethod
    def analyze_research_trend(
        papers: List[Dict],
        focus: str = "memory optimization"
    ) -> Dict:
        """
        Perform CoT analysis of research trend
        
        Returns structured reasoning chain
        """
        reasoning_chain = {
            "observations": [],
            "patterns": [],
            "contradictions": [],
            "gaps": [],
            "conclusions": []
        }
        
        # Step 1: Observe individual papers
        for paper in papers:
            observation = {
                "paper": paper.get('title', 'Unknown'),
                "key_finding": paper.get('memory_insight', 'N/A'),
                "approach": paper.get('quantization_method', 'Unknown'),
                "impact": paper.get('dram_impact', 'Unknown')
            }
            reasoning_chain["observations"].append(observation)
        
        # Step 2: Identify patterns
        approaches = defaultdict(int)
        impacts = defaultdict(int)
        platforms = defaultdict(int)
        
        for paper in papers:
            approaches[paper.get('quantization_method', 'Unknown')] += 1
            impacts[paper.get('dram_impact', 'Unknown')] += 1
            platforms[paper.get('platform', 'Unknown')] += 1
        
        # Most common approach
        if approaches:
            top_approach = max(approaches.items(), key=lambda x: x[1])
            if top_approach[1] >= 3:
                reasoning_chain["patterns"].append(
                    f"Dominant approach: {top_approach[0]} ({top_approach[1]} papers)"
                )
        
        # Platform focus
        if platforms:
            for platform, count in platforms.items():
                if count >= len(papers) * 0.3:  # 30%+
                    reasoning_chain["patterns"].append(
                        f"{platform} focus in {count}/{len(papers)} papers"
                    )
        
        # Step 3: Detect contradictions
        high_impact_papers = [p for p in papers if p.get('dram_impact') == 'High']
        low_impact_papers = [p for p in papers if p.get('dram_impact') == 'Low']
        
        if high_impact_papers and low_impact_papers:
            # Check if using same techniques with different results
            high_techniques = set(p.get('quantization_method', '') for p in high_impact_papers)
            low_techniques = set(p.get('quantization_method', '') for p in low_impact_papers)
            overlap = high_techniques & low_techniques
            
            if overlap:
                reasoning_chain["contradictions"].append(
                    f"Technique {overlap} shows varying DRAM impact across papers"
                )
        
        # Step 4: Identify gaps
        covered_platforms = set(p.get('platform') for p in papers)
        all_platforms = {'Mobile', 'Laptop', 'Both'}
        missing_platforms = all_platforms - covered_platforms
        
        if missing_platforms:
            reasoning_chain["gaps"].append(
                f"Limited research on: {', '.join(missing_platforms)}"
            )
        
        # Step 5: Draw conclusions
        if reasoning_chain["patterns"]:
            reasoning_chain["conclusions"].append(
                f"Research trend: {reasoning_chain['patterns'][0]}"
            )
        
        if len(high_impact_papers) > len(low_impact_papers):
            reasoning_chain["conclusions"].append(
                "Research focusing on high DRAM impact solutions"
            )
        
        return reasoning_chain
    
    @staticmethod
    def generate_context_prompt(
        similar_papers: List[Dict],
        graph_context: Dict,
        trend_analysis: Dict
    ) -> str:
        """
        Generate rich contextual prompt using CoT reasoning
        """
        prompt = "RESEARCH CONTEXT (Chain-of-Thought Analysis):\n\n"
        
        # 1. Similar historical papers
        if similar_papers:
            prompt += "SIMILAR PREVIOUS RESEARCH:\n"
            for i, paper in enumerate(similar_papers[:3], 1):
                prompt += f"{i}. {paper.get('title', 'Unknown')}\n"
                prompt += f"   Finding: {paper.get('memory_insight', 'N/A')}\n"
                prompt += f"   Approach: {paper.get('quantization_method', 'Unknown')}\n"
                prompt += f"   Impact: {paper.get('dram_impact', 'Unknown')}\n\n"
        
        # 2. Graph-based relationships
        if graph_context.get('related_techniques'):
            prompt += "RELATED TECHNIQUES IN KNOWLEDGE GRAPH:\n"
            for tech in graph_context['related_techniques'][:3]:
                prompt += f"- {tech}\n"
            prompt += "\n"
        
        # 3. Trend analysis
        if trend_analysis.get('patterns'):
            prompt += "OBSERVED PATTERNS:\n"
            for pattern in trend_analysis['patterns']:
                prompt += f"- {pattern}\n"
            prompt += "\n"
        
        if trend_analysis.get('contradictions'):
            prompt += "CONTRADICTIONS TO INVESTIGATE:\n"
            for contradiction in trend_analysis['contradictions']:
                prompt += f"- {contradiction}\n"
            prompt += "\n"
        
        if trend_analysis.get('conclusions'):
            prompt += "CURRENT RESEARCH DIRECTION:\n"
            for conclusion in trend_analysis['conclusions']:
                prompt += f"- {conclusion}\n"
            prompt += "\n"
        
        prompt += "TASK: Analyze the new paper in context of these trends and patterns.\n"
        
        return prompt


class EnterpriseKnowledgeManager:
    """
    Enterprise-grade knowledge management system combining:
    - Knowledge Graph (Graph RAG)
    - Vector Store (Semantic search)
    - Chain-of-Thought reasoning
    """
    
    def __init__(
        self,
        data_dir: str = "data",
        use_embeddings: bool = True
    ):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize components
        self.graph = KnowledgeGraph(os.path.join(data_dir, "knowledge_graph.pkl"))
        self.vector_store = VectorStore(os.path.join(data_dir, "vector_store.pkl"))
        self.reasoner = ChainOfThoughtReasoner()
        self.use_embeddings = use_embeddings and EMBEDDINGS_AVAILABLE
        # Initialize Embedding Model if available
        self.embedder = None
        if self.use_embeddings:
            try:
                local_model_path = r"C:\\Users\\PBTSVS\\Desktop\\GenerativeAI-agent\\models\\embeddinggemma-300m"
                logger.info("Loading embedding model (google/embeddinggemma-300m)...")
                #self.embedder = SentenceTransformer('google/embeddinggemma-300m')
                if os.path.exists(local_model_path):
                    logger.info(f"Loading local embedding model from: {local_model_path}")
                    self.embedder = SentenceTransformer(local_model_path)
                else:
                    logger.warning(f"Local model not found at {local_model_path}. Trying public fallback...")
                    # Fallback to a non-gated model that doesn't require login
                    self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                
                logger.info(f"✓ Knowledge Manager initialized (Embeddings: {self.use_embeddings})")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self.use_embeddings = False
        # JSON backup for compatibility
        self.json_path = os.path.join(data_dir, "history.json")
        
        logger.info(f"Enterprise Knowledge Manager initialized  (Embeddings: {self.use_embeddings})")
    def _generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding using real model or fallback"""
        if self.embedder:
            return self.embedder.encode(text)
        return None

    def add_paper(self, paper: Dict, embedding: Optional[np.ndarray] = None):
        """Add paper to graph and vector store"""
        # Auto-generate embedding if not provided and model is loaded
        if embedding is None and self.use_embeddings:
            text_content = f"{paper.get('title', '')} {paper.get('summary', '')}"
            embedding = self._generate_embedding(text_content)
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID from content"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _extract_entities(self, paper: Dict) -> List[Tuple[ResearchEntity, str, Dict]]:
        """Extract entities from paper using structured extraction"""
        entities = []
        
        # Platform entity
        if paper.get('platform'):
            entities.append((
                ResearchEntity.PLATFORM,
                paper['platform'],
                {'source': 'paper', 'paper_id': paper.get('title', '')}
            ))
        
        # Model type entity
        if paper.get('model_type'):
            entities.append((
                ResearchEntity.MODEL_TYPE,
                paper['model_type'],
                {'source': 'paper', 'paper_id': paper.get('title', '')}
            ))
        
        # Optimization technique
        if paper.get('quantization_method') and paper['quantization_method'] != 'Unknown':
            entities.append((
                ResearchEntity.TECHNIQUE,
                paper['quantization_method'],
                {'category': 'quantization', 'paper_id': paper.get('title', '')}
            ))
        
        # Key optimization
        if paper.get('key_optimization') and paper['key_optimization'] not in ['Unknown', 'None']:
            entities.append((
                ResearchEntity.OPTIMIZATION,
                paper['key_optimization'],
                {'paper_id': paper.get('title', '')}
            ))
        
        # Company/source
        if paper.get('source'):
            entities.append((
                ResearchEntity.COMPANY,
                paper['source'],
                {'paper_id': paper.get('title', '')}
            ))
        
        return entities
    
    def add_paper(self, paper: Dict, embedding: Optional[np.ndarray] = None):
        """
        Add paper to knowledge graph and vector store
        
        Args:
            paper: Paper dictionary with analysis
            embedding: Optional pre-computed embedding vector
        """
        paper_id = self._generate_id(paper.get('title', '') + paper.get('summary', ''))
        
        # Create paper node
        paper_node = ResearchNode(
            id=f"paper_{paper_id}",
            entity_type=ResearchEntity.PAPER,
            name=paper.get('title', 'Unknown'),
            attributes={
                'relevance_score': paper.get('relevance_score', 0),
                'platform': paper.get('platform', 'Unknown'),
                'model_type': paper.get('model_type', 'Unknown'),
                'dram_impact': paper.get('dram_impact', 'Unknown'),
                'memory_insight': paper.get('memory_insight', ''),
                'engineering_takeaway': paper.get('engineering_takeaway', ''),
                'source': paper.get('source', 'Unknown'),
                'link': paper.get('link', ''),
                'date': paper.get('date', datetime.now().isoformat())
            },
            embedding=embedding
        )
        
        self.graph.add_node(paper_node)
        
        # Extract and add entities
        entities = self._extract_entities(paper)
        entity_nodes = {}
        
        for entity_type, entity_name, attributes in entities:
            entity_id = self._generate_id(f"{entity_type.value}_{entity_name}")
            
            # Check if entity already exists
            if f"{entity_type.value}_{entity_id}" not in self.graph.nodes:
                entity_node = ResearchNode(
                    id=f"{entity_type.value}_{entity_id}",
                    entity_type=entity_type,
                    name=entity_name,
                    attributes=attributes
                )
                self.graph.add_node(entity_node)
                entity_nodes[entity_name] = entity_node.id
            else:
                entity_nodes[entity_name] = f"{entity_type.value}_{entity_id}"
        
        # Create edges from paper to entities
        for entity_name, entity_id in entity_nodes.items():
            edge = ResearchEdge(
                source_id=paper_node.id,
                target_id=entity_id,
                relationship="uses" if "technique" in entity_id or "optimization" in entity_id else "relates_to",
                weight=paper.get('relevance_score', 50) / 100.0,
                metadata={'paper_title': paper.get('title', '')}
            )
            self.graph.add_edge(edge)
        
        # Add to vector store if embedding provided
        if embedding is not None and self.use_embeddings:
            self.vector_store.add_embedding(
                doc_id=paper_node.id,
                embedding=embedding,
                metadata={
                    'title': paper.get('title', ''),
                    'platform': paper.get('platform', ''),
                    'relevance_score': paper.get('relevance_score', 0),
                    'date': paper.get('date', '')
                }
            )
        
        logger.info(f"Added paper to knowledge graph: {paper.get('title', 'Unknown')[:50]}")
    
    def get_contextual_knowledge(
        self,
        query_paper: Dict,
        query_embedding: Optional[np.ndarray] = None,
        context_days: int = 30
    ) -> str:
        """
        Generate rich contextual knowledge using Graph RAG + Vector Search + CoT
        
        This is the MAIN method for generating context for new paper analysis
        """
        # 1. Vector similarity search (if embedding available)
        similar_papers_data = []
        if query_embedding is not None and self.use_embeddings:
            similar_results = self.vector_store.similarity_search(
                query_embedding,
                top_k=10,
                filters=None
            )
            
            # Get full paper data for similar papers
            for doc_id, similarity, metadata in similar_results:
                if doc_id in self.graph.nodes:
                    node = self.graph.nodes[doc_id]
                    similar_papers_data.append({
                        **node.attributes,
                        'similarity_score': similarity
                    })
        
        # 2. Get recent papers from graph (time-based)
        cutoff = datetime.now() - timedelta(days=context_days)
        recent_papers = []
        
        for node_id, node in self.graph.nodes.items():
            if node.entity_type == ResearchEntity.PAPER:
                paper_date_str = node.attributes.get('date', '')
                try:
                    paper_date = datetime.fromisoformat(paper_date_str)
                    if paper_date > cutoff:
                        recent_papers.append(node.attributes)
                except:
                    pass
        
        # 3. Get graph context (related entities)
        graph_context = {
            'related_techniques': [],
            'related_platforms': [],
            'related_companies': []
        }
        
        # Get all techniques used in recent papers
        techniques = self.graph.get_entities_by_type(ResearchEntity.TECHNIQUE)
        graph_context['related_techniques'] = [t.name for t in techniques[:10]]
        
        platforms = self.graph.get_entities_by_type(ResearchEntity.PLATFORM)
        graph_context['related_platforms'] = [p.name for p in platforms]
        
        companies = self.graph.get_entities_by_type(ResearchEntity.COMPANY)
        graph_context['related_companies'] = [c.name for c in companies[:5]]
        
        # 4. Perform Chain-of-Thought analysis
        papers_for_cot = similar_papers_data if similar_papers_data else recent_papers[:10]
        trend_analysis = self.reasoner.analyze_research_trend(
            papers_for_cot,
            focus="memory optimization"
        )
        
        # 5. Generate rich context prompt
        context_prompt = self.reasoner.generate_context_prompt(
            similar_papers=similar_papers_data[:5],
            graph_context=graph_context,
            trend_analysis=trend_analysis
        )
        
        return context_prompt
    
    def get_trend_report(self, days: int = 30) -> Dict:
        """Generate comprehensive trend report"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_papers = []
        
        for node_id, node in self.graph.nodes.items():
            if node.entity_type == ResearchEntity.PAPER:
                try:
                    paper_date = datetime.fromisoformat(node.attributes.get('date', ''))
                    if paper_date > cutoff:
                        recent_papers.append(node.attributes)
                except:
                    pass
        
        # Perform CoT analysis
        trend_analysis = self.reasoner.analyze_research_trend(recent_papers)
        
        # Add graph statistics
        trend_analysis['statistics'] = {
            'total_papers': len(recent_papers),
            'total_nodes': len(self.graph.nodes),
            'total_edges': len(self.graph.edges),
            'techniques_tracked': len(self.graph.get_entities_by_type(ResearchEntity.TECHNIQUE)),
            'platforms': len(self.graph.get_entities_by_type(ResearchEntity.PLATFORM)),
            'companies': len(self.graph.get_entities_by_type(ResearchEntity.COMPANY))
        }
        
        return trend_analysis
    
    def search_semantic(
        self,
        query_embedding: np.ndarray,
        filters: Optional[Dict] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """Semantic search using vector embeddings"""
        results = self.vector_store.similarity_search(query_embedding, top_k, filters)
        
        papers = []
        for doc_id, similarity, metadata in results:
            if doc_id in self.graph.nodes:
                node = self.graph.nodes[doc_id]
                papers.append({
                    **node.attributes,
                    'similarity_score': similarity,
                    'node_id': doc_id
                })
        
        return papers
    
    def find_research_gaps(self) -> List[str]:
        """Identify gaps in research coverage"""
        gaps = []
        
        # Platform coverage
        platforms = self.graph.get_entities_by_type(ResearchEntity.PLATFORM)
        platform_names = {p.name for p in platforms}
        expected_platforms = {'Mobile', 'Laptop', 'Both', 'IoT', 'Edge'}
        missing_platforms = expected_platforms - platform_names
        
        if missing_platforms:
            gaps.append(f"Limited research on platforms: {', '.join(missing_platforms)}")
        
        # Technique diversity
        techniques = self.graph.get_entities_by_type(ResearchEntity.TECHNIQUE)
        if len(techniques) < 5:
            gaps.append("Limited diversity in optimization techniques")
        
        # Model type coverage
        model_types = self.graph.get_entities_by_type(ResearchEntity.MODEL_TYPE)
        if len(model_types) < 3:
            gaps.append("Research concentrated on few model types")
        
        return gaps
    
    def save(self):
        """Save all components"""
        self.graph.save()
        self.vector_store.save()
        
        # Also save to JSON for backward compatibility
        self._save_to_json()
    
    def _save_to_json(self):
        """Export to JSON format for compatibility"""
        papers = []
        for node_id, node in self.graph.nodes.items():
            if node.entity_type == ResearchEntity.PAPER:
                papers.append(node.attributes)
        
        try:
            with open(self.json_path, 'w') as f:
                json.dump(papers, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save JSON backup: {e}")


# Example usage for integration
def create_embedding_stub(text: str) -> np.ndarray:
    """
    Stub for embedding generation - replace with actual embedding model
    In production, use: OpenAI embeddings, sentence-transformers, or similar
    """
    # This is a placeholder - use real embeddings in production
    # Example: from sentence_transformers import SentenceTransformer
    # model = SentenceTransformer('google/embeddinggemma-300m')
    # embedding = model.encode(text)
    
    # For now, return random embedding for demonstration
    np.random.seed(hash(text) % (2**32))
    return np.random.randn(384).astype(np.float32)  # 384-dim embedding