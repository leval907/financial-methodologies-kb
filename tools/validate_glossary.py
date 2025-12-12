#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_glossary.py

Проверяет:
1) Все термины в data/glossary/*.yaml
2) Все glossary_terms в front matter методологий docs/methodologies/**.md
3) Несуществующие термины (используются, но нет yaml)
4) "Висячие" термины (есть yaml, но нигде не используются)
5) Дубли term в YAML
6) (опционально) соответствие methodology_id имени папки методологии
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml не установлен. Установи: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


FRONT_MATTER_RE = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL)

@dataclass
class MdDocMeta:
    path: Path
    methodology_id: str | None
    glossary_terms: List[str]


def load_front_matter(md_text: str) -> Dict:
    m = FRONT_MATTER_RE.match(md_text)
    if not m:
        return {}
    raw = m.group(1)
    try:
        data = yaml.safe_load(raw) or {}
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def read_md_meta(path: Path) -> MdDocMeta:
    text = path.read_text(encoding="utf-8", errors="ignore")
    fm = load_front_matter(text)

    methodology_id = fm.get("methodology_id")
    if methodology_id is not None and not isinstance(methodology_id, str):
        methodology_id = None

    gt = fm.get("glossary_terms", [])
    if gt is None:
        gt = []
    if isinstance(gt, str):
        gt = [gt]
    if not isinstance(gt, list):
        gt = []
    gt = [x.strip() for x in gt if isinstance(x, str) and x.strip()]

    return MdDocMeta(path=path, methodology_id=methodology_id, glossary_terms=gt)


def iter_md_files(root: Path) -> List[Path]:
    return [p for p in root.rglob("*.md") if p.is_file()]


def load_glossary_terms(glossary_dir: Path) -> Tuple[Dict[str, Path], Dict[str, List[Path]]]:
    """
    Возвращает:
    - term_to_file: term -> yaml path
    - duplicates: term -> [yaml paths...]
    """
    term_to_file: Dict[str, Path] = {}
    duplicates: Dict[str, List[Path]] = {}

    for ypath in sorted(glossary_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(ypath.read_text(encoding="utf-8", errors="ignore")) or {}
        except Exception:
            data = {}
        term = data.get("term")
        if not isinstance(term, str) or not term.strip():
            continue
        term = term.strip()

        if term in term_to_file:
            duplicates.setdefault(term, []).extend([term_to_file[term], ypath])
        else:
            term_to_file[term] = ypath

    # нормализуем duplicates (убираем повторы)
    for k, v in duplicates.items():
        uniq = []
        seen = set()
        for p in v:
            if p not in seen:
                uniq.append(p)
                seen.add(p)
        duplicates[k] = uniq

    return term_to_file, duplicates


def guess_methodology_folder_id(md_path: Path, methodologies_root: Path) -> str | None:
    """
    Пытается определить <id> из пути docs/methodologies/<id>/...
    """
    try:
        rel = md_path.relative_to(methodologies_root)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2:
        return None
    return parts[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Путь к корню репозитория financial-methodologies-kb")
    ap.add_argument("--glossary", default="data/glossary", help="Путь к data/glossary")
    ap.add_argument("--methodologies", default="docs/methodologies", help="Путь к docs/methodologies")
    ap.add_argument("--strict-methodology-id", action="store_true",
                    help="Если включено — проверяет, что methodology_id == имени папки методологии")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    glossary_dir = (repo / args.glossary).resolve()
    methodologies_root = (repo / args.methodologies).resolve()

    if not glossary_dir.exists():
        print(f"ERROR: Не найдена папка glossary: {glossary_dir}", file=sys.stderr)
        return 2

    term_to_file, duplicates = load_glossary_terms(glossary_dir)
    glossary_terms_set: Set[str] = set(term_to_file.keys())

    if not glossary_terms_set:
        print(f"ERROR: В {glossary_dir} не найдено ни одного валидного term", file=sys.stderr)
        return 2

    md_files = iter_md_files(methodologies_root) if methodologies_root.exists() else []
    used_terms: Set[str] = set()
    missing_terms_usage: Dict[str, List[Path]] = {}

    bad_methodology_ids: List[Tuple[Path, str, str]] = []  # (file, fm_id, folder_id)

    for md in md_files:
        meta = read_md_meta(md)

        # соберём использованные термины
        for t in meta.glossary_terms:
            used_terms.add(t)
            if t not in glossary_terms_set:
                missing_terms_usage.setdefault(t, []).append(md)

        # опциональная проверка methodology_id
        if args.strict_methodology_id:
            folder_id = guess_methodology_folder_id(md, methodologies_root)
            if folder_id and meta.methodology_id and meta.methodology_id != folder_id:
                bad_methodology_ids.append((md, meta.methodology_id, folder_id))

    orphan_terms = sorted(glossary_terms_set - used_terms)
    missing_terms = sorted(missing_terms_usage.keys())

    ok = True

    # Дубли
    if duplicates:
        ok = False
        print("\n[FAIL] Дубли term в YAML:")
        for term, paths in duplicates.items():
            print(f"  - {term}:")
            for p in paths:
                print(f"      {p.relative_to(repo)}")

    # Используются, но нет в data/glossary
    if missing_terms:
        ok = False
        print("\n[FAIL] Термины используются в методологиях, но отсутствуют в data/glossary:")
        for term in missing_terms:
            print(f"  - {term}")
            for p in sorted(missing_terms_usage[term]):
                print(f"      used in: {p.relative_to(repo)}")

    # Висячие термины
    if orphan_terms:
        print("\n[WARN] Термины есть в data/glossary, но не используются ни в одной методологии:")
        for term in orphan_terms:
            print(f"  - {term}  ({term_to_file[term].relative_to(repo)})")

    # Несоответствие methodology_id папке
    if bad_methodology_ids:
        ok = False
        print("\n[FAIL] Несоответствие methodology_id имени папки (strict-mode):")
        for f, fm_id, folder_id in bad_methodology_ids:
            print(f"  - {f.relative_to(repo)}: front_matter={fm_id} folder={folder_id}")

    # Итог
    print("\n[SUMMARY]")
    print(f"  glossary terms (yaml): {len(glossary_terms_set)}")
    print(f"  methodology md files:  {len(md_files)}")
    print(f"  used terms:            {len(used_terms)}")
    print(f"  orphan terms:          {len(orphan_terms)}")
    print(f"  missing terms:         {len(missing_terms)}")

    if ok:
        print("\nOK: Проверка пройдена.")
        return 0
    else:
        print("\nERROR: Проверка не пройдена.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
