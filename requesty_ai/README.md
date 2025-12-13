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

## 📊 Доступные модели (ПРОТЕСТИРОВАНО ✅)

| Модель | Статус | Cost/1M (in/out) | Рекомендация |
|--------|--------|------------------|--------------|
| `deepseek/deepseek-chat` | ✅ Работает | **$0.14/$0.28** | 🏆 **ЛУЧШИЙ для Agent B** |
| `smart/task` | ✅ Работает | **$0.10/$0.30** | Auto-routing |
| `openai/gpt-4o` | ✅ Работает | $2.50/$10.00 | Premium качество |
| `openai/gpt-5-mini` | ✅ Работает | $0.15/$0.60 | Быстро и дешево |
| `google/gemini-2.5-flash` | ✅ Работает | **$0.075/$0.30** | 1M context |
| `google/gemini-2.5-pro` | ❌ Blocked | $1.25/$5.00 | Не доступен |
| `coding/gemini-2.5-pro` | ✅ Работает | $1.25/$5.00 | 🎯 **2M context для кода!** |
| `xai/grok-code-fast-1` | ✅ Работает | $0.50/$1.50 | XAI Grok |

**🏆 Победитель:** `deepseek/deepseek-chat` - в **18x дешевле** чем GPT-4o при отличном качестве!

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
    model="deepseek/deepseek-chat"  # 🏆 Дешево и качественно!
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
    model="deepseek/deepseek-chat",  # или smart/task
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
    model="deepseek/deepseek-chat"
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
    model="deepseek/deepseek-chat",  # 🏆 В 18x дешевле GPT-4o!
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

## 💰 Стоимость (ОБНОВЛЕНО с DeepSeek!)

Для обработки 1 книги (~50K input tokens, ~10K output):

| Модель | Input | Output | Total за книгу |
|--------|-------|--------|----------------|
| **deepseek/deepseek-chat** | **$0.007** | **$0.003** | **$0.010** (~₽1) 🏆 |
| `smart/task` | $0.005 | $0.003 | **$0.008** (~₽0.80) |
| `google/gemini-2.5-flash` | $0.004 | $0.003 | **$0.007** (~₽0.70) |
| `openai/gpt-5-mini` | $0.008 | $0.006 | $0.014 (~₽1.40) |
| `openai/gpt-4o` | $0.125 | $0.100 | $0.225 (~₽22) |

**17 книг с DeepSeek:** ~$0.17 (~**₽17** вместо ₽383!)

### 🎯 Рекомендация для продакшна:

**Стратегия #1: DeepSeek для всего** (самое дешевое)
- Agent B: `deepseek/deepseek-chat` 
- Agent C: `deepseek/deepseek-chat`
- Agent D: `deepseek/deepseek-chat`
- **Итого:** ~₽17 за 17 книг ⚡

**Стратегия #2: Hybrid** (баланс качество/цена)
- Agent B: `deepseek/deepseek-chat` (основное)
- Agent D: `openai/gpt-4o` (критичный QA)
- **Итого:** ~₽10 + ₽12 = ₽22 за книгу

**Стратегия #3: Premium** (максимальное качество)
- Все агенты: `openai/gpt-4o`
- **Итого:** ~₽75 за книгу (₽1,275 за 17 книг)

## 🎯 Следующие шаги

1. ✅ Requesty AI установлен и протестирован
2. ⏳ Интеграция в Agent B (outline_builder.py)
3. ⏳ Few-shot промпты для Agent B
4. ⏳ Fallback на GigaChat (если нужно)
