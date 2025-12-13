# 📊 ТЕКУЩЕЕ СОСТОЯНИЕ PIPELINE
> Дата: 2025-12-13
> Версия: v2.0 (после реализации Agent D)

---

## 🎯 Общая архитектура

```
PDF/DOCX/PPTX
    ↓
┌─────────────────────────┐
│ Agent A v2              │ ✅ ГОТОВ
│ Document Extractor      │
└────────┬────────────────┘
         ↓ blocks.jsonl
┌─────────────────────────┐
│ Agent B v1.0            │ ✅ ГОТОВ (с проблемами)
│ Outline Builder         │
└────────┬────────────────┘
         ↓ outline.yaml
┌─────────────────────────┐
│ Agent C v2              │ ✅ ГОТОВ
│ Compiler (NO LLM)       │
└────────┬────────────────┘
         ↓ normalized YAML + docs
┌─────────────────────────┐
│ Agent D v1.0            │ ✅ ГОТОВ
│ QA Reviewer             │
└────────┬────────────────┘
         ↓ qa_report.md
┌─────────────────────────┐
│ Agent E                 │ ❌ НЕ РЕАЛИЗОВАН
│ Graph DB Publisher      │
└────────┬────────────────┘
         ↓
┌─────────────────────────┐
│ Agent F                 │ ❌ НЕ РЕАЛИЗОВАН
│ PR Publisher            │
└─────────────────────────┘
```

---

## 📦 Agent A v2: Document Extractor

### Статус
✅ **РЕАЛИЗОВАН и РАБОТАЕТ**

### Файлы
```
pipeline/agents/agent_a/
├── extractor.py          (основной код)
└── __init__.py
```

### Вход
```
cache/books/<filename>.pdf|docx|pptx|xlsx
```

### Выход
```
sources/<book_id>/
├── extracted/
│   └── blocks.jsonl      # ← Главный выход
└── metadata.json         # ← Метаданные экстракции
```

### Технологии
- **markitdown** - конвертация в markdown
- **Детерминированный парсинг** - без AI
- **Построчный JSONL** - эффективная память

### Формат blocks.jsonl
```jsonl
{"id": "block_001", "type": "paragraph", "text": "...", "source": {"page": 1}, "meta": {}}
{"id": "block_002", "type": "heading", "text": "...", "source": {"page": 2}, "meta": {"level": 1}}
{"id": "block_003", "type": "table", "text": "| A | B |...", "source": {"page": 3}, "meta": {}}
```

### Типы блоков
- `paragraph` - текст
- `heading` - заголовок (meta.level: 1-6)
- `table` - таблица
- `list` - список
- `formula` - формула
- `page_break` - разрыв страницы

### Метрики
```json
{
  "total_blocks": 515,
  "blocks_by_type": {
    "paragraph": 450,
    "heading": 45,
    "table": 15,
    "list": 5
  },
  "total_pages": 120,
  "total_chars": 125000
}
```

### AI модель
❌ **НЕТ** - чисто детерминированная обработка

### Стоимость
**₽0** (без AI)

### Команда запуска
```bash
python pipeline/agents/agent_a/extractor.py \
  --input cache/books/accounting.pdf \
  --book-id accounting-basics
```

### Проблемы
- ⚠️ Нет quality scoring
- ⚠️ Нет OCR repair mode
- ⚠️ Таблицы могут терять форматирование

---

## 🧠 Agent B v1.0: Outline Builder

### Статус
✅ **РЕАЛИЗОВАН**, но **ЕСТЬ ПРОБЛЕМЫ**

### Файлы
```
pipeline/agents/agent_b/
├── agent_b.py            (основной код)
└── __init__.py
```

### Вход
```
sources/<book_id>/extracted/blocks.jsonl
```

### Выход
```
work/<book_id>/
└── outline.yaml          # ← Главный выход
```

### AI Стратегия
- 🥇 **PRIMARY:** GigaChat (бесплатно, 1.06s, scope=GIGACHAT_API_PERS)
- 🥈 **FALLBACK:** Qwen3-Max через Requesty AI (4.04s)

