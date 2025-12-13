# pipeline/agents/agent_g_glossary_sync/normalize.py
from __future__ import annotations

import re


def normalize_text(s: str) -> str:
    """
    Normalize text for matching:
    - lowercase
    - ё → е
    - collapse whitespace
    """
    s = (s or "").strip().lower()
    s = s.replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_term_id(term_id: str) -> str:
    """
    Make stable _key / term_id for ArangoDB:
    - lowercase
    - replace spaces with _
    - keep only [a-z0-9_:-]
    - prefix with term_ if not present
    
    Examples:
      "Учетная политика" → "term_учетная_политика"
      "EBITDA" → "term_ebitda"
      "Коэффициент текущей ликвидности" → "term_коэффициент_текущей_ликвидности"
    """
    t = normalize_text(term_id)
    
    # Replace non-alphanumeric with underscore (keep cyrillic)
    t = re.sub(r"[^\w\-:]+", "_", t, flags=re.UNICODE)
    
    # Collapse multiple underscores
    t = re.sub(r"_+", "_", t).strip("_")
    
    # Ensure prefix
    if not t.startswith("term_"):
        t = f"term_{t}"
    
    return t
