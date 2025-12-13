# AI Pipeline for Financial Methodologies KB

Автоматическая обработка книг из S3 и генерация методологий с помощью AI агентов.

## 🏗️ Архитектура

```
S3 Books → Agent A: Extractor → Agent B: Outline Builder → Agent C: Compiler → Agent D: QA → Agent E: PR Publisher → ArangoDB
```

## 🤖 Агенты

### Agent A: Extractor (ГОТОВ ✅)
**Задача**: Конвертация файлов в единый формат

**Входы**:
- PDF (текстовый, скан)
- DOCX  
- PPTX

**Выходы**:
```
sources/<book_id>/
├── raw_text.md       # Чистый markdown
├── metadata.json     # Метаданные файла
├── tables/           # Извлеченные таблицы
│   └── table_001.txt
└── images/           # Изображения (опционально)
```

**Использует**:
- Unstructured.io для универсальной обработки
- OCR для сканов (Tesseract)
- LangGraph для workflow

### Agent B: Outline Builder (TODO)
**Задача**: Создание структуры методологии

**Выходы**:
```yaml
work/<methodology_id>/outline.yaml:
  title: "Simple Numbers"
  type: "financial_methodology"
  sections:
    - name: "stages"
      items: [...]
    - name: "indicators"
      items: [...]
```

### Agent C: Compiler (TODO)
**Задача**: Генерация файлов по шаблонам

### Agent D: QA Reviewer (TODO)
**Задача**: Валидация качества

### Agent E: PR Publisher (TODO)
**Задача**: Создание GitHub PR

## 🚀 Quick Start

### 1. Установка зависимостей

```bash
cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb
source venv/bin/activate
pip install -r pipeline/requirements.txt
```

### 2. Установка Tesseract для OCR

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-rus

# macOS
brew install tesseract tesseract-lang
```

### 3. Запуск Extractor Agent

```bash
# Обработать один файл
python pipeline/agents/extractor.py cache/books/Бухгалтерия_13.pdf

# С указанием output директории и book_id
python pipeline/agents/extractor.py \
  cache/books/Корбет\ Томас\ -\ Управленческий\ учёт\ по\ ТОС\ -\ 2009.pdf \
  sources \
  toc-corbett
```

### 4. Проверка результата

```bash
ls sources/<book_id>/
cat sources/<book_id>/raw_text.md
cat sources/<book_id>/metadata.json
```

## 📂 Структура проекта

```
pipeline/
├── agents/
│   ├── __init__.py
│   ├── extractor.py          # ✅ Agent A (ГОТОВ)
│   ├── outline_builder.py    # TODO: Agent B
│   ├── compiler.py           # TODO: Agent C
│   ├── qa_reviewer.py        # TODO: Agent D
│   └── pr_publisher.py       # TODO: Agent E
│
├── prompts/
│   └── system_prompt.md      # TODO: System prompt для всех агентов
│
├── schemas/
│   └── outline_schema.py     # TODO: Pydantic схемы
│
├── requirements.txt          # ✅ Зависимости
└── README.md                 # ✅ Эта документация
```

## 🧪 Тестирование

### Тест Extractor Agent на реальных книгах

```bash
# Книга 1: PDF с текстом
python pipeline/agents/extractor.py \
  cache/books/Бухгалтерия_13.pdf \
  sources \
  accounting-basics

# Книга 2: TOC (большой PDF)
python pipeline/agents/extractor.py \
  "cache/books/Корбет Томас - Управленческий учёт по ТОС - 2009.pdf" \
  sources \
  toc-corbett

# Книга 3: PowerPoint
python pipeline/agents/extractor.py \
  "cache/books/2020-Simple-Numbers-Presentation-Crisis-Mode [Автосохраненный].pptx" \
  sources \
  simple-numbers-presentation
```

### Ожидаемые результаты

После успешной обработки:

```bash
sources/
├── accounting-basics/
│   ├── raw_text.md       # ~50-100 KB текста
│   └── metadata.json
├── toc-corbett/
│   ├── raw_text.md       # ~500-1000 KB текста
│   ├── metadata.json
│   └── tables/
│       ├── table_001.txt
│       └── table_002.txt
└── simple-numbers-presentation/
    ├── raw_text.md
    └── metadata.json
```

## 🔧 Настройка

### OCR Languages

По умолчанию используется `rus+eng`. Для других языков:

```python
agent = ExtractorAgent()
result = await agent.process(
    file_path="book.pdf",
    ocr_languages="eng"  # Только английский
)
```

### Отключение OCR

Для текстовых PDF без необходимости OCR:

```python
from pipeline.agents.extractor import ExtractorState

state = ExtractorState(
    file_path="book.pdf",
    use_ocr=False  # Быстрее, но не для сканов
)
```

## 📊 Статус реализации

| Агент | Статус | Прогресс |
|-------|--------|----------|
| Agent A: Extractor | ✅ ГОТОВ | 100% |
| Agent B: Outline Builder | 🔴 TODO | 0% |
| Agent C: Compiler | 🔴 TODO | 0% |
| Agent D: QA Reviewer | 🔴 TODO | 0% |
| Agent E: PR Publisher | 🔴 TODO | 0% |

**Текущий milestone**: Issue #20 - Implement OCR Pipeline ✅

## 🎯 Следующие шаги

1. **Протестировать Extractor на всех 17 книгах из S3** ⬅️ СЕЙЧАС
2. Создать Issue #19: System Prompt
3. Реализовать Agent B: Outline Builder
4. Интегрировать LangGraph + GigaChat

## 🐛 Troubleshooting

### Ошибка: "unstructured not installed"

```bash
pip install "unstructured[all-docs]"
```

### Ошибка: "Tesseract not found"

```bash
# Ubuntu
sudo apt-get install tesseract-ocr tesseract-ocr-rus

# Check installation
tesseract --version
```

### Ошибка: Permission denied при сохранении

```bash
# Создать директорию с правами
mkdir -p sources
chmod 755 sources
```

## 📚 Связанные документы

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) - Полный план реализации
- [agent.md](../inputs/agent.md) - Философия AI методолога
- [issues_agent_pipeline.json](../issues_agent_pipeline.json) - GitHub issues

## 🤝 Contributing

См. [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) для плана разработки.

---

**Status**: Phase 1 (Foundation) - Agent A Complete ✅
