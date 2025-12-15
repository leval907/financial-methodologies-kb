"""
RAG-based semantic search for methodology extraction
"""
from typing import List, Dict
from ..stage1_ingestion.embedder import EmbeddingGenerator
from ..stage1_ingestion.qdrant_client import QdrantManager

class RAGSearcher:
    """
    Semantic search using Qdrant vector database
    """
    
    def __init__(
        self,
        qdrant_manager: QdrantManager,
        embedding_generator: EmbeddingGenerator,
        collection_name: str
    ):
        """
        Args:
            qdrant_manager: Qdrant client
            embedding_generator: Embedding generator
            collection_name: Target collection name
        """
        self.qdrant = qdrant_manager
        self.embedder = embedding_generator
        self.collection_name = collection_name
    
    def search_by_category(
        self,
        category: str,
        top_k: int = 50,
        min_similarity: float = 0.7
    ) -> List[Dict]:
        """
        Search for chunks relevant to a specific category
        
        Args:
            category: Category type ('stages', 'tools', 'indicators', 'rules')
            top_k: Number of chunks to retrieve
            min_similarity: Minimum cosine similarity threshold
        
        Returns:
            List of relevant chunks with metadata
        """
        # Define search queries for each category
        queries = {
            'stages': '''
            Этапы методологии, шаги процесса, фазы реализации, 
            стадии внедрения, алгоритмы выполнения работ, последовательность действий
            ''',
            'tools': '''
            Инструменты методологии, методы анализа, техники оптимизации,
            управленческий учет, аналитические подходы, программные средства
            ''',
            'indicators': '''
            Показатели эффективности, метрики производительности, KPI,
            финансовые индикаторы, операционные показатели, формулы расчета
            ''',
            'rules': '''
            Правила применения, принципы работы, ограничения методологии,
            условия использования, рекомендации, best practices
            '''
        }
        
        query_text = queries.get(category, category)
        
        # Generate query embedding
        query_embedding = self.embedder.embed_single(query_text)
        
        # Search in Qdrant
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=min_similarity
        )
        
        return results
    
    def search_custom(
        self,
        query_text: str,
        top_k: int = 50,
        min_similarity: float = 0.7,
        filter_dict: Dict = None
    ) -> List[Dict]:
        """
        Custom semantic search
        
        Args:
            query_text: Natural language query
            top_k: Number of results
            min_similarity: Minimum similarity score
            filter_dict: Optional metadata filters
        
        Returns:
            List of relevant chunks
        """
        query_embedding = self.embedder.embed_single(query_text)
        
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=min_similarity,
            filter_dict=filter_dict
        )
        
        return results
