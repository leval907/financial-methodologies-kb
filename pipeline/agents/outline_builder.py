#!/usr/bin/env python3
"""
Agent B: Outline Builder

ВХОД:
  sources/<book_id>/raw_text.md    - Извлеченный текст книги
  sources/<book_id>/metadata.json  - Метаданные файла

ВЫХОД:
  work/<methodology_id>/outline.yaml - Структура методологии
  work/<methodology_id>/sections.json - Извлеченные секции
  work/<methodology_id>/metadata.json - Метаданные обработки

ЗАДАЧИ:
  1. Классифицировать тип методологии (diagnostic, planning, analysis)
  2. Извлечь ключевые секции
  3. Найти indicators, rules, concepts
  4. Сопоставить с glossary
  5. Создать outline.yaml для Agent C
"""

import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class Section:
    """Секция документа"""
    title: str
    content: str
    start_line: int
    end_line: int
    level: int  # 1=chapter, 2=section, 3=subsection
    type: str  # 'concept', 'tool', 'indicator', 'rule', 'example'


@dataclass
class Indicator:
    """Финансовый индикатор"""
    name: str
    formula: Optional[str]
    unit: Optional[str]
    context: str  # Контекст из книги
    glossary_match: Optional[str]  # Найденный термин из glossary


@dataclass
class Rule:
    """Правило/рекомендация"""
    description: str
    condition: Optional[str]
    action: str
    context: str
    priority: str  # 'high', 'medium', 'low'


@dataclass
class Outline:
    """Структура методологии"""
    methodology_id: str
    title: str
    category: str  # cash_flow, profitability, working_capital, etc
    level: str  # strategic, tactical, operational
    
    source_book: str
    extraction_date: str
    
    # Основные компоненты
    overview: str
    key_concepts: List[str]
    indicators: List[Dict]
    rules: List[Dict]
    stages: List[Dict]
    
    # Связи с glossary
    glossary_matches: Dict[str, str]
    
    # Метаданные
    confidence: float  # 0-1, насколько уверены в классификации
    notes: List[str]


