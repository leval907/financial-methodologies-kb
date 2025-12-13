# Agent E: Graph DB Publisher

Загружает одобренные методологии из Agent C/D в ArangoDB.

## Назначение

Agent E - финальный этап публикации методологий. Берет compiled YAML от Agent C (опционально с QA approval от Agent D) и загружает в ArangoDB для:
- Графовых запросов
- Полнотекстового поиска
- API доступа
- Визуализации связей

## Вход

- `data/methodologies/<id>.yaml` - compiled methodology (Agent C output)
- `data/qa/<id>.json` - QA report (Agent D output, опционально)
- `.env.arango` - credentials для ArangoDB

## Выход

- **ArangoDB collections**:
  - `methodologies` - основные документы методологий
  - `stages` - этапы методологий
  - `tools` - инструменты
  - `indicators` - показатели
  - `rules` - правила
  
- **ArangoDB edges**:
  - `methodology_has_stage` - связи методология → этап
  - `stage_uses_tool` - связи этап → инструмент
  - `stage_uses_indicator` - связи этап → показатель
  - `stage_has_rule` - связи этап → правило
  - `*_uses_term` - связи с глоссарием (автоматически создает term stubs)
  
- **Отчет**: `data/published/<id>.json` - результаты публикации

## Использование

```bash
# Публикация с проверкой QA approval
python -m pipeline.agents.agent_e accounting-basics-test

# Принудительная публикация (skip QA)
python -m pipeline.agents.agent_e accounting-basics-test --skip-qa

# С явным base_dir
python -m pipeline.agents.agent_e my-method --base-dir /path/to/repo
```

## Ключевые особенности

### 1. Идемпотентность

Agent E использует **upsert** операции на основе stable `_key`:
- `_key` = `methodology_id` для методологий
- `_key` = `stage_001`, `stage_002`... для этапов
- `_key` = `tool_001`, `ind_001`, `rule_001`... для остальных

Повторный запуск обновляет существующие документы (merge update).

### 2. Автоматическое создание term stubs

Если edge ссылается на `glossary_terms/<term_key>`, а термин не существует:
- Создается **stub** с `status="needs_definition"`
- Добавляется **QA warning**

Это позволяет:
- Сохранить ссылки на термины
- Не блокировать публикацию
- Выявить пробелы в глоссарии

### 3. Lineage tracking

Каждый документ и edge содержит:
```json
{
  "source": {
    "repo": "financial-methodologies-kb",
    "ref": "main",
    "path": "data/methodologies/accounting-basics-test.yaml",
    "agent": "Agent E"
  },
  "compiled_hash": "sha256...",
  "created_at": "2025-12-13T...",
  "updated_at": "2025-12-13T..."
}
```

### 4. Content text для поиска

Каждая сущность получает `content_text` - конкатенацию:
- Methodology: title + description + tags
- Stage: title + description + tool names + indicator names
- Indicator: name + description + formula
- Tool: title + description

`content_hash` = SHA256 от `content_text` для детекции изменений.

### 5. Адаптация формата Agent C

Agent E понимает два формата YAML:
- **Старый**: `methodology_id` в корне
- **Новый**: `metadata.id`, `classification.methodology_type`, `structure.stages`

Автоматически нормализует в единый формат.

## Конфигурация ArangoDB

Файл `.env.arango` в корне репозитория:

```env
ARANGO_HOST=localhost
ARANGO_PORT=8529
ARANGO_DB=fin_kb_method
ARANGO_USER=root
ARANGO_PASSWORD=strongpassword
```

**Важно**: `.env.arango` в `.gitignore` (не коммитим credentials)

## Проверка QA approval

По умолчанию Agent E проверяет:
1. Наличие `data/qa/<id>.json`
2. Поле `approved: true` в QA report
3. Если не approved → ошибка

Флаг `--skip-qa` отключает проверку (для тестирования).

## Примеры вывода

### Успешная публикация

```
📚 Publishing methodology: accounting-basics-test
============================================================
✅ Loaded: accounting-basics-test.yaml
✅ QA approved
✅ Connected to ArangoDB

📦 Extracted entities:
  - Methodologies: 1
  - Stages: 26
  - Tools: 5
  - Indicators: 12
  - Rules: 8

🔗 Extracted edges:
  - methodology_has_stage: 26
  - stage_uses_tool: 15
  - stage_uses_indicator: 35
  - stage_has_rule: 8

📝 Upserting entities to ArangoDB...
  📝 methodologies: 0 inserted, 1 updated, 0 errors
  📝 stages: 2 inserted, 24 updated, 0 errors
  📝 tools: 1 inserted, 4 updated, 0 errors
  ...

✅ Published successfully!
📄 Report saved: data/published/accounting-basics-test.json

📊 Summary:
  Methodology: accounting-basics-test
  Entities upserted: 52
  Edges upserted: 84
  QA warnings: 3
```

### С term stubs

```
🔗 Upserting edges to ArangoDB...
  🔗 methodology_uses_term: 5 inserted, 0 updated, 3 term stubs created
  🔗 stage_uses_term: 12 inserted, 8 updated, 7 term stubs created
```

Означает: создано 10 term stubs (QA warnings добавлены).

## Структура отчета

`data/published/<id>.json`:

```json
{
  "methodology_id": "accounting-basics-test",
  "published_at": "2025-12-13T14:55:00+00:00",
  "agent": "Agent E v1.0",
  "source_yaml": "data/methodologies/accounting-basics-test.yaml",
  "compiled_hash": "abc123...",
  "qa_approved": true,
  "entities": {
    "methodologies": {"upserted": 1, "inserted": 0, "updated": 1},
    "stages": {"upserted": 26, "inserted": 2, "updated": 24},
    ...
  },
  "edges": {
    "methodology_has_stage": {"upserted": 26, ...},
    ...
  },
  "qa_warnings_count": 3
}
```

## Интеграция с другими агентами

```
Agent C (Compiler)
       ↓ data/methodologies/<id>.yaml
Agent D (QA Reviewer)
       ↓ data/qa/<id>.json
Agent E (Graph Publisher) ← ВЫ ЗДЕСЬ
       ↓ ArangoDB + data/published/<id>.json
Agent F (PR Publisher)
       ↓ GitHub PR
```

## Зависимости

```bash
pip install python-arango pyyaml python-dotenv
```

## Troubleshooting

### Error: [HTTP 401] not authorized

**Проблема**: Неверные credentials в `.env.arango`

**Решение**:
1. Проверьте `.env.arango` в корне репо
2. Убедитесь что `ARANGO_USER` и `ARANGO_PASSWORD` правильные
3. Попробуйте подключиться вручную: `arangosh --server.endpoint http+tcp://localhost:8529`

### Error: Missing methodology_id

**Проблема**: YAML файл не содержит `methodology_id` или `metadata.id`

**Решение**: Проверьте формат YAML. Agent E ожидает либо:
- `methodology_id: ...` в корне
- `metadata: {id: ...}` в корне

### QA failed with N issues

**Проблема**: Agent D не одобрил методологию

**Решение**:
1. Проверьте `data/qa/<id>.json`
2. Исправьте проблемы в исходном YAML
3. Пере-запустите Agent C и D
4. Или используйте `--skip-qa` для принудительной публикации

### Collection already exists

**Нормально**: Agent E использует идемпотентные операции. Повторный запуск обновит данные.

## Версия

Agent E v1.0 (December 2025)

## См. также

- [ArangoDB Schema](../../arangodb/README.md) - структура БД
- [Agent D](../agent_d/README.md) - QA проверки
- [Agent C v2](../agent_c_v2/README.md) - компиляция YAML