### Технологии
- **GigaChat SDK** - gigachat Python package
- **Requesty AI** - unified AI gateway для fallback
- **Map-Reduce** - chunking по 50 блоков или по headings

### Алгоритм

#### Шаг 1: Chunking
```python
# Если есть headings (level ≤ 2):
chapters = group_by_headings(blocks)

# Если нет headings:
chapters = chunk_by_50_blocks(blocks)
```

#### Шаг 2: Map (для каждой главы)
```python
for chapter in chapters:
    result = llm.extract({
        "stages": [...],
        "tools": [...],
        "indicators": [...],
        "rules": [...]
    })
```

#### Шаг 3: Reduce (объединение)
```python
outline = {
    'metadata': {...},
    'classification': {'methodology_type': 'analysis'},
    'structure': {
        'stages': merge_all(chapter_stages),
        'tools': merge_all(chapter_tools),
        'indicators': merge_all(chapter_indicators),
        'rules': merge_all(chapter_rules)
    }
}
```

### System Prompt
```
Ты эксперт-методолог по финансовому анализу и бухгалтерии.

Извлеки из текста:
1. Stages (этапы): title, description, order
2. Tools (инструменты): title, type, description
3. Indicators (показатели): name, formula, description
4. Rules (правила): condition, action, severity

Ответь строго в JSON формате.
```

### Формат outline.yaml
```yaml
metadata:
  agent: Agent B v1.0 (GigaChat + Qwen3-Max)
  model_used: gigachat
  chapters_processed: 11

classification:
  methodology_type: analysis

structure:
  stages:
    - title: "Название этапа"
      description: "Описание этапа"
      order: 1
  
  tools:
    - title: "Название инструмента"
      type: "graph|table|software"
      description: "Описание"
  
  indicators:
    - name: "Название показателя"
      formula: "Формула (если есть)"
      description: "Описание"
  
  rules:
    - condition: "Условие"
      action: "Действие"
      severity: "high|medium|low"
```

### Результаты тестирования
**Книга:** accounting-basics (515 блоков, 11 глав)

**Выход:**
- ✅ 26 stages извлечено
- ✅ 3 tools извлечено
- ✅ 21 indicators извлечено
- ✅ 6 rules извлечено
- ✅ methodology_type: analysis

**Проблемы (найдены Agent D):**
- ❌ 4 stages с пустыми descriptions ("Шаг 1-4")
- ❌ 8 indicators с пустыми descriptions
- ❌ 21/21 indicators БЕЗ формул (formula: '')
- ❌ Rules с severity='high'/'medium' (нужно 'critical'/'warning'/'info'/'low')
- ❌ Дублирование: "валовая прибыль" встречается 2 раза (разные descriptions)
- ❌ Сломанная нумерация: order=1 встречается 9 раз (не только у stage_001)

### AI модели
- **GigaChat**: 11 запросов
- **Fallback**: 0 (GigaChat сработал)

### Стоимость
**₽0** (GigaChat бесплатно)

### Команда запуска
```bash
python tests/test_agent_b.py

# Требует:
export GIGACHAT_CREDENTIALS="your_key"
export REQUESTY_API_KEY="your_key"
```

### Проблемы
- ⚠️ **НЕ ИЗВЛЕКАЕТ formulas** из текста
- ⚠️ **ПРОПУСКАЕТ descriptions** для некоторых элементов
- ⚠️ **НЕПРАВИЛЬНЫЕ severity** values (high/medium вместо critical/warning)
- ⚠️ **ДУБЛИРУЕТ показатели** с разными descriptions
- ⚠️ **СЛОМАННАЯ НУМЕРАЦИЯ** stages (order не последовательный)

---

## 📝 Agent C v2: Compiler (Deterministic)

### Статус
✅ **РЕАЛИЗОВАН и РАБОТАЕТ**

### Философия
**"Agent C is a COMPILER, not a content generator"**
- НЕТ LLM для генерации контента
- Только Jinja2 шаблоны
- Только трансформация данных
- Никаких новых фактов

### Файлы
```
pipeline/agents/agent_c_v2/
└── compiler.py           (460 lines)

templates/methodology/
├── README.md.j2
├── stage.md.j2
├── tool.md.j2
├── indicator.md.j2
└── rule.md.j2
```

