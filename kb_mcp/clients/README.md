# MCP Client Configuration

Конфигурации для подключения MCP сервера Financial Methodologies KB к различным AI клиентам.

---

## 🔌 Поддерживаемые клиенты

### 1️⃣ Claude Desktop

**Файл конфигурации:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Настройка:**

```bash
# Скопируй содержимое claude.json в файл конфигурации Claude Desktop
cat mcp/clients/claude.json

# Или автоматически (macOS/Linux):
mkdir -p ~/Library/Application\ Support/Claude/
cp mcp/clients/claude.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Перезапусти Claude Desktop
```

**Проверка:**  
После перезапуска Claude Desktop в чате должна появиться иконка 🔌 с доступными инструментами.

---

### 2️⃣ VS Code (MCP Client extension)

**Установка расширения:**
1. Открой VS Code
2. Установи расширение: [MCP Client for VS Code](https://marketplace.visualstudio.com/items?itemName=modelcontextprotocol.vscode-mcp)
3. Открой Settings (JSON): `Cmd+Shift+P` → "Preferences: Open User Settings (JSON)"

**Настройка:**

```bash
# Содержимое для добавления в settings.json
cat mcp/clients/vscode.json
```

Добавь этот JSON блок в свой `settings.json`.

---

### 3️⃣ Cline (AI coding assistant)

**Файл конфигурации:**  
`~/.cline/mcp_settings.json`

**Настройка:**

```bash
mkdir -p ~/.cline
cp mcp/clients/cline.json ~/.cline/mcp_settings.json

# Перезапусти VS Code
```

---

### 4️⃣ Cursor (AI IDE)

**Настройка:**
1. Открой Cursor
2. Settings → Features → MCP Servers
3. Добавь содержимое из `cline.json`

---

## 🛠️ Автоматическая настройка

Используй скрипт `setup_clients.sh` для автоматической настройки:

```bash
cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb
chmod +x mcp/setup_clients.sh
./mcp/setup_clients.sh
```

Скрипт предложит выбрать клиент и автоматически создаст нужный конфиг.

---

## ✅ Проверка работы

### В Claude Desktop:
```
Найди информацию про управленческий учёт
```

### В VS Code (Cline/Continue):
```
@financial-kb найди этапы бюджетирования
```

### В Cursor:
```
Search the financial KB for "cash flow analysis"
```

---

## 🔧 Troubleshooting

### Проблема: "MCP server not found"

**Решение:**
1. Проверь что путь к Python правильный:
   ```bash
   which python  # Должен быть /home/leval907/.../venv/bin/python
   ```
2. Обнови путь в конфиге
3. Перезапусти клиент

---

### Проблема: "Connection refused"

**Решение:**
1. Проверь что MCP сервер запускается:
   ```bash
   cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb
   source .venv/bin/activate
   python -m mcp.server
   ```
2. Проверь логи в консоли
3. Убедись что порты ArangoDB (8529) и Qdrant (6333) доступны

---

### Проблема: "Tool execution failed"

**Решение:**
1. Проверь `.env` файлы (QDRANT_URL, ARANGO_HOST, etc.)
2. Убедись что базы данных запущены:
   ```bash
   # Qdrant
   docker-compose -f docker-compose.rag.yml ps
   
   # ArangoDB
   curl http://localhost:8529/_api/version
   ```

---

## 📚 Доступные инструменты

После подключения MCP сервера, AI клиенты получат доступ к:

1. **semantic_search** — поиск по векторной БД (Qdrant)
2. **get_methodology_context** — структура методологии (ArangoDB)
3. **get_glossary_term** — определения терминов (ArangoDB)
4. **read_methodology_file** — чтение markdown файлов (FS)

Подробнее см. [../README.md](../README.md)

---

## 🔗 Полезные ссылки

- [MCP Specification](https://modelcontextprotocol.io/)
- [Claude Desktop MCP](https://docs.anthropic.com/claude/docs/mcp)
- [VS Code MCP Extension](https://marketplace.visualstudio.com/items?itemName=modelcontextprotocol.vscode-mcp)
- [Cline GitHub](https://github.com/cline/cline)
