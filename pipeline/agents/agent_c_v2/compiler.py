#!/usr/bin/env python3
"""
Agent C v2: Compiler (Deterministic, NO LLM Content Generation)

Philosophy:
- Agent C is a COMPILER, not a content generator
- NO adding new facts, recommendations, or "common mistakes"
- NO interpretation beyond formatting
- Only transforms outline.yaml → normalized YAML + markdown docs

Input:
  work/<book_id>/outline.yaml

Output:
  data/methodologies/<book_id>.yaml  (normalized, machine-readable)
  docs/methodologies/<book_id>/README.md
  docs/methodologies/<book_id>/stages/*.md
  docs/methodologies/<book_id>/tools/*.md
  docs/methodologies/<book_id>/indicators/*.md
  docs/methodologies/<book_id>/rules/*.md

Dependencies:
  pip install pyyaml jinja2 python-slugify
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from slugify import slugify


# Paths
REPO_ROOT = Path(__file__).resolve().parents[3]  # From pipeline/agents/agent_c_v2/ -> repo root
DEFAULT_WORK_DIR = REPO_ROOT / "work"
DEFAULT_SOURCES_DIR = REPO_ROOT / "sources"
DEFAULT_DOCS_DIR = REPO_ROOT / "docs"
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DEFAULT_TEMPLATES_DIR = REPO_ROOT / "templates" / "methodology"


# Helpers
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_slug(text: str) -> str:
    """Create safe filename slug."""
    if not text:
        return "item"
    s = slugify(text, lowercase=True)
    return (s[:60] if len(s) > 60 else s) or "item"


def read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a dict, got: {type(data)}")
    return data


def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=120)


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ensure_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def normalize_tool_type(t: str) -> str:
    """Normalize tool types to standard set."""
    if not isinstance(t, str):
        return "other"
    t0 = t.strip().lower()
    mapping = {
        "table": "table",
        "template": "template",
        "checklist": "checklist",
        "calculator": "calculator",
        "document": "document",
        "chart": "chart",
        "graph": "chart",
        "map": "other",
    }
    return mapping.get(t0, "other")


# Fallback templates (if no Jinja2 files)
FALLBACK_README = """# {{ title }}

## Тип методологии
- **methodology_type:** {{ methodology_type }}

## Этапы
{% for s in stages %}
{{ loop.index }}. **{{ s.title }}** — {{ s.description }}
{% endfor %}

## Разделы
- Этапы: `./stages/`
- Инструменты: `./tools/`
- Показатели: `./indicators/`
- Правила: `./rules/`
"""

FALLBACK_STAGE = """# {{ s.title }}

## Описание
{{ s.description }}

## Порядок
{{ s.order_display }}

{% if s.source %}
## Источник
{{ s.source }}
{% endif %}
"""

FALLBACK_TOOL = """# {{ t.title }}

## Тип
{{ t.type }}

## Описание
{{ t.description }}
"""

FALLBACK_INDICATOR = """# {{ i.name }}

## Описание
{{ i.description }}

{% if i.formula %}
## Формула
`{{ i.formula }}`
{% endif %}
"""

FALLBACK_RULE = """# Rule {{ r.id }}

## Условие
{{ r.condition }}

## Действие
{{ r.action }}

