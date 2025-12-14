# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from pipeline.orchestrator_cli.manifest import (
    StepRecord,
    RunManifest,
    QARecord,
    PolicyRecord,
    iso_now,
    ensure_dir,
    write_json,
)


ALLOWED_STEPS = ["B", "C", "D", "Gate", "G", "E", "F"]


def now_run_id() -> str:
    return f"kb_{int(time.time())}"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_cmd(cmd: List[str]) -> Tuple[int, str]:
    """
    Runs command and returns (returncode, printable_cmd).
    """
    printable = " ".join(cmd)
    r = subprocess.run(cmd, check=False)
    return r.returncode, printable


def find_outline(work_dir: Path, book_id: str) -> Path:
    preferred = work_dir / f"outline_{book_id}.yaml"
    if preferred.exists():
        return preferred
    legacy = work_dir / "outline.yaml"
    if legacy.exists():
        return legacy
    candidates = sorted(work_dir.glob("outline*.yaml"))
    if candidates:
        return candidates[0]
    raise FileNotFoundError(f"Outline file not found in: {work_dir}")


def _normalize_steps(raw: str) -> List[str]:
    steps = [s.strip() for s in raw.split(",") if s.strip()]
    # Validate
    unknown = [s for s in steps if s not in ALLOWED_STEPS]
    if unknown:
        raise ValueError(f"Unknown steps: {unknown}. Allowed: {ALLOWED_STEPS}")
    return steps


@dataclass
class OrchestratorConfig:
    book_id: str
    source_path: Path
    run_id: str
    steps: List[str]

    # policy
    require_gate_pass: bool = True

    # agent options
    use_gigachat: bool = False
    skip_qa_for_e: bool = False
    g_reconcile: bool = False
    g_dry_run: bool = False


