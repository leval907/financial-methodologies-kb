"""
Quality Metrics Calculator для Agent A

Подсчитывает метрики качества экстракции:
- text_density: доля страниц с текстом
- garbage_ratio: доля мусорных символов
- repeated_lines_ratio: колонтитулы, дубли
- table_extract_coverage: % извлеченных таблиц
- score: общая оценка 0-100

На основе score определяется routing:
- score >= 80: ok_for_outline
- 60-79: ok_with_warnings
- < 60: needs_repair
"""

import re
from collections import Counter
from typing import List, Dict


class QualityMetricsCalculator:
    """Калькулятор метрик качества экстракции"""
    
    @staticmethod
    def calculate(blocks: List[Dict], raw_text: str) -> Dict:
        """
        Подсчитать все метрики качества.
        
        Args:
            blocks: Список блоков из blocks_converter
            raw_text: Исходный markdown текст
            
        Returns:
            Dictionary с метриками и routing flags
        """
        # 1. Text density
        text_density = QualityMetricsCalculator._calculate_text_density(blocks)
        
        # 2. Garbage ratio
        garbage_ratio = QualityMetricsCalculator._calculate_garbage_ratio(raw_text)
        
        # 3. Repeated lines ratio
        repeated_lines_ratio = QualityMetricsCalculator._calculate_repeated_lines(blocks)
        
        # 4. Table extract coverage
        table_coverage = QualityMetricsCalculator._calculate_table_coverage(blocks, raw_text)
        
        # 5. Overall score
        score = QualityMetricsCalculator._calculate_score(
            text_density, garbage_ratio, repeated_lines_ratio, table_coverage
        )
        
        # 6. Routing flags
        routing = QualityMetricsCalculator._determine_routing(score)
        
        # 7. Warnings
        warnings = QualityMetricsCalculator._generate_warnings(
            text_density, garbage_ratio, repeated_lines_ratio, table_coverage
        )
        
        return {
            'score': round(score, 2),
            'text_density': round(text_density, 3),
            'garbage_ratio': round(garbage_ratio, 3),
            'repeated_lines_ratio': round(repeated_lines_ratio, 3),
            'table_extract_coverage': round(table_coverage, 3),
            'routing': routing,
            'warnings': warnings
        }
    
    @staticmethod
    def _calculate_text_density(blocks: List[Dict]) -> float:
        """
        Text density = (страницы с контентом) / (всего страниц)
        
        Страница с контентом = страница с хотя бы одним non-page_break блоком
        """
        if not blocks:
            return 0.0
        
        # Найти все упоминания страниц
        all_pages = set()
        pages_with_text = set()
        
        for block in blocks:
            page = block['source']['page']
            all_pages.add(page)
            
            if block['type'] != 'page_break':
                pages_with_text.add(page)
        
        total_pages = max(all_pages) if all_pages else 1
        
        return len(pages_with_text) / total_pages if total_pages > 0 else 0.0
    
    @staticmethod
    def _calculate_garbage_ratio(raw_text: str) -> float:
        """
        Garbage ratio = (мусорные символы) / (всего символов)
        
        Мусорные символы: не буквы, не цифры, не пробелы, не пунктуация
        """
        if not raw_text:
            return 0.0
        
        total_chars = len(raw_text)
        
        # Допустимые символы: буквы, цифры, пробелы, стандартная пунктуация
        allowed_pattern = r'[\w\s\.\,\:\;\-\!\?\(\)\[\]\{\}\"\'\`\n\r\t\=\+\*\/\%\|\#]'
        
        # Считаем допустимые символы
        allowed_chars = len(re.findall(allowed_pattern, raw_text, re.UNICODE))
        
        # Мусорные символы = все остальные
        garbage_chars = total_chars - allowed_chars
        
        return garbage_chars / total_chars if total_chars > 0 else 0.0
    
    @staticmethod
    def _calculate_repeated_lines(blocks: List[Dict]) -> float:
        """
        Repeated lines ratio = (повторяющиеся строки) / (всего строк)
        
        Повторяющиеся строки обычно это:
        - Колонтитулы (header/footer)
        - Номера страниц
        - Watermarks
        """
        # Собираем все paragraph и heading блоки
        text_blocks = [
            block['text'].strip() 
            for block in blocks 
            if block['type'] in ['paragraph', 'heading'] and block['text'].strip()
        ]
        
        if not text_blocks:
            return 0.0
        
        # Считаем частоту каждой строки
        line_counts = Counter(text_blocks)
        
        # Повторяющиеся = встречаются > 1 раза
        repeated_lines = sum(count - 1 for count in line_counts.values() if count > 1)
        
        return repeated_lines / len(text_blocks) if text_blocks else 0.0
    
    @staticmethod
    def _calculate_table_coverage(blocks: List[Dict], raw_text: str) -> float:
        """
        Table extract coverage = (извлечено таблиц) / (детектировано таблиц)
        
        Детектируем таблицы в raw_text по паттернам:
        - Markdown tables (|---|---|)
        - Aligned data (много пробелов/табов)
        """
        # Извлеченные таблицы
        extracted_tables = len([b for b in blocks if b['type'] == 'table'])
        
        # Детектируем таблицы в raw_text
        # 1. Markdown tables
        markdown_tables = len(re.findall(r'\|.+\|', raw_text))
        
        # 2. Табличные структуры (3+ подряд строк с табуляциями/множественными пробелами)
        lines = raw_text.split('\n')
        aligned_tables = 0
        consecutive_aligned = 0
        
        for line in lines:
            # Строка выровнена если содержит 3+ группы пробелов (5+ пробелов подряд)
            if re.search(r'\s{5,}', line):
                consecutive_aligned += 1
            else:
                if consecutive_aligned >= 3:
                    aligned_tables += 1
                consecutive_aligned = 0
        
        # Финализируем последнюю группу
        if consecutive_aligned >= 3:
            aligned_tables += 1
        
        detected_tables = markdown_tables + aligned_tables
        
        if detected_tables == 0:
            # Нет таблиц - coverage 100%
            return 1.0
        
        # Coverage = извлечено / детектировано (max 1.0)
        return min(extracted_tables / detected_tables, 1.0)
    
    @staticmethod
    def _calculate_score(
        text_density: float,
        garbage_ratio: float,
        repeated_lines_ratio: float,
        table_coverage: float
    ) -> float:
        """
        Общий score по формуле:
        
        score = 100
            - garbage_ratio * 200          (штраф x2 - критично)
            - repeated_lines_ratio * 100   (штраф x1 - важно)
            - (1 - text_density) * 80      (штраф x0.8 - важно)
            - (1 - table_coverage) * 40    (штраф x0.4 - средне)
        
        Результат: 0-100
        """
        score = 100.0
        score -= garbage_ratio * 200
        score -= repeated_lines_ratio * 100
        score -= (1 - text_density) * 80
        score -= (1 - table_coverage) * 40
        
        # Clamp to 0-100
        return max(0.0, min(100.0, score))
    
    @staticmethod
    def _determine_routing(score: float) -> Dict:
        """
        Определить routing flags на основе score.
        
        - score >= 80: ok_for_outline (отлично)
        - 60-79: ok_with_warnings (приемлемо с оговорками)
        - < 60: needs_repair (требуется OCR/AI-clean)
        """
        return {
            'ok_for_outline': score >= 80,
            'ok_with_warnings': 60 <= score < 80,
            'needs_repair': score < 60
        }
    
    @staticmethod
    def _generate_warnings(
        text_density: float,
        garbage_ratio: float,
        repeated_lines_ratio: float,
        table_coverage: float
    ) -> List[str]:
        """Генерация предупреждений на основе метрик"""
        warnings = []
        
        if text_density < 0.5:
            warnings.append(f"⚠️ Low text density ({text_density:.1%}): many empty pages")
        
        if garbage_ratio > 0.05:
            warnings.append(f"⚠️ High garbage ratio ({garbage_ratio:.1%}): encoding issues or binary data")
        
        if repeated_lines_ratio > 0.2:
            warnings.append(f"⚠️ Many repeated lines ({repeated_lines_ratio:.1%}): headers/footers not filtered")
        
        if table_coverage < 0.8:
            warnings.append(f"⚠️ Poor table extraction ({table_coverage:.1%}): complex tables lost")
        
        return warnings


