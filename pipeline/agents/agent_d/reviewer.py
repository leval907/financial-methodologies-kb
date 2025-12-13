#!/usr/bin/env python3
"""
Agent D: QA Reviewer (hybrid deterministic + LLM reasoning)

Architecture:
- Layer 1: Deterministic prechecks (NO LLM) - schema, IDs, docs, glossary, formulas
- Layer 2: LLM reasoning (Claude 3.5 Sonnet via Requesty) - coherence, completeness, sanity

Inputs:
  work/<book_id>/outline.yaml        (Agent B output)
  data/methodologies/<book_id>.yaml  (Agent C normalized output)
  docs/methodologies/<book_id>/**    (Agent C markdown docs)
  data/glossary/*.yaml               (optional glossary terms)

Outputs:
  work/<book_id>/qa/qa_result.json   (machine-readable verdict)
  work/<book_id>/qa/qa_report.md     (human-readable report)
  work/<book_id>/qa/approved.flag    (true/false)

Exit codes:
  0 -> approved=true
  1 -> approved=false (blockers or ≥3 majors)
  2 -> runtime error

Usage:
  python pipeline/agents/agent_d/reviewer.py --book accounting-basics-test
  python pipeline/agents/agent_d/reviewer.py --book accounting-basics-test --use-llm
  python pipeline/agents/agent_d/reviewer.py --book accounting-basics-test --glossary data/glossary
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
import requests
from dotenv import load_dotenv
from jsonschema import Draft202012Validator

# Load environment
load_dotenv()

# -----------------------------
# Paths (repo-relative)
# -----------------------------
REPO_ROOT = Path(__file__).resolve().parents[3]  # .../financial-methodologies-kb
WORK_DIR = REPO_ROOT / "work"
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"
SCHEMAS_DIR = REPO_ROOT / "schemas"
INPUTS_DIR = REPO_ROOT / "inputs"

# -----------------------------
# Helpers
# -----------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be dict, got {type(data)} at {path}")
    return data


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_schema(schema_path: Path) -> Dict[str, Any]:
    return read_json(schema_path)


def validate_schema(schema: Dict[str, Any], data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Returns list of errors (each is dict with path + message)."""
    v = Draft202012Validator(schema)
    errs = sorted(v.iter_errors(data), key=lambda e: e.path)
    out: List[Dict[str, Any]] = []
    for e in errs:
        loc = "/" + "/".join(str(p) for p in e.path) if e.path else "/"
        out.append({"path": loc, "message": e.message})
    return out


# -----------------------------
# Issue model
# -----------------------------
SEVERITIES = ("BLOCKER", "MAJOR", "MINOR")


@dataclass
class Issue:
    id: str
    severity: str
    category: str
    message: str
    evidence: Dict[str, Any]
    fix_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "evidence": self.evidence,
            "fix_hint": self.fix_hint,
        }


# -----------------------------
# Glossary loading
# -----------------------------
def load_glossary_terms(glossary_path: Optional[Path]) -> Optional[set[str]]:
    """
    Accepts:
      - index.json with {"terms":[{"term_id":"..."}, ...]} or {"term_ids":[...]}
      - yaml list of term objects with term_id
      - folder: data/glossary/*.yaml
    """
    if glossary_path is None:
        return None

    if glossary_path.is_dir():
        term_ids: set[str] = set()
        for p in sorted(glossary_path.glob("*.y*ml")):
            try:
                y = read_yaml(p)
                # support both single-term file or list
                if isinstance(y, dict) and "term_id" in y:
                    term_ids.add(str(y["term_id"]))
                elif isinstance(y, list):
                    for item in y:
                        if isinstance(item, dict) and "term_id" in item:
                            term_ids.add(str(item["term_id"]))
            except Exception:
                continue
        return term_ids

    if not glossary_path.exists():
        return None

    if glossary_path.suffix.lower() in (".json",):
        j = read_json(glossary_path)
        term_ids: set[str] = set()
        if isinstance(j, dict):
            if "term_ids" in j and isinstance(j["term_ids"], list):
                term_ids |= {str(x) for x in j["term_ids"]}
            if "terms" in j and isinstance(j["terms"], list):
                for t in j["terms"]:
                    if isinstance(t, dict) and "term_id" in t:
                        term_ids.add(str(t["term_id"]))
        return term_ids

    if glossary_path.suffix.lower() in (".yaml", ".yml"):
        y = read_yaml(glossary_path)
        term_ids: set[str] = set()
        if isinstance(y, dict) and "term_id" in y:
            term_ids.add(str(y["term_id"]))
        elif isinstance(y, dict) and "terms" in y and isinstance(y["terms"], list):
            for t in y["terms"]:
                if isinstance(t, dict) and "term_id" in t:
                    term_ids.add(str(t["term_id"]))
        elif isinstance(y, list):
            for t in y:
                if isinstance(t, dict) and "term_id" in t:
                    term_ids.add(str(t["term_id"]))
        return term_ids

    return None


# -----------------------------
# Deterministic prechecks
# -----------------------------
ID_RE = {
    "stage": re.compile(r"^stage_\d{3}$"),
    "tool": re.compile(r"^tool_\d{3}$"),
    "ind": re.compile(r"^ind_\d{3}$"),
    "rule": re.compile(r"^rule_\d{3}$"),
}


