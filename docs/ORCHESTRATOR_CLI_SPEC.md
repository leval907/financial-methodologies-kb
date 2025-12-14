# Orchestrator CLI - MVP Specification

## Overview

Минимальный pipeline runner который координирует запуск агентов B→C→D→Gate→G→E.

## Command Line Interface

```bash
python -m pipeline.orchestrator_cli \
  --book-id <id> \
  --steps B,C,D,Gate,G,E \
  --run-id kb_$(date +%s)
```

## Arguments

- `--book-id` (required): ID книги/методологии (напр. accounting-basics-test)
- `--steps` (optional, default: `B,C,D,Gate,G,E`): Список шагов через запятую
- `--run-id` (optional, default: `kb_<timestamp>`): Уникальный ID запуска
- `--skip-qa` (optional, flag): Пропустить QA approval check в Agent E
- `--require-gate-pass` (optional, default: true): Останавливать pipeline при Gate FAIL
- `--no-require-gate-pass` (optional): Продолжать pipeline даже при Gate FAIL (для отладки)

## Supported Steps

| Step | Agent | Implementation | Status |
|------|-------|----------------|--------|
| B | Outline Builder | Python API | ❌ No CLI |
| C | Compiler | Python function | ❌ No CLI |
| D | QA Reviewer | Python function | ❌ No CLI |
| Gate | B_QUALITY_GATE | CLI | ✅ Has CLI |
| G | Glossary Sync | CLI | ✅ Has CLI |
| E | Graph DB Publisher | CLI | ✅ Has CLI |

## Step Execution Details

### Step B: Outline Builder
```python
from pipeline.agents.agent_b.agent_b import OutlineBuilder

builder = OutlineBuilder(use_gigachat=True)
outline = builder.build_outline(
    blocks_jsonl_path=f"sources/{book_id}/extracted/blocks.jsonl"
)

# Save output
output_path = f"work/{book_id}/outline_{book_id}.yaml"
with open(output_path, 'w') as f:
    yaml.dump(outline, f, allow_unicode=True, sort_keys=False)
```

**Inputs**: `sources/{book_id}/extracted/blocks.jsonl`  
**Outputs**: `work/{book_id}/outline_{book_id}.yaml`

---

### Step C: Compiler
```python
from pipeline.agents.agent_c_v2.compiler import compile_methodology

# Note: function expects methodology_id, not book_id
compile_methodology(book_id)
```

**Inputs**: `work/{book_id}/outline_{book_id}.yaml`  
**Outputs**: `data/methodologies/{book_id}.yaml`, `work/{book_id}/compiled/*.md`

---

### Step D: QA Reviewer
```python
from pipeline.agents.agent_d.reviewer import validate_methodology

report = validate_methodology(book_id)

# Save report
output_path = f"work/{book_id}/qa/qa_result.json"
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
```

**Inputs**: `data/methodologies/{book_id}.yaml`  
**Outputs**: `work/{book_id}/qa/qa_result.json`

---

### Step Gate: B_QUALITY_GATE

**Input resolution** (в порядке приоритета):
1. `work/{book_id}/outline_{book_id}.yaml`
2. Fallback: `work/{book_id}/outline.yaml`
3. Если ни один файл не найден → Pipeline STOPS с exit code 1 (error)

```bash
python pipeline/agents/agent_b/quality_gate.py \
  --input <resolved_outline_path> \
  --report qa/runs/{run_id}/b_quality_gate.json
```

**Outputs**: `qa/runs/{run_id}/b_quality_gate.json`  
**Exit codes**: 0=PASS, 2=FAIL

**Critical**: If Gate returns exit code 2 (FAIL):
- Если `--require-gate-pass=true` → Pipeline **STOPS** (не выполняет G, E)
- Если `--no-require-gate-pass` → Pipeline **CONTINUES** с warning
- Manifest записывает: `gate_status="FAIL"`, `blockers=N`

---

### Step G: Glossary Sync
```bash
python -m pipeline.agents.agent_g_glossary_sync --reconcile
```

**Inputs**: `data/glossary/**/*.yaml`  
**Outputs**: ArangoDB glossary_terms collection, `work/glossary_sync_report.json`

---

### Step E: Graph DB Publisher
```bash
python -m pipeline.agents.agent_e {book_id} [--skip-qa]
```

