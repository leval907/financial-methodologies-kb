"""Filesystem tool для чтения файлов методологий"""

import os
from pathlib import Path
from typing import Dict, Any


class FilesystemTool:
    """Чтение файлов методологий из file system"""
    
    def __init__(self):
        """Инициализация путей"""
        # Корень проекта
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "data"
        self.work_dir = self.project_root / "work"
    
    def get_schema(self) -> Dict[str, Any]:
        """Схема инструмента для MCP"""
        return {
            "name": "read_methodology_file",
            "description": """
Прочитать markdown файлы методологии из файловой системы.

Используй когда нужно:
- Получить полный текст описания этапа методологии
- Прочитать детальное описание инструмента
- Посмотреть примеры использования индикатора
- Получить YAML-паспорт методологии

Типы файлов:
- stages: описание этапов методологии
- indicators: описание индикаторов
- tools: описание инструментов
- rules: правила применения
- methodology: общий YAML-паспорт методологии
- outline: структура методологии (outline.yaml или outline_rag.yaml)

Доступные методологии:
- budgeting-step-by-step
- toc-corbet
- accounting-basics-test
- goal-decomposition
            """.strip(),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "methodology_id": {
                        "type": "string",
                        "description": "ID методологии",
                        "enum": [
                            "budgeting-step-by-step",
                            "toc-corbet",
                            "accounting-basics-test",
                            "goal-decomposition",
                            "mckinsey-method"
                        ]
                    },
                    "file_type": {
                        "type": "string",
                        "description": "Тип файла для чтения",
                        "enum": [
                            "methodology",
                            "outline",
                            "stages",
                            "indicators",
                            "tools",
                            "rules"
                        ]
                    },
                    "specific_file": {
                        "type": "string",
                        "description": "Конкретный файл (например, 'stage_1.md', 'indicator_breakeven.md')"
                    }
                },
                "required": ["methodology_id", "file_type"]
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Прочитать файл методологии"""
        methodology_id = arguments["methodology_id"]
        file_type = arguments["file_type"]
        specific_file = arguments.get("specific_file")
        
        try:
            # Определяем путь в зависимости от типа файла
            if file_type == "methodology":
                # YAML паспорт из data/methodologies/
                file_path = self.data_dir / "methodologies" / f"{methodology_id}.yaml"
                
            elif file_type == "outline":
                # outline.yaml или outline_rag.yaml из work/
                work_methodology_dir = self.work_dir / methodology_id
                
                # Пробуем найти outline файлы
                outline_rag = work_methodology_dir / "outline_rag.yaml"
                outline = work_methodology_dir / "outline.yaml"
                
                if outline_rag.exists():
                    file_path = outline_rag
                elif outline.exists():
                    file_path = outline
                else:
                    return {
                        "error": f"Outline файл не найден для методологии '{methodology_id}'",
                        "searched_paths": [str(outline_rag), str(outline)]
                    }
            
            else:
                # MD файлы из data/methodologies/<id>/
                methodology_dir = self.data_dir / "methodologies" / methodology_id
                
                if specific_file:
                    file_path = methodology_dir / file_type / specific_file
                else:
                    # Читаем все файлы категории
                    category_dir = methodology_dir / file_type
                    
                    if not category_dir.exists():
                        return {
                            "error": f"Директория '{file_type}' не найдена для методологии '{methodology_id}'",
                            "path": str(category_dir)
                        }
                    
                    # Список всех файлов в категории
                    files = sorted(category_dir.glob("*.md"))
                    
                    if not files:
                        return {
                            "error": f"Нет файлов типа '{file_type}' для методологии '{methodology_id}'",
                            "path": str(category_dir)
                        }
                    
                    # Читаем все файлы
                    contents = []
                    for file in files:
                        with open(file, "r", encoding="utf-8") as f:
                            contents.append({
                                "file": file.name,
                                "content": f.read()
                            })
                    
                    return {
                        "methodology_id": methodology_id,
                        "file_type": file_type,
                        "total_files": len(contents),
                        "files": contents
                    }
            
            # Читаем конкретный файл
            if not file_path.exists():
                return {
                    "error": f"Файл не найден: {file_path}",
                    "methodology_id": methodology_id,
                    "file_type": file_type
                }
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            return {
                "methodology_id": methodology_id,
                "file_type": file_type,
                "file_path": str(file_path),
                "content": content,
                "size_bytes": len(content.encode("utf-8"))
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "methodology_id": methodology_id,
                "file_type": file_type
            }