## Важность
{{ r.severity }}
"""


def jinja_env(templates_dir: Path) -> Environment:
    """Create Jinja2 environment."""
    if templates_dir.exists():
        return Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)


def get_template(env: Environment, templates_dir: Path, name: str, fallback: str):
    """Get template from file or use fallback."""
    if templates_dir.exists():
        try:
            return env.get_template(name)
        except Exception:
            return env.from_string(fallback)
    return env.from_string(fallback)


@dataclass
class Normalized:
    """Normalized methodology data."""
    book_id: str
    title: str
    methodology_type: str
    raw_outline: Dict[str, Any]
    normalized_yaml: Dict[str, Any]
    stages: List[Dict[str, Any]]
    tools: List[Dict[str, Any]]
    indicators: List[Dict[str, Any]]
    rules: List[Dict[str, Any]]


def infer_book_id_from_outline_path(outline_path: Path) -> str:
    """Extract book_id from path: work/<book_id>/outline.yaml"""
    return outline_path.parent.name


def load_sources_metadata(sources_dir: Path, book_id: str) -> Dict[str, Any]:
    """Load sources/<book_id>/metadata.json if exists."""
    p = sources_dir / book_id / "metadata.json"
    if p.exists():
        try:
            return read_json(p)
        except Exception:
            return {}
    return {}


def normalize_outline(raw: Dict[str, Any], book_id: str, sources_meta: Dict[str, Any]) -> Normalized:
    """
    Normalize outline.yaml into clean structure.
    
    CRITICAL: This function does NOT add new content!
    - Only assigns stable IDs
    - Only normalizes types
    - Only fills metadata fields
    - Does NOT invent stages/tools/indicators/rules
    """
    classification = raw.get("classification") or {}
    structure = raw.get("structure") or {}

    methodology_type = str(classification.get("methodology_type") or "analysis").strip().lower()

    # Title: prefer sources metadata, else book_id
    title = (
        sources_meta.get("title")
        or sources_meta.get("name")
        or sources_meta.get("book_title")
        or book_id
    )

    raw_stages = ensure_list(structure.get("stages"))
    raw_tools = ensure_list(structure.get("tools"))
    raw_inds = ensure_list(structure.get("indicators"))
    raw_rules = ensure_list(structure.get("rules"))

    # Stages: preserve original order values, assign stable IDs
    stages: List[Dict[str, Any]] = []
    for idx, s in enumerate(raw_stages, start=1):
        if not isinstance(s, dict):
            continue
        title_s = str(s.get("title") or f"Stage {idx}").strip()
        desc_s = str(s.get("description") or "").strip()
        order_val = s.get("order")
        order_display = f"{idx} (source order: {order_val})" if order_val is not None else str(idx)
        stages.append({
            "id": f"stage_{idx:03d}",
            "title": title_s,
            "description": desc_s,
            "order": int(order_val) if isinstance(order_val, int) else None,
            "order_display": order_display,
            "source": None,
        })

    # Tools: normalize type, assign ID
    tools: List[Dict[str, Any]] = []
    for idx, t in enumerate(raw_tools, start=1):
        if not isinstance(t, dict):
            continue
        tools.append({
            "id": f"tool_{idx:03d}",
            "title": str(t.get("title") or f"Tool {idx}").strip(),
            "type": normalize_tool_type(t.get("type")),
            "description": str(t.get("description") or "").strip(),
        })

    # Indicators: use 'name' field (from current outline format)
    indicators: List[Dict[str, Any]] = []
    for idx, i in enumerate(raw_inds, start=1):
        if not isinstance(i, dict):
            continue
        indicators.append({
            "id": f"ind_{idx:03d}",
            "name": str(i.get("name") or i.get("title") or f"Indicator {idx}").strip(),
            "description": str(i.get("description") or "").strip(),
            "formula": (str(i.get("formula")).strip() if i.get("formula") else ""),
        })

    # Rules: condition/action/severity
    rules: List[Dict[str, Any]] = []
    for idx, r in enumerate(raw_rules, start=1):
        if not isinstance(r, dict):
            continue
        rules.append({
            "id": f"rule_{idx:03d}",
            "condition": str(r.get("condition") or "").strip(),
            "action": str(r.get("action") or "").strip(),
            "severity": str(r.get("severity") or "medium").strip().lower(),
        })

    # Build normalized YAML for machine layer
    normalized_yaml: Dict[str, Any] = {
        "metadata": {
            "id": book_id,
            "title": title,
            "created_at": now_iso(),
            "source": {
                "work_outline": f"work/{book_id}/outline.yaml",
                "sources_metadata": f"sources/{book_id}/metadata.json" if sources_meta else None,
            },
            "agent_b_metadata": raw.get("metadata") or {},
        },
        "classification": {"methodology_type": methodology_type},
        "structure": {
            "stages": stages,
            "tools": tools,
            "indicators": indicators,
            "rules": rules,
        },
    }

    return Normalized(
        book_id=book_id,
        title=title,
        methodology_type=methodology_type,
        raw_outline=raw,
        normalized_yaml=normalized_yaml,
        stages=stages,
        tools=tools,
        indicators=indicators,
        rules=rules,
    )


def render_all(norm: Normalized, templates_dir: Path, docs_dir: Path) -> Path:
    """Render all markdown documentation using Jinja2 templates."""
    env = jinja_env(templates_dir)

    readme_tpl = get_template(env, templates_dir, "README.md.j2", FALLBACK_README)
    stage_tpl = get_template(env, templates_dir, "stage.md.j2", FALLBACK_STAGE)
    tool_tpl = get_template(env, templates_dir, "tool.md.j2", FALLBACK_TOOL)
    ind_tpl = get_template(env, templates_dir, "indicator.md.j2", FALLBACK_INDICATOR)
    rule_tpl = get_template(env, templates_dir, "rule.md.j2", FALLBACK_RULE)

    out_base = docs_dir / "methodologies" / norm.book_id
    stages_dir = out_base / "stages"
    tools_dir = out_base / "tools"
    inds_dir = out_base / "indicators"
    rules_dir = out_base / "rules"

    # README
    readme = readme_tpl.render(
        title=norm.title,
        methodology_type=norm.methodology_type,
        stages=norm.stages,
    )
    write_text(out_base / "README.md", readme)

    # Stages
    for s in norm.stages:
        fname = f"{s['id']}_{safe_slug(s['title'])}.md"
        md = stage_tpl.render(s=s)
        write_text(stages_dir / fname, md)

    # Tools
    for t in norm.tools:
        fname = f"{t['id']}_{safe_slug(t['title'])}.md"
        md = tool_tpl.render(t=t)
        write_text(tools_dir / fname, md)

    # Indicators
    for i in norm.indicators:
        fname = f"{i['id']}_{safe_slug(i['name'])}.md"
        md = ind_tpl.render(i=i)
        write_text(inds_dir / fname, md)

    # Rules
    for r in norm.rules:
        fname = f"{r['id']}.md"
        md = rule_tpl.render(r=r)
        write_text(rules_dir / fname, md)

    return out_base


def compile_methodology(
    book_id: str,
    work_dir: Path = DEFAULT_WORK_DIR,
    sources_dir: Path = DEFAULT_SOURCES_DIR,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    data_dir: Path = DEFAULT_DATA_DIR,
    templates_dir: Path = DEFAULT_TEMPLATES_DIR,
) -> None:
    """
    Public API for orchestrator: compile outline.yaml -> normalized YAML + docs.
    
    Args:
        book_id: Book/methodology ID
        work_dir: Work directory (default: repo/work)
        sources_dir: Sources directory (default: repo/sources)
        docs_dir: Docs directory (default: repo/docs)
        data_dir: Data directory (default: repo/data)
        templates_dir: Templates directory (default: repo/templates/methodology)
    """
    outline_path = Path(work_dir) / book_id / "outline.yaml"
    
    if not outline_path.exists():
        raise FileNotFoundError(f"Outline not found: {outline_path}")
    
    # Load and normalize
    raw = read_yaml(outline_path)
    sources_meta = load_sources_metadata(Path(sources_dir), book_id)
    norm = normalize_outline(raw=raw, book_id=book_id, sources_meta=sources_meta)
    
    # Write normalized YAML (machine layer)
    out_yaml_path = Path(data_dir) / "methodologies" / f"{book_id}.yaml"
    write_yaml(out_yaml_path, norm.normalized_yaml)
    
    # Render docs
    render_all(norm, templates_dir=Path(templates_dir), docs_dir=Path(docs_dir))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Agent C v2: Deterministic Compiler")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--book", help="book_id (expects work/<book_id>/outline.yaml)")
    g.add_argument("--outline", help="path to outline.yaml")

    p.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR))
    p.add_argument("--sources-dir", default=str(DEFAULT_SOURCES_DIR))
    p.add_argument("--docs-dir", default=str(DEFAULT_DOCS_DIR))
    p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    p.add_argument("--templates-dir", default=str(DEFAULT_TEMPLATES_DIR))

    return p.parse_args()


def main() -> None:
    args = parse_args()

    work_dir = Path(args.work_dir)
    sources_dir = Path(args.sources_dir)
    docs_dir = Path(args.docs_dir)
    data_dir = Path(args.data_dir)
    templates_dir = Path(args.templates_dir)

    if args.book:
        book_id = args.book
        outline_path = work_dir / book_id / "outline.yaml"
    else:
        outline_path = Path(args.outline)
        book_id = infer_book_id_from_outline_path(outline_path)

    if not outline_path.exists():
        raise FileNotFoundError(f"Outline not found: {outline_path}")

    print(f"\n📚 Agent C v2: Deterministic Compiler")
    print(f"→ Input:  {outline_path}")
    print(f"→ Book ID: {book_id}")

    # Load and normalize
    raw = read_yaml(outline_path)
    sources_meta = load_sources_metadata(sources_dir, book_id)
    norm = normalize_outline(raw=raw, book_id=book_id, sources_meta=sources_meta)

    print(f"\n✅ Normalized:")
    print(f"   Stages: {len(norm.stages)}")
    print(f"   Tools: {len(norm.tools)}")
    print(f"   Indicators: {len(norm.indicators)}")
    print(f"   Rules: {len(norm.rules)}")

    # Write normalized YAML (machine layer)
    out_yaml_path = data_dir / "methodologies" / f"{book_id}.yaml"
    write_yaml(out_yaml_path, norm.normalized_yaml)
    print(f"\n💾 Machine YAML: {out_yaml_path}")

    # Render docs
    out_docs_path = render_all(norm, templates_dir=templates_dir, docs_dir=docs_dir)
    print(f"📝 Docs: {out_docs_path}")

    if templates_dir.exists():
        print(f"📄 Templates: {templates_dir}")
    else:
        print("📄 Templates: <fallback inline templates used>")

    print("\n✅ Agent C v2 compile done (NO LLM content generation)")


if __name__ == "__main__":
    main()
