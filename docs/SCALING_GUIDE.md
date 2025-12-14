# Scaling Guide: From 1 to 17 Books

После реализации Orchestrator CLI и Agent F0 система готова к масштабированию без деградации качества.

## 🎯 Текущее состояние

**Готово**:
- ✅ Orchestrator CLI: B→C→D→Gate→G→E→F
- ✅ Quality Gate: 6 детерминистических метрик
- ✅ Agent F0: Release summary с actionable insights
- ✅ Manifest tracking: таймлайны, статусы, артефакты
- ✅ Exit codes: 0=success, 1=error, 2=gate_fail

**Протестировано на**: 1 книге (accounting-basics-test)

## 📊 Инструменты для масштабирования

### 1. Batch Runner (автоматическая обработка нескольких книг)

```bash
# Обработать конкретные книги
python pipeline/run_batch.py \
  --books accounting-basics-test,simple-numbers,toc

# Авто-обнаружение всех книг в sources/
python pipeline/run_batch.py --auto

# Только Gate (быстрая проверка)
python pipeline/run_batch.py --auto --steps Gate
```

**Выход**: `qa/batch_<timestamp>.md` - сводка PASS/FAIL по всем книгам

**Цель**: Увидеть реальную стабильность Agent B на разных книгах.

### 2. CI Quality Gate (GitHub Actions)

**Файл**: `.github/workflows/quality-gate.yml`

**Триггеры**:
- Push в `work/**/outline*.yaml`
- Push в `pipeline/agents/agent_b/**`
- Pull Requests

**Поведение**:
- Проверяет все outline.yaml через Quality Gate
- Падает при FAIL (exit code 2)
- Загружает gate reports как artifacts

**Цель**: Превратить quality в "необсуждаемое правило" - никто не может залить мусор.

### 3. Метрики Agent B (для целевых улучшений)

После batch run появятся метрики по каждой книге:
- Empty stage descriptions (%)
- Empty indicator descriptions (%)
- Formula coverage (%)
- Order correctness
- Duplicate indicators (count)
- Severity enum violations

**Подход**: Улучшать Agent B **только по тому, что краснеет в Gate**. Никаких "улучшим смысл".

## 🚀 План масштабирования (3 фазы)

### Фаза 1: Proof of Stability (3 книги)

**Цель**: Подтвердить, что Agent B стабилен.

```bash
# Запустить на 3 разных книгах
python pipeline/run_batch.py \
  --books accounting-basics-test,simple-numbers,toc \
  --steps B,C,D,Gate,F

# Проверить batch report
cat qa/batch_*.md
```

**Критерий успеха**:
- Gate PASS >= 2/3 книг
- Agent B НЕ падает с exception
- Средняя длительность < 5 мин на книгу

**Если Gate FAIL**: Анализировать gate reports, улучшать Agent B **только под конкретные метрики**.

### Фаза 2: Scale to 10 Books

**Цель**: Найти edge cases и стабилизировать.

```bash
# Авто-обнаружение первых 10 книг
python pipeline/run_batch.py --auto --steps B,C,D,Gate,F
```

**Ожидаемые проблемы**:
- Разные структуры книг (длинные/короткие)
- Специфичные термины (юридические, технические)
- Форматирование (таблицы, формулы)

**Стратегия**:
1. Собрать gate reports
2. Группировать ошибки по кодам (BQG_STAGE_DESC_EMPTY, BQG_IND_DUPES, и т.д.)
3. Улучшать Agent B под топ-3 частых ошибок
4. Re-run только failed books

### Фаза 3: Full Scale (17 Books)

**Цель**: Обработать все книги с высоким % PASS.

```bash
# Полный batch с Gate enforcement
python pipeline/run_batch.py --auto

# Если есть FAIL - продолжить без require-gate-pass (для отладки)
python pipeline/run_batch.py --auto --no-require-gate-pass
```

**Критерий успеха**:
- Gate PASS >= 85% книг (14+/17)
- QA Approved >= 70% книг (12+/17)
- Средняя длительность < 10 мин на книгу

## 📈 Мониторинг качества

### Метрики для отслеживания

**Per-book metrics** (из gate reports):
```json
{
  "book_id": "accounting-basics-test",
  "gate_status": "PASS",
  "metrics": {
    "n_stages": 22,
    "empty_stage_desc_ratio": 0.0,
    "order_ok": true,
    "n_indicators": 12,
    "empty_indicator_desc_ratio": 0.0,
    "duplicate_indicators": 0
  }
}
```