def precheck_schema(compiled_yaml_path: Path, schema_path: Path) -> List[Issue]:
    issues: List[Issue] = []
    if not compiled_yaml_path.exists():
        issues.append(
            Issue(
                id="ISSUE-001",
                severity="BLOCKER",
                category="files",
                message="Compiled YAML not found (Agent C output missing).",
                evidence={"path": str(compiled_yaml_path)},
                fix_hint="Run Agent C compiler to produce data/methodologies/<id>.yaml",
            )
        )
        return issues

    data = read_yaml(compiled_yaml_path)
    schema = load_schema(schema_path)
    errors = validate_schema(schema, data)
    for idx, e in enumerate(errors, start=1):
        issues.append(
            Issue(
                id=f"SCHEMA-{idx:03d}",
                severity="BLOCKER",
                category="schema",
                message=e["message"],
                evidence={"path": str(compiled_yaml_path), "pointer": e["path"]},
                fix_hint="Fix Agent C output or schema mismatch.",
            )
        )
    return issues


def precheck_ids(compiled: Dict[str, Any]) -> List[Issue]:
    issues: List[Issue] = []
    st = compiled.get("structure", {}) or {}

    def check_list(kind: str, items: List[Dict[str, Any]], key: str = "id") -> None:
        pat = ID_RE[kind]
        seen: set[str] = set()
        for i, it in enumerate(items):
            _id = str(it.get(key) or "")
            if not pat.match(_id):
                issues.append(
                    Issue(
                        id=f"ID-{kind.upper()}-{i+1:03d}",
                        severity="MAJOR",
                        category="ids",
                        message=f"Invalid {kind} id: '{_id}'",
                        evidence={"pointer": f"/structure/{kind}s/{i}"},
                        fix_hint=f"Ensure {kind} ids follow pattern {pat.pattern}",
                    )
                )
            if _id in seen:
                issues.append(
                    Issue(
                        id=f"ID-DUP-{kind.upper()}-{i+1:03d}",
                        severity="BLOCKER",
                        category="ids",
                        message=f"Duplicate {kind} id: '{_id}'",
                        evidence={"pointer": f"/structure/{kind}s/{i}"},
                        fix_hint="Ensure IDs are unique (Agent C normalization).",
                    )
                )
            seen.add(_id)

    check_list("stage", st.get("stages", []) or [])
    check_list("tool", st.get("tools", []) or [])
    check_list("ind", st.get("indicators", []) or [])
    check_list("rule", st.get("rules", []) or [])
    return issues


def precheck_docs_consistency(book_id: str, compiled: Dict[str, Any]) -> List[Issue]:
    issues: List[Issue] = []
    base = DOCS_DIR / "methodologies" / book_id

    if not (base / "README.md").exists():
        issues.append(
            Issue(
                id="DOCS-001",
                severity="BLOCKER",
                category="docs",
                message="README.md not found for methodology docs.",
                evidence={"path": str(base / "README.md")},
                fix_hint="Run Agent C to generate docs/methodologies/<id>/README.md",
            )
        )
        return issues

    # Check stage files count matches stages list
    stages = (compiled.get("structure", {}) or {}).get("stages", []) or []
    stage_dir = base / "stages"
    if stages:
        if not stage_dir.exists():
            issues.append(
                Issue(
                    id="DOCS-002",
                    severity="BLOCKER",
                    category="docs",
                    message="Stages directory missing.",
                    evidence={"path": str(stage_dir)},
                    fix_hint="Run Agent C to generate docs stages.",
                )
            )
        else:
            files = list(stage_dir.glob("stage_*.md"))
            if len(files) != len(stages):
                issues.append(
                    Issue(
                        id="DOCS-003",
                        severity="MAJOR",
                        category="docs",
                        message=f"Stages docs count mismatch: yaml={len(stages)} files={len(files)}",
                        evidence={"path": str(stage_dir)},
                        fix_hint="Re-run Agent C; ensure stage ids are stable and file naming logic matches.",
                    )
                )

    return issues


def precheck_glossary(compiled: Dict[str, Any], glossary_terms: Optional[set[str]]) -> Tuple[List[Issue], float]:
    """
    Checks:
      - glossary_references.found_terms[*].term_id exists
      - any explicit glossary_ref fields (if present in YAML) exist
    Returns (issues, coverage_ratio).
    """
    if glossary_terms is None:
        return [], 1.0

    issues: List[Issue] = []
    found = (compiled.get("glossary_references", {}) or {}).get("found_terms", []) or []
    if not isinstance(found, list):
        found = []

    total = 0
    ok = 0
    for idx, ft in enumerate(found):
        if not isinstance(ft, dict):
            continue
        tid = str(ft.get("term_id") or "")
        if not tid:
            continue
        total += 1
        if tid in glossary_terms:
            ok += 1
        else:
            issues.append(
                Issue(
                    id=f"GLOSS-{idx+1:03d}",
                    severity="BLOCKER",
                    category="glossary",
                    message=f"Glossary term_id not found: '{tid}'",
                    evidence={"pointer": f"/glossary_references/found_terms/{idx}/term_id"},
                    fix_hint="Add term to glossary or replace with existing term_id.",
                )
            )

    coverage = (ok / total) if total else 1.0
    return issues, coverage


