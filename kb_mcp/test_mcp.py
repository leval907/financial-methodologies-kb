#!/usr/bin/env python3
"""
Тестирование MCP Server
Проверяет работу всех инструментов
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env", override=True)
load_dotenv(project_root / ".env.qdrant", override=True)
load_dotenv(project_root / ".env.arango", override=True)

from mcp.tools.search import QdrantSearchTool
from mcp.tools.graph import ArangoGraphTool
from mcp.tools.glossary import GlossaryTool
from mcp.tools.files import FilesystemTool


async def test_semantic_search():
    """Тест 1: Semantic Search (Qdrant)"""
    print("\n" + "="*60)
    print("🔍 ТЕСТ 1: Semantic Search (Qdrant)")
    print("="*60)
    
    tool = QdrantSearchTool()
    
    try:
        result = await tool.execute({
            "query": "бюджетирование",
            "top_k": 3,
            "methodology_id": "budgeting-step-by-step"
        })
        
        print(f"✅ Запрос: 'бюджетирование'")
        print(f"✅ Коллекция: {result.get('collection', 'N/A')}")
        print(f"✅ Найдено результатов: {result.get('total_results', 0)}")
        
        if result.get('results'):
            print(f"\n📄 Топ результат:")
            top = result['results'][0]
            print(f"   Score: {top['score']}")
            print(f"   Text: {top['text'][:150]}...")
            print(f"   Page: {top.get('page', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def test_methodology_context():
    """Тест 2: Methodology Context (ArangoDB)"""
    print("\n" + "="*60)
    print("🗄️ ТЕСТ 2: Methodology Context (ArangoDB)")
    print("="*60)
    
    tool = ArangoGraphTool()
    
    try:
        result = await tool.execute({
            "methodology_id": "budgeting-step-by-step",
            "include_stages": True,
            "include_indicators": True
        })
        
        if "error" in result:
            print(f"❌ Ошибка: {result['error']}")
            return False
        
        print(f"✅ Методология: {result['methodology']['name']}")
        print(f"✅ Stages: {result['stats']['total_stages']}")
        print(f"✅ Indicators: {result['stats']['total_indicators']}")
        
        if result.get('stages'):
            print(f"\n📊 Первые 3 этапа:")
            for stage in result['stages'][:3]:
                print(f"   {stage['order']}. {stage.get('name') or stage.get('title')}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def test_glossary():
    """Тест 3: Glossary Term (ArangoDB)"""
    print("\n" + "="*60)
    print("📖 ТЕСТ 3: Glossary Term (ArangoDB)")
    print("="*60)
    
    tool = GlossaryTool()
    
    try:
        result = await tool.execute({
            "term": "throughput",
            "language": "ru",
            "include_related": True
        })
        
        if "error" in result:
            print(f"⚠️ Термин не найден: {result.get('error')}")
            if result.get('suggestions'):
                print(f"💡 Предложения: {len(result['suggestions'])} терминов")
            return True  # Это ожидаемо, если термина нет
        
        print(f"✅ Термин: {result['term']}")
        print(f"✅ Определение: {result.get('definition', 'N/A')[:100]}...")
        print(f"✅ Формула: {result.get('formula', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def test_files():
    """Тест 4: Read Methodology File (FS)"""
    print("\n" + "="*60)
    print("📁 ТЕСТ 4: Read Methodology File (File System)")
    print("="*60)
    
    tool = FilesystemTool()
    
    try:
        result = await tool.execute({
            "methodology_id": "budgeting-step-by-step",
            "file_type": "outline"
        })
        
        if "error" in result:
            print(f"❌ Ошибка: {result['error']}")
            return False
        
        print(f"✅ Файл: {result.get('file_path', 'N/A')}")
        print(f"✅ Размер: {result.get('size_bytes', 0)} байт")
        
        content = result.get('content', '')
        if content:
            lines = content.split('\n')[:5]
            print(f"✅ Первые строки:")
            for line in lines:
                print(f"   {line[:70]}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def main():
    """Запуск всех тестов"""
    print("\n" + "🚀 " + "="*56)
    print("    MCP SERVER TESTING - Financial Methodologies KB")
    print("="*60)
    
    results = []
    
    # Тест 1: Semantic Search
    results.append(("Semantic Search", await test_semantic_search()))
    
    # Тест 2: Methodology Context
    results.append(("Methodology Context", await test_methodology_context()))
    
    # Тест 3: Glossary
    results.append(("Glossary Term", await test_glossary()))
    
    # Тест 4: Files
    results.append(("Read File", await test_files()))
    
    # Итоги
    print("\n" + "="*60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n{'✅' if passed == total else '⚠️'} Пройдено: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены! MCP Server готов к использованию.")
        print("\n📝 Следующий шаг:")
        print("   ./mcp/setup_clients.sh")
    else:
        print("\n⚠️ Некоторые тесты не прошли. Проверьте:")
        print("   - Qdrant работает: docker ps | grep qdrant")
        print("   - ArangoDB работает: docker ps | grep arango")
        print("   - .env файлы настроены правильно")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
