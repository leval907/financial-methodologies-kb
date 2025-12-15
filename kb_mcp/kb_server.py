#!/usr/bin/env python3
"""
Universal MCP Server для Financial Methodologies KB
Работает через stdio - совместим с Claude Desktop, VS Code, Cline и др.
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Any

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

from kb_mcp.tools.search import QdrantSearchTool
from kb_mcp.tools.graph import ArangoGraphTool
from kb_mcp.tools.glossary import GlossaryTool
from kb_mcp.tools.files import FilesystemTool
from kb_mcp.tools.aql_query import AQLQueryTool

# Загружаем .env файлы (специфичные загружаем ПЕРВЫМИ, чтобы они имели приоритет)
load_dotenv(project_root / ".env.arango", override=True)
load_dotenv(project_root / ".env.qdrant", override=True)
load_dotenv(project_root / ".env", override=False)  # общий файл загружаем последним без перезаписи


async def main():
    """Запуск MCP сервера"""
    
    # Создаём сервер с метаданными
    server = Server("financial-kb-mcp")
    
    # Инициализируем инструменты
    search_tool = QdrantSearchTool()
    graph_tool = ArangoGraphTool()
    glossary_tool = GlossaryTool()
    files_tool = FilesystemTool()
    aql_tool = AQLQueryTool()
    
    # Регистрируем список доступных инструментов
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Возвращает список доступных MCP инструментов"""
        tools = []
        
        # Semantic search tool
        search_schema = search_tool.get_schema()
        tools.append(Tool(
            name=search_schema["name"],
            description=search_schema["description"],
            inputSchema=search_schema["inputSchema"]
        ))
        
        # Methodology context tool
        graph_schema = graph_tool.get_schema()
        tools.append(Tool(
            name=graph_schema["name"],
            description=graph_schema["description"],
            inputSchema=graph_schema["inputSchema"]
        ))
        
        # Glossary tool
        glossary_schema = glossary_tool.get_schema()
        tools.append(Tool(
            name=glossary_schema["name"],
            description=glossary_schema["description"],
            inputSchema=glossary_schema["inputSchema"]
        ))
        
        # Filesystem tool
        files_schema = files_tool.get_schema()
        tools.append(Tool(
            name=files_schema["name"],
            description=files_schema["description"],
            inputSchema=files_schema["inputSchema"]
        ))
        
        # AQL query tool
        aql_schema = aql_tool.get_schema()
        tools.append(Tool(
            name=aql_schema["name"],
            description=aql_schema["description"],
            inputSchema=aql_schema["inputSchema"]
        ))
        
        return tools
    
    # Обработчик вызовов инструментов
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Выполняет запрошенный инструмент с заданными аргументами"""
        try:
            result = None
            
            if name == "semantic_search":
                result = await search_tool.execute(arguments)
            elif name == "get_methodology_context":
                result = await graph_tool.execute(arguments)
            elif name == "get_glossary_term":
                result = await glossary_tool.execute(arguments)
            elif name == "read_methodology_file":
                result = await files_tool.execute(arguments)
            elif name == "query_arangodb":
                result = await aql_tool.execute(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
            
            # Возвращаем результат в формате MCP
            return [TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            )]
            
        except Exception as e:
            # Логируем ошибку и возвращаем информативное сообщение
            import traceback
            error_details = {
                "error": str(e),
                "tool": name,
                "arguments": arguments,
                "traceback": traceback.format_exc()
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(error_details, ensure_ascii=False, indent=2)
            )]
    
    # Запускаем через stdio (универсальный протокол)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