def precheck_formulas(compiled: Dict[str, Any]) -> Tuple[List[Issue], float]:
    """
    Minimal syntax checks (not mathematical truth):
      - parenthesis balance
      - forbidden garbage chars
      - presence of '=' when it looks like definition
    """
    issues: List[Issue] = []
    inds = ((compiled.get("structure", {}) or {}).get("indicators", []) or [])
    if not isinstance(inds, list):
        return [], 1.0

    checked = 0
    passed = 0

    forbidden = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")  # control chars
    for idx, ind in enumerate(inds):
        if not isinstance(ind, dict):
            continue
        formula = str(ind.get("formula") or "").strip()
        if not formula:
            continue

        checked += 1

        # control chars
        if forbidden.search(formula):
            issues.append(
                Issue(
                    id=f"FORM-{idx+1:03d}",
                    severity="MAJOR",
                    category="formula",
                    message="Formula contains control/garbage characters.",
                    evidence={"pointer": f"/structure/indicators/{idx}/formula", "snippet": formula[:120]},
                    fix_hint="Clean extraction / normalize formula text.",
                )
            )
            continue

        # parentheses balance
        bal = 0
        ok_bal = True
        for ch in formula:
            if ch == "(":
                bal += 1
            elif ch == ")":
                bal -= 1
                if bal < 0:
                    ok_bal = False
                    break
        if not ok_bal or bal != 0:
            issues.append(
                Issue(
                    id=f"FORM-PAREN-{idx+1:03d}",
                    severity="MAJOR",
                    category="formula",
                    message="Unbalanced parentheses in formula.",
                    evidence={"pointer": f"/structure/indicators/{idx}/formula", "snippet": formula[:120]},
                    fix_hint="Fix parentheses or extraction errors.",
                )
            )
            continue

        # weak heuristic: definition-like should contain '='
        if re.search(r"\b(ratio|margin|roi|roa|roe|turnover|ratio)\b", formula.lower()) and "=" not in formula:
            issues.append(
                Issue(
                    id=f"FORM-EQ-{idx+1:03d}",
                    severity="MINOR",
                    category="formula",
                    message="Formula looks like a definition but '=' is missing.",
                    evidence={"pointer": f"/structure/indicators/{idx}/formula", "snippet": formula[:120]},
                    fix_hint="If it is a definition, write as 'X = ...'. Otherwise ignore.",
                )
            )
            passed += 1
            continue

        passed += 1

    ratio = (passed / checked) if checked else 1.0
    return issues, ratio


def precheck_duplicate_indicators(compiled: Dict[str, Any]) -> List[Issue]:
    """
    Check for duplicate indicator names (case-insensitive, normalized).
    Returns BLOCKER issues for exact duplicates.
    """
    issues: List[Issue] = []
    inds = ((compiled.get("structure", {}) or {}).get("indicators", []) or [])
    if not isinstance(inds, list):
        return []
    
    def normalize_name(name: str) -> str:
        """Normalize: lowercase, strip, ё→е"""
        return name.lower().strip().replace("ё", "е")
    
    seen: Dict[str, List[int]] = {}
    for idx, ind in enumerate(inds):
        if not isinstance(ind, dict):
            continue
        name = str(ind.get("name") or "").strip()
        if not name:
            continue
        
        norm_name = normalize_name(name)
        if norm_name not in seen:
            seen[norm_name] = []
        seen[norm_name].append(idx)
    
    # Find duplicates
    for norm_name, indices in seen.items():
        if len(indices) > 1:
            ids = [f"ind_{i+1:03d}" for i in indices]
            issues.append(
                Issue(
                    id=f"DUP-IND-{indices[0]+1:03d}",
                    severity="BLOCKER",
                    category="duplicates",
                    message=f"Duplicate indicator name '{norm_name}' found at {len(indices)} locations: {', '.join(ids)}",
                    evidence={
                        "pointer": f"/structure/indicators/{indices[0]} and {indices[1]}",
                        "snippet": f"Normalized name: '{norm_name}' appears {len(indices)} times"
                    },
                    fix_hint="Merge duplicate indicators or rename to distinguish different contexts.",
                )
            )
    
    return issues


