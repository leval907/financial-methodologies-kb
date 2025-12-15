"""Semantic search tool для Qdrant"""

import os
from typing import Dict, Any, List
from qdrant_client import QdrantClient
from openai import OpenAI
from qdrant_client.models import Filter, FieldCondition, MatchValue


class QdrantSearchTool:
    """Семантический поиск по векторной БД"""
    
    def __init__(self):
        """Инициализация клиента Qdrant"""
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        # Дефолтная коллекция (можно переопределить в arguments)
        self.default_collection = "books_budgeting_step_by_step"
        
        # Lazy initialization для OpenAI клиента
        self._openai_client = None
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
    
    @property
    def openai_client(self):
        """Lazy initialization OpenAI клиента"""
        if self._openai_client is None:
            self._openai_client = OpenAI(
                api_key=os.getenv("REQUESTY_API_KEY"),
                base_url="https://router.requesty.ai/v1"
            )
        return self._openai_client
    
    def get_schema(self) -> Dict[str, Any]:
        """Схема инструмента для MCP"""
        return {
            "name": "semantic_search",
            "description": """
Семантический поиск по базе знаний финансовых методологий.
Используй для поиска релевантных фрагментов текста по запросу пользователя.

Примеры запросов:
- "как построить бюджет движения денежных средств"
- "что такое contribution margin"
- "этапы внедрения бюджетирования"
- "точка безубыточности формула"
- "операционный рычаг расчет"

Возвращает список chunks с текстом, релевантным запросу, отсортированных по score.
            """.strip(),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Запрос пользователя (на русском или английском)"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Количество результатов (по умолчанию 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "methodology_id": {
                        "type": "string",
                        "description": "Фильтр по методологии (например, 'budgeting-step-by-step', 'toc-corbet')",
                        "enum": [
                            "budgeting-step-by-step",
                            "toc-corbet",
                            "accounting-basics-test",
                            "goal-decomposition",
                            "mckinsey-method"
                        ]
                    }
                },
                "required": ["query"]
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Выполнить семантический поиск"""
        query = arguments["query"]
        top_k = arguments.get("top_k", 5)
        methodology_id = arguments.get("methodology_id")
        
        # Определяем коллекцию
        if methodology_id:
            collection = f"books_{methodology_id.replace('-', '_')}"
        else:
            collection = self.default_collection
        
        try:
            # Проверяем существование коллекции
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if collection not in collection_names:
                return {
                    "error": f"Collection '{collection}' not found",
                    "available_collections": collection_names,
                    "hint": "Используй methodology_id из доступных коллекций или не указывай его для поиска по умолчанию"
                }
            
            # Генерируем embedding для запроса
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=query
            )
            query_vector = response.data[0].embedding
            
            # Поиск по векторам
            results = self.client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=top_k
            ).points
            
            # Форматируем результаты
            formatted_results = []
            for hit in results:
                formatted_results.append({
                    "chunk_id": hit.id,
                    "text": hit.payload.get("text", ""),
                    "page": hit.payload.get("page"),
                    "score": round(hit.score, 4),
                    "metadata": {
                        "book_id": hit.payload.get("book_id"),
                        "chunk_index": hit.payload.get("chunk_index"),
                        "category": hit.payload.get("category", "unknown")
                    }
                })
            
            return {
                "query": query,
                "collection": collection,
                "total_results": len(formatted_results),
                "results": formatted_results
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "query": query,
                "collection": collection
            }
