# Orchestrator CLI

MVP pipeline runner для координации агентов B→C→D→Gate→G→E.

## Установка

Orchestrator уже включен в репозиторий, требуются только базовые зависимости:

```bash
pip install pyyaml
```

## Быстрый старт

### Полный RAG pipeline (рекомендуется)

```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps B_RAG,C,D,Gate,G,E,H
```

### Legacy sequential pipeline

```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps B,C,D,Gate,G,E
```

### Semantic linking only

```bash
python -m pipeline.orchestrator_cli \
  --book-id toc \
  --steps H
```

### Gate-only (проверка существующего outline)

```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps Gate
```

### Re-publish (пропустить B/C/D)

```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps Gate,G,E
```

## Аргументы

- `--book-id` (required): ID методологии (например, `accounting-basics-test`)
- `--steps` (default: `B,C,D,Gate,G,E`): Список шагов через запятую
- `--run-id` (optional): Уникальный ID запуска (default: `kb_<timestamp>`)
- `--require-gate-pass` (default: true): Останавливать pipeline при Gate FAIL
- `--no-require-gate-pass`: Продолжать даже при Gate FAIL (для отладки)
- `--skip-qa`: Передать `--skip-qa` в Agent E
- `--use-gigachat`: Использовать GigaChat в Agent B
- `--g-reconcile`: Передать `--reconcile` в Agent G
- `--g-dry-run`: Передать `--dry-run` в Agent G

## Поддерживаемые шаги

| Шаг | Агент | Описание |
|-----|-------|----------|
| B | OutlineBuilder | Генерация outline.yaml из blocks.jsonl (sequential mode) |
| B_RAG | RAGExtractor | Vector-based extraction via Qdrant (4x faster, 10x cheaper) |
| C | Compiler | Компиляция MD файлов из outline |
| D | QA Reviewer | Валидация методологии |
| Gate | B_QUALITY_GATE | Проверка структуры outline (останавливает при FAIL) |
| G | GlossarySync | Синхронизация глоссария |
| E | PR Publisher | Подготовка PR |
| F | Release Summary | Генерация релиз-ноут |
| H | SemanticLinker | Создание semantic edges в ArangoDB (stage↔indicator/tool/rule) |

## Порядок выполнения

**Полный RAG pipeline** (рекомендуется):
```
B_RAG → C → D → Gate [PASS] → G → E → H
```

**Legacy sequential pipeline**:
```
B → C → D → Gate [PASS] → G → E
```

**Gate FAIL flow**:
```
B_RAG → C → D → Gate [FAIL] → STOP (G, E, H пропущены)
```

**Semantic linking only** (уже есть entities в ArangoDB):
```
H
```

## Выходные данные

### Manifest

После каждого запуска создается `qa/runs/<run_id>/manifest.json`:

```json
{
  "run_id": "kb_1734170000",
  "book_id": "accounting-basics-test",
  "source_path": "sources/accounting-basics-test",
  "created_at": "2025-12-14T10:00:00+0000",
  "steps": [
    {
      "name": "Gate",
      "status": "ok",
      "started_at": "2025-12-14T10:00:00+0000",
      "ended_at": "2025-12-14T10:00:01+0000",
      "duration_sec": 0.076,
      "artifacts": ["qa/runs/kb_1734170000/b_quality_gate.json"],
      "error": null
    }
  ],
  "qa": {
    "gate_status": "PASS",
    "approved": true,
    "blockers": 0,
    "warnings": 2
  },
  "policy": {
    "require_gate_pass": true
  }
}
```

### Статусы шагов

- `ok`: Шаг выполнен успешно
- `fail`: Ошибка выполнения (exception, missing file, non-zero exit)
- `skipped`: Пропущен из-за более раннего FAIL

### Exit codes

| Code | Значение |
|------|----------|
| 0 | Успех (все шаги завершены, Gate PASS если запущен) |
| 1 | Ошибка выполнения (exception, missing file, agent crashed) |
| 2 | Gate FAIL (Quality Gate вернул FAIL, pipeline остановлен) |

## Примеры

### Тест Gate на существующем outline

```bash
# Сначала нормализуем outline (если нужно)
python normalize_outline.py work/accounting-basics-test/outline.yaml

# Запускаем Gate
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps Gate
  
# Проверяем результат
echo $?  # 0 = PASS, 2 = FAIL
cat qa/runs/kb_*/manifest.json
```