def precheck_stage_order(compiled: Dict[str, Any]) -> List[Issue]:
    """
    Check stage order field for consistency:
    - No duplicate order values
    - No order=1 after stage_001 (broken numbering)
    - Ideally sequential 1..N
    """
    issues: List[Issue] = []
    stages = ((compiled.get("structure", {}) or {}).get("stages", []) or [])
    if not isinstance(stages, list):
        return []
    
    seen_orders: Dict[int, List[int]] = {}
    for idx, stage in enumerate(stages):
        if not isinstance(stage, dict):
            continue
        order = stage.get("order")
        if order is None:
            continue
        
        if not isinstance(order, int):
            issues.append(
                Issue(
                    id=f"ORDER-TYPE-{idx+1:03d}",
                    severity="MAJOR",
                    category="stage_order",
                    message=f"Stage {idx+1} has non-integer order: {order}",
                    evidence={"pointer": f"/structure/stages/{idx}/order"},
                    fix_hint="Ensure order is integer type.",
                )
            )
            continue
        
        if order not in seen_orders:
            seen_orders[order] = []
        seen_orders[order].append(idx)
        
        # Check for order=1 not at stage_001
        if order == 1 and idx > 0:
            issues.append(
                Issue(
                    id=f"ORDER-RESET-{idx+1:03d}",
                    severity="BLOCKER",
                    category="stage_order",
                    message=f"Stage {idx+1} has order=1 but is not the first stage (broken numbering)",
                    evidence={
                        "pointer": f"/structure/stages/{idx}/order",
                        "snippet": f"stage_{idx+1:03d} order: {order}, order_display: '{stage.get('order_display', '')}'"
                    },
                    fix_hint="Agent C should renumber stages sequentially (1..N) or fix source order mapping.",
                )
            )
    
    # Check for duplicate orders
    for order, indices in seen_orders.items():
        if len(indices) > 1:
            issues.append(
                Issue(
                    id=f"ORDER-DUP-{order:03d}",
                    severity="MAJOR",
                    category="stage_order",
                    message=f"Duplicate order={order} found at {len(indices)} stages: {', '.join([f'stage_{i+1:03d}' for i in indices])}",
                    evidence={"pointer": f"/structure/stages order={order}"},
                    fix_hint="Ensure each stage has unique order value.",
                )
            )
    
    return issues


def precheck_empty_formulas(compiled: Dict[str, Any], threshold: float = 0.7) -> List[Issue]:
    """
    Check if too many indicators have empty formulas.
    For diagnostic/analysis methodologies, empty formulas reduce actionability.
    
    Args:
        threshold: If ratio of empty formulas > threshold, raise MAJOR issue
    """
    issues: List[Issue] = []
    inds = ((compiled.get("structure", {}) or {}).get("indicators", []) or [])
    if not isinstance(inds, list) or len(inds) == 0:
        return []
    
    methodology_type = compiled.get("classification", {}).get("methodology_type", "")
    
    # Only check for types that should have formulas
    if methodology_type not in ["diagnostic", "analysis", "optimization"]:
        return []
    
    empty_count = 0
    total_count = len(inds)
    
    for ind in inds:
        if not isinstance(ind, dict):
            continue
        formula = str(ind.get("formula") or "").strip()
        if not formula:
            empty_count += 1
    
    empty_ratio = empty_count / total_count if total_count > 0 else 0
    
    if empty_ratio >= 1.0:
        # 100% empty formulas
        issues.append(
            Issue(
                id="EMPTY-FORM-001",
                severity="BLOCKER",
                category="completeness",
                message=f"All {total_count} indicators have empty formulas (methodology_type={methodology_type})",
                evidence={
                    "pointer": "/structure/indicators/*/formula",
                    "snippet": f"{empty_count}/{total_count} indicators with empty formula"
                },
                fix_hint="Extract formulas from source text or mark methodology_type as 'planning' if formulas not applicable.",
            )
        )
    elif empty_ratio > threshold:
        issues.append(
            Issue(
                id="EMPTY-FORM-002",
                severity="MAJOR",
                category="completeness",
                message=f"{empty_count}/{total_count} ({empty_ratio:.0%}) indicators have empty formulas (threshold={threshold:.0%})",
                evidence={
                    "pointer": "/structure/indicators/*/formula",
                    "snippet": f"{empty_count} indicators without formulas"
                },
                fix_hint="Extract formulas from source text or reduce indicator count to only those with clear definitions.",
            )
        )
    
    return issues


def precheck_readme_coverage(book_id: str, compiled: Dict[str, Any]) -> List[Issue]:
    """
    Check if README.md covers all stages.
    README should list all stage titles or at least mention all stage_XXX IDs.
    """
    issues: List[Issue] = []
    readme_path = DOCS_DIR / "methodologies" / book_id / "README.md"
    
    if not readme_path.exists():
        return []  # Already caught by precheck_docs_consistency
    
    stages = ((compiled.get("structure", {}) or {}).get("stages", []) or [])
    if not stages:
        return []
    
    try:
        readme_content = readme_path.read_text(encoding="utf-8").lower()
    except Exception:
        return []
    
    total_stages = len(stages)
    found_count = 0
    missing_stages = []
    
    for idx, stage in enumerate(stages):
        if not isinstance(stage, dict):
            continue
        
        stage_id = stage.get("id", f"stage_{idx+1:03d}")
        title = str(stage.get("title") or "").strip().lower()
        
        # Check if stage_id or title appears in README
        if stage_id.lower() in readme_content or (title and title in readme_content):
            found_count += 1
        else:
            missing_stages.append(stage_id)
    
    coverage_ratio = found_count / total_stages if total_stages > 0 else 1.0
    
    if coverage_ratio < 0.5:
        # Less than 50% stages covered
        issues.append(
            Issue(
                id="README-COV-001",
                severity="BLOCKER",
                category="docs",
                message=f"README.md covers only {found_count}/{total_stages} ({coverage_ratio:.0%}) stages",
                evidence={
                    "path": str(readme_path),
                    "snippet": f"Missing stages: {', '.join(missing_stages[:5])}{'...' if len(missing_stages) > 5 else ''}"
                },
                fix_hint="Re-run Agent C to generate complete README with all stages.",
            )
        )
    elif coverage_ratio < 0.8:
        # 50-80% coverage
        issues.append(
            Issue(
                id="README-COV-002",
                severity="MAJOR",
                category="docs",
                message=f"README.md incomplete: {found_count}/{total_stages} ({coverage_ratio:.0%}) stages documented",
                evidence={
                    "path": str(readme_path),
                    "snippet": f"Missing {len(missing_stages)} stages"
                },
                fix_hint="Complete README generation to include all stages.",
            )
        )
    
    return issues


