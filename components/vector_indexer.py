# components/vector_indexer.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import pickle
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

class VectorIndexer:
    """FAISS-based vector indexer for semantic search"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', index_path: str = 'faiss_index'):
        self.model_name = model_name
        self.index_path = Path(index_path)
        self.index_path.mkdir(exist_ok=True)
        
        # Load sentence transformer model
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # Initialize or load FAISS index
        self.index = None
        self.id_mapping = {}  # Maps FAISS index position to metadata ID
        self.load_or_create_index()
    
    def load_or_create_index(self):
        """Load existing index or create new one"""
        index_file = self.index_path / 'index.faiss'
        mapping_file = self.index_path / 'id_mapping.pkl'
        
        if index_file.exists() and mapping_file.exists():
            try:
                self.index = faiss.read_index(str(index_file))
                with open(mapping_file, 'rb') as f:
                    self.id_mapping = pickle.load(f)
                logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
            except Exception as e:
                logger.error(f"Error loading index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self):
        """Create new FAISS index"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.id_mapping = {}
        logger.info(f"Created new FAISS index with dimension {self.dimension}")
    
    def save_index(self):
        """Persist index to disk"""
        index_file = self.index_path / 'index.faiss'
        mapping_file = self.index_path / 'id_mapping.pkl'
        
        faiss.write_index(self.index, str(index_file))
        with open(mapping_file, 'wb') as f:
            pickle.dump(self.id_mapping, f)
        
        logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")
    
    def add_texts(self, texts: List[str], metadata_ids: List[int]) -> List[int]:
        """Add texts to index with metadata IDs"""
        if not texts:
            return []
        
        # Generate embeddings
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        embeddings = np.array(embeddings).astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Get current index size
        start_idx = self.index.ntotal
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Update ID mapping
        for i, meta_id in enumerate(metadata_ids):
            self.id_mapping[start_idx + i] = meta_id
        
        # Save index
        self.save_index()
        
        return list(range(start_idx, start_idx + len(texts)))
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """Search for similar texts"""
        if self.index.ntotal == 0:
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        query_embedding = np.array(query_embedding).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        top_k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, top_k)
        
        # Convert to similarity scores (1 - distance for normalized vectors)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx in self.id_mapping:
                similarity = 1 - (dist / 2)  # Convert L2 distance to cosine similarity
                results.append((self.id_mapping[idx], float(similarity)))
        
        return results
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for texts"""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return np.array(embeddings).astype('float32')
    
    def clear_index(self):
        """Clear all data from index"""
        self._create_new_index()
        self.save_index()
        logger.info("Cleared FAISS index")