**Inputs**: `data/methodologies/{book_id}.yaml`, `work/{book_id}/qa/qa_result.json`  
**Outputs**: ArangoDB collections, `data/published/{book_id}.json`

---

## Flow Control

### Normal Flow (Gate PASS)
```
B → C → D → Gate [PASS] → G → E
```

### Gate FAIL Flow
```
B → C → D → Gate [FAIL] → STOP
```

Manifest записывается в обоих случаях, но с разным статусом.

---

## Manifest Format

**Location**: `qa/runs/{run_id}/manifest.json`

```json
{
  "run_id": "kb_1734170000",
  "book_id": "accounting-basics-test",
  "source_path": "sources/accounting-basics-test",
  "created_at": "2025-12-14T10:00:00Z",
  "steps": [
    {
      "name": "B",
      "status": "ok",
      "started_at": "2025-12-14T10:00:00Z",
      "ended_at": "2025-12-14T10:02:00Z",
      "duration_sec": 120.5,
      "artifacts": ["work/accounting-basics-test/outline_accounting-basics-test.yaml"],
      "error": null
    },
    {
      "name": "C",
      "status": "ok",
      "started_at": "2025-12-14T10:02:00Z",
      "ended_at": "2025-12-14T10:02:15Z",
      "duration_sec": 15.2,
      "artifacts": [
        "data/methodologies/accounting-basics-test.yaml",
        "work/accounting-basics-test/compiled/"
      ],
      "error": null
    },
    {
      "name": "D",
      "status": "ok",
      "started_at": "2025-12-14T10:02:15Z",
      "ended_at": "2025-12-14T10:02:24Z",
      "duration_sec": 8.7,
      "artifacts": ["work/accounting-basics-test/qa/qa_result.json"],
      "error": null
    },
    {
      "name": "Gate",
      "status": "ok",
      "started_at": "2025-12-14T10:02:24Z",
      "ended_at": "2025-12-14T10:02:25Z",
      "duration_sec": 0.3,
      "artifacts": ["qa/runs/kb_1734170000/b_quality_gate.json"],
      "error": null
    },
    {
      "name": "G",
      "status": "ok",
      "started_at": "2025-12-14T10:02:25Z",
      "ended_at": "2025-12-14T10:02:30Z",
      "duration_sec": 5.1,
      "artifacts": ["work/glossary_sync_report.json"],
      "error": null
    },
    {
      "name": "E",
      "status": "ok",
      "started_at": "2025-12-14T10:02:30Z",
      "ended_at": "2025-12-14T10:02:43Z",
      "duration_sec": 12.8,
      "artifacts": ["data/published/accounting-basics-test.json"],
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

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (all selected steps completed, Gate PASS if included) |
| 1 | Execution error (exception, file not found, agent crashed) |
| 2 | Gate FAIL (Quality Gate returned FAIL, pipeline stopped) |

---

## Error Handling

**Step Status Values**:
- `ok`: шаг выполнен успешно
- `fail`: любая ошибка выполнения (exception, missing file, non-zero exit code)
- `skipped`: шаг пропущен из-за более раннего FAIL

### Agent Exception
If any agent raises exception:
1. Catch exception
2. Record step status = "fail" in manifest with error_message
3. Mark subsequent steps as "skipped"
4. Save manifest with partial results
5. Exit with code 1

### Missing Input Files
If input file not found (e.g., blocks.jsonl, outline.yaml missing):
1. Log error
2. Record step status = "fail" with error message
3. Mark subsequent steps as "skipped"
4. Save manifest
5. Exit with code 1

### Gate FAIL
If Gate returns exit code 2:
1. Record Gate step status = "ok" (Gate executed successfully, result is FAIL)
2. Record qa.gate_status = "FAIL", qa.blockers = N
3. Если `--require-gate-pass=true` (default):
   - Do NOT execute subsequent steps (G, E)
   - Mark G, E as "skipped" with error = "Skipped due to Gate FAIL"
   - Exit with code 2
4. Если `--no-require-gate-pass`:
   - Continue with G, E
   - Log warning about Gate FAIL
   - Exit with code 0 if G, E succeed

---

## Manifest Fields

**Root level** (REQUIRED):
- `run_id`: string - Unique ID запуска
- `book_id`: string - ID методологии
- `source_path`: string - Путь к sources/<book_id>
- `created_at`: ISO8601 timestamp - Начало всего pipeline

**steps[].*** (REQUIRED for each step):
- `name`: string - Step name (B, C, D, Gate, G, E)
- `status`: string - `ok | fail | skipped`
- `started_at`: ISO8601 timestamp - Начало шага
- `ended_at`: ISO8601 timestamp - Конец шага
- `duration_sec`: float - Длительность шага в секундах
- `artifacts`: array of strings - Created files (relative paths)
- `error`: (optional) string or null - Error details if status=fail

**qa.*** (REQUIRED if D or Gate executed):
- `gate_status`: string - `PASS` or `FAIL` (from Gate)
- `blockers`: int - Number of blocking errors from Gate
- `approved`: bool - Validation result from Agent D
- `warnings`: int - Number of warnings from Agent D

**policy.*** (REQUIRED):
- `require_gate_pass`: bool - Whether Gate FAIL stops pipeline (from --require-gate-pass)

---

## Implementation Structure

```
pipeline/orchestrator_cli/
├── __init__.py
├── __main__.py          # CLI entry point
├── runner.py            # Step execution logic
├── manifest.py          # Manifest creation/save
└── README.md            # Usage documentation
```

---

## Usage Examples

### Full pipeline
```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps B,C,D,Gate,G,E
```

### Skip Gate (for testing)
```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps B,C,D,G,E
```

### Re-publish existing (skip B,C,D)
```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps Gate,G,E
```

**Note**: Gate найдёт `work/{book_id}/outline_{book_id}.yaml` или fallback `outline.yaml`. Если outline не найден → exit code 1.

### Custom run ID
```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps B,C,D,Gate,G,E \
  --run-id kb_manual_20251214
