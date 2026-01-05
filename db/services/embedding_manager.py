"""
Embedding Manager Service
Generates text embeddings using Qwen3-Embedding or sentence-transformers.
"""
from typing import Optional, List
import numpy as np

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Try to import for LM Studio/OpenAI compatible API
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class EmbeddingManager:
    """
    Manager for generating text embeddings.
    
    Supports two modes:
    1. Local: sentence-transformers (Qwen3-Embedding-0.6B)
    2. API: LM Studio or OpenAI-compatible embedding API
    """
    
    # Embedding dimension for Qwen3-Embedding-0.6B
    EMBEDDING_DIM = 1024
    
    def __init__(self, mode: str = 'local', api_base: str = 'http://localhost:1234'):
        """
        Initialize embedding manager.
        
        Args:
            mode: 'local' for sentence-transformers, 'api' for LM Studio
            api_base: Base URL for API mode
        """
        self.mode = mode
        self.api_base = api_base
        self._model = None
        self._loaded = False
        
        print(f"[Embedding] Manager initialized (mode={mode})")
    
    def load_model(self, model_name: str = 'Qwen/Qwen3-Embedding-0.6B'):
        """
        Load the embedding model.
        
        Args:
            model_name: HuggingFace model name
                - 'Qwen/Qwen3-Embedding-0.6B' (1024 dim, recommended)
                - 'Alibaba-NLP/gte-Qwen2-1.5B-instruct' (768 dim)
                - 'BAAI/bge-small-en-v1.5' (384 dim, smaller)
        """
        if self._loaded:
            return
        
        if self.mode == 'local':
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
            
            print(f"[Embedding] Loading model: {model_name}...")
            self._model = SentenceTransformer(model_name)
            self._loaded = True
            print(f"[Embedding] Model loaded (dim={self._model.get_sentence_embedding_dimension()})")
    
    def encode(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for single text.
        
        Args:
            text: Text to encode
            
        Returns:
            List of floats (embedding vector) or None if failed
        """
        if not self._loaded and self.mode == 'local':
            self.load_model()
        
        try:
            if self.mode == 'local':
                # Truncate text if too long (avoid OOM)
                max_tokens = 8000  # Approximate
                text = text[:max_tokens]
                
                embedding = self._model.encode(text)
                return embedding.tolist()
            else:
                # API mode - needs async
                raise NotImplementedError("Use encode_async for API mode")
                
        except Exception as e:
            print(f"[Embedding] Encode error: {e}")
            return None
    
    def encode_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to encode
            
        Returns:
            List of embedding vectors
        """
        if not self._loaded and self.mode == 'local':
            self.load_model()
        
        try:
            if self.mode == 'local':
                # Truncate texts
                truncated = [t[:8000] for t in texts]
                
                embeddings = self._model.encode(truncated)
                return [e.tolist() for e in embeddings]
            else:
                raise NotImplementedError("Use encode_batch_async for API mode")
                
        except Exception as e:
            print(f"[Embedding] Batch encode error: {e}")
            return [None] * len(texts)
    
    async def encode_async(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding using API (async).
        
        Works with LM Studio or OpenAI-compatible API.
        """
        if self.mode == 'local':
            return self.encode(text)
        
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp not installed")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/v1/embeddings",
                    json={
                        "input": text[:8000],
                        "model": "text-embedding"  # LM Studio uses this
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    result = await resp.json()
                    return result['data'][0]['embedding']
                    
        except Exception as e:
            print(f"[Embedding] API error: {e}")
            return None
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._loaded and self._model:
            return self._model.get_sentence_embedding_dimension()
        return self.EMBEDDING_DIM
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded
