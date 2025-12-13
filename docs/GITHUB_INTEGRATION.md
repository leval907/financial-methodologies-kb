# GitHub Integration Guide

## Статус интеграции

✅ **Репозиторий настроен и работает**

- **Repository**: leval907/financial-methodologies-kb
- **Branch**: main
- **Authentication**: Token-based (в git remote URL)
- **Git config**: Claude Assistant <claude@findbc.ru>

## Инструменты для работы с GitHub

### 1. Python скрипт (рекомендуется)

**Файл**: `tools/import_github_issues.py`

**Использование:**
```bash
cd /home/leval907/financial-methodologies-kb/financial-methodologies-kb
source venv/bin/activate
python3 tools/import_github_issues.py <issues_file.json>
```

**Возможности:**
- ✅ Создание milestones
- ✅ Создание issues с labels
- ✅ Автоматическая привязка к milestones
- ✅ Проверка дубликатов
- ✅ Подробная статистика

**Пример:**
```bash
python3 tools/import_github_issues.py issues_agent_pipeline.json
```

### 2. Bash скрипт с gh CLI

**Файл**: `tools/import_agent_pipeline_issues.sh`

⚠️ **Требует**: `gh auth login` перед использованием

**Использование:**
```bash
gh auth login  # один раз
./tools/import_agent_pipeline_issues.sh
```

## Текущие Milestones

1. **Foundation v0.1** - Базовая архитектура, глоссарий, шаблоны
2. **Power of One v0.2** - Формализация методологии Power of One
3. **Integration v0.3** - Интеграция с finance-knowledge, ArangoDB
4. **Methodologies Expansion v0.4** - Дополнительные методологии
5. **Agent Pipeline v0.5** - AI-powered пайплайн (новый!)

## Импортированные Issues

### Agent Pipeline (issues #18-#24)

| # | Issue | Labels | Milestone |
|---|-------|--------|-----------|
| #18 | Implement Agent Pipeline Architecture | enhancement, ai-agents, pipeline | Agent Pipeline v0.5 |
| #19 | Create AI Methodologist System Prompt | documentation, ai-agents, prompts | Agent Pipeline v0.5 |
| #20 | Implement OCR Pipeline | enhancement, ocr, document-processing | Agent Pipeline v0.5 |
| #21 | Integrate LangGraph | enhancement, ai-agents, langgraph | Agent Pipeline v0.5 |
| #22 | Implement ArangoDB Knowledge Base | enhancement, database, arango, rag | Integration v0.3 |
| #23 | Setup GitHub Actions | automation, ci-cd, github-actions | Agent Pipeline v0.5 |
| #24 | Implement Pipeline Monitoring | monitoring, metrics, observability | Agent Pipeline v0.5 |

## Проверка статуса

### Список milestones
```bash
curl -s -H "Authorization: token $(git remote get-url origin | grep -oP 'ghp_[^@]+')" \
  "https://api.github.com/repos/leval907/financial-methodologies-kb/milestones" \
  | python3 -m json.tool
```

### Список issues
```bash
curl -s -H "Authorization: token $(git remote get-url origin | grep -oP 'ghp_[^@]+')" \
  "https://api.github.com/repos/leval907/financial-methodologies-kb/issues" \
  | python3 -m json.tool
```

### Через браузер
https://github.com/leval907/financial-methodologies-kb/issues
https://github.com/leval907/financial-methodologies-kb/milestones

## Создание новых issues

### Формат JSON файла

```json
[
  {
    "title": "Issue Title",
    "body": "## Description\n\nDetailed description...",
    "labels": ["label1", "label2"],
    "milestone": "Milestone Name"
  }
]
```

### Импорт

```bash
# 1. Создайте JSON файл
vim issues_new_feature.json

# 2. Импортируйте
python3 tools/import_github_issues.py issues_new_feature.json
```

## Git Workflow

### Стандартный процесс

```bash
# 1. Изменения
git add .
git commit -m "Описание изменений"

# 2. Проверка перед push
git status
git log --oneline -5

# 3. Push
git push origin main
```

### Создание веток для фич

```bash
# Создать ветку для issue #18
git checkout -b feature/agent-pipeline-architecture

# Работа...
git add .
git commit -m "Implement agent pipeline architecture (#18)"

# Push ветки
git push origin feature/agent-pipeline-architecture

# Создать PR через GitHub UI
```

## Troubleshooting

### Problem: gh CLI не авторизован

**Solution**: Используйте Python скрипт `tools/import_github_issues.py` - он работает с токеном из git remote URL

### Problem: Token expired

**Solution**: Обновите token в git remote URL
```bash
git remote set-url origin https://NEW_TOKEN@github.com/leval907/financial-methodologies-kb.git
```

### Problem: Issues создаются дублями

**Solution**: Python скрипт автоматически проверяет дубликаты по title и пропускает их

## Best Practices

1. **Всегда проверяйте перед push**
   ```bash
   git status
   git diff
   ```

2. **Используйте осмысленные commit messages**
   ```
   ✅ Add agent pipeline architecture
   ✅ Fix glossary validation script
   ✅ Update S3 workflow documentation
   
   ❌ fix
   ❌ update
   ❌ changes
   ```

3. **Группируйте связанные изменения**
   ```bash
   # Плохо: 10 коммитов для одной фичи
   # Хорошо: 1-2 коммита с логическими блоками
   ```

4. **Используйте branches для больших фич**
   ```bash
   main  # всегда стабильная
   feature/* # разработка новых фич
   hotfix/* # срочные исправления
   ```

## Links

- **Repository**: https://github.com/leval907/financial-methodologies-kb
- **Issues**: https://github.com/leval907/financial-methodologies-kb/issues
- **Milestones**: https://github.com/leval907/financial-methodologies-kb/milestones
- **Projects**: https://github.com/leval907/financial-methodologies-kb/projects

## Status: ✅ WORKING

Последняя проверка: 2024-12-13
- Git push: ✅ работает
- Issues import: ✅ работает  
- Milestones: ✅ работают
- API access: ✅ работает
