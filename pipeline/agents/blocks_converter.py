"""
Конвертация Markdown → blocks.jsonl

Этот модуль преобразует plain Markdown в структурированный формат blocks.jsonl,
где каждый блок имеет тип (heading, paragraph, table, formula, list) и метаданные.
"""

import re
import json
from typing import List, Dict, Optional
from pathlib import Path


class BlocksConverter:
    """Конвертер Markdown → blocks.jsonl"""
    
    def __init__(self, source_file: str):
        self.source_file = source_file
        self.blocks = []
        self.block_counter = 0
        self.current_page = 1
    
    def convert(self, markdown_text: str) -> List[Dict]:
        """
        Конвертировать Markdown текст в список блоков.
        
        Args:
            markdown_text: Markdown текст из markitdown
            
        Returns:
            List of block dictionaries
        """
        lines = markdown_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Page break detection
            if self._is_page_break(line):
                self.current_page += 1
                self._add_page_break()
                i += 1
                continue
            
            # Skip empty lines
            if not line.strip():
                i += 1
                continue
            
            # Heading (# ## ### ...)
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                self._add_heading(text, level)
                i += 1
                continue
            
            # Table (starts with |)
            if line.strip().startswith('|'):
                table_lines, consumed = self._collect_table(lines[i:])
                if table_lines:
                    self._add_table(table_lines)
                    i += consumed
                    continue
            
            # List (ordered or unordered)
            if self._is_list_item(line):
                list_lines, consumed = self._collect_list(lines[i:])
                if list_lines:
                    self._add_list(list_lines)
                    i += consumed
                    continue
            
            # Formula detection (contains = and math symbols)
            if self._is_formula(line):
                self._add_formula(line.strip())
                i += 1
                continue
            
            # Default: paragraph
            self._add_paragraph(line.strip())
            i += 1
        
        return self.blocks
    
    def _is_page_break(self, line: str) -> bool:
        """Проверка на page break"""
        return line.strip() in ['\f', '---PAGE-BREAK---', '<!-- PAGE BREAK -->']
    
    def _is_list_item(self, line: str) -> bool:
        """Проверка на элемент списка"""
        stripped = line.strip()
        return (
            re.match(r'^\d+\.\s+', stripped) is not None or  # 1. 2. 3.
            stripped.startswith('- ') or
            stripped.startswith('* ') or
            stripped.startswith('+ ')
        )
    
    def _is_formula(self, line: str) -> bool:
        """
        Эвристика для определения формулы.
        
        Формула если:
        - Содержит знак =
        - Содержит математические операторы (+, -, *, /)
        - Содержит переменные (заглавные буквы или термины)
        """
        # Игнорируем если это просто текст с =
        if '=' not in line:
            return False
        
        # Проверяем наличие математических операторов или переменных
        has_math = bool(re.search(r'[\+\-\*/\(\)\[\]]', line))
        has_variables = bool(re.search(r'[A-Z][A-Za-z]*\s*=', line))  # ROI = ...
        
        return has_math or has_variables
    
    def _collect_table(self, lines: List[str]) -> tuple[List[str], int]:
        """Собрать все строки таблицы"""
        table_lines = []
        
        for i, line in enumerate(lines):
            if line.strip().startswith('|'):
                table_lines.append(line)
            else:
                # Таблица закончилась
                break
        
        return table_lines, len(table_lines)
    
    def _collect_list(self, lines: List[str]) -> tuple[List[str], int]:
        """Собрать все элементы списка"""
        list_lines = []
        
        for i, line in enumerate(lines):
            if self._is_list_item(line):
                list_lines.append(line)
            elif line.strip() == '':
                # Пустая строка - продолжаем (может быть вложенный список)
                continue
            else:
                # Список закончился
                break
        
        return list_lines, len(list_lines)
    
    def _extract_variables(self, formula_text: str) -> List[str]:
        """Извлечь переменные из формулы"""
        # Найти все слова перед/после знаков = + - * /
        variables = re.findall(r'[A-Z][A-Za-z\s]*(?=\s*[=\+\-\*/])|(?<=[=\+\-\*/])\s*[A-Z][A-Za-z\s]*', formula_text)
        return [v.strip() for v in variables if v.strip()]
    
    def _count_table_columns(self, table_lines: List[str]) -> int:
        """Подсчитать количество колонок в таблице"""
        if not table_lines:
            return 0
        # Считаем по первой строке
        return table_lines[0].count('|') - 1
    
    def _add_page_break(self):
        """Добавить page break блок"""
        self.blocks.append({
            'id': f'block_{self.block_counter:04d}',
            'type': 'page_break',
            'text': '',
            'source': {
                'page': self.current_page,
                'file': self.source_file
            },
            'meta': {}
        })
        self.block_counter += 1
    
    def _add_heading(self, text: str, level: int):
        """Добавить заголовок"""
        self.blocks.append({
            'id': f'block_{self.block_counter:04d}',
            'type': 'heading',
            'text': text,
            'source': {
                'page': self.current_page,
                'file': self.source_file
            },
            'meta': {
                'level': level
            }
        })
        self.block_counter += 1
    
    def _add_table(self, table_lines: List[str]):
        """Добавить таблицу"""
        text = '\n'.join(table_lines)
        rows = len([line for line in table_lines if '---' not in line])  # Исключаем separator
        cols = self._count_table_columns(table_lines)
        
        self.blocks.append({
            'id': f'block_{self.block_counter:04d}',
            'type': 'table',
            'text': text,
            'source': {
                'page': self.current_page,
                'file': self.source_file
            },
            'meta': {
                'rows': rows,
                'cols': cols
            }
        })
        self.block_counter += 1
    
    def _add_list(self, list_lines: List[str]):
        """Добавить список"""
        text = '\n'.join(list_lines)
        ordered = bool(re.match(r'^\d+\.', list_lines[0].strip()))
        
        self.blocks.append({
            'id': f'block_{self.block_counter:04d}',
            'type': 'list',
            'text': text,
            'source': {
                'page': self.current_page,
                'file': self.source_file
            },
            'meta': {
                'ordered': ordered,
                'items': len(list_lines)
            }
        })
        self.block_counter += 1
    
    def _add_formula(self, text: str):
        """Добавить формулу"""
        variables = self._extract_variables(text)
        
        self.blocks.append({
            'id': f'block_{self.block_counter:04d}',
            'type': 'formula',
            'text': text,
            'source': {
                'page': self.current_page,
                'file': self.source_file
            },
            'meta': {
                'variables': variables
            }
        })
        self.block_counter += 1
    
    def _add_paragraph(self, text: str):
        """Добавить параграф"""
        self.blocks.append({
            'id': f'block_{self.block_counter:04d}',
            'type': 'paragraph',
            'text': text,
            'source': {
                'page': self.current_page,
                'file': self.source_file
            },
            'meta': {}
        })
        self.block_counter += 1
    
    def save_jsonl(self, output_path: str):
        """
        Сохранить блоки в JSONL формат.
        
        Args:
            output_path: Путь к выходному .jsonl файлу
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for block in self.blocks:
                f.write(json.dumps(block, ensure_ascii=False) + '\n')


def load_blocks_jsonl(input_path: str) -> List[Dict]:
    """
    Загрузить блоки из JSONL файла.
    
    Args:
        input_path: Путь к .jsonl файлу
        
    Returns:
        List of block dictionaries
    """
    blocks = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                blocks.append(json.loads(line))
    return blocks


if __name__ == '__main__':
    # Test
    test_markdown = """
# Глава 1. Введение

Это параграф с текстом.

## 1.1 Формулы

ROI = (Profit - Investment) / Investment * 100

Current Ratio = Current Assets / Current Liabilities

## 1.2 Таблица

| Показатель | 2022 | 2023 |
|---|---|---|
| Выручка | 1000 | 1200 |
| Прибыль | 200 | 300 |

## 1.3 Список

1. Первый пункт
2. Второй пункт
3. Третий пункт

Обычный текст после списка.
"""
    
    converter = BlocksConverter("test.md")
    blocks = converter.convert(test_markdown)
    
    print(f"✅ Converted {len(blocks)} blocks:")
    for block in blocks:
        print(f"  - {block['type']}: {block['text'][:50]}...")