class OutlineBuilder:
    """Строитель структуры методологии"""
    
    def __init__(self, glossary_dir: Path = Path('data/glossary')):
        self.glossary_dir = glossary_dir
        self.glossary_terms = self._load_glossary()
    
    def _load_glossary(self) -> Dict[str, Any]:
        """Загрузить термины из glossary"""
        terms = {}
        
        if not self.glossary_dir.exists():
            print(f"⚠️ Glossary directory not found: {self.glossary_dir}")
            return terms
        
        for yaml_file in self.glossary_dir.glob('*.yaml'):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    term_data = yaml.safe_load(f)
                    term_id = yaml_file.stem
                    terms[term_id] = term_data
            except Exception as e:
                print(f"⚠️ Failed to load {yaml_file}: {e}")
        
        print(f"✅ Loaded {len(terms)} glossary terms")
        return terms
    
    def build(self, book_id: str, methodology_id: str) -> Outline:
        """
        Построить outline из извлеченного текста
        
        Args:
            book_id: ID обработанной книги (из sources/)
            methodology_id: ID создаваемой методологии
        
        Returns:
            Outline со структурой методологии
        """
        
        # Читаем входные данные
        sources_dir = Path('sources') / book_id
        raw_text_file = sources_dir / 'raw_text.md'
        metadata_file = sources_dir / 'metadata.json'
        
        if not raw_text_file.exists():
            raise FileNotFoundError(f"Raw text not found: {raw_text_file}")
        
        text = raw_text_file.read_text(encoding='utf-8')
        metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}
        
        print(f"📖 Processing: {book_id}")
        print(f"   Text length: {len(text)} chars")
        print(f"   Lines: {len(text.splitlines())}")
        
        # 1. Извлекаем секции
        sections = self._extract_sections(text)
        print(f"   Sections: {len(sections)}")
        
        # 2. Классифицируем методологию
        category, level = self._classify_methodology(text, sections)
        print(f"   Category: {category}, Level: {level}")
        
        # 3. Извлекаем индикаторы
        indicators = self._extract_indicators(text, sections)
        print(f"   Indicators: {len(indicators)}")
        
        # 4. Извлекаем правила
        rules = self._extract_rules(text, sections)
        print(f"   Rules: {len(rules)}")
        
        # 5. Определяем ключевые концепции
        key_concepts = self._extract_concepts(text, sections)
        print(f"   Concepts: {len(key_concepts)}")
        
        # 6. Сопоставляем с glossary
        glossary_matches = self._match_glossary(text, indicators, key_concepts)
        print(f"   Glossary matches: {len(glossary_matches)}")
        
        # 7. Извлекаем этапы (stages)
        stages = self._extract_stages(sections)
        print(f"   Stages: {len(stages)}")
        
        # 8. Создаём overview
        overview = self._generate_overview(text, sections)
        
        # Собираем outline
        outline = Outline(
            methodology_id=methodology_id,
            title=self._extract_title(text, metadata),
            category=category,
            level=level,
            source_book=book_id,
            extraction_date=datetime.now().isoformat(),
            overview=overview,
            key_concepts=key_concepts,
            indicators=[asdict(ind) for ind in indicators],
            rules=[asdict(rule) for rule in rules],
            stages=stages,
            glossary_matches=glossary_matches,
            confidence=0.8,  # TODO: вычислять автоматически
            notes=[
                "Auto-generated by Agent B",
                f"Source: {metadata.get('source_file', 'unknown')}",
                f"Method: {metadata.get('method', 'unknown')}"
            ]
        )
        
        return outline
    
    def _extract_sections(self, text: str) -> List[Section]:
        """Извлечь секции по заголовкам"""
        sections = []
        lines = text.splitlines()
        
        current_section = None
        current_content = []
        
        for i, line in enumerate(lines, 1):
            # Определяем уровень заголовка
            level = None
            title = None
            
            if line.startswith('# '):
                level, title = 1, line[2:].strip()
            elif line.startswith('## '):
                level, title = 2, line[3:].strip()
            elif line.startswith('### '):
                level, title = 3, line[4:].strip()
            
            if level:
                # Сохраняем предыдущую секцию
                if current_section:
                    current_section.content = '\n'.join(current_content)
                    current_section.end_line = i - 1
                    sections.append(current_section)
                
                # Начинаем новую секцию
                current_section = Section(
                    title=title,
                    content='',
                    start_line=i,
                    end_line=i,
                    level=level,
                    type='unknown'
                )
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Сохраняем последнюю секцию
        if current_section:
            current_section.content = '\n'.join(current_content)
            current_section.end_line = len(lines)
            sections.append(current_section)
        
        return sections
    
    def _classify_methodology(self, text: str, sections: List[Section]) -> tuple:
        """Классифицировать методологию"""
        
        text_lower = text.lower()
        
        # Категория
        categories = {
            'cash_flow': ['денежный поток', 'cash flow', 'оборотный капитал'],
            'profitability': ['прибыль', 'рентабельность', 'profit', 'margin'],
            'working_capital': ['оборотный капитал', 'working capital', 'запасы'],
            'costs': ['затраты', 'расходы', 'costs', 'expenses'],
            'pricing': ['цена', 'pricing', 'ценообразование'],
        }
        
        category_scores = {}
        for cat, keywords in categories.items():
            score = sum(text_lower.count(kw) for kw in keywords)
            category_scores[cat] = score
        
        category = max(category_scores, key=category_scores.get)
        
        # Уровень
        if any(kw in text_lower for kw in ['стратегия', 'strategy', 'долгосрочн']):
            level = 'strategic'
        elif any(kw in text_lower for kw in ['метрика', 'indicator', 'kpi', 'показатель']):
            level = 'tactical'
        else:
            level = 'operational'
        
        return category, level
    
    def _extract_indicators(self, text: str, sections: List[Section]) -> List[Indicator]:
        """Извлечь финансовые индикаторы"""
        indicators = []
        
        # Простой паттерн: ищем формулы и числовые выражения
        lines = text.splitlines()
        for i, line in enumerate(lines):
            # Ищем формулы: "ROI = ..."
            if '=' in line and any(c.isupper() for c in line):
                parts = line.split('=', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    formula = parts[1].strip()
                    
                    # Ищем единицы измерения
                    unit = None
                    if '%' in formula:
                        unit = 'percent'
                    elif 'руб' in formula.lower() or 'rub' in formula.lower():
                        unit = 'rub'
                    
                    # Контекст (3 строки до и после)
                    context_lines = lines[max(0, i-3):min(len(lines), i+4)]
                    context = '\n'.join(context_lines)
                    
                    # Сопоставление с glossary
                    glossary_match = self._find_glossary_match(name)
                    
                    indicators.append(Indicator(
                        name=name,
                        formula=formula if len(formula) < 200 else formula[:200] + '...',
                        unit=unit,
                        context=context[:300],
                        glossary_match=glossary_match
                    ))
        
        return indicators[:50]  # Максимум 50 индикаторов
    
    def _extract_rules(self, text: str, sections: List[Section]) -> List[Rule]:
        """Извлечь правила и рекомендации"""
        rules = []
        
        # Ищем императивные конструкции
        rule_keywords = [
            'должен', 'необходимо', 'рекомендуется', 'следует',
            'важно', 'критично', 'нужно', 'требуется'
        ]
        
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in rule_keywords):
                # Определяем приоритет
                priority = 'high' if any(w in line.lower() for w in ['критично', 'важно', 'обязательно']) else 'medium'
                
                # Контекст
                context_lines = lines[max(0, i-2):min(len(lines), i+3)]
                context = '\n'.join(context_lines)
                
                rules.append(Rule(
                    description=line.strip(),
                    condition=None,  # TODO: извлекать условия
                    action=line.strip(),
                    context=context[:200],
                    priority=priority
                ))
        
        return rules[:30]  # Максимум 30 правил
    
    def _extract_concepts(self, text: str, sections: List[Section]) -> List[str]:
        """Извлечь ключевые концепции"""
        concepts = []
        
        # Ищем термины в заголовках секций
        for section in sections:
            if section.level <= 2:  # Только главные заголовки
                concepts.append(section.title)
        
        # Добавляем термины из glossary, если встречаются
        for term_id, term_data in self.glossary_terms.items():
            term_title = term_data.get('title', term_id)
            if term_title.lower() in text.lower():
                concepts.append(term_title)
        
        return list(set(concepts))[:20]  # Уникальные, максимум 20
    
    def _match_glossary(self, text: str, indicators: List[Indicator], 
                       concepts: List[str]) -> Dict[str, str]:
        """Сопоставить с glossary"""
        matches = {}
        
        text_lower = text.lower()
        
        for term_id, term_data in self.glossary_terms.items():
            term_title = term_data.get('title', term_id).lower()
            
            if term_title in text_lower:
                matches[term_id] = term_data.get('title', term_id)
        
        return matches
    
    def _find_glossary_match(self, name: str) -> Optional[str]:
        """Найти соответствие в glossary"""
        name_lower = name.lower()
        
        for term_id, term_data in self.glossary_terms.items():
            term_title = term_data.get('title', '').lower()
            if name_lower in term_title or term_title in name_lower:
                return term_id
        
        return None
    
    def _extract_stages(self, sections: List[Section]) -> List[Dict]:
        """Извлечь этапы методологии"""
        stages = []
        
        # Ищем секции с последовательностью (шаг 1, этап 1, etc)
        stage_keywords = ['шаг', 'этап', 'step', 'stage', 'фаза']
        
        for section in sections:
            if any(kw in section.title.lower() for kw in stage_keywords):
                stages.append({
                    'title': section.title,
                    'description': section.content[:200] + '...' if len(section.content) > 200 else section.content,
                    'order': len(stages) + 1
                })
        
        return stages
    
    def _generate_overview(self, text: str, sections: List[Section]) -> str:
        """Сгенерировать краткое описание"""
        # Берем первую секцию или первые 500 символов
        if sections:
            return sections[0].content[:500] + '...'
        else:
            return text[:500] + '...'
    
    def _extract_title(self, text: str, metadata: Dict) -> str:
        """Извлечь название методологии"""
        lines = text.splitlines()
        
        # Ищем первый заголовок
        for line in lines[:20]:
            if line.startswith('# '):
                return line[2:].strip()
        
        # Fallback: из имени файла
        return metadata.get('source_file', 'Unknown').split('/')[-1]
    
    def save(self, outline: Outline, output_dir: Path):
        """Сохранить outline"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Сохраняем outline.yaml
        outline_file = output_dir / 'outline.yaml'
        outline_dict = asdict(outline)
        
        with open(outline_file, 'w', encoding='utf-8') as f:
            yaml.dump(outline_dict, f, allow_unicode=True, sort_keys=False)
        
        print(f"✅ Saved outline: {outline_file}")
        
        # 2. Сохраняем metadata.json
        metadata_file = output_dir / 'metadata.json'
        metadata = {
            'methodology_id': outline.methodology_id,
            'source_book': outline.source_book,
            'extraction_date': outline.extraction_date,
            'confidence': outline.confidence,
            'agent': 'Agent B: Outline Builder',
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved metadata: {metadata_file}")
        
        return {
            'outline_file': str(outline_file),
            'metadata_file': str(metadata_file),
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Agent B: Build methodology outline from extracted text'
    )
    parser.add_argument('book_id', type=str, help='Book ID (from sources/)')
    parser.add_argument('--methodology-id', type=str, required=True,
                       help='Methodology ID to create')
    parser.add_argument('--output-dir', type=Path, default=None,
                       help='Output directory (default: work/<methodology_id>/)')
    
    args = parser.parse_args()
    
    # Определяем output_dir
    if args.output_dir is None:
        args.output_dir = Path('work') / args.methodology_id
    
    try:
        builder = OutlineBuilder()
        outline = builder.build(args.book_id, args.methodology_id)
        
        result = builder.save(outline, args.output_dir)
        
        print(f"\n✅ Agent B completed!")
        print(f"   Methodology: {outline.methodology_id}")
        print(f"   Category: {outline.category}")
        print(f"   Indicators: {len(outline.indicators)}")
        print(f"   Rules: {len(outline.rules)}")
        print(f"   Concepts: {len(outline.key_concepts)}")
        print(f"   Glossary matches: {len(outline.glossary_matches)}")
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
