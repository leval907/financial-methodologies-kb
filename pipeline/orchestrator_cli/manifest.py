# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


def iso_now() -> str:
    # Simple ISO-like timestamp; good enough for logs/manifest
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class StepRecord:
    name: str
    status: str  # ok|fail|skipped
    artifacts: List[str]

    started_at: str
    ended_at: str
    duration_sec: float

    error: Optional[str] = None


@dataclass
class QARecord:
    approved: Optional[bool] = None
    blockers: Optional[int] = None
    warnings: Optional[int] = None
    gate_status: Optional[str] = None  # PASS|FAIL|None


@dataclass
class PolicyRecord:
    require_gate_pass: bool = True


@dataclass
class RunManifest:
    run_id: str
    book_id: str
    source_path: str

    steps: List[StepRecord]
    qa: QARecord
    policy: PolicyRecord

    created_at: str
    
    # Multi-source support
    sources: List[str] = None  # List of source_ids that contributed to this methodology

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    def write(self, run_dir: Path) -> None:
        write_json(run_dir / "manifest.json", self.to_dict())