**Batch metrics** (из batch reports):
```
Total books: 17
Success: 14
Failed: 3
Gate PASS: 15/17 (88%)
QA Approved: 12/17 (71%)
Avg duration: 8.5 min/book
```

### Degradation Indicators

⚠️ **Остановить масштабирование если**:
- Gate PASS rate < 60%
- Agent B падает с exception > 20% случаев
- Средняя длительность растёт > 15 мин на книгу
- Duplicate indicators > 5 на книгу (среднее)

## 🔧 Улучшение Agent B по метрикам

### Приоритизация (по частоте в gate reports)

1. **Empty descriptions** (BQG_STAGE_DESC_EMPTY, BQG_IND_DESC_COVERAGE)
   - Проблема: Agent B возвращает пустые строки
   - Решение: Улучшить prompt или добавить fallback логику

2. **Order correctness** (BQG_STAGE_ORDER_RANGE)
   - Проблема: Дублирующиеся/пропущенные номера стадий
   - Решение: Post-processing re-numbering (уже есть в _normalize_and_validate)

3. **Duplicate indicators** (BQG_IND_DUPES)
   - Проблема: Одинаковые indicators с разным форматированием
   - Решение: Deduplication (уже есть, проверить эффективность)

4. **Severity enum** (BQG_SEVERITY_ENUM)
   - Проблема: Agent B возвращает 'high', 'medium' вместо 'critical', 'warning'
   - Решение: Mapping (уже есть, проверить полноту)

### Процесс улучшения

```bash
# 1. Собрать все gate reports после batch
find qa/runs -name "b_quality_gate.json" > gate_reports.txt

# 2. Агрегировать ошибки
python scripts/aggregate_gate_errors.py gate_reports.txt > errors_summary.json

# 3. Улучшить Agent B под топ-3 ошибки

# 4. Re-run только failed books
for book in $(jq -r '.failed_books[]' errors_summary.json); do
  python -m pipeline.orchestrator_cli --book-id $book --steps B,C,D,Gate,F
done

# 5. Проверить улучшение
python pipeline/run_batch.py --auto --steps Gate
```

## 🎯 KPI для масштабирования

| Метрика | Текущее | Цель (Phase 1) | Цель (Phase 3) |
|---------|---------|----------------|----------------|
| Gate PASS rate | 100% (1/1) | 67% (2/3) | 85% (14+/17) |
| QA Approved | N/A | 50% (1.5/3) | 70% (12+/17) |
| Avg duration | ~2 min | < 5 min | < 10 min |
| Agent B exceptions | 0% | < 10% | < 5% |
| Empty descriptions | 0% | < 15% avg | < 10% avg |
| Duplicate indicators | 0 | < 3 avg | < 2 avg |

## 🚫 Антипаттерны (чего НЕ делать)

❌ **Переписывать Agent B для "улучшения смысла"**
- Делать только то, что краснеет в Gate
- Метрики > субъективные оценки

❌ **Запускать full pipeline на всех 17 книгах сразу**
- Начать с Gate-only batch (быстро)
- Потом B,C,D,Gate (без G,E для экономии времени)
- Полный pipeline только на validated books

❌ **Игнорировать Gate FAIL**
- Gate - это необсуждаемое правило
- Если FAIL - чинить, не продолжать

❌ **Добавлять новые метрики в Gate без причины**
- Каждая метрика должна решать реальную проблему
- Текущие 6 метрик - это минимум для MVP

## 📚 Следующие шаги

1. **Сейчас (Priority 1)**:
   ```bash
   python pipeline/run_batch.py --books accounting-basics-test,simple-numbers,toc --steps Gate
   ```
   Цель: Проверить Gate на 3 книгах (быстро, ~1 мин).

2. **Через 1 день (Priority 2)**:
   ```bash
   python pipeline/run_batch.py --auto --steps B,C,D,Gate,F
   ```
   Цель: Полный batch на всех доступных книгах, собрать метрики.

3. **Через 3 дня (Priority 3)**:
   - Проанализировать batch report
   - Улучшить Agent B под топ-3 ошибки
   - Re-run failed books
   - Achieve Gate PASS rate > 85%

4. **Через неделю (Priority 4)**:
   - Enable CI Quality Gate
   - Запретить merge PR с Gate FAIL
   - Документировать best practices для Agent B prompts

## 🔗 Связанные документы

- [Orchestrator CLI README](../pipeline/orchestrator_cli/README.md)
- [Quality Gate Implementation](../pipeline/agents/agent_b/quality_gate.py)
- [Agent F0 Publisher](../pipeline/agents/agent_f/publisher.py)
- [Batch Runner](../pipeline/run_batch.py)