if __name__ == '__main__':
    # Test
    test_blocks = [
        {'id': 'block_0001', 'type': 'heading', 'text': 'Chapter 1', 'source': {'page': 1, 'file': 'test.md'}, 'meta': {'level': 1}},
        {'id': 'block_0002', 'type': 'paragraph', 'text': 'Some text', 'source': {'page': 1, 'file': 'test.md'}, 'meta': {}},
        {'id': 'block_0003', 'type': 'table', 'text': '| A | B |\n|---|---|\n| 1 | 2 |', 'source': {'page': 2, 'file': 'test.md'}, 'meta': {'rows': 2, 'cols': 2}},
        {'id': 'block_0004', 'type': 'page_break', 'text': '', 'source': {'page': 3, 'file': 'test.md'}, 'meta': {}},
    ]
    
    test_raw = "# Chapter 1\n\nSome text\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    
    metrics = QualityMetricsCalculator.calculate(test_blocks, test_raw)
    
    print("📊 Quality Metrics:")
    print(f"  Score: {metrics['score']}")
    print(f"  Text density: {metrics['text_density']}")
    print(f"  Garbage ratio: {metrics['garbage_ratio']}")
    print(f"  Repeated lines: {metrics['repeated_lines_ratio']}")
    print(f"  Table coverage: {metrics['table_extract_coverage']}")
    print(f"  Routing: {metrics['routing']}")
    if metrics['warnings']:
        print(f"  Warnings: {metrics['warnings']}")
