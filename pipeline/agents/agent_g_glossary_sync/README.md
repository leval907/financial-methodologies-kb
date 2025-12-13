# Agent G: Glossary Sync

Synchronizes canonical glossary from `data/glossary/**` into ArangoDB `glossary_terms` collection.

## Features

- **Canonical glossary layer:** `glossary_terms` становится единственным источником истины
- **Stub reconciliation:** Автоматическое сопоставление stubs (`needs_definition`) с каноническими терминами
- **Idempotent upsert:** Повторные запуски безопасны (stable `_key`)
- **Lineage tracking:** `source.repo/ref/path/agent` на каждом термине
- **Full-text ready:** `content_text` для ArangoSearch
- **Deduplication:** `content_hash` (SHA256)

---

## Installation

```bash
# No additional dependencies required
# Uses: yaml, python-arango (already in project)
```

---

## Usage

### Basic Sync (без reconciliation)

```bash
python -m pipeline.agents.agent_g_glossary_sync \
  --glossary-dir data/glossary \
  --env-file .env.arango \
  --base-dir . \
  --source-repo financial-methodologies-kb \
  --source-ref main
```

### Sync + Stub Reconciliation

```bash
python -m pipeline.agents.agent_g_glossary_sync \
  --glossary-dir data/glossary \
  --reconcile \
  --output-report data/published/glossary_sync_report.json
```

### Dry Run (не пишет в БД)

```bash
python -m pipeline.agents.agent_g_glossary_sync \
  --glossary-dir data/glossary \
  --dry-run
```

### Apply Schema (первый запуск)

```bash
python -m pipeline.agents.agent_g_glossary_sync \
  --glossary-dir data/glossary \
  --apply-schema
```

---

## Glossary File Format

Поддерживаемые форматы: **YAML** и **JSON**

### YAML Example (single term)

```yaml
# data/glossary/accounting.yaml
term_id: учетная_политика
name: Учетная политика
definition: |
  Совокупность способов ведения бухгалтерского учета, выбранных организацией 
  в соответствии с ПБУ 1/2008.
aliases:
  - Учётная политика
  - Accounting policy
tags:
  - бухгалтерия
  - ПБУ
status: active
version: "1.0"
```

### YAML Example (list of terms)

```yaml
# data/glossary/ratios.yaml
- term_id: коэффициент_текущей_ликвидности
  name: Коэффициент текущей ликвидности
  definition: Отношение оборотных активов к краткосрочным обязательствам
  aliases: [Current Ratio, Текущая ликвидность]
  tags: [финансовый анализ, ликвидность]

- term_id: ebitda
  name: EBITDA
  definition: Прибыль до вычета процентов, налогов, амортизации
  aliases: [Earnings Before Interest, Taxes, Depreciation, and Amortization]
  tags: [финансовый анализ, прибыльность]
```

### JSON Example

```json
{
  "term_id": "рентабельность",
  "name": "Рентабельность",
  "definition": "Относительный показатель эффективности деятельности",
  "aliases": ["Profitability", "ROI"],
  "tags": ["финансовый анализ", "прибыльность"],
  "status": "active",
  "version": "1.0"
}
```

---

## Output

### 1. ArangoDB Collection: `glossary_terms`

Canonical terms в БД:

```json
{
  "_key": "term_учетная_политика",
  "term_id": "term_учетная_политика",
  "name": "Учетная политика",
  "definition": "Совокупность способов ведения бухгалтерского учета...",
  "aliases": ["Учётная политика", "Accounting policy"],
  "tags": ["бухгалтерия", "ПБУ"],
  "status": "active",
  "version": "1.0",
  "entity_type": "term",
  "content_text": "Учетная политика\nСовокупность способов...\nУчётная политика Accounting policy\nбухгалтерия ПБУ",
  "content_hash": "a1b2c3d4e5f6...",
  "source": {
    "repo": "financial-methodologies-kb",
    "ref": "main",
    "path": "data/glossary",
    "agent": "agent_g_glossary_sync"
  },
  "created_at": "2025-12-13T15:30:00Z",
  "updated_at": "2025-12-13T15:30:00Z"
}
```

### 2. Report: `data/published/glossary_sync_report.json`

```json
{
  "agent": "agent_g_glossary_sync",
  "glossary_dir": "data/glossary",
  "source": {
    "repo": "financial-methodologies-kb",
    "ref": "main",
    "path": "data/glossary",
    "agent": "agent_g_glossary_sync"
  },
  "loaded_terms": 50,
  "prepared_docs": 48,
  "errors": [],
  "dry_run": false,
  "timestamp": "2025-12-13T15:30:00Z",
  "result": {
    "upsert_entities": {
      "glossary_terms": {
        "inserted": 45,
        "updated": 3,
        "errors": 0
      }
    },
    "qa_warnings_count": 0,
    "reconciliation": {
      "total_stubs": 2,
      "matched": 1,
      "unmatched": 1,
      "updated_count": 1,
      "matched_details": [
        {
          "stub_id": "test_term_auto",
          "canonical_id": "term_автоматизация",
          "match_type": "name"
        }
      ],
      "unknown_terms": [
        {
          "stub_id": "test_term_fixed",
          "stub_name": "Fixed Term",
          "status": "unknown_term"
        }
      ]
    }
  }
}
```

