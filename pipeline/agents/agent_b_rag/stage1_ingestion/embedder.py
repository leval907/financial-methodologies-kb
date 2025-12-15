"""
Embedding generation via Requesty AI
"""
from openai import OpenAI
from typing import List
import asyncio
from tqdm import tqdm

class EmbeddingGenerator:
    """
    Generate embeddings using Requesty AI (OpenAI-compatible)
    """
    
    def __init__(self, api_key: str, model: str = 'openai/text-embedding-3-small'):
        """
        Args:
            api_key: Requesty AI API key
            model: Embedding model name (format: provider/model)
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://router.requesty.ai/v1"
        )
        self.model = model
    
    def embed_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API request (reduced to 20 for large files)
        
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        # Process in batches
        for i in tqdm(range(0, len(texts), batch_size), desc='Embedding batches'):
            batch = texts[i:i + batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f'Error embedding batch {i//batch_size}: {e}')
                # Add zero vectors as fallback
                embeddings.extend([[0.0] * 1536] * len(batch))
        
        return embeddings
    
    def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        return self.embed_batch([text])[0]