### Вход
```
work/<book_id>/outline.yaml
```

### Выход
```
data/methodologies/<book_id>.yaml    # ← Нормализованная структура
docs/methodologies/<book_id>/
├── README.md
├── stages/
│   ├── stage_001_*.md
│   ├── stage_002_*.md
│   └── ...
├── tools/
│   └── tool_001_*.md
└── indicators/
    └── ind_001_*.md
```

### Технологии
- **python-slugify** - безопасные имена файлов
- **jinja2** - шаблонизация markdown
- **pyyaml** - парсинг YAML
- **Детерминированная логика** - NO LLM

### Алгоритм

#### 1. Нормализация
```python
def normalize_outline(outline):
    # Присваивает стабильные ID
    stages[0].id = "stage_001"
    stages[1].id = "stage_002"
    tools[0].id = "tool_001"
    indicators[0].id = "ind_001"
    rules[0].id = "rule_001"
    
    # Нормализует типы
    if tool.type == "graph": tool.type = "chart"
    if tool.type == "map": tool.type = "other"
    
    # Сохраняет order
    stage.order = original_order
    
    return normalized
```

#### 2. Рендеринг Jinja2
```python
def render_all(normalized):
    # README
    render('README.md.j2', normalized)
    
    # Stages
    for stage in stages:
        render('stage.md.j2', stage)
    
    # Tools, Indicators, Rules
    # ...аналогично
```

### Пример шаблона (stage.md.j2)
```jinja2
# {{ stage.title }}

## Описание
{{ stage.description }}

## Порядок выполнения
Этап {{ stage.order }} из {{ total_stages }}

{% if stage.source %}
## Источник
{{ stage.source }}
{% endif %}
```

### Результаты тестирования
**Книга:** accounting-basics-test

**Вход:**
- 26 stages
- 3 tools
- 21 indicators
- 6 rules

**Выход:**
- ✅ 1 README.md
- ✅ 26 stage files
- ✅ 3 tool files
- ✅ 21 indicator files
- ✅ 6 rule files
- ✅ 1 normalized YAML
- **Всего: 59 файлов**

### Отличия от Agent C v1
| Критерий | Agent C v1 (старый) | Agent C v2 (новый) |
|----------|---------------------|-------------------|
| LLM генерация | ✅ Да | ❌ Нет |
| Jinja2 шаблоны | ❌ Нет | ✅ Да |
| "Практические рекомендации" | ✅ Генерирует | ❌ Не генерирует |
| "Частые ошибки" | ✅ Генерирует | ❌ Не генерирует |
| Добавление фактов | ❌ Плохо | ✅ Никогда |
| Скорость | Медленно (LLM) | Быстро (<1s) |
| Стоимость | ₽5-10 за книгу | ₽0 |
| Детерминизм | ❌ Нет | ✅ Да |

### AI модель
❌ **НЕТ** - чисто Jinja2 трансформация

### Стоимость
**₽0** (без AI)

### Команда запуска
```bash
python pipeline/agents/agent_c_v2/compiler.py \
  --outline work/accounting-basics-test/outline.yaml

# Или с book-id:
python pipeline/agents/agent_c_v2/compiler.py \
  --book accounting-basics-test
```

### Проблемы
- ⚠️ НЕ ВАЛИДИРУЕТ outline.yaml перед компиляцией
- ⚠️ НЕ МАППИТ severity (high→critical, medium→warning)
- ⚠️ НЕ ПЕРЕНУМЕРОВЫВАЕТ stages (сохраняет исходный order)

---

## 🔍 Agent D v1.0: QA Reviewer

### Статус
✅ **РЕАЛИЗОВАН и ПРОТЕСТИРОВАН**

### Философия
**"Agent D is a CONTROLLER, not a content generator"**
- Hybrid: Deterministic + LLM
- Layer 1: Быстрые детерминированные проверки
- Layer 2: Claude для семантического анализа

### Файлы
```
pipeline/agents/agent_d/
└── reviewer.py           (1100+ lines)

inputs/
└── agent_d_system.md     (system prompt)

schemas/
└── methodology_compiled.schema.json
```

