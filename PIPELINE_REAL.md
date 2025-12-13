# РЕАЛЬНАЯ АРХИТЕКТУРА PIPELINE

> Этот документ описывает **РЕАЛЬНУЮ** имплементацию, а не теоретические планы.

## 📊 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT: PDF/DOCX/PPTX файлы                                      │
└───────────────────────┬─────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ Agent A: Document Extractor                                     │
│ ВХОД:  cache/books/<file>                                       │
│ ВЫХОД: sources/<book_id>/extracted/blocks.jsonl                 │
│ AI:    ❌ НЕТ (только markitdown + openpyxl)                    │
└───────────────────────┬─────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ Agent B: Outline Builder                                        │
│ ВХОД:  sources/<book_id>/extracted/blocks.jsonl                 │
│ ВЫХОД: work/<book_id>/outline.yaml + outline.json              │
│ AI:    ✅ GigaChat (primary) + Qwen3-Max (fallback)             │
└───────────────────────┬─────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ Agent C: Compiler                                               │
│ ВХОД:  work/<book_id>/outline.yaml                             │
│ ВЫХОД: docs/methodologies/<id>/*.md                            │
│        data/methodologies/<id>.yaml                            │
│ AI:    ✅ GigaChat Lite (primary) + Qwen3-Max (fallback)        │
└───────────────────────┬─────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ Agent D: QA Reviewer (НЕ РЕАЛИЗОВАН)                           │
│ Agent E: Graph DB Publisher (НЕ РЕАЛИЗОВАН)                    │
│ Agent F: PR Publisher (НЕ РЕАЛИЗОВАН)                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Agent A: Document Extractor

### Статус
✅ **РЕАЛИЗОВАН** (базовая версия)

### Вход
```
cache/books/<filename>.pdf|docx|pptx|xlsx
```

### Выход
```
sources/<book_id>/
├── extracted/
│   ├── blocks.jsonl       # ← Основной выход
│   └── full_text.md       # Для человека (опционально)
└── raw/
    └── original.<ext>
```

### Что делает
1. **markitdown** конвертирует файл → markdown
2. **BlocksConverter** парсит markdown → blocks.jsonl
3. **Каждый блок** = одна строка JSON

### Формат blocks.jsonl
```jsonl
{"id": "block_001", "type": "paragraph", "text": "Текст абзаца...", "source": {"page": 1}, "meta": {}}
{"id": "block_002", "type": "heading", "text": "Глава 1", "source": {"page": 2}, "meta": {"level": 1}}
{"id": "block_003", "type": "table", "text": "| A | B |\n|---|---|\n| 1 | 2 |", "source": {"page": 3}, "meta": {}}
```

### Типы блоков
- `paragraph` - обычный текст
- `heading` - заголовок (meta.level: 1-6)
- `table` - таблица
- `list` - список
- `formula` - формула
- `page_break` - разрыв страницы

### AI модель
❌ **НЕТ** - чисто детерминированная обработка

### Ограничения
⚠️ **НЕ РЕАЛИЗОВАНО:**
- manifest.json с метриками качества
- quality scoring (0-100)
- routing logic (ok_for_outline / needs_repair)
- OCR repair mode

---

## 🧠 Agent B: Outline Builder

### Статус
✅ **РЕАЛИЗОВАН и ПРОТЕСТИРОВАН**

### Вход
```
sources/<book_id>/extracted/blocks.jsonl
```

### Выход
```
work/<book_id>/
├── outline.yaml      # ← Главный выход
└── outline.json      # Для машин
```

### AI Стратегия
- 🥇 **PRIMARY:** GigaChat (бесплатно, 1.06s, правильно определяет методологию)
- 🥈 **FALLBACK:** Qwen3-Max через Requesty AI (4.04s, корректный JSON с русскими ключами)

### Алгоритм

#### 1. Chunking (разбиение на главы)
```python
# Логика:
if есть heading (level ≤ 2):
    group_by_headings()
else:
    chunk_by_50_blocks()
```

#### 2. Map Phase (для каждой главы)
```python
for chapter in chapters:
    analysis = llm.analyze_chapter(chapter)
    # Извлекает: stages, tools, indicators, rules
```

#### 3. Reduce Phase
```python
outline = {
    'metadata': {...},
    'classification': {'methodology_type': '...'},
    'structure': {
        'stages': merge_and_dedupe(all_stages),
        'tools': merge_and_dedupe(all_tools),
        'indicators': merge_and_dedupe(all_indicators),
        'rules': merge_and_dedupe(all_rules)
    }
}
```

### System Prompt (РЕАЛЬНЫЙ)
```
Ты эксперт-методолог по финансовому анализу и бухгалтерии.

Твоя задача — извлекать структурированную информацию из финансовых книг.

Извлеки из текста:

1. **Stages (этапы методологии)**: шаги, которые нужно выполнить
   Формат: [{"title": "название", "description": "описание", "order": 1}]

2. **Tools (инструменты)**: таблицы, шаблоны, чек-листы
   Формат: [{"title": "название", "type": "table|template|checklist", "description": "описание"}]

3. **Indicators (показатели)**: метрики, формулы
   Формат: [{"name": "название", "formula": "формула если есть", "description": "описание"}]

4. **Rules (правила)**: условия и действия
   Формат: [{"condition": "когда", "action": "что делать", "severity": "high|medium|low"}]

5. **Methodology type**: определи тип методологии
   Варианты: diagnostic | planning | analysis | standard

Ответь в формате JSON:
{
  "methodology_type": "diagnostic|planning|analysis|standard",
  "stages": [...],
  "tools": [...],
  "indicators": [...],
  "rules": [...]
}
```

### User Prompt (РЕАЛЬНЫЙ)
```
**Глава:** {chapter['title']}

**Текст:**
{chapter_text}
```

### Формат outline.yaml (РЕАЛЬНЫЙ ПРИМЕР)
```yaml
metadata:
  agent: Agent B v1.0 (GigaChat + Qwen3-Max)
  model_used: gigachat
  chapters_processed: 11

classification:
  methodology_type: analysis

structure:
  stages:
    - title: Признание роли бухгалтерии
      description: Осознание влияния бухгалтерии на прибыль компании...
      order: 1
    - title: Определение слабостей компании
      description: Выявление проблем через недооценивание...
      order: 2

  tools:
    - title: Каскадная диаграмма
      type: template
      description: График выручки по категориям клиентов

  indicators:
    - name: Валовая прибыль
      formula: "Выручка - Себестоимость"
      description: Ключевой показатель рентабельности

  rules:
    - condition: Снижение закупок клиента более 20%
      action: Связаться с клиентом для выяснения причин
      severity: high
```

### Результаты тестирования
- Тест: `accounting-basics` (515 блоков)
- Модель: gigachat (primary)
- Chunks: 11 (по 50 блоков)
- Результат:
  * ✅ 36 stages
  * ✅ 3 tools
  * ✅ 19 indicators
  * ✅ 10 rules
  * ✅ methodology_type: analysis
- Ошибки: 2/11 chunks (GigaChat вернул JSON с комментариями)

---

## 📝 Agent C: Compiler

### Статус
✅ **РЕАЛИЗОВАН и ПРОТЕСТИРОВАН**

### Вход
```
work/<book_id>/outline.yaml
```

### Выход
```
docs/methodologies/<id>/
├── README.md                  # Обзор методологии
├── stages/
│   ├── stage_01_*.md
│   ├── stage_02_*.md
│   └── ...
├── tools/
│   └── tool_01_*.md
└── indicators/
    └── indicator_01_*.md

data/methodologies/<id>.yaml   # Копия outline.yaml
```

### AI Стратегия
- 🥇 **PRIMARY:** GigaChat Lite (быстро, дешево, для шаблонов)
- 🥈 **FALLBACK:** Qwen3-Max через Requesty AI

### Что делает

#### 1. Генерация README.md
**System Prompt:**
```
Ты эксперт по финансовой методологии и техническому писательству.
Твоя задача - создавать четкие, структурированные README для финансовых методологий.

Требования:
- Используй markdown форматирование
- Будь кратким и конкретным
- Фокусируйся на практической пользе
- Используй профессиональную терминологию
```

**User Prompt:**
```
Создай README.md для методологии.

**Данные:**

Метаданные:
{yaml.dump(metadata)}

Классификация:
{yaml.dump(classification)}

Этапы:
{yaml.dump(stages)}

**Требования к README:**

# Название методологии

## 📋 Описание
[Краткое описание]

## 🎯 Тип методологии
[{methodology_type}]

## 📊 Структура
### Этапы методологии
1. **[Название]** - [Описание]

## 📚 Связанные разделы
- [Stages](./stages/)
- [Tools](./tools/)
- [Indicators](./indicators/)

Сгенерируй только содержимое README в markdown формате.
```

#### 2. Генерация stage_XX.md
**System Prompt:**
```
Ты эксперт по финансовым методологиям и процессам.
Твоя задача - создавать подробную документацию для каждого этапа методологии.

Требования:
- Четкая структура
- Пошаговые инструкции
- Практические примеры
- Связь с другими этапами
```

**User Prompt:**
```
Создай детальную документацию для этапа методологии.

**Данные этапа:**
{yaml.dump(stage)}

**Требования к документу:**

# {stage.title}

## 📝 Описание
{stage.description}

## 🔢 Порядок выполнения
Этап {stage.order}

## 📋 Подэтапы
[Если есть substages]

## 🛠 Используемые инструменты
[Если есть связанные tools]

## 📊 Измеряемые показатели
[Если есть связанные indicators]

## 💡 Практические рекомендации
[Советы по выполнению]

## ⚠️ Частые ошибки
[Типичные проблемы]

Сгенерируй только содержимое в markdown формате.
```

#### 3. Аналогично для tools, indicators

### Результаты тестирования
- Тест: `accounting-basics` outline.yaml
- Создано:
  * ✅ README.md (6.3KB, профессиональный обзор)
  * ✅ stage_01_priznanie_roli_buhgalterii.md (детальное описание + практические рекомендации + частые ошибки)
  * ✅ stage_02_opredelenie_slabostey_kompanii.md
  * ✅ data/methodologies/accounting-basics.yaml

### ⚠️ Проблема: LLM ГЕНЕРИРУЕТ КОНТЕНТ

**Текущая реализация:**
- LLM **придумывает** "Практические рекомендации"
- LLM **придумывает** "Частые ошибки"
- LLM **интерпретирует** данные, а не просто форматирует

**Это НЕ компилятор!** Это генератор контента.

**Правильная архитектура (по gpt_4.md):**
- Agent C должен только **форматировать** данные из outline.yaml
- Использовать **Jinja2 шаблоны**
- LLM только для переформулирования существующего текста
- НЕ добавлять новый контент

---

## 📊 Форматы данных

### blocks.jsonl
```jsonl
{"id": "block_001", "type": "paragraph", "text": "...", "source": {"page": 1}, "meta": {}}
{"id": "block_002", "type": "heading", "text": "...", "source": {"page": 2}, "meta": {"level": 1}}
```

**Особенности:**
- Один блок = одна строка JSON
- Легко читать построчно (не грузит всю книгу в память)
- Типизированные блоки (paragraph, heading, table, formula, list)

### outline.yaml
```yaml
metadata:
  agent: "Agent B v1.0"
  model_used: "gigachat"
  chapters_processed: 11

classification:
  methodology_type: "analysis"

structure:
  stages: [...]
  tools: [...]
  indicators: [...]
  rules: [...]
```

**Особенности:**
- Человекочитаемый (для review)
- Иерархическая структура
- Легко парсится (PyYAML)

---

## 💰 Стоимость (РЕАЛЬНАЯ)

### Тест accounting-basics

| Агент | Модель | Запросов | Стоимость |
|-------|--------|----------|-----------|
| Agent A | - | 0 | ₽0 |
| Agent B | GigaChat | 11 chunks | ₽0 (бесплатно) |
| Agent C | GigaChat Lite | ~10 (README + stages) | ₽0 (бесплатно) |
| **ИТОГО** | | | **₽0** |

### Проекция на 17 книг
- GigaChat стратегия: **₽0** (100% бесплатно)
- Альтернатива (Qwen3-Max): ~₽50-100 за все книги
- Альтернатива (Claude/GPT-4): ~₽3,500-5,000 за все книги

---

## 🚀 Как запустить

### Agent A
```bash
# TODO: Создать test_agent_a.py
```

### Agent B
```bash
python tests/test_agent_b.py

# Требует:
export GIGACHAT_CREDENTIALS="your_key"
export REQUESTY_API_KEY="your_key"

# Вход: sources/accounting-basics-test/extracted/blocks.jsonl
# Выход: work/accounting-basics-test/outline.yaml
```

### Agent C
```bash
python tests/test_agent_c.py

# Требует:
export GIGACHAT_CREDENTIALS="your_key"
export REQUESTY_API_KEY="your_key"

# Вход: work/accounting-basics-test/outline.yaml
# Выход: docs/methodologies/accounting-basics/*.md
```

---

## ❌ Что НЕ РЕАЛИЗОВАНО

### Agent A
- [ ] manifest.json с метриками качества
- [ ] QualityMetricsCalculator
- [ ] Routing logic (ok/warnings/repair)
- [ ] OCR repair mode

### Agent B
- [x] Основная функциональность ✅
- [ ] Glossary matching (сопоставление с глоссарием)
- [ ] Улучшенный JSON parsing (обработка комментариев от GigaChat)

### Agent C
- [x] Основная функциональность ✅
- [ ] Валидация outline.yaml по schema
- [ ] Нормализация типов (diagnostic → diagnostic_methodology)
- [ ] Jinja2 шаблоны вместо LLM generation
- [ ] Детерминированная часть (без LLM для структуры)

### Agent D, E, F
- [ ] Полностью не реализованы

---

## 🎯 Следующие шаги

1. **Переработать Agent C** по архитектуре gpt_4.md:
   - Добавить Jinja2 шаблоны
   - Валидация + нормализация без LLM
   - LLM только для форматирования текста

2. **Улучшить Agent A**:
   - Добавить QualityMetricsCalculator
   - Реализовать manifest.json
   - Routing logic

3. **Начать Agent D (QA Reviewer)**:
   - Проверка логической связности
   - Валидация glossary terms
   - Оценка полноты методологии