def precheck_duplicate_stage_titles(compiled: Dict[str, Any]) -> List[Issue]:
    """
    Check for duplicate stage titles (exact match after normalization).
    This catches obvious copy-paste errors before LLM semantic analysis.
    """
    issues: List[Issue] = []
    stages = ((compiled.get("structure", {}) or {}).get("stages", []) or [])
    if not isinstance(stages, list):
        return []
    
    def normalize_title(title: str) -> str:
        """Normalize: lowercase, strip, ё→е, remove extra spaces"""
        return re.sub(r'\s+', ' ', title.lower().strip().replace("ё", "е"))
    
    seen: Dict[str, List[int]] = {}
    for idx, stage in enumerate(stages):
        if not isinstance(stage, dict):
            continue
        title = str(stage.get("title") or "").strip()
        if not title:
            continue
        
        norm_title = normalize_title(title)
        if norm_title not in seen:
            seen[norm_title] = []
        seen[norm_title].append(idx)
    
    # Find duplicates
    for norm_title, indices in seen.items():
        if len(indices) > 1:
            ids = [f"stage_{i+1:03d}" for i in indices]
            issues.append(
                Issue(
                    id=f"DUP-STAGE-{indices[0]+1:03d}",
                    severity="MAJOR",
                    category="duplicates",
                    message=f"Duplicate stage title '{norm_title}' found at {len(indices)} locations: {', '.join(ids)}",
                    evidence={
                        "pointer": f"/structure/stages/{indices[0]} and {indices[1]}",
                        "snippet": f"Title: '{norm_title}' appears {len(indices)} times"
                    },
                    fix_hint="Merge duplicate stages or rename to distinguish different contexts.",
                )
            )
    
    return issues


