# 📘 Инструкция для Milena: RAG data + Agent H + Orchestrator

## ✅ Что сделано (2025-01-26)

### 1. RAG данные загружены в ArangoDB
- **144 RAG entities** из 3 книг успешно загружены
- Книги: `toc-thinking-processes`, `throughput-accounting`, `toc-steroids`
- Entities: 20 stages, 41 tools, 42 indicators, 41 rules
- Все entities помечены: `source_book` + `created_by: "agent_b_rag"`

### 2. Agent H (Semantic Linker) завершен
- ✅ **4,414 semantic edges** создано для 427 stages
- Edge types:
  - `stage_uses_indicator`: 2,090 связей
  - `stage_uses_tool`: 1,502 связи
  - `stage_has_rule`: 822 связи
- Токенов использовано: 25,388 (LLM: alibaba/qwen3-max)

### 3. Orchestrator интегрирован с B_RAG и H
- **Новые шаги добавлены:**
  - `B_RAG` — Agent B RAG mode (4x faster, 10x cheaper)
  - `H` — Agent H Semantic Linker (graph edges)
- **Default pipeline** теперь: `B_RAG,C,D,Gate,G,E,F,H`

---

## 🚀 Как запустить full pipeline через Orchestrator

### Вариант 1: Полный RAG pipeline (рекомендуется)

```bash
cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb

python -m pipeline.orchestrator_cli \
  --book-id toc-thinking-processes \
  --steps B_RAG,C,D,Gate,G,E,H
```

**Что происходит:**
1. `B_RAG` — Извлекает entities через Qdrant (vector search + LLM)
2. `C` — Компилирует MD файлы
3. `D` — QA валидация
4. `Gate` — Quality Gate (PASS/FAIL)
5. `G` — Glossary sync
6. `E` — Publish to ArangoDB
7. `H` — Semantic linking (graph edges)

### Вариант 2: Только Agent H (если entities уже в ArangoDB)

```bash
python -m pipeline.orchestrator_cli \
  --book-id toc \
  --steps H
```

### Вариант 3: Legacy pipeline (без RAG, без H)

```bash
python -m pipeline.orchestrator_cli \
  --book-id accounting-basics-test \
  --steps B,C,D,Gate,G,E
```

---

## 📂 Результаты работы

### ArangoDB (после загрузки RAG + Agent H)

```
📊 ВСЕГО ENTITIES: 1,719

По типам:
- Stages: 466 (RAG: 20)
- Tools: 194 (RAG: 41)
- Indicators: 391 (RAG: 42)
- Rules: 668 (RAG: 41)

📊 ВСЕГО EDGES: 4,414
- stage_uses_indicator: 2,090
- stage_uses_tool: 1,502
- stage_has_rule: 822
```

### Файлы и логи

```
work/
├── toc-thinking-processes/
│   └── outline_rag.yaml          # RAG extraction output
├── throughput-accounting/
│   └── outline_rag.yaml
└── toc-steroids/
    └── outline_rag.yaml

qa/runs/
└── kb_<timestamp>/
    ├── manifest.json              # Orchestrator run log
    ├── b_quality_gate.json        # Gate result
    └── final.json                 # Final status

/tmp/agent_h_full.log              # Agent H logs
```

---

## 🔍 Как проверить результаты

### 1. Проверить RAG entities в ArangoDB

```bash
cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb

python << 'EOF'
from arango import ArangoClient
client = ArangoClient(hosts='http://localhost:8529')
db = client.db('fin_kb_method', username='root', password='test_password')

# RAG entities count
for coll_name in ['stages', 'tools', 'indicators', 'rules']:
    count = db.aql.execute(f"""
        FOR doc IN {coll_name}
        FILTER doc.created_by == 'agent_b_rag'
        RETURN doc.source_book
    """).count()
    print(f"✅ {coll_name}: {count} RAG entities")

# Edges count
edges = db.aql.execute("""
    RETURN {
        indicators: LENGTH(stage_uses_indicator),
        tools: LENGTH(stage_uses_tool),
        rules: LENGTH(stage_has_rule)
    }
""").next()
print(f"\n✅ Edges:")
print(f"  stage_uses_indicator: {edges['indicators']}")
print(f"  stage_uses_tool: {edges['tools']}")
print(f"  stage_has_rule: {edges['rules']}")
print(f"  ИТОГО: {sum(edges.values())}")
EOF
```

### 2. Проверить semantic graph (visual)

```bash
# Запустить ArangoDB Web UI
open http://localhost:8529

# Login: root / test_password
# Database: fin_kb_method
# Graph: methodology_graph
```

В Graph Viewer выбрать:
- Vertex collections: `stages`, `indicators`, `tools`, `rules`
- Edge collections: `stage_uses_indicator`, `stage_uses_tool`, `stage_has_rule`

---

## 📝 Примечания

### Agent B RAG vs Agent B Sequential

| Параметр | B_RAG | B_sequential |
|----------|-------|--------------|
| Скорость | **4x faster** | Slow (sequential) |
| Стоимость | **10x cheaper** | Expensive |
| Качество | High (semantic search) | High |
| Output | `outline_rag.yaml` | `outline.yaml` |

### Agent H Requirements

- ArangoDB must be running (`docker-compose up -d arangodb`)
- Methodology `toc` must exist in ArangoDB
- Collections: `stages`, `indicators`, `tools`, `rules` must have entities
- Model: `alibaba/qwen3-max` via Requesty AI (requires API key in `.env`)

---

## 🐛 Troubleshooting

### Agent H не находит methodology

```bash
# Проверить methodologies в ArangoDB
python << 'EOF'
from arango import ArangoClient
client = ArangoClient(hosts='http://localhost:8529')
db = client.db('fin_kb_method', username='root', password='test_password')

result = db.aql.execute("FOR m IN methodologies RETURN {id: m._key, name: m.name}")
for m in result:
    print(f"✅ {m['id']}: {m['name']}")
EOF
```

### RAG entities не загружаются

Ошибка: `unique constraint violated`

**Решение:** Используйте скрипт `scripts/load_rag_to_arango.py` с MD5 hashing:

```bash
python scripts/load_rag_to_arango.py
```

### Orchestrator не находит Agent B RAG

Ошибка: `ModuleNotFoundError: No module named 'pipeline.agents.agent_b_rag'`

**Решение:** Убедитесь, что вы в правильной директории:

```bash
cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb
python -m pipeline.orchestrator_cli --help
```

---

## 📚 Дополнительно

### Полная документация

- Orchestrator CLI: `pipeline/orchestrator_cli/README.md`
- Agent B RAG: `pipeline/agents/agent_b_rag/README.md`
- Agent H: `pipeline/agents/agent_h_semantic_linker/README.md`

### Мониторинг Agent H (если запускаете вручную)

```bash
# Запуск Agent H в фоне
nohup python -m pipeline.agents.agent_h_semantic_linker toc > /tmp/agent_h_full.log 2>&1 &

# Мониторинг прогресса
./monitor_agent_h.sh

# Или просто tail
tail -f /tmp/agent_h_full.log
```

---

## ✨ Итого

Теперь у тебя **полный RAG pipeline** с semantic linking через один оркестратор:

```bash
python -m pipeline.orchestrator_cli \
  --book-id <book-id> \
  --steps B_RAG,C,D,Gate,G,E,H
```

**Результат:**
- RAG extraction → Qdrant
- Entities → ArangoDB
- Semantic edges → ArangoDB graph
- Manifest → `qa/runs/<run-id>/manifest.json`

🎉 **Profit!**