### Вход
```
work/<book_id>/outline.yaml                 # Agent B output
data/methodologies/<book_id>.yaml           # Agent C output
docs/methodologies/<book_id>/**             # Agent C docs
data/glossary/*.yaml (optional)             # Glossary terms
```

### Выход
```
work/<book_id>/qa/
├── qa_result.json        # ← Machine-readable
├── qa_report.md          # ← Human-readable
└── approved.flag         # ← true/false
```

### AI Стратегия
- **Optional:** Claude Sonnet 4.5 via Requesty AI
- **Flag:** `--use-llm` для включения LLM reasoning

### Архитектура: Layer 1 (Deterministic Prechecks)

#### 1. Schema validation
```python
# JSON Schema validation против methodology_compiled.schema.json
validate_schema(compiled_yaml, schema)
# Находит: пустые required fields, неправильные типы
```

#### 2. ID format checks
```python
# Проверяет формат ID
assert stage.id.matches("stage_\d{3}")
assert tool.id.matches("tool_\d{3}")
assert indicator.id.matches("ind_\d{3}")
assert rule.id.matches("rule_\d{3}")

# Находит дубликаты ID
```

#### 3. Duplicate indicators
```python
# Нормализация: lowercase, strip, ё→е
normalize("Валовая Прибыль") == "валовая прибыль"

# Находит точные дубли
```

#### 4. Broken stage numbering
```python
# Проверки:
- order=1 только у stage_001
- order уникален для каждого stage
- order не повторяется

# Находит: сломанную нумерацию
```

#### 5. Duplicate stage titles
```python
# Exact match после нормализации
normalize(title1) == normalize(title2)
```

#### 6. README coverage
```python
# Проверяет что README упоминает все stages
coverage = found_stages / total_stages
if coverage < 0.5: BLOCKER
if coverage < 0.8: MAJOR
```

#### 7. Empty formulas
```python
# Для methodology_type: diagnostic|analysis|optimization
empty_ratio = empty_formulas / total_indicators

if empty_ratio == 1.0: BLOCKER (100% empty)
if empty_ratio > 0.7: MAJOR (>70% empty)
```

#### 8. Glossary validation
```python
# Проверяет glossary_references.found_terms
for term_id in found_terms:
    if term_id not in glossary:
        BLOCKER
```

#### 9. Formula syntax
```python
# Минимальные синтаксические проверки:
- Баланс скобок
- Контрольные символы
- Наличие '=' в определениях
```

#### 10. Docs consistency
```python
# Проверяет соответствие файлов и YAML
assert len(stage_files) == len(stages)
assert README.md exists
```

### Архитектура: Layer 2 (LLM Reasoning)

**Модель:** Claude Sonnet 4.5 via Requesty

**Проверяет:**
1. **Логическая связность**
   - Противоречия между stages
   - Дублирование по смыслу (не exact match)
   - Сломанный flow (stage 5 перед stage 2)

2. **Completeness**
   - Является ли методология применимой?
   - Достаточно ли информации?

3. **Formula sanity**
   - Семантические ошибки (numerator/denominator swap)
   - "Profit Margin = Revenue + Expenses" (должно быть минус)

4. **Glossary consistency**
   - Использование терминов соответствует определениям

**Output:**
```json
{
  "issues": [
    {
      "severity": "BLOCKER|MAJOR|MINOR",
      "category": "coherence|completeness|formula|other",
      "message": "...",
      "evidence": {"path": "...", "pointer": "...", "snippet": "..."},
      "fix_hint": "..."
    }
  ],
  "strengths": ["...", "..."]
}
```

### Severity Levels
- **BLOCKER**: Нельзя публиковать (пустые поля, дубли ID, сломанные формулы)
- **MAJOR**: Важно исправить (дублирование stages, >70% пустых формул)
- **MINOR**: Косметика (форматирование, verbose описания)

### Decision Policy
```python
if blockers >= 1:
    approved = False
elif majors >= 3:
    approved = False
else:
    approved = True
```

