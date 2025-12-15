#!/usr/bin/env python3
"""
Обновление индикаторов в ArangoDB - добавление формул из YAML

Usage:
    python scripts/update_indicators_formulas.py --dry-run  # Просмотр
    python scripts/update_indicators_formulas.py            # Обновление
"""

import yaml
import os
import sys
from pathlib import Path
from arango import ArangoClient
from dotenv import load_dotenv
import argparse

# Загружаем .env
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env.arango', override=True)
load_dotenv(project_root / '.env', override=False)


def connect_arango():
    """Подключение к ArangoDB"""
    client = ArangoClient(hosts='http://localhost:8529')
    db = client.db(
        'fin_kb_method',
        username='root',
        password=os.getenv('ARANGO_PASSWORD', 'strongpassword')
    )
    return db


def update_budgeting_indicators(db, dry_run=False):
    """Обновление индикаторов для budgeting-step-by-step"""
    
    # Загружаем данные из YAML
    yaml_path = project_root / 'work' / 'budgeting-step-by-step' / 'outline_rag.yaml'
    if not yaml_path.exists():
        print(f"❌ Файл не найден: {yaml_path}")
        return 0
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    indicators_yaml = data.get('indicators', [])
    print(f"📊 Найдено индикаторов в YAML: {len(indicators_yaml)}")
    
    # Получаем индикаторы из базы
    query = """
    FOR i IN indicators
        FILTER i.book_id == 'budgeting-step-by-step'
        SORT i._key ASC
        RETURN {
            key: i._key,
            title: i.title,
            formula: i.formula,
            definition: i.definition
        }
    """
    indicators_db = list(db.aql.execute(query))
    print(f"📊 Найдено индикаторов в базе: {len(indicators_db)}")
    
    # Сопоставляем по названию и обновляем
    updated_count = 0
    indicators_col = db.collection('indicators')
    
    for ind_yaml in indicators_yaml:
        yaml_name = ind_yaml['name']
        yaml_formula = ind_yaml.get('formula', '')
        
        # Ищем соответствующий индикатор в базе по названию
        matching_db = None
        for ind_db in indicators_db:
            if ind_db['title'] == yaml_name:
                matching_db = ind_db
                break
        
        if not matching_db:
            print(f"⚠️  Не найден в базе: {yaml_name}")
            continue
        
        # Проверяем, нужно ли обновление
        if matching_db['formula'] is None and yaml_formula:
            print(f"✅ Обновление: {yaml_name}")
            print(f"   formula: {yaml_formula[:80]}...")
            
            if not dry_run:
                try:
                    indicators_col.update({
                        '_key': matching_db['key'],
                        'formula': yaml_formula
                    })
                    updated_count += 1
                except Exception as e:
                    print(f"   ❌ Ошибка обновления: {e}")
        else:
            if yaml_formula:
                print(f"⏭️  Уже есть формула: {yaml_name}")
            else:
                print(f"⚠️  Нет формулы в YAML: {yaml_name}")
    
    return updated_count


def main():
    parser = argparse.ArgumentParser(description='Обновление формул индикаторов в ArangoDB')
    parser.add_argument('--dry-run', action='store_true', help='Только просмотр, без обновления')
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔄 ОБНОВЛЕНИЕ ФОРМУЛ ИНДИКАТОРОВ В ARANGODB")
    print("=" * 70)
    
    if args.dry_run:
        print("🔍 РЕЖИМ ПРОСМОТРА (изменения не будут сохранены)")
    else:
        print("⚠️  РЕЖИМ ОБНОВЛЕНИЯ (изменения будут сохранены)")
    
    print()
    
    db = connect_arango()
    print(f"✅ Подключено к базе: {db.name}\n")
    
    # Обновляем индикаторы budgeting
    updated = update_budgeting_indicators(db, dry_run=args.dry_run)
    
    print("\n" + "=" * 70)
    if args.dry_run:
        print(f"📊 Будет обновлено: {updated} индикаторов")
        print("💡 Запустите без --dry-run для применения изменений")
    else:
        print(f"✅ Обновлено: {updated} индикаторов")
    print("=" * 70)


if __name__ == '__main__':
    main()
