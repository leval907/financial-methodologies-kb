#!/usr/bin/env python3
"""
Проверка качества ответов MCP инструментов
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env", override=True)
load_dotenv(project_root / ".env.qdrant", override=True)
load_dotenv(project_root / ".env.arango", override=True)

from mcp.tools.search import QdrantSearchTool
from mcp.tools.graph import ArangoGraphTool
from mcp.tools.glossary import GlossaryTool


async def test_qdrant_queries():
    """Тест разных запросов к Qdrant"""
    print("\n" + "="*70)
    print("🔍 ТЕСТИРОВАНИЕ SEMANTIC SEARCH (Qdrant)")
    print("="*70)
    
    tool = QdrantSearchTool()
    
    queries = [
        {
            "query": "как рассчитать точку безубыточности",
            "top_k": 3,
            "description": "Поиск про индикаторы"
        },
        {
            "query": "этап планирования бюджета",
            "top_k": 3,
            "description": "Поиск про конкретный этап"
        },
        {
            "query": "ограничения системы",
            "top_k": 3,
            "methodology_id": "toc-corbet",
            "description": "Поиск в другой книге (TOC)"
        },
        {
            "query": "постановка целей и KPI",
            "top_k": 2,
            "description": "Поиск про цели"
        }
    ]
    
    for i, query_params in enumerate(queries, 1):
        description = query_params.pop("description")
        print(f"\n{'─'*70}")
        print(f"📌 ЗАПРОС {i}: {description}")
        print(f"   Query: '{query_params['query']}'")
        if "methodology_id" in query_params:
            print(f"   Collection: {query_params['methodology_id']}")
        print(f"{'─'*70}")
        
        try:
            result = await tool.execute(query_params)
            
            if "error" in result:
                print(f"❌ Ошибка: {result['error']}")
                continue
            
            print(f"✅ Найдено: {result['total_results']} результатов")
            print(f"📚 Коллекция: {result['collection']}\n")
            
            for j, r in enumerate(result['results'], 1):
                print(f"  {j}. Score: {r['score']:.4f}")
                text = r['text'][:200].replace('\n', ' ')
                print(f"     Text: {text}...")
                if r.get('page'):
                    print(f"     Page: {r['page']}")
                print()
            
        except Exception as e:
            print(f"❌ Ошибка выполнения: {e}")


async def test_arango_queries():
    """Тест разных запросов к ArangoDB"""
    print("\n" + "="*70)
    print("🗄️ ТЕСТИРОВАНИЕ METHODOLOGY CONTEXT (ArangoDB)")
    print("="*70)
    
    tool = ArangoGraphTool()
    
    queries = [
        {
            "methodology_id": "budgeting-step-by-step",
            "include_stages": True,
            "include_indicators": False,
            "include_tools": True,
            "description": "Бюджетирование: этапы + инструменты"
        },
        {
            "methodology_id": "budgeting-step-by-step",
            "include_stages": False,
            "include_indicators": True,
            "description": "Бюджетирование: только индикаторы"
        }
    ]
    
    for i, query_params in enumerate(queries, 1):
        description = query_params.pop("description")
        print(f"\n{'─'*70}")
        print(f"📌 ЗАПРОС {i}: {description}")
        print(f"{'─'*70}")
        
        try:
            result = await tool.execute(query_params)
            
            if "error" in result:
                print(f"❌ Ошибка: {result['error']}")
                continue
            
            print(f"✅ Методология: {result['methodology']['name']}")
            print(f"📊 Статистика:")
            print(f"   - Этапов: {result['stats']['total_stages']}")
            print(f"   - Индикаторов: {result['stats']['total_indicators']}")
            print(f"   - Инструментов: {result['stats']['total_tools']}")
            print(f"   - Правил: {result['stats']['total_rules']}")
            
            if result.get('stages'):
                print(f"\n   🔹 Этапы ({len(result['stages'])}):")
                for stage in result['stages'][:5]:
                    title = stage.get('title') or stage.get('name')
                    desc = stage.get('description', '')[:80]
                    print(f"      {stage['order']}. {title}")
                    print(f"         {desc}...")
            
            if result.get('indicators'):
                print(f"\n   📈 Индикаторы ({len(result['indicators'])}):")
                for ind in result['indicators'][:5]:
                    name = ind.get('name', 'N/A')
                    formula = ind.get('formula', '')
                    print(f"      • {name}")
                    if formula:
                        print(f"        Формула: {formula[:60]}")
            
            if result.get('tools'):
                print(f"\n   🛠️  Инструменты ({len(result['tools'])}):")
                for tool_item in result['tools'][:5]:
                    name = tool_item.get('name', 'N/A')
                    purpose = tool_item.get('purpose', '')[:60]
                    print(f"      • {name}")
                    if purpose:
                        print(f"        {purpose}")
            
        except Exception as e:
            print(f"❌ Ошибка выполнения: {e}")


async def test_glossary_queries():
    """Тест поиска терминов в глоссарии"""
    print("\n" + "="*70)
    print("📖 ТЕСТИРОВАНИЕ GLOSSARY SEARCH (ArangoDB)")
    print("="*70)
    
    tool = GlossaryTool()
    
    terms = [
        {"term": "методология", "description": "Базовый термин"},
        {"term": "показатель", "description": "Измеримая характеристика"},
        {"term": "артефакт", "description": "Результат применения методологии"},
        {"term": "модел", "description": "Частичное совпадение (fuzzy search)"}
    ]
    
    for i, term_params in enumerate(terms, 1):
        description = term_params.pop("description")
        print(f"\n{'─'*70}")
        print(f"📌 ЗАПРОС {i}: {description}")
        print(f"   Термин: '{term_params['term']}'")
        print(f"{'─'*70}")
        
        try:
            result = await tool.execute(term_params)
            
            if "error" in result:
                print(f"⚠️  {result['error']}")
                if result.get('suggestions'):
                    print(f"\n   💡 Похожие термины:")
                    for sug in result['suggestions'][:3]:
                        print(f"      • {sug.get('term', 'N/A')}")
                continue
            
            print(f"✅ Термин найден: {result['term']}")
            print(f"\n   Определение:")
            print(f"   {result['definition'][:300]}")
            
            if result.get('formula'):
                print(f"\n   Формула: {result['formula']}")
            
            if result.get('aliases'):
                print(f"\n   Синонимы: {', '.join(result['aliases'])}")
            
            if result.get('related_terms'):
                print(f"\n   Связанные термины ({len(result['related_terms'])}):")
                for rel in result['related_terms'][:3]:
                    print(f"      • {rel.get('term', 'N/A')}: {rel.get('definition', '')[:60]}...")
            
        except Exception as e:
            print(f"❌ Ошибка выполнения: {e}")


async def main():
    """Запуск всех тестов"""
    print("\n" + "="*70)
    print("🚀 ТЕСТИРОВАНИЕ КАЧЕСТВА ОТВЕТОВ MCP SERVER")
    print("="*70)
    
    await test_qdrant_queries()
    await test_arango_queries()
    await test_glossary_queries()
    
    print("\n" + "="*70)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