# -----------------------------
# LLM reasoning (Claude 3.5 Sonnet via Requesty)
# -----------------------------
class LLMReviewer:
    """
    Claude Sonnet 4.5 via Requesty AI gateway.
    
    Checks:
    - Logical coherence: contradictions, duplication, broken flow
    - Completeness: is methodology actionable?
    - Formula sanity: semantic errors (e.g., numerator/denominator swap)
    - Glossary consistency: term usage matches definitions
    
    Returns:
      - issues: List[Issue] with evidence
      - strengths: List[str] (brief positive observations)
    """

    def __init__(self, requesty_api_key: Optional[str] = None) -> None:
        self.api_key = requesty_api_key or os.getenv("REQUESTY_API_KEY")
        if not self.api_key:
            raise ValueError("REQUESTY_API_KEY not found in environment or parameters")
        
        self.base_url = "https://router.requesty.ai"
        
        # Load prompts
        system_prompt_path = INPUTS_DIR / "agent_d_system.md"
        if system_prompt_path.exists():
            self.system_prompt = system_prompt_path.read_text(encoding="utf-8")
        else:
            self.system_prompt = self._default_system_prompt()
    
    def _default_system_prompt(self) -> str:
        return """You are Agent D (QA Reviewer). You do quality assurance only.

Hard rules:
- Do NOT add new stages/tools/indicators/rules.
- Do NOT rewrite the methodology content.
- Do NOT use external knowledge.
- Evaluate only based on the provided artifacts.
- Output must be strictly grounded in evidence (file path + pointer/quote snippet ≤ 25 words).

Your tasks:
1) Logical coherence: detect contradictions, duplication, broken flow across stages.
2) Glossary validation: identify terms not present in glossary or inconsistent usage.
3) Formula sanity: check formulas for obvious semantic or structural errors.
4) Completeness: whether the methodology is actionable (stages + at least some indicators/tools/rules where appropriate).

Return JSON object with:
- issues: array of {severity: "BLOCKER"|"MAJOR"|"MINOR", category: string, message: string, evidence: {path: string, pointer: string, snippet?: string}, fix_hint: string}
- strengths: array of strings (brief positive observations)

Severity:
- BLOCKER: must fix before publish
- MAJOR: important, likely reduces usability or correctness
- MINOR: formatting or small clarity issues

Decision policy:
If any BLOCKER -> approved=false.
Else if majors >= 3 -> approved=false.
Else approved=true.

Output ONLY valid JSON, no additional text."""

    def review(
        self,
        *,
        compiled_yaml: Dict[str, Any],
        outline_yaml: Dict[str, Any],
        docs_readme: str,
    ) -> Tuple[List[Issue], List[str]]:
        """
        Run LLM reasoning on methodology artifacts.
        
        Returns:
            (issues, strengths)
        """
        # Build user prompt
        user_prompt = self._build_user_prompt(compiled_yaml, outline_yaml, docs_readme)
        
        # Call Claude via Requesty
        try:
            messages = [
                {"role": "user", "content": f"{self.system_prompt}\n\n{user_prompt}"},
            ]
            
            # HTTP request to Requesty
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": "anthropic/claude-sonnet-4-5",
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": 4000,
            }
            
            response = requests.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            
            # Requesty возвращает Anthropic format
            data = response.json()
            
            # Extract text from Anthropic response format
            content = data.get("content", [])
            if isinstance(content, list) and len(content) > 0:
                text = content[0].get("text", "")
            else:
                text = str(content)
            
            # Debug: print raw response
            print(f"\n🔍 Claude response (first 500 chars):\n{text[:500]}\n", file=sys.stderr)
            
            # Try to extract JSON from markdown code blocks if present
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                if json_end > json_start:
                    text = text[json_start:json_end].strip()
            elif "```" in text:
                # Try generic code block
                json_start = text.find("```") + 3
                json_end = text.find("```", json_start)
                if json_end > json_start:
                    text = text[json_start:json_end].strip()
            
            # Parse JSON response
            result = json.loads(text)
            
            # Convert to Issue objects
            issues = []
            for idx, iss in enumerate(result.get("issues", []), start=1):
                issues.append(
                    Issue(
                        id=f"LLM-{idx:03d}",
                        severity=iss.get("severity", "MINOR"),
                        category=iss.get("category", "reasoning"),
                        message=iss.get("message", ""),
                        evidence=iss.get("evidence", {}),
                        fix_hint=iss.get("fix_hint", ""),
                    )
                )
            
            strengths = result.get("strengths", [])
            
            return issues, strengths
        
        except Exception as e:
            print(f"⚠️ LLM reasoning failed: {e}", file=sys.stderr)
            return [], []
    
    def _build_user_prompt(
        self,
        compiled_yaml: Dict[str, Any],
        outline_yaml: Dict[str, Any],
        docs_readme: str,
    ) -> str:
        """Build user prompt with artifacts."""
        
        # Extract key sections (avoid sending too much)
        structure = compiled_yaml.get("structure", {}) or {}
        stages = structure.get("stages", []) or []
        tools = structure.get("tools", []) or []
        indicators = structure.get("indicators", []) or []
        rules = structure.get("rules", []) or []
        
        # Outline metadata
        outline_meta = outline_yaml.get("metadata", {}) or {}
        outline_class = outline_yaml.get("classification", {}) or {}
        
        prompt = f"""Artifacts for QA review:

## 1) Compiled YAML (Agent C output)

**Metadata:**
- book_id: {compiled_yaml.get('book_id', 'N/A')}
- title: {compiled_yaml.get('title', 'N/A')}
- methodology_type: {compiled_yaml.get('methodology_type', 'N/A')}

**Structure summary:**
- Stages: {len(stages)}
- Tools: {len(tools)}
- Indicators: {len(indicators)}
- Rules: {len(rules)}

**Stages (first 5 for context):**
{json.dumps(stages[:5], ensure_ascii=False, indent=2)}

**Tools:**
{json.dumps(tools, ensure_ascii=False, indent=2)}

**Indicators (first 10):**
{json.dumps(indicators[:10], ensure_ascii=False, indent=2)}

**Rules:**
{json.dumps(rules, ensure_ascii=False, indent=2)}

## 2) Outline YAML (Agent B output)

**Metadata:**
{json.dumps(outline_meta, ensure_ascii=False, indent=2)}

**Classification:**
{json.dumps(outline_class, ensure_ascii=False, indent=2)}

## 3) README.md (docs)

```markdown
{docs_readme[:2000]}
{"..." if len(docs_readme) > 2000 else ""}
```

## Your task:

Analyze the above artifacts for:
1. **Logical coherence**: Do stages make sense in order? Any contradictions/duplication?
2. **Completeness**: Is the methodology actionable? Missing critical components?
3. **Formula sanity**: Do indicator formulas make semantic sense?
4. **Consistency**: Does compiled YAML match outline intent?

Return JSON with:
- issues: [{{"severity": "BLOCKER/MAJOR/MINOR", "category": "string", "message": "string", "evidence": {{"path": "string", "pointer": "string", "snippet": "string"}}, "fix_hint": "string"}}]
- strengths: ["string"]

Output ONLY valid JSON."""
        
        return prompt


# -----------------------------
# Scoring & decision
# -----------------------------
def compute_score(issues: List[Issue], glossary_coverage: float, formula_ratio: float, schema_ok: bool) -> int:
    # Start from 100; subtract penalties
    score = 100
    if not schema_ok:
        score -= 40

    for it in issues:
        if it.severity == "BLOCKER":
            score -= 25
        elif it.severity == "MAJOR":
            score -= 10
        elif it.severity == "MINOR":
            score -= 3

    # metrics influence (soft)
    score -= int((1.0 - glossary_coverage) * 20)
    score -= int((1.0 - formula_ratio) * 15)

    return max(0, min(100, score))


def decide(issues: List[Issue]) -> bool:
    blockers = sum(1 for i in issues if i.severity == "BLOCKER")
    majors = sum(1 for i in issues if i.severity == "MAJOR")
    if blockers >= 1:
        return False
    if majors >= 3:
        return False
    return True