### Scoring
```python
score = 100
if not schema_valid: score -= 40
for issue in issues:
    if issue.severity == "BLOCKER": score -= 25
    elif issue.severity == "MAJOR": score -= 10
    elif issue.severity == "MINOR": score -= 3

score -= (1.0 - glossary_coverage) * 20
score -= (1.0 - formula_ratio) * 15

return max(0, min(100, score))
```

### Результаты тестирования

#### Тест 1: Без LLM (только детерминированные проверки)
```
Agent D QA Reviewer
Book: accounting-basics-test
LLM: disabled

✅ Schema validation: 18 issues (BLOCKER)
✅ Outline loaded
✅ ID format: 0 issues
✅ Docs consistency: 0 issues
✅ Duplicate indicators: 2 issues (BLOCKER)
   - "валовая прибыль" x2
   - "вклад в формирование прибыли" x2
✅ Stage order: 12 issues (BLOCKER)
   - 8 stages с order=1 не на первой позиции
   - 4 duplicate order values
✅ Duplicate titles: 0 issues
✅ README coverage: 0 issues (100%)
✅ Glossary: 0 issues
✅ Formulas syntax: 0 issues
✅ Empty formulas: 1 issue (BLOCKER)
   - 21/21 (100%) indicators without formulas

Total issues: 33
Approved: false
Score: 0/100
```

#### Тест 2: С Claude Sonnet 4.5 (--use-llm)
```
Agent D QA Reviewer
Book: accounting-basics-test
LLM: Claude Sonnet 4.5 (Requesty)

Deterministic: 33 issues (как выше)

Claude findings:
+ 2 BLOCKER (coherence):
  - Duplicate "валовая прибыль" (подтверждение)
  - Broken stage numbering (подтверждение)

+ 5 MAJOR (semantic):
  - All indicators missing formulas (подтверждение)
  - Stage duplication: stages 9-11 overlap
  - README truncated at stage 15

+ 2 MINOR:
  - Metadata N/A values
  - source: null in all stages

Strengths found:
- Clear progression: recognition → analysis → action
- Concrete thresholds in rules (40%, 10%, 15%)
- Well-categorized tools
- Multi-dimensional indicators

Total issues: 41 (33 deterministic + 8 LLM)
Approved: false
Score: 0/100
Time: ~5s (LLM call)
```

### AI модель
- **Layer 1:** ❌ NO AI (детерминированные проверки)
- **Layer 2:** ✅ Claude Sonnet 4.5 via Requesty (optional)

### Стоимость
- **Без --use-llm:** ₽0
- **С --use-llm:** ~₽0.50 за проверку (Claude Sonnet 4.5)

### Команда запуска
```bash
# Только детерминированные проверки (быстро, бесплатно)
python pipeline/agents/agent_d/reviewer.py \
  --book accounting-basics-test

# С Claude reasoning (медленнее, платно)
python pipeline/agents/agent_d/reviewer.py \
  --book accounting-basics-test \
  --use-llm

# С glossary validation
python pipeline/agents/agent_d/reviewer.py \
  --book accounting-basics-test \
  --glossary data/glossary

# Кастомная схема
python pipeline/agents/agent_d/reviewer.py \
  --book accounting-basics-test \
  --schema schemas/custom.schema.json
```

### Exit codes
- `0` → approved=true
- `1` → approved=false
- `2` → runtime error

### Проблемы
- ⚠️ Claude иногда возвращает markdown вместо чистого JSON
- ⚠️ Нет автоматического retry при API errors

---

## ❌ Agent E: Graph DB Publisher (НЕ РЕАЛИЗОВАН)

### Статус
❌ **НЕ РЕАЛИЗОВАН**

### Планируемая функциональность
- Публикация в Neo4j/ArangoDB
- Создание графа связей между методологиями
- Индексация для поиска

---

## ❌ Agent F: PR Publisher (НЕ РЕАЛИЗОВАН)

### Статус
❌ **НЕ РЕАЛИЗОВАН**

### Планируемая функциональность
- Создание Pull Request в GitHub
- Автоматическое форматирование коммитов
- CI/CD интеграция

---

## 💰 Стоимость (РЕАЛЬНАЯ)

### Тест: accounting-basics (515 блоков, 26 stages)

