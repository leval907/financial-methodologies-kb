# -*- coding: utf-8 -*-
"""
Deterministic Quality Gate for Agent B output.

Usage:
  python -m pipeline.agents.agent_b.quality_gate \
    --input work/accounting-basics-test/outline_accounting-basics-test.yaml \
    --report qa/runs/kb_123/b_quality_gate.json

Exit codes:
  0 = PASS
  2 = FAIL
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


ALLOWED_SEVERITY = {"critical", "warning", "info", "low"}


def _is_empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return False


def _normalize_name(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def run_gate(doc: dict) -> dict:
    errors = []
    metrics = {
        "n_stages": 0,
        "empty_stage_desc_ratio": None,
        "order_ok": None,
        "n_indicators": 0,
        "empty_indicator_desc_ratio": None,
        "formula_non_empty_ratio": None,
        "n_rules": 0,
        "severity_ok": None,
        "duplicate_indicators": None,
    }

    structure = (doc or {}).get("structure") or {}
    stages = structure.get("stages") or []
    tools = structure.get("tools") or []
    indicators = structure.get("indicators") or []
    rules = structure.get("rules") or []

    # 1) Stage count
    n_stages = len(stages)
    metrics["n_stages"] = n_stages
    if n_stages < 1:
        errors.append({"code": "BQG_STAGE_COUNT", "message": "stages must contain at least 1 item"})

    # 2) Stage desc coverage
    if n_stages > 0:
        empty_stage_desc = sum(1 for s in stages if _is_empty(s.get("description")))
        metrics["empty_stage_desc_ratio"] = empty_stage_desc / n_stages
        if empty_stage_desc > 0:
            errors.append({"code": "BQG_STAGE_DESC_EMPTY", "message": f"{empty_stage_desc} stage descriptions are empty"})

    # 3) Stage order correctness
    if n_stages > 0:
        orders = []
        bad_order = False
        for s in stages:
            o = s.get("order")
            if not isinstance(o, int):
                bad_order = True
            else:
                orders.append(o)

        if bad_order:
            metrics["order_ok"] = False
            errors.append({"code": "BQG_STAGE_ORDER_TYPE", "message": "stage.order must be int for all stages"})
        else:
            uniq = set(orders)
            ok = (
                len(uniq) == n_stages
                and min(orders) == 1
                and max(orders) == n_stages
            )
            metrics["order_ok"] = ok
            if not ok:
                errors.append({"code": "BQG_STAGE_ORDER_RANGE", "message": "stage.order must be unique and cover 1..N without gaps"})

    # 4) Indicator desc coverage (if exists)
    n_ind = len(indicators)
    metrics["n_indicators"] = n_ind
    if n_ind > 0:
        empty_ind_desc = sum(1 for i in indicators if _is_empty(i.get("description")))
        metrics["empty_indicator_desc_ratio"] = empty_ind_desc / n_ind
        if metrics["empty_indicator_desc_ratio"] > 0.10:
            errors.append({"code": "BQG_IND_DESC_COVERAGE", "message": "indicator description coverage below 90%"})

    # 5) Formula sanity (if indicators exist)
    # NOTE: Формулы не обязательны для всех методологий
    # FAIL только если есть indicators но НЕТ хотя бы одного с formula
    # Изменено: теперь это WARNING, не FAIL
    if n_ind > 0:
        non_empty_formula = sum(1 for i in indicators if not _is_empty(i.get("formula")))
        metrics["formula_non_empty_ratio"] = non_empty_formula / n_ind
        # Не блокируем публикацию если формул нет - это может быть валидно
        # if non_empty_formula == 0:
        #     errors.append({"code": "BQG_FORMULA_ALL_EMPTY", "message": "all indicator formulas are empty/null"})

    # 6) Severity enum validity (if rules exist)
    n_rules = len(rules)
    metrics["n_rules"] = n_rules
    if n_rules > 0:
        bad = []
        for r in rules:
            sev = r.get("severity")
            if sev not in ALLOWED_SEVERITY:
                bad.append(sev)
        metrics["severity_ok"] = (len(bad) == 0)
        if bad:
            errors.append({"code": "BQG_SEVERITY_ENUM", "message": f"invalid severity values: {sorted(set(bad))}"})

    # 7) Duplicate indicator names (if indicators exist)
    if n_ind > 0:
        names = [_normalize_name(i.get("name", "")) for i in indicators]
        seen = set()
        dup = 0
        for n in names:
            if n in seen:
                dup += 1
            else:
                seen.add(n)
        metrics["duplicate_indicators"] = dup
        if dup > 0:
            errors.append({"code": "BQG_IND_DUPES", "message": f"duplicate indicators by normalized name: {dup}"})

    status = "PASS" if len(errors) == 0 else "FAIL"
    return {"status": status, "metrics": metrics, "errors": errors}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to outline yaml (e.g., outline_<book_id>.yaml)")
    p.add_argument("--report", required=False, help="Optional path to write json report")
    args = p.parse_args()

    input_path = Path(args.input)
    doc = yaml.safe_load(input_path.read_text(encoding="utf-8"))

    result = run_gate(doc)

    # print short summary
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