# -----------------------------
# Report generation
# -----------------------------
def render_qa_report(book_id: str, approved: bool, score: int, issues: List[Issue], strengths: List[str]) -> str:
    blockers = [i for i in issues if i.severity == "BLOCKER"]
    majors = [i for i in issues if i.severity == "MAJOR"]
    minors = [i for i in issues if i.severity == "MINOR"]

    def fmt_issue(i: Issue) -> str:
        ev = i.evidence or {}
        ptr = ev.get("pointer") or ev.get("path") or ""
        snippet = ev.get("snippet")
        s = f"- **[{i.severity}][{i.category}]** {i.message}"
        if ptr:
            s += f"\n  - Evidence: `{ptr}`"
        if snippet:
            s += f"\n  - Snippet: `{snippet}`"
        if i.fix_hint:
            s += f"\n  - Fix: {i.fix_hint}"
        return s

    md = []
    md.append(f"# QA Report — {book_id}\n")
    md.append("## Verdict")
    md.append(f"- approved: **{str(approved).lower()}**")
    md.append(f"- score: **{score}/100**\n")

    if blockers:
        md.append("## Blockers")
        for i in blockers:
            md.append(fmt_issue(i))
        md.append("")

    if majors:
        md.append("## Major issues")
        for i in majors:
            md.append(fmt_issue(i))
        md.append("")

    if minors:
        md.append("## Minor issues")
        for i in minors:
            md.append(fmt_issue(i))
        md.append("")

    if strengths:
        md.append("## Strengths (from reasoning layer)")
        for s in strengths:
            md.append(f"- {s}")
        md.append("")

    md.append("## Next actions (pipeline)")
    md.append("1. Fix BLOCKER/MAJOR issues in Agent B output or Agent C compilation.")
    md.append("2. Re-run Agent C (compile) to regenerate `data/` and `docs/`.")
    md.append("3. Re-run Agent D (QA) until approved.\n")

    return "\n".join(md)


