# S3 Workflow Pipeline

Pipeline для автоматической работы с книгами из облака S3 и создания методик.

## Что делает Pipeline

1. **Подключается к S3** - читает список книг из `Financial Methodologies_kb/books/`
2. **Скачивает книги** - сохраняет в локальный кеш `cache/books/`
3. **Определяет тип методики** - по имени файла (Simple Numbers, TOC, Power of One и т.д.)
4. **Создает заготовку методики** - из шаблона `templates/README.md`
5. **Сохраняет в структуру проекта** - `docs/methodologies/{methodology-id}/README.md`

## Быстрый старт

### 1. Список книг в S3

```bash
python3 s3/workflow_pipeline.py list
```

Покажет все книги в облаке:
- Имя файла
- Размер
- Дата загрузки

### 2. Обработать все книги

```bash
python3 s3/workflow_pipeline.py process-all
```

Автоматически:
- Скачает все книги из S3
- Создаст заготовки методик
- Выведет статистику

### 3. Обработать одну книгу

```bash
python3 s3/workflow_pipeline.py process "Сила одного"
```

Обработает только указанную книгу (поиск по частичному совпадению имени).

## Структура после обработки

```
financial-methodologies-kb/
├── cache/books/                    # Локальный кеш книг из S3
│   ├── Сила одного_14.pdf
│   ├── Корбет Томас - ТОС.pdf
│   └── ...
│
├── docs/methodologies/             # Созданные методики
│   ├── simple-numbers/
│   │   └── README.md
│   ├── theory-of-constraints-toc/
│   │   └── README.md
│   ├── power-of-one/
│   │   └── README.md
│   ├── company-valuation/
│   │   └── README.md
│   ├── business-metrics/
│   │   └── README.md
│   └── accounting-fundamentals/
│       └── README.md
│
└── s3/
    ├── workflow_pipeline.py        # Этот скрипт
    ├── s3_uploader.py             # Загрузка в S3
    └── README.md
```

## Типы методик (автоопределение)

Pipeline автоматически определяет тип методики по имени файла:

| Ключевые слова | Тип методики |
|----------------|--------------|
| simple, numbers | Simple Numbers |
| тос, corbett, корбет | Theory of Constraints (TOC) |
| power, сила, одного | Power of One |
| стоимость, valuation, коуленд | Company Valuation |
| метрик, metrics | Business Metrics |
| бухгалтерия | Accounting Fundamentals |

## Что создается для каждой методики

Каждая заготовка методики содержит:

1. **Метаданные** (YAML front matter)
   - `methodology_id`
   - `title`
   - `tags`
   - `difficulty`
   - `focus_areas`

2. **Информация об источнике**
   - Имя файла книги
   - Размер
   - Формат

3. **Структура из шаблона**
   - Описание
   - Ключевые компоненты
   - Показатели
   - Алгоритм применения
   - Примеры
   - Ошибки и подводные камни
   - Связь с другими методиками

## Дальнейшая работа

После создания заготовки:

1. Откройте `docs/methodologies/{methodology-id}/README.md`
2. Заполните секции на основе книги из `cache/books/`
3. Добавьте конкретные метрики в раздел "Показатели"
4. Опишите алгоритм применения пошагово
5. Добавьте реальные примеры

## Загрузка новых книг в S3

```bash
# Загрузить одну книгу
s3cmd put "book.pdf" "s3://db6a1f644d97-la-ducem1/Financial Methodologies_kb/books/"

# Загрузить папку
s3cmd put books/*.pdf "s3://db6a1f644d97-la-ducem1/Financial Methodologies_kb/books/"

# Проверить список
s3cmd ls "s3://db6a1f644d97-la-ducem1/Financial Methodologies_kb/books/"
```

После загрузки запустите `process-all` для обработки новых книг.

## Примеры использования

### Пример 1: Первичная загрузка всех книг

```bash
# 1. Загрузить книги в S3
s3cmd put books/*.* "s3://db6a1f644d97-la-ducem1/Financial Methodologies_kb/books/"

# 2. Обработать все книги
python3 s3/workflow_pipeline.py process-all

# Результат: 6 методик созданы в docs/methodologies/
```

### Пример 2: Добавление новой книги

```bash
# 1. Загрузить новую книгу
s3cmd put "new_book.pdf" "s3://db6a1f644d97-la-ducem1/Financial Methodologies_kb/books/"

# 2. Обработать только её
python3 s3/workflow_pipeline.py process "new_book"

# Результат: новая методика создана
```

### Пример 3: Обновление кеша

```bash
# Удалить локальный кеш
rm -rf cache/books/*

# Перезагрузить все книги
python3 s3/workflow_pipeline.py process-all

# Результат: свежие копии книг в cache/
```

## Технические детали

- **S3 Endpoint**: https://s3.ru1.storage.beget.cloud
- **Bucket**: db6a1f644d97-la-ducem1
- **Prefix**: Financial Methodologies_kb/books/
- **Local Cache**: cache/books/
- **Output**: docs/methodologies/

## Требования

```bash
pip install boto3
```

Credentials должны быть настроены в `~/.aws/credentials` (см. `s3/SETUP_GUIDE.md`).

## См. также

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - настройка подключения к S3
- [S3_STORAGE.md](S3_STORAGE.md) - документация по хранилищу
- [../templates/TEMPLATE_GUIDE.md](../templates/TEMPLATE_GUIDE.md) - структура методик
