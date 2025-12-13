# Implementation Plan: S3 → AI Pipeline → Knowledge Base

## 📊 Текущее состояние

### ✅ Готово
- S3 хранилище настроено (Beget Cloud)
- 17 книг загружено (224.7 MB)
- 6 Excel шаблонов (11.4 MB)
- 5 нормативных документов (4.86 MB)
- Структура папок:
  ```
  s3://db6a1f644d97-la-ducem1/Financial Methodologies_kb/
  ├── books/
  ├── templates/excel/
  └── нормативные документы/
  ```
- Glossary v1.0 (25 терминов)
- Шаблоны методологий (10 файлов)
- GitHub issues система

## 🎯 Цель

Создать автоматический pipeline для обработки книг из S3 и генерации методологий.

## 🏗️ Архитектура

```
S3 Bucket (Beget Cloud)
  └── books/ (17 PDF/DOCX/PPTX)
       ↓
┌─────────────────────────────────┐
│  Agent A: Ingest/Extractor      │
│  (Unstructured.io / DocTR)      │
│  - OCR для сканов               │
│  - Извлечение таблиц            │
│  - Нормализация текста          │
└──────────────┬──────────────────┘
               ↓
    sources/<book_id>/raw_text.md
    + metadata.json
               ↓
┌─────────────────────────────────┐
│  Agent B: Outline Builder       │
│  (LangGraph + GigaChat)         │
│  - Классификация типа документа │
│  - Извлечение секций            │
│  - Создание outline.yaml        │
└──────────────┬──────────────────┘
               ↓
    work/<id>/outline.yaml
    (stages, tools, indicators, rules)
               ↓
┌─────────────────────────────────┐
│  Agent C: Compiler              │
│  (Template Engine)              │
│  - Генерация по шаблонам        │
│  - Использование glossary       │
│  - Создание YAML паспортов      │
└──────────────┬──────────────────┘
               ↓
    docs/methodologies/<id>/*.md
    data/methodologies/<id>.yaml
               ↓
┌─────────────────────────────────┐
│  Agent D: QA/Reviewer           │
│  (Validation + Quality Checks)  │
│  - validate_glossary.py         │
│  - Проверка полноты             │
│  - Генерация qa_report.md       │
└──────────────┬──────────────────┘
               ↓
    work/<id>/qa_report.md
               ↓
┌─────────────────────────────────┐
│  Agent E: PR Publisher          │
│  (GitHub API)                   │
│  - Создание ветки               │
│  - Коммит + Push                │
│  - Открытие PR                  │
└──────────────┬──────────────────┘
               ↓
    GitHub Pull Request
               ↓
┌─────────────────────────────────┐
│  ArangoDB Knowledge Base        │
│  (Graph + Vector Search)        │
│  - Методологии (vertices)       │
│  - Связи (edges)                │
│  - Embeddings для RAG           │
└─────────────────────────────────┘
```

## 📋 План реализации (по issues)

### Phase 1: Foundation (Sprint 1, 2 недели)

**Issue #19: System Prompt для AI Methodologist** ⭐ FIRST
- [ ] Создать `pipeline/prompts/system_prompt.md`
- [ ] Определить роль агента (методолог, не учитель)
- [ ] Прописать правила (не придумывать, использовать glossary)
- [ ] Примеры правильного/неправильного поведения
- [ ] Разделение: методология ≠ модель ≠ modeling tool
- [ ] Шаблон выходных форматов (YAML/MD)

**Deliverable**: `pipeline/prompts/system_prompt.md`

---

**Issue #20: OCR Pipeline** ⭐ SECOND
- [ ] Выбрать OCR движок (Unstructured.io vs DocTR)
- [ ] Реализовать детектор типа PDF (текстовый/скан)
- [ ] Обработка PDF → Markdown
- [ ] Обработка DOCX → Markdown
- [ ] Обработка PPTX → Markdown
- [ ] Извлечение таблиц → CSV
- [ ] Тесты на наших книгах