### Полный цикл с пользовательским run_id

```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps B,C,D,Gate,G,E \
  --run-id my_test_run_$(date +%s)
```

### Отладка: продолжить даже при Gate FAIL

```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps B,C,D,Gate,G,E \
  --no-require-gate-pass
```

## Обработка ошибок

### Agent Exception

Если любой агент выбрасывает exception:
1. Записывается `status="fail"` в manifest с `error_message`
2. Последующие шаги получают `status="skipped"`
3. Pipeline завершается с exit code 1

### Missing Input Files

Если входной файл не найден (например, `blocks.jsonl`, `outline.yaml`):
1. Шаг фейлится с `status="fail"`
2. Последующие шаги `status="skipped"`
3. Exit code 1

### Gate FAIL

Если Gate возвращает exit code 2:
1. Шаг Gate: `status="ok"` (Gate выполнился успешно, результат FAIL)
2. `qa.gate_status="FAIL"`, `qa.blockers=N`
3. Если `--require-gate-pass=true` (default):
   - G, E НЕ выполняются (status="skipped" с error="Skipped due to Gate FAIL")
   - Exit code 2
4. Если `--no-require-gate-pass`:
   - G, E продолжают выполнение
   - Exit code 0 если G, E успешны

## Архитектура

```
pipeline/orchestrator_cli/
├── __init__.py         # Пакет
├── __main__.py         # CLI entry point (argparse)
├── runner.py           # OrchestratorRunner: выполнение шагов
└── manifest.py         # RunManifest: tracking с таймингами
```

### Вызов агентов

- **Agent B**: Python API (`OutlineBuilder.build_outline()`)
- **Agent C**: Python API (`compile_methodology(book_id)`)
- **Agent D**: Python API (`validate_methodology(book_id)`)
- **Gate**: CLI subprocess (`python pipeline/agents/agent_b/quality_gate.py`)
- **Agent G**: CLI subprocess (`python -m pipeline.agents.agent_g_glossary_sync`)
- **Agent E**: CLI subprocess (`python -m pipeline.agents.agent_e <book_id>`)

## Особенности реализации

### Gate Input Resolution

Gate ищет outline в следующем порядке:
1. `work/<book_id>/outline_<book_id>.yaml` (предпочтительный)
2. `work/<book_id>/outline.yaml` (legacy fallback)
3. Любой `outline*.yaml` в алфавитном порядке

Если ни один не найден → Pipeline STOPS с exit code 1.

### Обязательные тайминги

Каждый шаг записывает:
- `started_at`: ISO8601 timestamp начала
- `ended_at`: ISO8601 timestamp конца
- `duration_sec`: Длительность в секундах (float)

Это необходимо для метрик деградации и оптимизации.

### QA Aggregation

После Agent D orchestrator извлекает:
- `qa.approved`: bool (методология одобрена?)
- `qa.blockers`: int (количество блокеров)
- `qa.warnings`: int (количество warnings)

Эти данные доступны даже если Gate не запускался.

## Разработка

### Добавление нового шага

1. Добавить шаг в `ALLOWED_STEPS` в `runner.py`
2. Реализовать метод `step_<Name>(self) -> List[str]`
3. Добавить в `run()` обработку нового шага
4. Обновить документацию

### Тестирование

```bash
# Gate-only (быстро)
python -m pipeline.orchestrator_cli --book-id accounting-basics-test --steps Gate

# Full pipeline (долго, требует LLM)
python -m pipeline.orchestrator_cli --book-id accounting-basics-test --steps B,C,D,Gate,G,E
```

## Roadmap

### MVP (DONE ✅)
- [x] CLI interface с argparse
- [x] Выполнение B,C,D,Gate,G,E
- [x] Manifest с таймингами
- [x] Exit codes 0/1/2
- [x] Gate FAIL останавливает pipeline
- [x] QA aggregation из Agent D

### v2 (TODO)
- [ ] VS Code Tasks (.vscode/tasks.json)
- [ ] Параллельное выполнение независимых шагов
- [ ] Resume from failed step
- [ ] Agent F (PR Publisher)
- [ ] MCP Server integration

## Поддержка

Для вопросов и проблем создайте issue в репозитории.
