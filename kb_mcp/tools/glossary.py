"""Glossary tool для ArangoDB"""

import os
from typing import Dict, Any, Optional
from arango import ArangoClient


class GlossaryTool:
    """Разрешение терминов из глоссария"""
    
    def __init__(self):
        """Инициализация клиента ArangoDB"""
        # Формируем полный URL с проверкой протокола
        host = os.getenv("ARANGO_HOST", "localhost")
        port = os.getenv("ARANGO_PORT", "8529")
        
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
            password=os.getenv("ARANGO_PASSWORD", "strongpassword")
        )
    
    def get_schema(self) -> Dict[str, Any]:
        """Схема инструмента для MCP"""
        return {
            "name": "get_glossary_term",
            "description": """
Получить определение термина из глоссария финансовых методологий.

Используй когда пользователь спрашивает:
- "Что такое X?"
- "Определение X"
- "Как понимать термин X"
- "Расшифруй X"

Глоссарий содержит канонические определения терминов, формулы, синонимы и связи между понятиями.

Примеры терминов:
- contribution margin (маржинальный доход)
- throughput (пропускная способность системы)
- constraint (ограничение системы)
- budgeting (бюджетирование)
- point of sale (точка продаж)
            """.strip(),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "Термин для поиска (на русском или английском)"
                    },
                    "language": {
                        "type": "string",
                        "description": "Язык определения (ru или en, default: ru)",
                        "enum": ["ru", "en"],
                        "default": "ru"
                    },
                    "include_related": {
                        "type": "boolean",
                        "description": "Включить связанные термины (default: true)",
                        "default": True
                    }
                },
                "required": ["term"]
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получить определение термина"""
        term = arguments["term"].lower().strip()
        language = arguments.get("language", "ru")
        include_related = arguments.get("include_related", True)
        
        try:
            # Поиск термина по имени или алиасам
            aql = """
                FOR gt IN glossary_terms
                    FILTER LOWER(gt.name) == @term
                       OR @term IN gt.aliases
                    RETURN {
                        term: gt.name,
                        aliases: gt.aliases,
                        definition: gt.definition,
                        formula: gt.formula,
                        category: gt.tags,
                        related_terms: []
                    }
            """
            
            cursor = self.db.aql.execute(aql, bind_vars={"term": term})
            results = list(cursor)
            
            if not results:
                # Попробуем fuzzy search
                aql_fuzzy = """
                    FOR gt IN glossary_terms
                        FILTER CONTAINS(LOWER(gt.name), @term)
                        LIMIT 5
                        RETURN {
                            term: gt.name,
                            definition: gt.definition
                        }
                """
                cursor_fuzzy = self.db.aql.execute(aql_fuzzy, bind_vars={"term": term})
                suggestions = list(cursor_fuzzy)
                
                return {
                    "error": f"Термин '{term}' не найден в глоссарии",
                    "suggestions": suggestions,
                    "hint": "Попробуйте один из предложенных терминов"
                }
            
            # Берём первый результат (самый релевантный)
            glossary_entry = results[0]
            
            # Формируем ответ в зависимости от языка
            if language == "en":
                result = {
                    "term": glossary_entry.get("term_en", glossary_entry["term"]),
                    "definition": glossary_entry.get("definition_en", glossary_entry.get("definition")),
                    "aliases": glossary_entry.get("aliases", []),
                    "formula": glossary_entry.get("formula"),
                    "category": glossary_entry.get("category"),
                    "methodology": glossary_entry.get("methodology")
                }
            else:
                result = {
                    "term": glossary_entry["term"],
                    "definition": glossary_entry.get("definition"),
                    "aliases": glossary_entry.get("aliases", []),
                    "formula": glossary_entry.get("formula"),
                    "category": glossary_entry.get("category"),
                    "methodology": glossary_entry.get("methodology")
                }
            
            # Добавляем связанные термины если запрошены
            if include_related and glossary_entry.get("related_terms"):
                related_terms_list = glossary_entry.get("related_terms", [])
                result["related_terms"] = []
                
                for related_term in related_terms_list[:5]:  # Ограничиваем 5 терминами
                    aql_related = """
                        FOR gt IN glossary_terms
                            FILTER LOWER(gt.term) == @related_term
                               OR LOWER(gt.term_en) == @related_term
                            LIMIT 1
                            RETURN {
                                term: gt.term,
                                definition: gt.definition
                            }
                    """
                    cursor_related = self.db.aql.execute(
                        aql_related, 
                        bind_vars={"related_term": related_term.lower()}
                    )
                    related_results = list(cursor_related)
                    if related_results:
                        result["related_terms"].append(related_results[0])
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "term": term
            }