# -----------------------------
# Main runner
# -----------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Agent D QA Reviewer")
    p.add_argument("--book", required=True, help="book_id (work/<id>/outline.yaml, data/methodologies/<id>.yaml)")
    p.add_argument(
        "--schema",
        default=str(SCHEMAS_DIR / "methodology_compiled.schema.json"),
        help="Schema for compiled YAML (Agent C output).",
    )
    p.add_argument(
        "--glossary",
        default="",
        help="Optional glossary index path or folder (e.g., data/glossary or data/glossary/index.json).",
    )
    p.add_argument("--use-llm", action="store_true", help="Enable reasoning layer (Claude Sonnet 4.5 via Requesty).")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    book_id = args.book

    outline_path = WORK_DIR / book_id / "outline.yaml"
    compiled_path = DATA_DIR / "methodologies" / f"{book_id}.yaml"
    docs_readme_path = DOCS_DIR / "methodologies" / book_id / "README.md"
    schema_path = Path(args.schema)

    qa_dir = WORK_DIR / book_id / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    issues: List[Issue] = []
    strengths: List[str] = []

    print("🔍 Agent D QA Reviewer")
    print(f"📖 Book: {book_id}")
    print(f"🧬 Schema: {schema_path.name}")
    print(f"🤖 LLM: {'Claude Sonnet 4.5 (Requesty)' if args.use_llm else 'disabled'}\n")

    # --- Schema precheck
    print("1️⃣ Schema validation...")
    schema_issues = precheck_schema(compiled_path, schema_path)
    issues.extend(schema_issues)

    schema_ok = (len([i for i in schema_issues if i.severity == "BLOCKER"]) == 0)
    print(f"   {'✅' if schema_ok else '❌'} Schema: {len(schema_issues)} issues")

    # If schema is broken, we still try to load compiled YAML for better feedback
    compiled: Dict[str, Any] = {}
    if compiled_path.exists():
        try:
            compiled = read_yaml(compiled_path)
        except Exception as e:
            issues.append(
                Issue(
                    id="RUNTIME-001",
                    severity="BLOCKER",
                    category="runtime",
                    message=f"Failed to parse compiled YAML: {e}",
                    evidence={"path": str(compiled_path)},
                    fix_hint="Fix YAML syntax or regenerate with Agent C.",
                )
            )

    # --- Outline presence check
    print("2️⃣ Outline validation...")
    outline: Dict[str, Any] = {}
    if not outline_path.exists():
        issues.append(
            Issue(
                id="FILES-OUTLINE-001",
                severity="BLOCKER",
                category="files",
                message="Outline YAML not found (Agent B output missing).",
                evidence={"path": str(outline_path)},
                fix_hint="Run Agent B to produce work/<id>/outline.yaml",
            )
        )
        print("   ❌ Outline: missing")
    else:
        try:
            outline = read_yaml(outline_path)
            print("   ✅ Outline: loaded")
        except Exception as e:
            issues.append(
                Issue(
                    id="FILES-OUTLINE-002",
                    severity="BLOCKER",
                    category="files",
                    message=f"Failed to parse outline YAML: {e}",
                    evidence={"path": str(outline_path)},
                    fix_hint="Fix outline.yaml syntax or regenerate Agent B.",
                )
            )
            print(f"   ❌ Outline: parse error ({e})")

    # --- Other prechecks (only if compiled loaded)
    if compiled:
        print("3️⃣ ID format checks...")
        id_issues = precheck_ids(compiled)
        issues.extend(id_issues)
        print(f"   {'✅' if not id_issues else '⚠️'} IDs: {len(id_issues)} issues")

        print("4️⃣ Docs consistency...")
        docs_issues = precheck_docs_consistency(book_id, compiled)
        issues.extend(docs_issues)
        print(f"   {'✅' if not docs_issues else '⚠️'} Docs: {len(docs_issues)} issues")

        print("5️⃣ Duplicate indicators...")
        dup_ind_issues = precheck_duplicate_indicators(compiled)
        issues.extend(dup_ind_issues)
        print(f"   {'✅' if not dup_ind_issues else '⚠️'} Duplicates: {len(dup_ind_issues)} issues")

        print("6️⃣ Stage order checks...")
        order_issues = precheck_stage_order(compiled)
        issues.extend(order_issues)
        print(f"   {'✅' if not order_issues else '⚠️'} Stage order: {len(order_issues)} issues")

        print("7️⃣ Duplicate stage titles...")
        dup_stage_issues = precheck_duplicate_stage_titles(compiled)
        issues.extend(dup_stage_issues)
        print(f"   {'✅' if not dup_stage_issues else '⚠️'} Duplicate titles: {len(dup_stage_issues)} issues")

        print("8️⃣ README coverage...")
        readme_issues = precheck_readme_coverage(book_id, compiled)
        issues.extend(readme_issues)
        print(f"   {'✅' if not readme_issues else '⚠️'} README: {len(readme_issues)} issues")

        print("9️⃣ Glossary checks...")
        glossary_terms = None
        if args.glossary:
            glossary_terms = load_glossary_terms(Path(args.glossary))
        glossary_issues, glossary_cov = precheck_glossary(compiled, glossary_terms)
        issues.extend(glossary_issues)
        print(f"   {'✅' if not glossary_issues else '⚠️'} Glossary: {len(glossary_issues)} issues, coverage={glossary_cov:.2%}")

        print("🔟 Formula syntax...")
        formula_issues, formula_ratio = precheck_formulas(compiled)
        issues.extend(formula_issues)
        print(f"   {'✅' if not formula_issues else '⚠️'} Formulas: {len(formula_issues)} issues, passed={formula_ratio:.2%}")

        print("1️⃣1️⃣ Empty formulas check...")
        empty_form_issues = precheck_empty_formulas(compiled, threshold=0.7)
        issues.extend(empty_form_issues)
        print(f"   {'✅' if not empty_form_issues else '⚠️'} Empty formulas: {len(empty_form_issues)} issues")
    else:
        glossary_cov = 1.0
        formula_ratio = 1.0

    # --- Reasoning layer (LLM) optional
    docs_readme = ""
    if docs_readme_path.exists():
        docs_readme = docs_readme_path.read_text(encoding="utf-8")

    llm_issues: List[Issue] = []
    llm_strengths: List[str] = []
    
    if args.use_llm:
        print("🤖 LLM reasoning (Claude Sonnet 4.5)...")
        requesty_api_key = os.getenv("REQUESTY_API_KEY")
        reviewer = LLMReviewer(requesty_api_key=requesty_api_key)
        llm_issues, llm_strengths = reviewer.review(
            compiled_yaml=compiled,
            outline_yaml=outline,
            docs_readme=docs_readme,
        )
        issues.extend(llm_issues)
        strengths.extend(llm_strengths)
        print(f"   {'✅' if not llm_issues else '⚠️'} LLM: {len(llm_issues)} issues, {len(llm_strengths)} strengths")

    # --- Decide & score
    print("\n📊 Computing verdict...")
    approved = decide(issues)
    score = compute_score(issues, glossary_cov, formula_ratio, schema_ok)

    # --- Build qa_result.json
    qa_result = {
        "book_id": book_id,
        "approved": approved,
        "score": score,
        "summary": {
            "blockers": sum(1 for i in issues if i.severity == "BLOCKER"),
            "majors": sum(1 for i in issues if i.severity == "MAJOR"),
            "minors": sum(1 for i in issues if i.severity == "MINOR"),
        },
        "issues": [i.to_dict() for i in issues],
        "metrics": {
            "schema_valid": schema_ok,
            "glossary_coverage": round(float(glossary_cov), 4),
            "formula_checks_passed": round(float(formula_ratio), 4),
        },
        "llm_findings": {
            "enabled": args.use_llm,
            "issues_found": len(llm_issues) if args.use_llm else 0,
            "strengths_found": len(llm_strengths) if args.use_llm else 0,
            "model": "claude-sonnet-4.5" if args.use_llm else None,
        },
        "generated_at": now_iso(),
        "reviewer": {
            "agent": "Agent D",
            "model": "claude-sonnet-4.5" if args.use_llm else "none (precheck-only)",
            "prompt_version": "v1.0",
        },
    }

    qa_report = render_qa_report(book_id, approved, score, issues, strengths)

    # --- Write outputs
    write_json(qa_dir / "qa_result.json", qa_result)
    write_text(qa_dir / "qa_report.md", qa_report)
    write_text(qa_dir / "approved.flag", "true" if approved else "false")

    # --- Console summary
    print("\n✅ Agent D QA done")
    print(f"- approved: {approved}")
    print(f"- score:    {score}/100")
    print(f"- out:      {qa_dir}\n")

    return 0 if approved else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"❌ Agent D failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)
