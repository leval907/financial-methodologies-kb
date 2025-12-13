# ArangoDB Integration

Хранилище графовых данных для методологий с глоссарием и поддержкой embeddings.

## Архитектура

### Принципы
1. **Глоссарий - единственный источник терминов** (обязательно)
2. **Embeddings - опциональны**, но поля заложены в схеме
3. **Стабильные ID** для всех документов
4. **Графовая модель** для связей между сущностями

### Структура

```
arangodb/
├── schema/              # JSON Schemas для всех коллекций
│   ├── methodologies.json     # Методологии (+ content_text, embedding)
│   ├── stages.json            # Этапы (+ content_text, embedding)
│   ├── tools.json             # Инструменты
│   ├── indicators.json        # Показатели (+ content_text, embedding)
│   ├── rules.json             # Правила
│   ├── glossary_terms.json    # Глоссарий терминов (канон)
│   ├── chunks.json            # Чанки для RAG (опционально)
│   └── edges.json             # Все edge-коллекции
├── views/
│   └── kb_search_view.json    # ArangoSearch view (full-text)
├── queries/             # AQL запросы
│   ├── find_methodology.aql
│   ├── search_indicators.aql
│   ├── find_by_term.aql       # Поиск по термину
│   ├── search_text.aql        # Full-text search
│   └── methodology_analytics.aql
├── migrations/          # Миграции структуры (будущее)
└── client.py           # Python клиент
```

## Подключение

### Конфигурация
Создайте файл `.env.arango` в корне проекта:
```bash
ARANGO_HOST=localhost
ARANGO_PORT=8529
ARANGO_DB=fin_kb_method
ARANGO_USER=root
ARANGO_PASSWORD=strongpassword
```

### Python код
```python
from arangodb.client import ArangoDBClient
from dotenv import load_dotenv

# Загружаем конфигурацию
load_dotenv('.env.arango')

# Создаем клиент (параметры из .env.arango)
client = ArangoDBClient()
db = client.connect()

# Инициализация структуры
client.setup_collections()
client.create_graph()
```

## Коллекции

### Document Collections
- `methodologies` - основные методологии
- `stages` - этапы методологий
- `tools` - инструменты
- `indicators` - показатели
- `rules` - правила
- **`glossary_terms`** - **глоссарий терминов (канон)** ✅
- `chunks` - чанки текста для RAG (опционально)

### Edge Collections

**Структура методологии:**
- `methodology_stages` - методология → этапы
- `stage_tools` - этап → инструменты
- `stage_indicators` - этап → показатели
- `stage_rules` - этап → правила
- `indicator_depends_on` - показатель → показатель (зависимости)

**Связи с глоссарием:** ✅
- `methodology_terms` - методология → термин (defines/uses/mentions)
- `stage_terms` - этап → термин
- `indicator_terms` - показатель → термин
- `tool_terms` - инструмент → термин
- `term_relations` - термин → термин (synonym/related/antonym)

**RAG (опционально):**
- `chunk_of` - chunk → document

## Граф

```
[Methodology]
    ↓ (methodology_stages)
[Stage_001]
    ├→ (stage_tools) → [Tool_001]
    ├→ (stage_indicators) → [Indicator_001]
    ├→ (stage_rules) → [Rule_001]
    └→ (stage_terms) → [GlossaryTerm: "Валовая прибыль"]
    
[Indicator_001]
    ├→ (indicator_depends_on) → [Indicator_002]
    └→ (indicator_terms) → [GlossaryTerm: "Рентабельность"]

[GlossaryTerm: "Cash Flow"]
    └→ (term_relations: synonym) → [GlossaryTerm: "Денежный поток"]
```

### Пример графового обхода

**Найти все термины используемые в методологии:**
```aql
FOR m IN methodologies
  FILTER m.methodology_id == "accounting-basics"
  FOR term IN 1..2 OUTBOUND m 
    methodology_terms, methodology_stages, stage_terms
    FILTER IS_SAME_COLLECTION('glossary_terms', term)
    RETURN DISTINCT term
```

**Найти методологии где используется термин:**
```aql
FOR term IN glossary_terms
  FILTER term.name == "Валовая прибыль"
  FOR m IN 2..3 INBOUND term
    methodology_terms, stage_terms, methodology_stages
    FILTER IS_SAME_COLLECTION('methodologies', m)
    RETURN DISTINCT m
```
