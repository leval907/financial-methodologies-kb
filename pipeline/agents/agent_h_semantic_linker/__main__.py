"""
CLI для запуска Agent H (Semantic Linker)

Примеры использования:
  # Тестовый прогон на 10 этапах (dry-run)
  python -m pipeline.agents.agent_h_semantic_linker toc --limit 10 --dry-run

  # Полная обработка всех этапов
  python -m pipeline.agents.agent_h_semantic_linker toc

  # С указанием модели
  python -m pipeline.agents.agent_h_semantic_linker toc --model alibaba/qwen-turbo
"""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем env переменные ПЕРВЫМ делом, до других импортов
# override=True чтобы перезаписать любые существующие переменные
load_dotenv('.env.arango', override=True)

# Теперь импортируем агента
from .semantic_linker import SemanticLinker


def main():
    parser = argparse.ArgumentParser(
        description='Agent H: Создание семантических связей через LLM'
    )
    
    parser.add_argument(
        'methodology_id',
        help='ID методологии в ArangoDB (например: toc)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Ограничить количество stages (для тестирования)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Не создавать edges, только показать что будет сделано'
    )
    
    parser.add_argument(
        '--model',
        default='alibaba/qwen3-max',
        help='Модель LLM (по умолчанию: alibaba/qwen3-max)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Сколько candidates показывать LLM за раз (по умолчанию: 50)'
    )
    
    parser.add_argument(
        '--arango-env',
        default='.env.arango',
        help='Путь к .env файлу с настройками ArangoDB'
    )
    
    args = parser.parse_args()
    
    # Проверяем что .env.arango существует
    if not Path(args.arango_env).exists():
        print(f"❌ Файл {args.arango_env} не найден!")
        print(f"   Создайте файл с настройками ArangoDB")
        sys.exit(1)
    
    # Создаем linker (env переменные уже загружены выше)
    try:
        linker = SemanticLinker(
            model=args.model,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        sys.exit(1)
    
    # Запускаем линкинг
    try:
        stats = linker.link_methodology(
            methodology_id=args.methodology_id,
            limit=args.limit
        )
        
        # Показываем итоги
        print("\n" + "="*60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("="*60)
        print(f"Stages обработано:     {stats['stages_processed']}")
        print(f"Indicators связано:    {stats['indicators_linked']}")
        print(f"Tools связано:         {stats['tools_linked']}")
        print(f"Rules связано:         {stats['rules_linked']}")
        print(f"Всего edges создано:   {stats['indicators_linked'] + stats['tools_linked'] + stats['rules_linked']}")
        print(f"LLM вызовов:           {stats['llm_calls']}")
        print(f"Токенов использовано:  {stats['total_tokens']:,}")
        print("="*60)
        
        if args.dry_run:
            print("\n⚠️  DRY RUN - edges не были созданы в БД")
            print("    Запустите без --dry-run для создания реальных связей")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка выполнения: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