---

## Stub Reconciliation

Если есть stubs с `status="needs_definition"`, Agent G может их сопоставить:

### Matching Strategy

1. **Exact ID match:** `stub._key == canonical._key`
2. **Normalized name match:** `normalize(stub.name) == normalize(canonical.name)`
3. **Alias match:** `normalize(stub.name) in [normalize(a) for a in canonical.aliases]`

### After Match

**Matched stubs:**
- `status` → `"merged"`
- `merged_into` → `<canonical_term_id>`
- `merged_at` → `<timestamp>`

**Unmatched stubs:**
- Остаются с `status="needs_definition"`
- Добавляются в `unknown_terms` list в report
- Требуют ручной проверки

### Edge Rewiring (TODO)

После reconciliation нужно перенаправить edges:
```aql
FOR e IN methodology_uses_term
    FILTER e._to == "glossary_terms/stub_id"
    UPDATE e WITH { _to: "glossary_terms/canonical_id" } IN methodology_uses_term
```

---

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--glossary-dir` | `data/glossary` | Directory with glossary files |
| `--env-file` | `.env.arango` | Arango env file |
| `--base-dir` | `.` | Repo base directory |
| `--source-repo` | `financial-methodologies-kb` | Source repo name |
| `--source-ref` | `main` | Git ref (commit/tag) |
| `--source-path` | `data/glossary` | Relative path in repo |
| `--apply-schema` | `False` | Apply Arango schema before sync |
| `--reconcile` | `False` | Reconcile stubs with canonical |
| `--dry-run` | `False` | Don't write to DB |
| `--output-report` | `data/published/glossary_sync_report.json` | Report path |

---

## Integration with Pipeline

### Agent E → Agent G dependency

Agent E создает stubs при публикации методологий. Agent G их reconciliates:

```bash
# 1. Publish methodology (creates stubs)
python -m pipeline.agents.agent_e accounting-basics-test

# 2. Sync canonical glossary + reconcile stubs
python -m pipeline.agents.agent_g_glossary_sync --reconcile
```

### Scheduled Sync

Рекомендуется запускать Agent G:
- После обновления `data/glossary/**` (commit hook)
- Периодически (cron: 1 раз в день)
- Перед публикацией критичных методологий

---

## Testing

### Test with sample glossary

```bash
# Create test glossary
mkdir -p data/glossary/test
cat > data/glossary/test/sample.yaml << 'EOF'
- term_id: тестовый_термин
  name: Тестовый термин
  definition: Определение для теста
  aliases: [Test Term]
  tags: [тест]
EOF

# Dry run
python -m pipeline.agents.agent_g_glossary_sync --dry-run

# Real sync
python -m pipeline.agents.agent_g_glossary_sync
```

### Verify in ArangoDB

```bash
python -c "
from arango import ArangoClient
client = ArangoClient(hosts='http://localhost:8529')
db = client.db('fin_kb_method', username='root', password='strongpassword')

result = db.aql.execute('''
    FOR t IN glossary_terms
        FILTER t.status == \"active\"
        SORT t.created_at DESC
        LIMIT 5
        RETURN {key: t._key, name: t.name, status: t.status}
''')

for term in result:
    print(f'{term[\"key\"]}: {term[\"name\"]} ({term[\"status\"]})')
"
```

---

## Troubleshooting

### Error: "Glossary dir not found"

```bash
# Check path
ls -la data/glossary/

# Use absolute path
python -m pipeline.agents.agent_g_glossary_sync --glossary-dir /full/path/to/data/glossary
```

### Error: "Cannot determine term_id"

Ensure glossary files have at least one of:
- `term_id`
- `id`
- `_key`
- `slug`
- `name`

### Duplicates in batch

Agent G автоматически сливает дубликаты внутри батча (merge aliases/tags).

---

## Future Enhancements

- [ ] Edge rewiring after reconciliation (auto-update `_to` in edges)
- [ ] Glossary versioning (track changes over time)
- [ ] Conflict resolution (если canonical term изменился)
- [ ] Embeddings generation (для semantic search)
- [ ] Web UI для управления glossary

---

**Version:** 1.0.0  
**Author:** @leval907  
**Status:** Production Ready 🚀