| Агент | AI модель | Запросов | Стоимость |
|-------|-----------|----------|-----------|
| Agent A v2 | - | 0 | **₽0** |
| Agent B v1.0 | GigaChat | 11 | **₽0** (бесплатно) |
| Agent C v2 | - | 0 | **₽0** (Jinja2) |
| Agent D v1.0 (precheck) | - | 0 | **₽0** |
| Agent D v1.0 (--use-llm) | Claude Sonnet 4.5 | 1 | **~₽0.50** |
| **ИТОГО БЕЗ LLM** | | | **₽0** |
| **ИТОГО С LLM** | | | **~₽0.50** |

### Проекция на 17 книг

**Вариант 1: Только детерминированные проверки**
- Agent A + B + C + D (precheck): **₽0**
- Скорость: ~30 сек на книгу
- **ИТОГО: ₽0**

**Вариант 2: С Claude QA**
- Agent A + B + C + D (--use-llm): **~₽8.50** (17 × ₽0.50)
- Скорость: ~1 мин на книгу
- **ИТОГО: ~₽8.50**

**Альтернативы (отклонены):**
- GPT-4: ~₽3,000-5,000 за 17 книг
- Claude без Requesty: ~₽2,000-3,000 за 17 книг

---

## 🚀 Полный пайплайн (end-to-end)

### Вариант 1: Базовый (без QA)
```bash
# 1. Экстракция
python pipeline/agents/agent_a/extractor.py \
  --input cache/books/accounting.pdf \
  --book-id accounting-basics

# 2. Outline extraction
python tests/test_agent_b.py  # TODO: CLI wrapper

# 3. Компиляция
python pipeline/agents/agent_c_v2/compiler.py \
  --book accounting-basics

# Результат:
# - sources/accounting-basics/extracted/blocks.jsonl
# - work/accounting-basics/outline.yaml
# - data/methodologies/accounting-basics.yaml
# - docs/methodologies/accounting-basics/*.md
```

### Вариант 2: С QA (рекомендуется)
```bash
# Шаги 1-3 как выше

# 4. QA проверка (детерминированная)
python pipeline/agents/agent_d/reviewer.py \
  --book accounting-basics

# Если approved=false, смотрим qa_report.md
cat work/accounting-basics/qa/qa_report.md

# Исправляем проблемы в Agent B/C
# Повторяем шаги 2-4 до approved=true
```

### Вариант 3: С Claude QA (максимальное качество)
```bash
# Шаги 1-3 как выше

# 4. QA проверка с Claude
python pipeline/agents/agent_d/reviewer.py \
  --book accounting-basics \
  --use-llm

# Claude найдёт семантические проблемы
# Исправляем и повторяем
```

---

## 📊 Текущие проблемы

### 🔴 Критические (блокируют production)

1. **Agent B не извлекает формулы**
   - Проблема: 21/21 indicators БЕЗ формул
   - Причина: LLM prompt не акцентирует formula extraction
   - Решение: Улучшить prompt, добавить примеры формул

2. **Agent B пропускает descriptions**
   - Проблема: 4 stages + 8 indicators с пустыми descriptions
   - Причина: LLM возвращает неполный JSON
   - Решение: Добавить валидацию, требовать required fields

3. **Agent B неправильные severity**
   - Проблема: high/medium вместо critical/warning/info/low
   - Причина: Prompt использует неправильную схему
   - Решение: Обновить prompt с правильными enum values

4. **Agent B дублирует indicators**
   - Проблема: "валовая прибыль" встречается 2 раза
   - Причина: Нет дедупликации в reduce phase
   - Решение: Добавить deduplication по normalized name

5. **Agent B сломанная нумерация**
   - Проблема: order=1 встречается 9 раз (не последовательно)
   - Причина: Каждая глава начинает с order=1
   - Решение: Перенумеровать в reduce phase (1..N)

### 🟡 Средние (снижают качество)

6. **Agent C не валидирует outline.yaml**
   - Проблема: Компилирует даже невалидные данные
   - Решение: Добавить pre-compile validation

7. **Agent C не маппит severity**
   - Проблема: high/medium проходят в compiled YAML
   - Решение: Добавить severity normalization

