# Issues Management Workflow

Инструменты и процессы для работы с GitHub Issues в проекте.

## Инструменты

### 1. `manage_issues.py` - Управление issues

**Основной инструмент** для просмотра и анализа issues.

```bash
# Активировать venv
cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb
source venv/bin/activate

# Показать статистику
python3 tools/manage_issues.py stats

# Список открытых issues
python3 tools/manage_issues.py open

# Недавно закрытые issues
python3 tools/manage_issues.py closed

# Группировка по milestones
python3 tools/manage_issues.py milestones

# Следующие 5 задач (по приоритету)
python3 tools/manage_issues.py next 5
```

### 2. `close_completed_issues.py` - Закрытие issues

Закрывает выполненные issues с комментариями.

```bash
python3 tools/close_completed_issues.py
```

### 3. `import_github_issues.py` - Импорт issues

Создает новые issues из JSON файла.

```bash
python3 tools/import_github_issues.py issues_file.json
```

## Текущий статус

### 📊 Статистика (2024-12-13)

- **Всего issues**: 24
- **Закрыто**: 6 (25%)
- **Открыто**: 18 (75%)

### ✅ Закрытые issues (6)

| # | Issue | Milestone |
|---|-------|-----------|
| #1 | Define core project terminology and glossary structure | Foundation v0.1 |
| #2 | Create Glossary v1.0 (25 core terms) | Foundation v0.1 |
| #3 | Add glossary validation script | Foundation v0.1 |
| #4 | Define universal methodology template | Foundation v0.1 |
| #5 | Enforce front matter standard for methodologies | Foundation v0.1 |
| #8 | Define Power of One output report form | Power of One v0.2 |

### 🎯 Приоритетные задачи (Top 5)

1. **#21** - Integrate LangGraph for Methodology Structuring
   - Milestone: Agent Pipeline v0.5
   - Labels: enhancement, ai-agents, langgraph

2. **#20** - Implement OCR Pipeline for Scanned Documents
   - Milestone: Agent Pipeline v0.5
   - Labels: enhancement, ocr, document-processing

3. **#18** - Implement Agent Pipeline Architecture
   - Milestone: Agent Pipeline v0.5
   - Labels: enhancement, ai-agents, pipeline

4. **#24** - Implement Pipeline Monitoring and Metrics
   - Milestone: Agent Pipeline v0.5
   - Labels: monitoring, metrics, observability

5. **#23** - Setup GitHub Actions for Automated Pipeline
   - Milestone: Agent Pipeline v0.5
   - Labels: automation, ci-cd, github-actions

## Workflow для работы над issue

### 1. Выбор задачи

```bash
# Показать следующие задачи
python3 tools/manage_issues.py next 5

# Выбрать issue, например #18
```

### 2. Создание ветки

```bash
# Создать ветку для issue #18
git checkout -b feature/issue-18-agent-pipeline

# Альтернативные названия:
# feature/agent-pipeline-architecture
# feat/18-agent-pipeline
```

### 3. Работа над задачей

- Читаем описание issue на GitHub
- Реализуем функциональность
- Коммитим изменения с упоминанием issue

```bash
git add .
git commit -m "Implement agent pipeline architecture (#18)

- Created pipeline/ directory structure
- Implemented 5 agent classes
- Added system prompt templates
- Tests for each agent

Related to #18"
```

### 4. Push и PR

```bash
# Push ветки
git push origin feature/issue-18-agent-pipeline

# Создать PR через GitHub UI или gh CLI
gh pr create --title "Implement Agent Pipeline Architecture (#18)" \
  --body "Closes #18

## Changes
- Pipeline architecture with 5 agents
- System prompts
- Tests

## Checklist
- [x] Code implemented
- [x] Tests added
- [x] Documentation updated"
```

### 5. После merge

```bash
# Вернуться в main
git checkout main
git pull origin main

# Удалить локальную ветку
git branch -d feature/issue-18-agent-pipeline
```

## Milestones Progress

### Foundation v0.1 (71% complete)

- ✅ #1 - Core terminology
- ✅ #2 - Glossary v1.0
- ✅ #3 - Validation script
- ✅ #4 - Universal template
- ✅ #5 - Front matter standard
- 🔴 #6 - Power of One 5 stages
- 🔴 #7 - Separate modeling tool

### Power of One v0.2 (33% complete)

- 🔴 #6 - Formalize as methodology
- 🔴 #7 - Separate modeling tool
- ✅ #8 - Output report form

### Integration v0.3 (0% complete)

- 🔴 #9 - Indexing rules
- 🔴 #10 - Graph entities
- 🔴 #11 - Validation
- 🔴 #22 - ArangoDB implementation

### Methodologies Expansion v0.4 (0% complete)

- 🔴 #14 - Simple Numbers
- 🔴 #15 - Theory of Constraints
- 🔴 #16 - Lean Accounting
- 🔴 #17 - Cross-methodology mapping

### Agent Pipeline v0.5 (0% complete)

- 🔴 #18 - Pipeline architecture
- 🔴 #19 - System prompt
- 🔴 #20 - OCR pipeline
- 🔴 #21 - LangGraph
- 🔴 #23 - GitHub Actions
- 🔴 #24 - Monitoring

## Labels

### По типу работы
- `foundation` - базовая архитектура
- `core` - ключевая функциональность
- `enhancement` - улучшения
- `documentation` - документация

### По области
- `glossary` - глоссарий
- `methodology` - методологии
- `ai-agents` - AI агенты
- `integration` - интеграция с другими системами
- `automation` - автоматизация

### По технологии
- `ocr` - распознавание текста
- `langgraph` - LangGraph
- `arango` - ArangoDB
- `github-actions` - CI/CD

## Quick Commands

```bash
# Показать статистику
python3 tools/manage_issues.py stats

# Следующие задачи
python3 tools/manage_issues.py next 10

# Открытые issues
python3 tools/manage_issues.py open

# По milestone
python3 tools/manage_issues.py milestones
```

## Tips

1. **Работайте по одному issue за раз**
   - Фокусируйтесь на одной задаче
   - Используйте отдельные ветки

2. **Всегда упоминайте issue номер**
   - В commit message: `(#18)`
   - В PR description: `Closes #18`

3. **Добавляйте комментарии при закрытии**
   - Что сделано
   - Где находятся файлы
   - Примеры использования

4. **Проверяйте связанные issues**
   - Смотрите "Related to", "Depends on"
   - Обновляйте связанные issues

## Links

- **Issues**: https://github.com/leval907/financial-methodologies-kb/issues
- **Milestones**: https://github.com/leval907/financial-methodologies-kb/milestones
- **Pull Requests**: https://github.com/leval907/financial-methodologies-kb/pulls
- **Project Board**: https://github.com/leval907/financial-methodologies-kb/projects
