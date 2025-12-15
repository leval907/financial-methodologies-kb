"""
Qdrant vector database client
"""
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
)
from typing import List, Dict, Optional
from tqdm import tqdm

class QdrantManager:
    """
    Manage Qdrant vector database operations
    """
    
    def __init__(
        self, 
        host: str = 'localhost', 
        port: int = 6333,
        api_key: Optional[str] = None
    ):
        """
        Args:
            host: Qdrant host
            port: Qdrant port
            api_key: Optional API key for authentication
        """
        # For local Qdrant, use http://localhost:port URL format
        self.client = QdrantClient(
            url=f'http://{host}:{port}',
            api_key=api_key if api_key else None,
            timeout=60,
            prefer_grpc=False
        )
    
    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 1536,
        distance: Distance = Distance.COSINE,
        recreate: bool = False
    ):
        """
        Create a collection in Qdrant
        
        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors
            distance: Distance metric (COSINE, DOT, EUCLIDEAN)
            recreate: If True, delete existing collection
        """
        if recreate:
            try:
                self.client.delete_collection(collection_name)
                print(f'Deleted existing collection: {collection_name}')
            except:
                pass
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance
            )
        )
        print(f'Created collection: {collection_name}')
    
    def upsert_chunks(
        self,
        collection_name: str,
        chunks: List[Dict],
        embeddings: List[List[float]],
        batch_size: int = 100
    ):
        """
        Insert chunks with embeddings into Qdrant
        
        Args:
            collection_name: Target collection
            chunks: List of chunk dictionaries
            embeddings: Corresponding embeddings
            batch_size: Batch size for upload
        """
        assert len(chunks) == len(embeddings), "Chunks and embeddings count mismatch"
        
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            point = PointStruct(
                id=chunk['chunk_id'],
                vector=embedding,
                payload={
                    'text': chunk['text'],
                    'book_id': chunk['book_id'],
                    'page': chunk['page'],
                    'word_count': chunk['word_count'],
                }
            )
            points.append(point)
        
        # Upload in batches
        for i in tqdm(range(0, len(points), batch_size), desc='Uploading to Qdrant'):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=collection_name,
                points=batch
            )
        
        print(f'Uploaded {len(points)} chunks to {collection_name}')
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 50,
        score_threshold: Optional[float] = None,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar vectors
        
        Args:
            collection_name: Collection to search
            query_vector: Query embedding
            limit: Max number of results
            score_threshold: Minimum similarity score
            filter_dict: Optional filters (e.g., {'book_id': 'toc-corbet'})
        
        Returns:
            List of search results with payload and score
        """
        query_filter = None
        if filter_dict:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_dict.items()
            ]
            query_filter = Filter(must=conditions)
        
        results = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter
        ).points
        
        return [
            {
                'id': r.id,
                'score': r.score,
                'text': r.payload['text'],
                'page': r.payload['page'],
                'book_id': r.payload['book_id']
            }
            for r in results
        ]
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """Get collection statistics"""
        info = self.client.get_collection(collection_name)
        return {
            'name': collection_name,
            'points_count': info.points_count,
            'vectors_count': info.vectors_count if hasattr(info, 'vectors_count') else info.points_count,
            'status': info.status
        }
