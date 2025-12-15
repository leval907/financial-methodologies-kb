"""Graph queries tool для ArangoDB"""

import os
from typing import Dict, Any, List
from arango import ArangoClient


class ArangoGraphTool:
    """Получение контекста методологии из графа знаний"""
    
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
            "name": "get_methodology_context",
            "description": """
Получить структурированную информацию о методологии из графа знаний:
- Этапы (stages) методологии с описаниями
- Инструменты (tools) для каждого этапа
- Индикаторы (indicators) для оценки результатов
- Правила (rules) применения методологии
- Связи между сущностями

Используй когда нужно понять:
- Из каких шагов состоит методология
- Какие инструменты применяются на каждом этапе
- Как измерять эффективность
- Какая последовательность действий

Доступные методологии:
- toc (Theory of Constraints)
- budgeting-step-by-step (Бюджетирование: шаг за шагом)
- accounting-basics-test (Основы бухучёта)
            """.strip(),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "methodology_id": {
                        "type": "string",
                        "description": "ID методологии",
                        "enum": [
                            "toc",
                            "budgeting-step-by-step",
                            "accounting-basics-test"
                        ]
                    },
                    "include_stages": {
                        "type": "boolean",
                        "description": "Включить этапы методологии (default: true)",
                        "default": True
                    },
                    "include_indicators": {
                        "type": "boolean",
                        "description": "Включить индикаторы (default: true)",
                        "default": True
                    },
                    "include_tools": {
                        "type": "boolean",
                        "description": "Включить инструменты (default: false)",
                        "default": False
                    },
                    "include_rules": {
                        "type": "boolean",
                        "description": "Включить правила (default: false)",
                        "default": False
                    }
                },
                "required": ["methodology_id"]
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получить контекст методологии"""
        methodology_id = arguments["methodology_id"]
        include_stages = arguments.get("include_stages", True)
        include_indicators = arguments.get("include_indicators", True)
        include_tools = arguments.get("include_tools", False)
        include_rules = arguments.get("include_rules", False)
        
        result = {
            "methodology_id": methodology_id,
            "methodology": None,
            "stages": [],
            "indicators": [],
            "tools": [],
            "rules": []
        }
        
        try:
            # 1. Основная информация о методологии
            methodologies_coll = self.db.collection("methodologies")
            methodology_doc = methodologies_coll.get(methodology_id)
            
            if not methodology_doc:
                return {
                    "error": f"Методология '{methodology_id}' не найдена",
                    "available_methodologies": [
                        "toc",
                        "budgeting-step-by-step",
                        "accounting-basics-test"
                    ]
                }
            
            result["methodology"] = {
                "id": methodology_doc.get("_key"),
                "name": methodology_doc.get("title", methodology_doc.get("name")),
                "description": methodology_doc.get("description", ""),
                "book_title": methodology_doc.get("book_title", ""),
                "author": methodology_doc.get("author", ""),
                "source_book": methodology_doc.get("source_book", "")
            }
            
            # 2. Этапы методологии
            if include_stages:
                aql = """
                    FOR stage IN stages
                        FILTER stage.book_id == @methodology_id 
                           OR stage.methodology_id == @methodology_id
                           OR stage.source_book == @methodology_id
                        SORT stage.order ASC
                        RETURN {
                            id: stage._key,
                            name: stage.title || stage.name,
                            title: stage.title || stage.name,
                            order: stage.order,
                            description: stage.description,
                            inputs: stage.inputs,
                            outputs: stage.outputs
                        }
                """
                cursor = self.db.aql.execute(aql, bind_vars={"methodology_id": methodology_id})
                result["stages"] = list(cursor)
            
            # 3. Индикаторы
            if include_indicators:
                aql = """
                    FOR indicator IN indicators
                        FILTER indicator.book_id == @methodology_id
                           OR indicator.methodology_id == @methodology_id
                           OR indicator.source_book == @methodology_id
                        RETURN {
                            id: indicator._key,
                            name: indicator.title || indicator.name,
                            title: indicator.title || indicator.name,
                            description: indicator.description,
                            definition: indicator.definition,
                            formula: indicator.formula,
                            unit: indicator.unit,
                            abbreviation: indicator.abbreviation,
                            interpretation: indicator.interpretation
                        }
                """
                cursor = self.db.aql.execute(aql, bind_vars={"methodology_id": methodology_id})
                result["indicators"] = list(cursor)
            
            # 4. Инструменты (если запрошены)
            if include_tools:
                aql = """
                    FOR tool IN tools
                        FILTER tool.book_id == @methodology_id
                           OR tool.methodology_id == @methodology_id
                        RETURN {
                            id: tool._key,
                            name: tool.title || tool.name,
                            title: tool.title || tool.name,
                            description: tool.description,
                            purpose: tool.purpose,
                            when_to_use: tool.when_to_use,
                            application_area: tool.application_area
                        }
                """
                cursor = self.db.aql.execute(aql, bind_vars={"methodology_id": methodology_id})
                result["tools"] = list(cursor)
            
            # 5. Правила (если запрошены)
            if include_rules:
                aql = """
                    FOR rule IN rules
                        FILTER rule.book_id == @methodology_id
                           OR rule.methodology_id == @methodology_id
                        RETURN {
                            id: rule._key,
                            name: rule.title || rule.name,
                            title: rule.title || rule.name,
                            description: rule.description,
                            type: rule.type,
                            rationale: rule.rationale,
                            condition: rule.condition,
                            action: rule.action
                        }
                """
                cursor = self.db.aql.execute(aql, bind_vars={"methodology_id": methodology_id})
                result["rules"] = list(cursor)
            
            # Добавляем статистику
            result["stats"] = {
                "total_stages": len(result["stages"]),
                "total_indicators": len(result["indicators"]),
                "total_tools": len(result["tools"]),
                "total_rules": len(result["rules"])
            }
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "methodology_id": methodology_id
            }