**Deliverable**: `pipeline/agents/extractor.py`

---

**Issue #18: Agent Pipeline Architecture** ⭐ THIRD
- [ ] Создать структуру директорий `pipeline/`
- [ ] Реализовать Agent A (Extractor) - использует OCR
- [ ] Реализовать Agent B (Outline Builder)
- [ ] Реализовать Agent C (Compiler)
- [ ] Реализовать Agent D (QA Reviewer)
- [ ] Реализовать Agent E (PR Publisher)
- [ ] CLI интерфейс `pipeline/cli.py`
- [ ] Тест на одной книге end-to-end

**Deliverable**: Рабочий pipeline с 5 агентами

---

### Phase 2: AI Integration (Sprint 2, 2 недели)

**Issue #21: LangGraph Integration**
- [ ] Создать граф обработки документов
- [ ] Узел: Classify Document (определение типа)
- [ ] Узел: Extract Sections (разбивка на секции)
- [ ] Узел: Generate Methodology (генерация по шаблону)
- [ ] Узел: Create Embeddings (векторы для RAG)
- [ ] Интеграция с GigaChat API
- [ ] Retry logic и error handling
- [ ] Unit тесты для каждого узла

**Deliverable**: `pipeline/langgraph_workflow.py`

---

**Issue #22: ArangoDB Knowledge Base**
- [ ] Схема коллекций (methodologies, indicators, rules, terms)
- [ ] Схема рёбер (uses, depends_on, related_to, defines)
- [ ] API класс `KnowledgeBase`
- [ ] Векторный поиск (ArangoSearch)
- [ ] Графовые запросы (AQL)
- [ ] Миграция из текущих YAML/MD
- [ ] Документация API

**Deliverable**: `pipeline/knowledge_base.py` + ArangoDB setup

---

### Phase 3: Automation (Sprint 3, 1 неделя)

**Issue #23: GitHub Actions**
- [ ] Workflow файл `.github/workflows/process-books.yml`
- [ ] Триггер: manual dispatch
- [ ] Триггер: schedule (weekly)
- [ ] Secrets configuration
- [ ] Автоматический PR после обработки
- [ ] Notifications (Telegram/Email)
- [ ] Артефакты (logs, reports)

**Deliverable**: GitHub Actions workflow

---

**Issue #24: Pipeline Monitoring**
- [ ] Класс `PipelineMetrics`
- [ ] Логирование (структурированное JSON)
- [ ] Метрики производительности
- [ ] Метрики качества
- [ ] Dashboard/Report генератор
- [ ] Alerts при ошибках

**Deliverable**: `pipeline/metrics.py` + monitoring dashboard

---

## 🛠️ Технологический стек

### Python пакеты
```txt
# Document Processing
unstructured[all-docs]>=0.10.0
python-doctr[torch]>=0.7.0
pytesseract>=0.3.10
pdf2image>=1.16.3
pymupdf>=1.23.0
pdfplumber>=0.10.3
python-docx>=1.1.0
Pillow>=10.0.0

# AI & LLM
langgraph>=0.0.26
gigachat>=0.1.13
sentence-transformers>=2.2.2
openai>=1.3.0  # для embeddings

# Database
python-arango>=7.5.9

# Infrastructure
boto3>=1.29.0
python-dotenv>=1.0.0
pyyaml>=6.0.1
pydantic>=2.5.0
requests>=2.31.0

# CLI & Tools
click>=8.1.7
rich>=13.7.0  # красивый CLI output
tqdm>=4.66.0  # progress bars

# Testing
pytest>=7.4.3
pytest-asyncio>=0.21.1
```

### Внешние сервисы
- **S3**: Beget Cloud (уже настроен)
- **LLM**: GigaChat API (нужен API key)
- **Database**: ArangoDB (локальный или cloud)
- **CI/CD**: GitHub Actions (есть)
- **Monitoring**: Можно добавить Grafana/Prometheus (опционально)

---

## 📁 Структура проекта

