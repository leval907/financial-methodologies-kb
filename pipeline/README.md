# AI Pipeline для обработки документов

## Agent A: Document Extractor

### Возможности

✅ **Поддерживаемые форматы:**
- PDF (через markitdown)
- DOCX (через markitdown)
- PPTX (через markitdown)
- XLSX/XLS (через openpyxl + pandas)
- TXT, MD (прямое чтение)

✅ **Извлечение данных:**
- Текст в Markdown формате
- Таблицы из Excel (с сохранением структуры)
- Формулы из Excel (с значениями)
- Метаданные документов

### Использование

```bash
# PDF книга
python pipeline/agents/extractor.py \
  "cache/books/book.pdf" \
  --output-dir "sources/book-id" \
  --book-id "book-id"

# Excel файл (без markitdown для лучшего качества)
python pipeline/agents/extractor.py \
  "cache/excel/file.xlsx" \
  --output-dir "sources/excel-id" \
  --book-id "excel-id" \
  --no-markitdown
```

### Структура выхода

```
sources/<book-id>/
├── raw_text.md           # Основной текст в Markdown
├── metadata.json         # Метаданные документа
├── tables/               # Таблицы (только для Excel)
│   ├── table_1_Sheet1.json
│   └── table_2_Sheet2.json
└── formulas.json         # Формулы (только для Excel)
```

### Примеры

#### PDF книга
```bash
python pipeline/agents/extractor.py \
  "cache/books/Бухгалтерия_13.pdf" \
  --output-dir "sources/accounting-basics" \
  --book-id "accounting-basics"

# Результат:
# ✅ Extracted: accounting-basics
#    Text: sources/accounting-basics/raw_text.md (765 lines)
#    Metadata: sources/accounting-basics/metadata.json
```

#### Excel файл
```bash
python pipeline/agents/extractor.py \
  "cache/excel/План счетов.xlsx" \
  --output-dir "sources/chart-of-accounts" \
  --book-id "chart-of-accounts" \
  --no-markitdown

# Результат:
# ✅ Extracted: chart-of-accounts
#    Text: sources/chart-of-accounts/raw_text.md (242 lines)
#    Metadata: sources/chart-of-accounts/metadata.json
#    Tables: 1
```

## Следующие шаги

1. **Agent B: Outline Builder** - Анализ текста и создание структуры методологии
2. **Agent C: Compiler** - Генерация методологий по шаблонам
3. **Agent D: QA Reviewer** - Валидация качества
4. **Agent E: PR Publisher** - Публикация в GitHub

## Технологии

- **markitdown**: Универсальный конвертер (PDF, DOCX, PPTX)
- **openpyxl**: Чтение Excel с формулами
- **pandas**: Обработка табличных данных
- **Python 3.12**: Основной язык
