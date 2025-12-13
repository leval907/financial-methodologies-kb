# Requesty AI Integration

Unified AI gateway для работы с различными LLM провайдерами через единый API.

## ✅ Что установлено

```bash
pip install openai python-dotenv
```

## 🔑 Конфигурация

1. **API ключ уже настроен** в `.env`:
   ```bash
   REQUESTY_API_KEY=rqsty-sk-spqNA0sy...
   ```

2. **Проверка доступных моделей:**
   ```bash
   python requesty_ai/test_connection.py
   ```

## 📊 Доступные модели (проверено)

| Модель | Статус | Cost/1M | Рекомендация |
|--------|--------|---------|--------------|
| `openai/gpt-4o` | ✅ Работает | $2.50/$10.00 | **Agent B/D** |
| `openai/gpt-4o-mini` | ❌ Blocked by policy | $0.15/$0.60 | Нужно включить в dashboard |
| `anthropic/claude-3-5-haiku` | ❌ Blocked by policy | $0.80/$4.00 | Нужно включить |

**Статус:** Только `openai/gpt-4o` доступен из коробки.

## 🚀 Использование

### Простой запрос

```python
from requesty_ai import chat_with_retry

messages = [
    {"role": "system", "content": "Ты эксперт по финансам."},
    {"role": "user", "content": "Что такое ОСВ?"}
]

response = chat_with_retry(
    messages,
    model="openai/gpt-4o"  # Работает!
)

print(response)
```

### С использованием класса

```python
from requesty_ai import RequestyClient

client = RequestyClient()

response = client.chat(
    messages=[
        {"role": "user", "content": "Hello!"}
    ],
    model="openai/gpt-4o",
    temperature=0.7
)

print(response)
```

### Streaming (real-time)

```python
from requesty_ai import RequestyClient

client = RequestyClient()

for chunk in client.chat_stream(
    messages=[{"role": "user", "content": "Объясни DCF метод"}],
    model="openai/gpt-4o"
):
    print(chunk, end="", flush=True)
```

## 🎯 Для нашего проекта

### Agent B (Outline Builder)

```python
from requesty_ai import RequestyClient

client = RequestyClient(max_retries=3, timeout=120)

response = client.chat(
    messages=[
        {"role": "system", "content": "Ты методолог по финансам..."},
        {"role": "user", "content": f"Проанализируй главу: {chapter_text}"}
    ],
    model="openai/gpt-4o",  # Лучшая модель для reasoning
    temperature=0.3  # Меньше креативности, больше точности
)
```

## ⚙️ Features

✅ **Автоматический retry** с exponential backoff  
✅ **Обработка всех ошибок**: rate limits, timeouts, connection  
✅ **Streaming support** для real-time вывода  
✅ **Логирование** всех запросов и использования токенов  
✅ **Cost estimation** (см. `requesty_ai/models.py`)  

## 📝 Структура

```
requesty_ai/
├── __init__.py          # Экспорты
├── client.py            # Основной клиент с retry
├── models.py            # Информация о моделях
├── test_connection.py   # Проверка доступности
└── README.md           # Эта документация
```

## 🔧 Troubleshooting

### 403 "Provider blocked by policy"

**Причина:** Провайдер не включен в вашем Requesty AI аккаунте.

**Решение:**
1. Перейти на https://requesty.ai/dashboard
2. Settings → Providers
3. Включить нужных провайдеров (OpenAI, Anthropic, Google)

### 404 "Provider and/or model not supported"

**Причина:** Модель не поддерживается Requesty AI.

**Решение:** Использовать проверенные модели из `test_connection.py`.

## 💰 Стоимость

Для обработки 1 книги (~50K input tokens, ~10K output):

| Модель | Input | Output | Total |
|--------|-------|--------|-------|
| `openai/gpt-4o` | $0.125 | $0.100 | **$0.225** (~₽22) |

**17 книг:** ~$3.83 (~₽383)

Это дороже GigaChat Pro (~₽25-50 за книгу), но:
- ✅ Работает из коробки (GigaChat нужно регистрировать)
- ✅ Лучшее качество для английских терминов
- ✅ Более стабильное API

## 🎯 Следующие шаги

1. ✅ Requesty AI установлен и протестирован
2. ⏳ Интеграция в Agent B (outline_builder.py)
3. ⏳ Few-shot промпты для Agent B
4. ⏳ Fallback на GigaChat (если нужно)
