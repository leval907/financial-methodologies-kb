# Tests

Тесты для pipeline агентов

## Структура

```
tests/
├── test_agent_a.py     # Тесты Agent A (Document Extractor)
├── test_agent_b.py     # Тесты Agent B (Outline Builder)
├── test_agent_c.py     # Тесты Agent C (Compiler)
└── ...
```

## Запуск тестов

### Agent B (Outline Builder)

```bash
# Из корня проекта
python tests/test_agent_b.py
```

**Что тестирует:**
- Загрузка blocks.jsonl
- Разбиение на главы/chunks
- Запросы к GigaChat (primary) + Qwen3-Max (fallback)
- Извлечение stages, tools, indicators, rules
- Генерация outline.yaml

**Требуется:**
- GigaChat API key (из `/home/leval907/finance-knowledge/.env`)
- Requesty AI API key (уже настроен)
- Входной файл: `sources/accounting-basics-test/extracted/blocks.jsonl`

**Результат:**
- `work/accounting-basics-test/outline.yaml`
- `work/accounting-basics-test/outline.json`

## Конфигурация

Переменные окружения (`.env` в корне):
```bash
GIGACHAT_API_KEY=MDE5...
REQUESTY_API_KEY=rqsty-sk-...
```
