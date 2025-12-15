# Настройка MCP в VS Code

## Вариант 1: GitHub Copilot Chat (Рекомендуется)

### 1. Установите расширения:
```bash
code --install-extension GitHub.copilot
code --install-extension GitHub.copilot-chat
```

### 2. Добавьте конфигурацию MCP:

Откройте настройки VS Code (`Ctrl+,`) или отредактируйте файл:
```bash
~/.config/Code/User/settings.json
```

Добавьте:
```json
{
  "github.copilot.chat.mcp.servers": {
    "financial-kb": {
      "command": "/home/leval907/financial-methodologies-kb/financial-methodologies-kb/.venv/bin/python",
      "args": ["-m", "mcp.server"],
      "cwd": "/home/leval907/financial-methodologies-kb/financial-methodologies-kb",
      "env": {
        "PYTHONPATH": "/home/leval907/financial-methodologies-kb/financial-methodologies-kb"
      }
    }
  }
}
```

### 3. Перезапустите VS Code

### 4. Используйте в Copilot Chat:

Откройте Copilot Chat (`Ctrl+Shift+I`) и задайте вопрос:
```
Найди информацию про этап планирования бюджета
```

Copilot автоматически использует MCP инструменты!

---

## Вариант 2: Cline (AI Assistant)

### 1. Установите расширение:
```bash
code --install-extension saoudrizwan.claude-dev
```

### 2. Настройте MCP:

Откройте Cline настройки и добавьте MCP сервер:
- Command: `/home/leval907/financial-methodologies-kb/financial-methodologies-kb/.venv/bin/python`
- Args: `-m mcp.server`
- CWD: `/home/leval907/financial-methodologies-kb/financial-methodologies-kb`

### 3. Используйте Cline:

Cline будет иметь доступ к 4 инструментам:
- **semantic_search** - поиск по Qdrant
- **get_methodology_context** - структура методологии из ArangoDB
- **get_glossary_term** - термины из глоссария
- **read_methodology_file** - чтение файлов методологий

---

## 🧪 Проверка работы

### Тест MCP сервера:
```bash
cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb
python mcp/test_mcp.py
```

Должно быть: ✅ 4/4 теста пройдено

### Доступные инструменты:

1. **semantic_search** (Qdrant)
   - Поиск по 7 книгам
   - Векторный поиск через embeddings
   - Возвращает релевантные фрагменты с score

2. **get_methodology_context** (ArangoDB)
   - 7 этапов методологии "Бюджетирование"
   - 17 индикаторов
   - Связи между сущностями

3. **get_glossary_term** (ArangoDB)
   - 27 терминов в глоссарии
   - Fuzzy search с подсказками
   - Синонимы и связи

4. **read_methodology_file** (Filesystem)
   - Чтение YAML паспортов
   - Доступ к outline файлам
   - Поддержка MD файлов

---

## 🔍 Примеры запросов:

**В Copilot Chat или Cline:**

1. Поиск информации:
   ```
   Найди информацию про точку безубыточности
   ```

2. Структура методологии:
   ```
   Покажи все этапы методологии бюджетирования
   ```

3. Определение термина:
   ```
   Что такое "показатель" в контексте методологий?
   ```

4. Чтение файлов:
   ```
   Прочитай outline методологии budgeting-step-by-step
   ```

---

## ⚙️ Альтернативная настройка (если нет Copilot)

Используйте **Continue.dev** - бесплатная альтернатива:

```bash
code --install-extension Continue.continue
```

Настройка аналогична Cline.
