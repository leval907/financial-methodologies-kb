#!/bin/bash
# Скрипт для автоматической настройки MCP клиентов
# Financial Methodologies KB

set -e

PROJECT_ROOT="/home/leval907/financial-methodologies-kb/financial-methodologies-kb"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"

# Проверка существования Python
if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ Ошибка: Python не найден по пути $PYTHON_BIN"
    echo "Создайте virtual environment: python3 -m venv .venv"
    exit 1
fi

# Шаблон конфига
read -r -d '' MCP_CONFIG << EOM || true
{
  "mcpServers": {
    "financial-kb": {
      "command": "$PYTHON_BIN",
      "args": ["-m", "mcp.server"],
      "cwd": "$PROJECT_ROOT",
      "env": {
        "PYTHONPATH": "$PROJECT_ROOT"
      }
    }
  }
}
EOM

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 MCP Setup для Financial Methodologies KB"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Выберите клиент для настройки:"
echo ""
echo "  1) Claude Desktop (macOS)"
echo "  2) Claude Desktop (Linux)"
echo "  3) VS Code (MCP Client extension)"
echo "  4) Cline"
echo "  5) Cursor"
echo "  6) Показать конфиг для ручной установки"
echo "  7) Установить зависимости MCP"
echo ""
read -p "Ваш выбор [1-7]: " choice

case $choice in
  1)
    CONFIG_PATH="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    echo ""
    echo "📂 Устанавливаю конфиг для Claude Desktop (macOS)..."
    ;;
  2)
    CONFIG_PATH="$HOME/.config/Claude/claude_desktop_config.json"
    echo ""
    echo "📂 Устанавливаю конфиг для Claude Desktop (Linux)..."
    ;;
  3)
    echo ""
    echo "📋 Конфиг для VS Code Settings (JSON):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    cat "$PROJECT_ROOT/mcp/clients/vscode.json" | jq '.'
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Скопируйте этот блок в ваш VS Code settings.json:"
    echo "  Cmd+Shift+P → 'Preferences: Open User Settings (JSON)'"
    echo ""
    exit 0
    ;;
  4)
    CONFIG_PATH="$HOME/.cline/mcp_settings.json"
    echo ""
    echo "📂 Устанавливаю конфиг для Cline..."
    ;;
  5)
    echo ""
    echo "📋 Конфиг для Cursor:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    cat "$PROJECT_ROOT/mcp/clients/cline.json" | jq '.'
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Добавьте в Cursor → Settings → Features → MCP Servers"
    echo ""
    exit 0
    ;;
  6)
    echo ""
    echo "📋 Полный конфиг MCP:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$MCP_CONFIG" | jq '.'
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    exit 0
    ;;
  7)
    echo ""
    echo "📦 Устанавливаю зависимости MCP..."
    source "$PROJECT_ROOT/.venv/bin/activate"
    pip install mcp anthropic-mcp-server qdrant-client python-arango python-dotenv
    echo ""
    echo "✅ Зависимости установлены!"
    echo ""
    echo "Теперь запустите скрипт снова и выберите клиент."
    exit 0
    ;;
  *)
    echo "❌ Неверный выбор"
    exit 1
    ;;
esac

# Создаём директорию если нужно
mkdir -p "$(dirname "$CONFIG_PATH")"

# Записываем конфиг
echo "$MCP_CONFIG" > "$CONFIG_PATH"

echo ""
echo "✅ Конфиг записан в:"
echo "   $CONFIG_PATH"
echo ""
echo "🔄 Перезапустите клиент для применения изменений."
echo ""
echo "📝 Проверка:"
echo "   1. Перезапустите приложение"
echo "   2. Найдите иконку 🔌 MCP в интерфейсе"
echo "   3. Проверьте доступные инструменты"
echo ""
echo "🧪 Тестовый запрос:"
echo '   "Найди информацию про бюджетирование"'
echo ""
