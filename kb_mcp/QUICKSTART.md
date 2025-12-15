# 🚀 MCP Server — Быстрый старт

**3 минуты до работающего MCP сервера для AI агентов**

---

## ⚡ За 3 шага

### 1️⃣ Установка (30 сек)

```bash
cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb
source .venv/bin/activate
pip install -r mcp/requirements.txt
```

### 2️⃣ Проверка баз (30 сек)

```bash
# Qdrant
curl http://localhost:6333/health

# ArangoDB
curl http://localhost:8529/_api/version

# Если не запущены:
docker-compose -f docker-compose.rag.yml up -d
```

### 3️⃣ Подключение к AI (2 мин)

```bash
./mcp/setup_clients.sh
# Выбери свой клиент (Claude Desktop, VS Code, etc.)
# Перезапусти приложение
```

**Готово! 🎉**

---

## 🧪 Тест

В Claude Desktop / VS Code:

```
Найди информацию про бюджетирование
```

AI должен вызвать `semantic_search` → получить данные из Qdrant → ответить.

---

## 🛠️ Доступные инструменты

1. **semantic_search** — Поиск по Qdrant (векторная БД)
2. **get_methodology_context** — Структура методологии (ArangoDB)
3. **get_glossary_term** — Определения терминов (ArangoDB)
4. **read_methodology_file** — Чтение файлов (FS)

---

## 📚 Полная документация

- [mcp/README.md](README.md) — Подробная документация
- [mcp/clients/README.md](clients/README.md) — Настройка клиентов
- [.github/ISSUE_MCP_SERVER.md](../.github/ISSUE_MCP_SERVER.md) — Roadmap

---

## 🐛 Проблемы?

```bash
# Проверь запуск сервера
python -m mcp.server

# Проверь логи
tail -f ~/Library/Logs/Claude/mcp.log  # macOS
```

**Troubleshooting:** [mcp/README.md#troubleshooting](README.md#-troubleshooting)

---

**Версия:** 0.1.0  
**Статус:** ✅ Ready to use
