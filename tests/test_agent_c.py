#!/usr/bin/env python3
"""
Тест Agent C: Methodology Compiler
Компилирует outline.yaml → markdown документацию.

Использование:
    python tests/test_agent_c.py
"""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.agents.agent_c import MethodologyCompiler

# Пути
PROJECT_ROOT = Path(__file__).parent.parent
OUTLINE_PATH = PROJECT_ROOT / "work" / "accounting-basics-test" / "outline.yaml"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "methodologies"
METHODOLOGY_ID = "accounting-basics"


def main():
    """Тестирование Agent C."""
    
    print("="*60)
    print("ТЕСТ Agent C: Methodology Compiler")
    print("="*60)
    
    # Проверка существования outline.yaml
    if not OUTLINE_PATH.exists():
        print(f"❌ Outline не найден: {OUTLINE_PATH}")
        print("→ Сначала запустите: python tests/test_agent_b.py")
        sys.exit(1)
    
    print(f"\n📋 Входные данные:")
    print(f"  Outline: {OUTLINE_PATH}")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  ID: {METHODOLOGY_ID}")
    
    # Получение credentials
    gigachat_key = os.getenv('GIGACHAT_CREDENTIALS')
    requesty_key = os.getenv('REQUESTY_API_KEY')
    
    if not gigachat_key and not requesty_key:
        print("\n⚠️  Предупреждение: Нет API ключей!")
        print("   Set GIGACHAT_CREDENTIALS or REQUESTY_API_KEY")
        print("\n   Примеры:")
        print("   export GIGACHAT_CREDENTIALS='your_key'")
        print("   export REQUESTY_API_KEY='your_key'")
        sys.exit(1)
    
    if gigachat_key:
        print(f"\n✅ GigaChat credentials: {gigachat_key[:20]}...")
    if requesty_key:
        print(f"✅ Requesty API key: {requesty_key[:20]}...")
    
    # Создание компилятора
    print("\n📦 Инициализация Agent C...")
    compiler = MethodologyCompiler(
        gigachat_credentials=gigachat_key,
        requesty_api_key=requesty_key,
        use_gigachat=True  # GigaChat Lite как primary
    )
    
    # Компиляция методологии
    print("\n🚀 Запуск компиляции...")
    print("-"*60)
    
    stats = compiler.compile_methodology(
        outline_path=OUTLINE_PATH,
        output_dir=OUTPUT_DIR,
        methodology_id=METHODOLOGY_ID
    )
    
    # Итоги
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТА")
    print("="*60)
    
    print(f"\n✅ Создано файлов: {stats['generated_files']}")
    print(f"📋 Этапов: {stats['total_stages']}")
    print(f"🛠 Инструментов: {stats['total_tools']}")
    print(f"📊 Показателей: {stats['total_indicators']}")
    
    if stats['errors']:
        print(f"\n⚠️  Ошибок: {len(stats['errors'])}")
        for error in stats['errors'][:5]:  # Показываем первые 5
            print(f"  - {error}")
        if len(stats['errors']) > 5:
            print(f"  ... и еще {len(stats['errors']) - 5} ошибок")
    
    # Проверка созданных файлов
    methodology_dir = OUTPUT_DIR / METHODOLOGY_ID
    if methodology_dir.exists():
        print(f"\n📁 Структура документации:")
        print(f"\n{methodology_dir}/")
        
        # README
        readme = methodology_dir / "README.md"
        if readme.exists():
            print(f"  ✅ README.md ({readme.stat().st_size} bytes)")
        
        # Stages
        stages_dir = methodology_dir / "stages"
        if stages_dir.exists():
            stage_files = list(stages_dir.glob("*.md"))
            print(f"  ✅ stages/ ({len(stage_files)} files)")
            for f in stage_files[:3]:
                print(f"     - {f.name}")
            if len(stage_files) > 3:
                print(f"     ... и еще {len(stage_files) - 3} файлов")
        
        # Tools
        tools_dir = methodology_dir / "tools"
        if tools_dir.exists():
            tool_files = list(tools_dir.glob("*.md"))
            if tool_files:
                print(f"  ✅ tools/ ({len(tool_files)} files)")
        
        # Indicators
        indicators_dir = methodology_dir / "indicators"
        if indicators_dir.exists():
            indicator_files = list(indicators_dir.glob("*.md"))
            if indicator_files:
                print(f"  ✅ indicators/ ({len(indicator_files)} files)")
    
    # YAML data
    data_path = PROJECT_ROOT / "data" / "methodologies" / f"{METHODOLOGY_ID}.yaml"
    if data_path.exists():
        print(f"\n💾 YAML данные: {data_path}")
        print(f"   Размер: {data_path.stat().st_size} bytes")
    
    print("\n" + "="*60)
    
    # Exit code
    if stats['errors']:
        print("⚠️  Тест завершен с ошибками")
        sys.exit(1)
    else:
        print("✅ Тест успешно завершен!")
        sys.exit(0)


if __name__ == "__main__":
    main()
