#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone normalizer для outline.yaml (применяет Quality Gate fixes)
"""
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_and_validate(outline: Dict[str, Any]) -> Dict[str, Any]:
    """
    Постпроцессинг outline: нормализация + валидация под B_QUALITY_GATE
    """
    structure = outline.get('structure', {})
    
    # 1. Фильтрация stages (удаляем placeholder'ы и пустые descriptions)
    stages = structure.get('stages', [])
    valid_stages = []
    for stage in stages:
        title = (stage.get('title') or '').strip()
        desc = (stage.get('description') or '').strip()
        
        # Пропускаем placeholder'ы
        if title in ['Шаг 1', 'Шаг 2', 'Шаг 3', 'Шаг 4', 'Этап 1', 'Этап 2']:
            logger.warning(f"⚠️ Пропущен placeholder stage: {title}")
            continue
        
        # Пропускаем пустые descriptions
        if len(desc) < 15:
            logger.warning(f"⚠️ Пропущен stage с коротким description: {title}")
            continue
        
        valid_stages.append(stage)
    
    # 2. Перенумерация stages (1..N)
    for i, stage in enumerate(valid_stages, 1):
        stage['order'] = i
    
    # 3. Фильтрация indicators (удаляем пустые descriptions) + дедупликация
    indicators = structure.get('indicators', [])
    valid_indicators = []
    seen_names = set()
    
    for ind in indicators:
        desc = (ind.get('description') or '').strip()
        
        if len(desc) < 10:
            logger.warning(f"⚠️ Пропущен indicator с пустым description: {ind.get('name')}")
            continue
        
        # Дедупликация по normalized name
        name = (ind.get('name') or '').strip().lower()
        name = re.sub(r'\s+', ' ', name)
        
        if name in seen_names:
            logger.warning(f"⚠️ Пропущен дубликат indicator: {ind.get('name')}")
            continue
        
        seen_names.add(name)
        
        # Нормализация formula: '' → None
        if ind.get('formula') == '':
            ind['formula'] = None
        
        valid_indicators.append(ind)
    
    # 4. Нормализация severity в rules
    SEVERITY_MAP = {
        'high': 'critical',
        'medium': 'warning',
        'low': 'info'
    }
    
    rules = structure.get('rules', [])
    for rule in rules:
        sev = rule.get('severity', 'info')
        rule['severity'] = SEVERITY_MAP.get(sev, sev)
    
    # 5. Обновляем структуру
    outline['structure'] = {
        'stages': valid_stages,
        'tools': structure.get('tools', []),
        'indicators': valid_indicators,
        'rules': rules
    }
    
    logger.info(f"✅ Нормализация: {len(valid_stages)} stages, {len(valid_indicators)} indicators")
    
    return outline


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python normalize_outline.py <input_outline.yaml> [output_outline.yaml]")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.parent / f"{input_path.stem}_normalized.yaml"
    
    # Загрузка
    outline = yaml.safe_load(input_path.read_text(encoding='utf-8'))
    
    # Нормализация
    normalized = normalize_and_validate(outline)
    
    # Сохранение
    output_path.write_text(yaml.dump(normalized, allow_unicode=True, sort_keys=False), encoding='utf-8')
    
    print(f"✅ Normalized outline saved to: {output_path}")
