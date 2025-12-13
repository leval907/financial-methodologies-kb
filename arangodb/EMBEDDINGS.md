## Поля для embeddings (опционально)

Все основные коллекции имеют поля для будущей интеграции с embeddings:

### В каждой коллекции (methodologies, stages, indicators, tools, glossary_terms):

```json
{
  "content_text": "Нормализованный текст для поиска/эмбеддинга",
  "content_hash": "SHA256 хэш content_text",
  "embedding": null,          // массив float[] или null
  "embedding_model": null,    // "text-embedding-3-small" или null
  "embedding_dim": null       // 1536 или null
}
```

### Как это работает:

**Сейчас (без embeddings):**
- `content_text` = склеенный текст для full-text search через ArangoSearch
- `content_hash` = для детекта изменений (нужно ли пересчитать embedding)
- `embedding*` = null (не используем)

**Позже (с embeddings):**
- Загружаем документы с `embedding == null`
- Генерируем embedding через OpenAI/Cohere/local model
- Сохраняем vector в поле `embedding`
- Указываем `embedding_model` и `embedding_dim`
- `content_hash` не меняется → embedding актуален

**Поиск:**
- Full-text: через ArangoSearch view (быстро, без ML)
- Semantic: через vector similarity (точнее, требует векторную БД или Qdrant)

### Формирование content_text:

**Methodologies:**
```python
content_text = f"{title}\n{methodology_type}\n{' '.join(tags)}"
```

**Stages:**
```python
content_text = f"{title}\n{description}"
```

**Indicators:**
```python
content_text = f"{name}\n{description}\n{formula or ''}"
```

**Glossary Terms:**
```python
content_text = f"{name}\n{definition}\n{' '.join(aliases)}"
```

## ArangoSearch View

`kb_search_view` - полнотекстовый поиск через ArangoSearch:

**Индексируемые поля:**
- `methodologies`: title, methodology_type, tags, content_text
- `stages`: title, description, content_text
- `indicators`: name, description, formula, content_text
- `tools`: title, description, content_text
- `glossary_terms`: name, definition, aliases, content_text, category, tags

**Анализаторы:**
- `text_ru` - русский текст (стемминг, stop-words)
- `identity` - точное совпадение (для ID, enum)

**Пример поиска:**
```aql
FOR doc IN kb_search_view
  SEARCH ANALYZER(
    PHRASE(doc.content_text, "валовая прибыль", "text_ru"),
    "text_ru"
  )
  SORT BM25(doc) DESC
  LIMIT 10
  RETURN doc
```

## Chunks для RAG (опционально)

Коллекция `chunks` предназначена для:
- Разбиения длинных текстов на куски (512-1024 tokens)
- Генерации embeddings для каждого чанка
- RAG (Retrieval-Augmented Generation) через vector search

**Связь:** `chunk_of` edge коллекция связывает chunk с исходным документом.

**Когда использовать:**
- Если документы длинные (>2000 tokens)
- Если нужен точный RAG retrieval
- Если нужна hybrid search (full-text + semantic)

**Когда НЕ нужно:**
- Если объём данных небольшой (<1000 документов)
- Если достаточно ArangoSearch full-text
- Если методологии короткие (<500 слов)

## Glossary Terms - обязательная структура

### Статусы термина:
- `active` - термин актуален, используется
- `deprecated` - термин устарел, есть замена
- `needs_definition` - термин упомянут, но определение не найдено
- `draft` - определение в разработке

### Пример термина:

```json
{
  "_key": "term_001",
  "term_id": "term_001",
  "name": "Валовая прибыль",
  "definition": "Разница между выручкой и себестоимостью продаж",
  "aliases": ["Gross Profit", "GP"],
  "status": "active",
  "version": "1.0",
  "category": "financial_indicator",
  "tags": ["прибыль", "рентабельность"],
  "source": {
    "type": "book",
    "book_id": "accounting-basics",
    "reference": "Глава 3, стр. 45",
    "page": 45
  },
  "examples": [
    "GP = 1,000,000 - 600,000 = 400,000 руб."
  ],
  "content_text": "Валовая прибыль\nРазница между выручкой и себестоимостью продаж\nGross Profit GP",
  "content_hash": "a3f5...",
  "embedding": null,
  "embedding_model": null,
  "embedding_dim": null
}
```

