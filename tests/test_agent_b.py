#!/usr/bin/env python3
"""
Тест Agent B на accounting-basics
"""

import os
import sys
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Добавляем родительскую директорию в PATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.agents import OutlineBuilder

# GigaChat credentials из другого проекта
GIGACHAT_KEY = os.getenv('GIGACHAT_API_KEY') or 'MDE5YWM4ZGQtNDkzNS03ZTI3LWIzODEtZWRlN2Q3ZmEyYjE2OmJhMjZjZDExLTQzMjYtNDYwZC1hMTZlLWQzZTEwZDVhYzA4Zg=='

print("="*70)
print("🧪 Тест Agent B: Outline Builder")
print("="*70)
print()

# Путь к blocks.jsonl
blocks_path = Path('sources/accounting-basics-test/extracted/blocks.jsonl')

if not blocks_path.exists():
    print(f"❌ Файл не найден: {blocks_path}")
    sys.exit(1)

print(f"📂 Входной файл: {blocks_path}")
print()

# Инициализируем Agent B
print("🤖 Инициализация Agent B...")
agent = OutlineBuilder(
    gigachat_credentials=GIGACHAT_KEY,
    use_gigachat=True  # GigaChat PRIMARY, Qwen3-Max FALLBACK
)
print()

# Строим outline
try:
    outline = agent.build_outline(blocks_path)
    
    # Сохраняем результат
    output_dir = Path('work/accounting-basics-test')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_yaml = output_dir / 'outline.yaml'
    output_json = output_dir / 'outline.json'
    
    # Сохраняем в YAML
    with open(output_yaml, 'w', encoding='utf-8') as f:
        yaml.dump(outline, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    
    # Сохраняем в JSON (для отладки)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(outline, f, ensure_ascii=False, indent=2)
    
    print()
    print("="*70)
    print("✅ РЕЗУЛЬТАТЫ")
    print("="*70)
    print()
    print(f"📊 Методология: {outline['classification']['methodology_type']}")
    print(f"📖 Обработано глав: {outline['metadata']['chapters_processed']}")
    print(f"🔧 Модель: {outline['metadata']['model_used']}")
    print()
    print(f"📋 Извлечено:")
    print(f"   - Stages: {len(outline['structure']['stages'])}")
    print(f"   - Tools: {len(outline['structure']['tools'])}")
    print(f"   - Indicators: {len(outline['structure']['indicators'])}")
    print(f"   - Rules: {len(outline['structure']['rules'])}")
    print()
    print(f"💾 Результаты сохранены:")
    print(f"   - {output_yaml}")
    print(f"   - {output_json}")
    print()
    
    # Показываем первые stages
    if outline['structure']['stages']:
        print("🎯 Первые 3 stage:")
        for i, stage in enumerate(outline['structure']['stages'][:3], 1):
            print(f"   {i}. {stage.get('title', 'Без названия')}")
            print(f"      {stage.get('description', '')[:80]}...")
        print()

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("="*70)
print("🎉 Тест завершен успешно!")
print("="*70)
