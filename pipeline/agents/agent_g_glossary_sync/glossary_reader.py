# pipeline/agents/agent_g_glossary_sync/glossary_reader.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import yaml


def load_glossary_terms(glossary_dir: str) -> List[Dict[str, Any]]:
    """
    Reads glossary terms from directory:
      - *.yml / *.yaml: single doc or list
      - *.json: single doc or list
    
    Returns list of term dicts.
    Each dict will have _source_file added for traceability.
    """
    terms: List[Dict[str, Any]] = []
    
    if not os.path.isdir(glossary_dir):
        raise FileNotFoundError(f"Glossary dir not found: {glossary_dir}")

    for root, _, files in os.walk(glossary_dir):
        for fn in files:
            path = os.path.join(root, fn)
            if fn.endswith((".yml", ".yaml")):
                terms.extend(_read_yaml(path))
            elif fn.endswith(".json"):
                terms.extend(_read_json(path))

    return terms


def _read_yaml(path: str) -> List[Dict[str, Any]]:
    """Read YAML file and return list of terms."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return _ensure_list(data, source_path=path)


def _read_json(path: str) -> List[Dict[str, Any]]:
    """Read JSON file and return list of terms."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _ensure_list(data, source_path=path)


def _ensure_list(data: Any, source_path: str) -> List[Dict[str, Any]]:
    """
    Normalize data to list of dicts.
    Adds _source_file to each dict for lineage tracking.
    """
    if data is None:
        return []
    
    if isinstance(data, dict):
        # Single term
        data["_source_file"] = source_path
        return [data]
    
    if isinstance(data, list):
        # List of terms
        out = []
        for item in data:
            if isinstance(item, dict):
                item["_source_file"] = source_path
                out.append(item)
        return out
    
    # Unsupported type
    return []