### Валидация терминов в Agent D:

QA Reviewer проверяет:
1. Все термины в методологии есть в `glossary_terms`
2. Если термин отсутствует → BLOCKER или auto-create stub (`status=needs_definition`)
3. Если термин `deprecated` → MAJOR warning
4. Если термин `draft` → MINOR warning

## Миграция данных

### Добавление embedding к существующим документам:

```python
from arangodb.client import ArangoDBClient
import openai

client = ArangoDBClient()
db = client.connect()

# Найти документы без embedding
methodologies = db.collection("methodologies")
for doc in methodologies.all():
    if doc.get("embedding") is None and doc.get("content_text"):
        # Генерируем embedding
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=doc["content_text"]
        )
        
        # Обновляем документ
        methodologies.update({
            "_key": doc["_key"],
            "embedding": response.data[0].embedding,
            "embedding_model": "text-embedding-3-small",
            "embedding_dim": len(response.data[0].embedding)
        })
```

### Создание chunks из длинных документов:

```python
from arangodb.client import ArangoDBClient
import hashlib

def chunk_text(text, chunk_size=512, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

client = ArangoDBClient()
db = client.connect()
chunks_coll = db.collection("chunks")
chunk_of_edge = db.collection("chunk_of")

# Обработка методологий
for methodology in db.collection("methodologies").all():
    if methodology.get("content_text"):
        text_chunks = chunk_text(methodology["content_text"])
        
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"chunk_{methodology['_key']}_{i:03d}"
            
            # Создаем chunk
            chunks_coll.insert({
                "_key": chunk_id,
                "chunk_id": chunk_id,
                "text": chunk_text,
                "source_type": "methodology",
                "source_id": methodology["methodology_id"],
                "position": i,
                "chunk_size": len(chunk_text),
                "content_hash": hashlib.sha256(chunk_text.encode()).hexdigest(),
                "embedding": None,
                "embedding_model": None,
                "embedding_dim": None
            })
            
            # Создаем связь
            chunk_of_edge.insert({
                "_from": f"chunks/{chunk_id}",
                "_to": methodology["_id"],
                "position": i
            })
```

## Запросы через Python

### Поиск по термину:

```python
from arangodb.client import ArangoDBClient

client = ArangoDBClient()
db = client.connect()

# Загружаем AQL запрос
with open('arangodb/queries/find_by_term.aql', 'r') as f:
    query = f.read()

# Выполняем
cursor = db.aql.execute(query, bind_vars={'term_name': 'Валовая прибыль'})
result = list(cursor)
print(result[0])
```

### Full-text search:

```python
with open('arangodb/queries/search_text.aql', 'r') as f:
    query = f.read()

cursor = db.aql.execute(query, bind_vars={
    'search_query': 'анализ прибыльности',
    'limit': 20
})

for doc in cursor:
    print(f"{doc['doc_type']}: {doc.get('title') or doc.get('name')} (score: {doc['score']:.2f})")
```

### Получение методологии со всеми связями:

```python
with open('arangodb/queries/find_methodology.aql', 'r') as f:
    query = f.read()

cursor = db.aql.execute(query, bind_vars={'methodology_id': 'accounting-basics'})
methodology = list(cursor)[0]

print(f"Методология: {methodology['title']}")
print(f"Этапов: {len(methodology['stages'])}")
for stage in methodology['stages']:
    print(f"  - {stage['title']}")
    print(f"    Инструменты: {len(stage['tools'])}")
    print(f"    Показатели: {len(stage['indicators'])}")
```

## Следующие шаги

1. ✅ Структура создана
2. ✅ Схемы определены
3. ✅ Индексы настроены
4. ✅ ArangoSearch view создан
5. ⏭️  Agent E (Publisher) - загрузка методологий в базу
6. ⏭️  Валидация терминов в Agent D
7. ⏭️  (Опционально) Генерация embeddings
8. ⏭️  (Опционально) RAG с chunking