class OrchestratorRunner:
    def __init__(self, cfg: OrchestratorConfig, run_dir: Path):
        self.cfg = cfg
        self.run_dir = run_dir

        self.manifest = RunManifest(
            run_id=cfg.run_id,
            book_id=cfg.book_id,
            source_path=str(cfg.source_path),
            steps=[],
            qa=QARecord(),
            policy=PolicyRecord(require_gate_pass=cfg.require_gate_pass),
            created_at=iso_now(),
        )

        ensure_dir(run_dir)
        self.manifest.write(run_dir)

    def _add_step(self, rec: StepRecord) -> None:
        self.manifest.steps.append(rec)
        self.manifest.write(self.run_dir)

    def _record_step(self, name: str, func) -> Tuple[bool, Optional[List[str]], Optional[str]]:
        """
        Execute a step function with timing + error capture.
        Returns: (ok, artifacts, error)
        """
        started = iso_now()
        t0 = time.time()
        try:
            artifacts = func() or []
            ended = iso_now()
            dt = time.time() - t0
            self._add_step(
                StepRecord(
                    name=name,
                    status="ok",
                    artifacts=[str(a) for a in artifacts],
                    started_at=started,
                    ended_at=ended,
                    duration_sec=round(dt, 3),
                    error=None,
                )
            )
            return True, artifacts, None
        except Exception as e:
            ended = iso_now()
            dt = time.time() - t0
            self._add_step(
                StepRecord(
                    name=name,
                    status="fail",
                    artifacts=[],
                    started_at=started,
                    ended_at=ended,
                    duration_sec=round(dt, 3),
                    error=str(e),
                )
            )
            return False, None, str(e)

    # ---------------- Step implementations ----------------

    def step_B(self) -> List[str]:
        """
        Agent B has no CLI; call Python API.
        Input: sources/<book_id>/extracted/blocks.jsonl
        Output: work/<book_id>/outline_<book_id>.yaml (fallback outline.yaml accepted)
        """
        book_id = self.cfg.book_id
        blocks_path = self.cfg.source_path / "extracted" / "blocks.jsonl"
        if not blocks_path.exists():
            raise FileNotFoundError(f"blocks.jsonl not found: {blocks_path}")

        work_dir = Path("work") / book_id
        ensure_dir(work_dir)

        from pipeline.agents.agent_b.agent_b import OutlineBuilder

        builder = OutlineBuilder(use_gigachat=self.cfg.use_gigachat)
        outline = builder.build_outline(str(blocks_path))

        # If Agent B already wrote a file, keep it; otherwise write canonical
        out_path = work_dir / f"outline_{book_id}.yaml"
        if not out_path.exists():
            out_path.write_text(
                yaml.safe_dump(outline, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

        return [out_path]

    def step_C(self) -> List[str]:
        """
        Agent C has no CLI; call compile_methodology(book_id)
        Outputs:
          data/methodologies/<book_id>.yaml
          work/<book_id>/compiled/*
        """
        from pipeline.agents.agent_c_v2.compiler import compile_methodology

        compile_methodology(self.cfg.book_id)

        artifacts: List[Path] = []
        meth = Path("data") / "methodologies" / f"{self.cfg.book_id}.yaml"
        if meth.exists():
            artifacts.append(meth)

        compiled_dir = Path("work") / self.cfg.book_id / "compiled"
        if compiled_dir.exists():
            artifacts.append(compiled_dir)

        return artifacts

    def step_D(self) -> List[str]:
        """
        Agent D has no CLI; call validate_methodology(book_id)
        Output:
          work/<book_id>/qa/qa_result.json
        Also fills manifest.qa approved/blockers/warnings.
        """
        from pipeline.agents.agent_d.reviewer import validate_methodology

        report = validate_methodology(self.cfg.book_id)

        qa_dir = Path("work") / self.cfg.book_id / "qa"
        ensure_dir(qa_dir)
        out = qa_dir / "qa_result.json"
        if not out.exists():
            write_json(out, report)

        # Fill qa summary in manifest
        try:
            # prefer written file, but fallback to returned dict
            data = read_json(out) if out.exists() else report
            self.manifest.qa.approved = data.get("approved")
            self.manifest.qa.blockers = data.get("blockers")
            self.manifest.qa.warnings = data.get("warnings")
            self.manifest.write(self.run_dir)
        except Exception:
            # do not fail the step because of summary parsing
            pass

        return [out]

    def step_Gate(self) -> Dict[str, Any]:
        """
        Deterministic gate for Agent B output.
        Input: work/<book_id>/outline*.yaml
        Output: qa/runs/<run_id>/b_quality_gate.json
        
        Returns gate result dict.
        Raises RuntimeError only on unexpected exit codes (not 0 or 2).
        """
        book_id = self.cfg.book_id
        outline_path = find_outline(Path("work") / book_id, book_id)

        report_path = self.run_dir / "b_quality_gate.json"

        cmd = [
            "python",
            "pipeline/agents/agent_b/quality_gate.py",
            "--input",
            str(outline_path),
            "--report",
            str(report_path),
        ]
        code, printable = run_cmd(cmd)
        
        # Gate exit codes: 0=PASS, 2=FAIL
        if code not in (0, 2):
            raise RuntimeError(f"Gate command failed with unexpected code ({code}): {printable}")

        gate = read_json(report_path)
        self.manifest.qa.gate_status = gate.get("status")
        self.manifest.write(self.run_dir)
        return gate

    def step_G(self) -> List[str]:
        """
        Agent G has CLI.
        Output: work/glossary_sync_report.json (as declared in your entrypoints)
        """
        cmd = ["python", "-m", "pipeline.agents.agent_g_glossary_sync"]
        if self.cfg.g_reconcile:
            cmd.append("--reconcile")
        if self.cfg.g_dry_run:
            cmd.append("--dry-run")

        code, printable = run_cmd(cmd)
        if code != 0:
            raise RuntimeError(f"Agent G failed ({code}): {printable}")

        report = Path("work") / "glossary_sync_report.json"
        return [report] if report.exists() else []

    def step_E(self) -> List[str]:
        """
        Agent E has CLI.
        Inputs:
          data/methodologies/<id>.yaml
          work/<id>/qa/qa_result.json
        Output:
          data/published/<id>.json
        """
        cmd = ["python", "-m", "pipeline.agents.agent_e", self.cfg.book_id]
        if self.cfg.skip_qa_for_e:
            cmd.append("--skip-qa")

        code, printable = run_cmd(cmd)
        if code != 0:
            raise RuntimeError(f"Agent E failed ({code}): {printable}")

        report = Path("data") / "published" / f"{self.cfg.book_id}.json"
        return [report] if report.exists() else []

    def step_F(self) -> List[str]:
        """
        Agent F: Release Summary Publisher (F0 - no GitHub API).
        Input: manifest.json (current run)
        Output: qa/runs/<run_id>/release/summary.md
        """
        manifest_path = self.run_dir / "manifest.json"
        output_path = self.run_dir / "release" / "summary.md"
        
        cmd = [
            "python",
            "pipeline/agents/agent_f/publisher.py",
            "--manifest",
            str(manifest_path),
            "--output",
            str(output_path),
        ]
        code, printable = run_cmd(cmd)
        if code != 0:
            raise RuntimeError(f"Agent F failed ({code}): {printable}")
        
        return [output_path] if output_path.exists() else []

    # ---------------- Main run logic ----------------

    def run(self) -> int:
        """
        Returns exit code:
          0 success
          2 gate fail (if require_gate_pass)
          1 runtime fail
        """
        steps = self.cfg.steps

        # Execute in the order requested, but typically B,C,D,Gate,G,E
        gate_result: Optional[Dict[str, Any]] = None

        for s in steps:
            if s == "B":
                ok, _, _ = self._record_step("B", self.step_B)
                if not ok:
                    write_json(self.run_dir / "final.json", {"status": "FINALIZE", "reason": "Step B failed"})
                    return 1

            elif s == "C":
                ok, _, _ = self._record_step("C", self.step_C)
                if not ok:
                    write_json(self.run_dir / "final.json", {"status": "FINALIZE", "reason": "Step C failed"})
                    return 1

            elif s == "D":
                ok, _, _ = self._record_step("D", self.step_D)
                if not ok:
                    write_json(self.run_dir / "final.json", {"status": "FINALIZE", "reason": "Step D failed"})
                    return 1

            elif s == "Gate":
                ok, _, _ = self._record_step("Gate", lambda: [str(self.run_dir / "b_quality_gate.json")] if self.step_Gate() else [])
                if not ok:
                    write_json(self.run_dir / "final.json", {"status": "FINALIZE", "reason": "Gate step failed"})
                    return 1

                # Read the produced gate JSON
                try:
                    gate_result = read_json(self.run_dir / "b_quality_gate.json")
                except Exception:
                    gate_result = None

                if (
                    self.cfg.require_gate_pass
                    and gate_result is not None
                    and gate_result.get("status") != "PASS"
                ):
                    # Gate fail: mark remaining steps as skipped
                    for remaining in steps[steps.index(s) + 1 :]:
                        if remaining in {"G", "E"}:
                            started = iso_now()
                            ended = iso_now()
                            self._add_step(
                                StepRecord(
                                    name=remaining,
                                    status="skipped",
                                    artifacts=[],
                                    started_at=started,
                                    ended_at=ended,
                                    duration_sec=0.0,
                                    error="Skipped due to Gate FAIL",
                                )
                            )
                    write_json(self.run_dir / "final.json", {"status": "FINALIZE", "reason": "Gate FAIL"})
                    return 2

            elif s == "G":
                ok, _, _ = self._record_step("G", self.step_G)
                if not ok:
                    write_json(self.run_dir / "final.json", {"status": "FINALIZE", "reason": "Step G failed"})
                    return 1

            elif s == "E":
                ok, _, _ = self._record_step("E", self.step_E)
                if not ok:
                    write_json(self.run_dir / "final.json", {"status": "FINALIZE", "reason": "Step E failed"})
                    return 1

            elif s == "F":
                ok, _, _ = self._record_step("F", self.step_F)
                if not ok:
                    write_json(self.run_dir / "final.json", {"status": "FINALIZE", "reason": "Step F failed"})
                    return 1

        write_json(self.run_dir / "final.json", {"status": "FINALIZE", "reason": "Completed"})
        return 0