```

---

## VS Code Tasks Integration

After orchestrator is implemented, add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "KB: Run Pipeline (Full)",
      "type": "shell",
      "command": "source .venv/bin/activate && python -m pipeline.orchestrator_cli --book-id ${input:bookId} --steps B,C,D,Gate,G,E --run-id kb_${input:runId}",
      "options": { "cwd": "${workspaceFolder}" },
      "problemMatcher": [],
      "group": "build"
    },
    {
      "label": "KB: Run Gate Only",
      "type": "shell",
      "command": "source .venv/bin/activate && python -m pipeline.orchestrator_cli --book-id ${input:bookId} --steps Gate",
      "options": { "cwd": "${workspaceFolder}" },
      "problemMatcher": [],
      "group": "test"
    }
  ],
  "inputs": [
    {
      "id": "bookId",
      "type": "promptString",
      "description": "Book ID",
      "default": "accounting-basics-test"
    },
    {
      "id": "runId",
      "type": "promptString",
      "description": "Run ID (or empty for timestamp)",
      "default": ""
    }
  ]
}
```

---

## Success Criteria

MVP считается готовым если:

- ✅ Запускается командой `python -m pipeline.orchestrator_cli`
- ✅ Принимает `--book-id`, `--steps`, `--run-id`
- ✅ Выполняет шаги B→C→D→Gate→G→E в правильном порядке
- ✅ Останавливается при Gate FAIL (не запускает G/E)
- ✅ Создаёт manifest.json с деталями по каждому шагу
- ✅ Возвращает правильные exit codes (0/1/2)
- ✅ Работает на accounting-basics-test от начала до конца

---

## What NOT to Implement (out of scope for MVP)

❌ GitHub PR creation (Agent F)  
❌ Parallel step execution  
❌ Smart book discovery (only explicit --book-id)  
❌ Resume from failed step  
❌ LangGraph integration  
❌ Web UI  
❌ REST API  
❌ Webhook notifications  

These are for v2+.

---

## Estimated Implementation Time

- **runner.py** (core logic): 1.5 hours
- **manifest.py** (save/load): 30 minutes
- **__main__.py** (CLI args): 30 minutes
- **Testing** (accounting-basics-test): 30 minutes
- **Documentation** (README): 15 minutes

**Total**: ~3 hours

---

## Next Steps After MVP

1. ✅ Orchestrator CLI working
2. 🟡 Add VS Code Tasks (.vscode/tasks.json)
3. 🟡 Test on 2-3 more books
4. 🟢 Agent F (PR Publisher) - optional
5. 🟢 MCP Server - optional