```
financial-methodologies-kb/
├── pipeline/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── extractor.py          # Agent A: OCR + извлечение
│   │   ├── outline_builder.py    # Agent B: структурирование
│   │   ├── compiler.py           # Agent C: генерация по шаблонам
│   │   ├── qa_reviewer.py        # Agent D: валидация
│   │   └── pr_publisher.py       # Agent E: GitHub PR
│   ├── prompts/
│   │   ├── system_prompt.md      # Универсальный system prompt
│   │   ├── extractor_prompt.md
│   │   ├── outline_prompt.md
│   │   ├── compiler_prompt.md
│   │   └── qa_prompt.md
│   ├── schemas/
│   │   ├── outline_schema.py     # Pydantic модели
│   │   ├── methodology_schema.py
│   │   └── document_state.py
│   ├── cli.py                    # CLI интерфейс
│   ├── langgraph_workflow.py     # LangGraph граф
│   ├── knowledge_base.py         # ArangoDB API
│   ├── metrics.py                # Мониторинг
│   └── README.md
│
├── sources/                      # Извлеченные данные из книг
│   └── <book_id>/
│       ├── raw_text.md
│       ├── metadata.json
│       └── tables/
│
├── work/                         # Рабочие файлы агентов
│   └── <methodology_id>/
│       ├── outline.yaml
│       ├── qa_report.md
│       └── artifacts/
│
├── .github/
│   └── workflows/
│       └── process-books.yml     # GitHub Actions
│
├── s3/                           # Существующий S3 код
├── tools/                        # Существующие tools
├── data/                         # Существующие данные
├── docs/                         # Существующая документация
└── templates/                    # Существующие шаблоны
```

---

## 🚀 Порядок действий

### Неделя 1-2: Foundation

