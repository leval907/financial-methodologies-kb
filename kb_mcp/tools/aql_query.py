"""AQL Query tool для произвольных запросов к ArangoDB"""

import os
from typing import Dict, Any, List
from arango import ArangoClient


class AQLQueryTool:
    """Выполнение произвольных AQL запросов к графовой БД"""
    
    def __init__(self):
        """Инициализация клиента ArangoDB"""
        # Формируем полный URL с проверкой протокола
        host = os.getenv("ARANGO_HOST", "localhost")
        port = os.getenv("ARANGO_PORT", "8529")
        password = os.getenv("ARANGO_PASSWORD", "strongpassword")
        
        # Добавляем http:// если не указан протокол
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"
        
        # Добавляем порт если не указан в host
        if ":" not in host.split("//")[1]:
            host = f"{host}:{port}"
        
        client = ArangoClient(hosts=host)
        self.db = client.db(
            name=os.getenv("ARANGO_DB", "fin_kb_method"),
            username=os.getenv("ARANGO_USER", "root"),
            password=password
        )
    
    def get_schema(self) -> Dict[str, Any]:
        """Схема инструмента для MCP"""
        return {
            "name": "query_arangodb",
            "description": """
Выполнить произвольный AQL (ArangoDB Query Language) запрос к графовой базе знаний.

Доступные коллекции:
- methodologies (методологии)
- stages (этапы методологий)
- tools (инструменты)
- indicators (индикаторы/метрики)
- rules (правила применения)
- concepts (концепции/термины)
- examples (примеры)

Рёбра (relationships):
- has_stage (методология → этап)
- has_tool (этап → инструмент)
- has_indicator (этап/методология → индикатор)
- related_to (связи между концепциями)
- prerequisite (зависимости между этапами)

Примеры запросов:
1. Получить все методологии:
   FOR m IN methodologies RETURN m

2. Найти связанные концепции:
   FOR c IN concepts
     FILTER c.name == "Budget"
     FOR v, e, p IN 1..2 ANY c related_to
       RETURN {concept: c.name, related: v.name, path_length: LENGTH(p.edges)}

3. Найти инструменты для этапа:
   FOR stage IN stages
     FILTER stage.name LIKE "%Planning%"
     FOR tool IN 1 OUTBOUND stage has_tool
       RETURN {stage: stage.name, tool: tool.name}

ВАЖНО: Запросы только на чтение (FOR, RETURN). Модификация данных (INSERT, UPDATE, DELETE) запрещена.
            """.strip(),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "AQL запрос (только SELECT/FOR, без модификации данных)"
                    },
                    "bind_vars": {
                        "type": "object",
                        "description": "Параметры запроса (необязательно), например: {\"methodology_id\": \"toc\"}",
                        "default": {}
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Максимальное количество результатов (default: 50)",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 500
                    }
                },
                "required": ["query"]
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнить AQL запрос"""
        query = arguments["query"]
        bind_vars = arguments.get("bind_vars", {})
        limit = arguments.get("limit", 50)
        
        # Безопасность: запрещаем модификацию данных
        query_upper = query.upper().strip()
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "REMOVE", "REPLACE", "UPSERT"]
        
        for keyword in forbidden_keywords:
            if keyword in query_upper:
                return {
                    "error": f"Операция {keyword} запрещена. Разрешены только запросы на чтение (FOR, RETURN).",
                    "query": query
                }
        
        # Добавляем LIMIT если его нет в запросе
        if "LIMIT" not in query_upper:
            query = f"{query.rstrip()} LIMIT {limit}"
        
        try:
            # Выполняем запрос
            cursor = self.db.aql.execute(
                query,
                bind_vars=bind_vars,
                count=True,  # получаем общее количество
                batch_size=min(limit, 100)
            )
            
            results = list(cursor)
            
            return {
                "success": True,
                "query": query,
                "bind_vars": bind_vars,
                "count": len(results),
                "results": results
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "query": query,
                "bind_vars": bind_vars,
                "hint": "Проверьте синтаксис AQL и названия коллекций. Используйте FOR...RETURN для выборки."
            }
    
    async def get_collections(self) -> List[str]:
        """Получить список всех коллекций"""
        try:
            collections = self.db.collections()
            return [c["name"] for c in collections if not c["name"].startswith("_")]
        except Exception as e:
            return []
    
    async def get_collection_sample(self, collection_name: str, limit: int = 5) -> List[Dict]:
        """Получить примеры документов из коллекции"""
        try:
            query = f"FOR doc IN {collection_name} LIMIT @limit RETURN doc"
            cursor = self.db.aql.execute(query, bind_vars={"limit": limit})
            return list(cursor)
        except Exception as e:
            return []