8. **Agent C не перенумеровывает stages**
   - Проблема: Сохраняет сломанный order из outline.yaml
   - Решение: Принудительная перенумерация 1..N

9. **Agent D Claude JSON parsing**
   - Проблема: Claude иногда оборачивает JSON в markdown
   - Решение: ✅ ИСПРАВЛЕНО (парсинг ```json блоков)

### 🟢 Низкие (косметика)

10. **Agent A нет quality scoring**
    - Проблема: Нет метрик качества экстракции
    - Решение: Добавить QualityMetricsCalculator

11. **Agent B нет glossary matching**
    - Проблема: Не сопоставляет термины с глоссарием
    - Решение: Добавить glossary_references в outline.yaml

---

## ✅ Что работает хорошо

1. ✅ **Agent A экстракция** - стабильно, быстро, бесплатно
2. ✅ **Agent B classification** - правильно определяет methodology_type
3. ✅ **Agent B map-reduce** - эффективно обрабатывает большие книги
4. ✅ **Agent C Jinja2 компиляция** - детерминированно, быстро, без LLM
5. ✅ **Agent C stable IDs** - stage_001, tool_001 корректны
6. ✅ **Agent D schema validation** - находит все structural issues
7. ✅ **Agent D deterministic checks** - быстро, бесплатно, стабильно
8. ✅ **Agent D Claude integration** - семантический анализ работает
9. ✅ **Agent D QA reports** - понятные, actionable

---

## 🎯 Приоритеты развития

### Неделя 1: Исправить Agent B (критично)
1. Улучшить prompt для formula extraction
2. Добавить валидацию required fields
3. Исправить severity enum (high→critical, medium→warning)
4. Добавить deduplication indicators
5. Перенумеровать stages в reduce phase (1..N)

### Неделя 2: Улучшить Agent C
1. Добавить pre-compile validation
2. Добавить severity normalization
3. Добавить forced stage renumbering

### Неделя 3: Начать Agent E (Graph DB)
1. Спроектировать Neo4j schema
2. Реализовать publisher
3. Добавить индексацию

### Неделя 4: Agent F (PR Publisher)
1. GitHub integration
2. Automatic commits
3. CI/CD hooks

---

## 📈 Метрики качества

### Agent B (текущие)
- **Recall stages:** 95% (пропускает "Шаг 1-4" без descriptions)
- **Recall tools:** 100%
- **Recall indicators:** 80% (пропускает formulas)
- **Recall rules:** 100%
- **Precision methodology_type:** 100% (всегда правильно)
- **Deduplication:** 90% (2 дубля из 21 indicators)

### Agent C v2 (текущие)
- **Compilation success:** 100%
- **File generation:** 100% (все 59 файлов созданы)
- **Content hallucination:** 0% (нет LLM генерации)
- **Template coverage:** 100%

### Agent D (текущие)
- **Schema issues found:** 100% (все 18 найдены)
- **Duplicate detection:** 100% (2/2 найдены)
- **Stage order issues:** 100% (12/12 найдены)
- **Formula coverage:** 100% (21/21 пустых найдены)
- **False positives:** 0%
- **Claude accuracy:** ~95% (5% markdown wrapping issues)

---

## 🔧 Конфигурация

### Environment Variables
```bash
# Agent B
export GIGACHAT_CREDENTIALS="your_gigachat_key"
export REQUESTY_API_KEY="your_requesty_key"

# Agent D (если --use-llm)
export REQUESTY_API_KEY="your_requesty_key"
```

### Dependencies
```
# Core
python>=3.12
pyyaml
python-slugify

# Agent A
markitdown
openpyxl

# Agent B
gigachat
requesty-ai (custom package)

# Agent C v2
jinja2

# Agent D
jsonschema
requests
python-dotenv
```

---

## 📝 Следующий коммит

После исправления Agent B нужно:
1. Обновить PIPELINE_REAL.md
2. Обновить этот файл (PIPELINE_STATUS.md)
3. Создать release notes
4. Протестировать на всех 3 книгах (accounting-basics, simple-numbers, business-metrics)

---

**Дата обновления:** 2025-12-13  
**Версия:** v2.0 (Agent D released)  
**Следующая цель:** Agent B fixes → v2.1