1. **Day 1-2: System Prompt (#19)**
   ```bash
   mkdir -p pipeline/prompts
   # Создать system_prompt.md на основе agent.md
   # Протестировать на GigaChat
   ```

2. **Day 3-7: OCR Pipeline (#20)**
   ```bash
   pip install unstructured[all-docs] python-doctr[torch]
   # Реализовать extractor.py
   # Тесты на 3-х книгах (текст, скан, презентация)
   ```

3. **Day 8-14: Agent Pipeline (#18)**
   ```bash
   mkdir -p pipeline/agents pipeline/schemas
   # Реализовать 5 агентов
   # CLI интерфейс
   # End-to-end тест
   ```

### Неделя 3-4: AI Integration

4. **Day 15-21: LangGraph (#21)**
   ```bash
   pip install langgraph gigachat sentence-transformers
   # Создать граф обработки
   # Интеграция с GigaChat
   # Генерация embeddings
   ```

5. **Day 22-28: ArangoDB (#22)**
   ```bash
   docker run -p 8529:8529 arangodb/arangodb
   pip install python-arango
   # Схема БД
   # API класс
   # Миграция данных
   ```

### Неделя 5: Automation

6. **Day 29-31: GitHub Actions (#23)**
   ```bash
   # Создать workflow
   # Настроить secrets
   # Тестовый запуск
   ```

7. **Day 32-35: Monitoring (#24)**
   ```bash
   # PipelineMetrics класс
   # Логирование
   # Dashboard
   ```

---

## 🎯 Критерии успеха

### Milestone: Agent Pipeline v0.5 ✅

- [ ] Все 5 агентов работают
- [ ] Успешно обработана хотя бы **1 книга** из S3
- [ ] Сгенерирована методология по шаблону
- [ ] QA отчёт показывает 100% валидности
- [ ] GitHub PR создаётся автоматически
- [ ] Документация `pipeline/README.md` готова

### Milestone: Integration v0.3 ✅

- [ ] LangGraph граф обрабатывает документы
- [ ] GigaChat генерирует outline
- [ ] ArangoDB хранит методики
- [ ] Векторный поиск находит похожие методики
- [ ] Графовые запросы работают

### Milestone: Production Ready ✅

- [ ] GitHub Actions запускается по расписанию
- [ ] Обработано минимум **5 книг** из S3
- [ ] Метрики собираются
- [ ] Ошибки логируются
- [ ] Documentation полная

---

## 📊 Метрики успеха

| Метрика | Цель | Текущее |
|---------|------|---------|
| Книг обработано | 17 | 0 |
| Методологий создано | 10+ | 7 (stubs) |
| Индикаторов извлечено | 50+ | 0 |
| Правил (rules) | 30+ | 0 |
| Покрытие глоссарием | 80%+ | N/A |
| Время обработки книги | < 5 мин | N/A |
| Success rate | 90%+ | N/A |

---

## 🔑 Необходимые API Keys

```bash
# .env файл
GIGACHAT_API_KEY=your_gigachat_key
S3_ACCESS_KEY=JQDHVXZY7XFWUHF8LV0S
S3_SECRET_KEY=pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk
S3_ENDPOINT=https://s3.ru1.storage.beget.cloud
S3_BUCKET=db6a1f644d97-la-ducem1
ARANGO_HOST=http://localhost:8529
ARANGO_DATABASE=financial_kb
ARANGO_USERNAME=root
ARANGO_PASSWORD=your_arango_password
GITHUB_TOKEN=your_github_token  # уже есть в git remote
```

---

## 🧪 Тестовый запуск

```bash
# 1. Установка зависимостей
cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb
source venv/bin/activate
pip install -r pipeline/requirements.txt

# 2. Настройка .env
cp .env.example .env
# Заполнить API keys

# 3. Запуск на одной книге
python pipeline/cli.py process \
  --book-id "simple-numbers" \
  --s3-path "s3://db6a1f644d97-la-ducem1/Financial Methodologies_kb/books/2020-Simple-Numbers-Presentation-Crisis-Mode.pptx" \
  --output-dir work/simple-numbers

# 4. Проверка результата
cat work/simple-numbers/outline.yaml
cat work/simple-numbers/qa_report.md

# 5. Если всё ОК - создать PR
python pipeline/cli.py publish \
  --methodology-id simple-numbers \
  --branch feature/methodology-simple-numbers
```

---

## 📚 Дополнительные ресурсы

- **agent.md**: Философия и принципы AI методолога
- **issues_agent_pipeline.json**: Детальное описание issues
- **templates/**: Шаблоны для генерации методологий
- **data/glossary/**: Канонические определения терминов
- **docs/GITHUB_INTEGRATION.md**: Работа с GitHub API
- **s3/WORKFLOW.md**: Работа с S3

---

## 🎉 Что будет в итоге

После реализации всех issues:

1. **Автоматическая обработка книг**
   - Загрузили PDF в S3 → через 5 минут готова методология

2. **Knowledge Base**
   - Все методики в ArangoDB
   - Связи между понятиями
   - RAG поиск по векторам

3. **Качественные методологии**
   - Следуют канону (agent.md)
   - Используют glossary
   - Проходят QA валидацию

4. **Прозрачный процесс**
   - GitHub PR с результатами
   - QA отчёт
   - Метрики качества

5. **Масштабируемость**
   - Добавили 100 книг → получили 100 методологий
   - GitHub Actions автоматически
   - Monitoring показывает проблемы

---

## 🤔 Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| OCR плохо распознаёт сканы | Высокая | Тестировать на реальных книгах, выбрать лучший движок |
| GigaChat API лимиты | Средняя | Rate limiting, retry logic, кеширование |
| Методики низкого качества | Средняя | Строгий QA агент, human review через PR |
| ArangoDB сложно настроить | Низкая | Docker compose, документация |
| GitHub Actions дорого | Низкая | Self-hosted runner на сервере |

---

## 📝 Next Steps

1. **Сейчас**: Создать issue в GitHub для этого плана
2. **Завтра**: Начать с #19 (System Prompt)
3. **Через неделю**: Первый working prototype
4. **Через месяц**: Production ready pipeline

**Готовы начать? 🚀**
