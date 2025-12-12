# Financial Methodologies Knowledge Base

> 📚 **Универсальная база знаний по методологиям финансового анализа**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/user/financial-methodologies-kb/releases)
[![Sync Status](https://img.shields.io/badge/sync-automated-green.svg)](https://kb.findbc.ru)

Библиотека содержит структурированные знания о 5 ведущих методологиях финансового анализа и управления. Может быть использована как самостоятельно (Git clone), так и через API и Web UI.

## 🎯 Для кого эта база знаний?

- **Финансовые консультанты** — готовые методологии для работы с клиентами
- **Бизнес-аналитики** — структурированный подход к диагностике
- **CFO и финансовые директора** — инструменты для принятия решений
- **Разработчики** — интеграция в собственные продукты
- **AI/ML проекты** — база знаний для обучения агентов

## 📖 Методологии

| Методология | Автор | Фокус | Подходит для |
|-------------|-------|-------|--------------|
| **[Cash Flow Story](docs/methodologies/cash-flow-story/)** | Joss Milner | Денежный поток и Working Capital | Компании с парадоксом роста |
| **[Simple Numbers](docs/methodologies/simple-numbers/)** | Greg Crabtree | Капитал и бизнес-модели | SMB, планирование капитала |
| **[Theory of Constraints](docs/methodologies/theory-of-constraints/)** | Eliyahu Goldratt | Узкие места и throughput | Manufacturing, product mix |
| **[Lean Accounting](docs/methodologies/lean-accounting/)** | Maskell & Baggaley | Value Streams | Lean производства |
| **[Analytics Factory](docs/methodologies/analytics-factory/)** | Vladimir Volnin | Комплексный анализ | Холдинги, корпорации |

## 🚀 Быстрый старт

### Вариант 1: Использование через Git

```bash
# Клонировать репозиторий
git clone https://github.com/user/financial-methodologies-kb.git

# Или добавить как submodule в свой проект
git submodule add https://github.com/user/financial-methodologies-kb.git knowledge
```

### Вариант 2: Использование через API

```bash
# Поиск по базе знаний
curl https://kb.findbc.ru/api/search?q=marginal+cash+flow

# Список всех методологий
curl https://kb.findbc.ru/api/methodologies

# Получить информацию о показателе
curl https://kb.findbc.ru/api/indicators/marginal_cash_flow
```

### Вариант 3: Web UI

Откройте [kb.findbc.ru](https://kb.findbc.ru) для интерактивной работы:
- 🔍 Поиск по базе знаний
- 💬 Чат с AI агентом
- 📊 Визуализация связей между концептами
- 📖 Интерактивная документация

## 📚 Структура базы знаний

```
docs/
├── methodologies/           # Описание методологий
│   ├── cash-flow-story/
│   │   ├── README.md
│   │   ├── philosophy.md
│   │   ├── indicators/      # Показатели методологии
│   │   ├── frameworks/      # Аналитические фреймворки
│   │   └── use-cases/       # Практические сценарии
│   ├── simple-numbers/
│   ├── theory-of-constraints/
│   ├── lean-accounting/
│   └── analytics-factory/
│
├── indicators/              # Справочник всех показателей
│   ├── cash-flow/
│   ├── profitability/
│   ├── efficiency/
│   └── capital/
│
├── cross-methodology/       # Связи между методологиями
│   ├── indicator-mapping.md
│   └── complementary-use.md
│
└── diagnostics/             # Диагностические паттерны
    ├── symptoms/
    └── decision-trees/

data/                        # Структурированные данные (JSON)
├── indicators/              # Библиотека показателей
├── methodologies/           # Метаданные методологий
├── business-models/         # Бизнес-модели
└── diagnostic-rules/        # Правила диагностики
```

## 🔗 Интеграция в проекты

### Python

```python
from knowledge_base import FinancialKnowledgeBase

kb = FinancialKnowledgeBase.load_from_github(
    repo="user/financial-methodologies-kb",
    version="v1.0.0"
)

# Получить методологию
cfs = kb.get_methodology("cash_flow_story")

# Получить показатель
marginal_cf = kb.get_indicator("marginal_cash_flow")
print(marginal_cf.formula)  # ΔCF / ΔRevenue

# Найти применимые методологии
methodologies = kb.recommend_for_problem("growth without cash")
```

### JavaScript/TypeScript

```typescript
import { FinancialKB } from '@findbc/financial-methodologies-kb';

const kb = new FinancialKB();

// Загрузить данные
await kb.loadFromGitHub('user/financial-methodologies-kb', 'v1.0.0');

// Поиск
const results = await kb.search('working capital');

// Получить показатель
const indicator = await kb.getIndicator('marginal_cash_flow');
```

### REST API

```bash
# API доступен на kb.findbc.ru/api

# Аутентификация (для расширенных возможностей)
export API_KEY="your-api-key"

# Поиск
curl -H "Authorization: Bearer $API_KEY" \
  "https://kb.findbc.ru/api/search?q=cash+flow&limit=10"

# Чат с AI
curl -X POST https://kb.findbc.ru/api/chat \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Почему у компании растёт выручка, но нет денег?",
    "context": {"industry": "retail"}
  }'
```

## 🤖 AI Agent

База знаний интегрирована с AI агентом на базе GraphRAG:

```python
from finance_knowledge import FinancialAgent

agent = FinancialAgent(
    knowledge_base="financial-methodologies-kb"
)

# Объяснить концепт
explanation = await agent.explain("marginal_cash_flow")

# Диагностика проблем
diagnosis = await agent.diagnose({
    "revenue": 1_200_000,
    "cash_flow": -50_000,
    "working_capital": 200_000
})

# Рекомендовать методологию
recommendation = await agent.recommend_methodology({
    "industry": "manufacturing",
    "has_constraints": True
})
```

## 📊 Данные и схемы

Все данные доступны в структурированном формате (JSON):

```json
// data/indicators/indicators-library.json
{
  "indicators": [
    {
      "id": "marginal_cash_flow",
      "name_en": "Marginal Cash Flow",
      "name_ru": "Маржинальный денежный поток",
      "formula": {
        "latex": "\\frac{\\Delta CF}{\\Delta Revenue}",
        "variables": {...}
      },
      "methodologies": ["cash_flow_story"],
      "interpretation": {...},
      "documentation": "docs/indicators/cash-flow/marginal-cash-flow.md"
    }
  ]
}
```

JSON схемы для валидации: `schemas/`

## 🤝 Контрибьюции

Мы приветствуем вклад в развитие базы знаний!

1. Fork репозитория
2. Создайте ветку: `git checkout -b feature/new-methodology`
3. Внесите изменения
4. Commit: `git commit -am 'Add: New methodology description'`
5. Push: `git push origin feature/new-methodology`
6. Создайте Pull Request

См. [CONTRIBUTING.md](CONTRIBUTING.md) для деталей.

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE)

Вы можете свободно использовать эту базу знаний в коммерческих и некоммерческих проектах.

## 🔗 Ссылки

- **Web UI**: https://kb.findbc.ru
- **API Docs**: https://kb.findbc.ru/api/docs
- **GitHub**: https://github.com/user/financial-methodologies-kb
- **Issues**: https://github.com/user/financial-methodologies-kb/issues
- **Discussions**: https://github.com/user/financial-methodologies-kb/discussions

## 📞 Контакты

- **Website**: https://findbc.ru
- **Email**: info@findbc.ru
- **Author**: Milena (Financial Consultant & Business Analyst)

---

**Версия**: 1.0.0 | **Последнее обновление**: 2024-12-12
