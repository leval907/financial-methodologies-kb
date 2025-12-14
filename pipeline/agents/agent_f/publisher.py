# -*- coding: utf-8 -*-
"""
Agent F0: Release Summary Publisher (MVP without GitHub API)

Philosophy:
- F0 = Local summary generation only
- NO GitHub API integration
- Input: manifest.json from orchestrator
- Output: release/summary.md with actionable insights

Future F1:
- GitHub PR creation via API
- Auto-labeling (qa:pass, qa:fail)
- PR description from summary.md
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class StepSummary:
    name: str
    status: str
    duration_sec: float
    artifacts: List[str]
    error: Optional[str]


@dataclass
class ReleaseSummary:
    run_id: str
    book_id: str
    created_at: str
    total_duration: float
    
    steps: List[StepSummary]
    
    # QA
    gate_status: Optional[str]
    gate_metrics: Optional[Dict[str, Any]]
    gate_errors: Optional[List[Dict[str, str]]]
    
    approved: Optional[bool]
    blockers: int
    warnings: int
    
    # Policy
    require_gate_pass: bool
    
    # Overall
    success: bool
    exit_code: int
    
    @property
    def total_steps(self) -> int:
        return len(self.steps)
    
    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == "ok")
    
    @property
    def failed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == "fail")
    
    @property
    def skipped_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == "skipped")


def parse_manifest(manifest_path: Path) -> ReleaseSummary:
    """Parse manifest.json into ReleaseSummary."""
    with manifest_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    steps = [
        StepSummary(
            name=s["name"],
            status=s["status"],
            duration_sec=s.get("duration_sec", 0.0),
            artifacts=s.get("artifacts", []),
            error=s.get("error"),
        )
        for s in data.get("steps", [])
    ]
    
    qa = data.get("qa", {})
    policy = data.get("policy", {})
    
    # Calculate total duration
    total_duration = sum(s.duration_sec for s in steps)
    
    # Determine exit code and success
    gate_status = qa.get("gate_status")
    require_gate_pass = policy.get("require_gate_pass", True)
    
    failed = any(s.status == "fail" for s in steps)
    gate_fail = gate_status == "FAIL" and require_gate_pass
    
    if failed:
        exit_code = 1
        success = False
    elif gate_fail:
        exit_code = 2
        success = False
    else:
        exit_code = 0
        success = True
    
    # Try to load gate report for detailed metrics
    gate_metrics = None
    gate_errors = None
    if gate_status:
        run_dir = manifest_path.parent
        gate_report = run_dir / "b_quality_gate.json"
        if gate_report.exists():
            with gate_report.open("r", encoding="utf-8") as f:
                gate_data = json.load(f)
                gate_metrics = gate_data.get("metrics", {})
                gate_errors = gate_data.get("errors", [])
    
    return ReleaseSummary(
        run_id=data["run_id"],
        book_id=data["book_id"],
        created_at=data["created_at"],
        total_duration=total_duration,
        steps=steps,
        gate_status=gate_status,
        gate_metrics=gate_metrics,
        gate_errors=gate_errors,
        approved=qa.get("approved"),
        blockers=qa.get("blockers", 0),
        warnings=qa.get("warnings", 0),
        require_gate_pass=require_gate_pass,
        success=success,
        exit_code=exit_code,
    )


def render_summary(summary: ReleaseSummary) -> str:
    """Render ReleaseSummary as markdown."""
    lines = []
    
    # Header
    lines.append(f"# Release Summary: {summary.book_id}")
    lines.append("")
    lines.append(f"**Run ID**: `{summary.run_id}`  ")
    lines.append(f"**Created**: {summary.created_at}  ")
    lines.append(f"**Duration**: {summary.total_duration:.1f}s  ")
    lines.append(f"**Status**: {'✅ SUCCESS' if summary.success else '❌ FAILED'}  ")
    lines.append(f"**Exit Code**: {summary.exit_code}")
    lines.append("")
    
    # Overall verdict
    lines.append("## Verdict")
    lines.append("")
    if summary.success:
        lines.append("✅ **Pipeline completed successfully**")
        if summary.gate_status == "PASS":
            lines.append("- Quality Gate: **PASS**")
        if summary.approved is not None:
            status = "✅ APPROVED" if summary.approved else "⚠️ NOT APPROVED"
            lines.append(f"- QA Review: **{status}**")
        lines.append("")
        lines.append("**Next actions**:")
        lines.append("- Review artifacts in `work/` and `data/`")
        lines.append("- Methodology ready for publication")
    elif summary.exit_code == 2:
        lines.append("🚫 **Pipeline stopped: Quality Gate FAIL**")
        lines.append("")
        lines.append(f"- Gate status: **{summary.gate_status}**")
        lines.append(f"- Blockers: **{summary.blockers}** issues")
        lines.append("")
        lines.append("**Next actions**:")
        lines.append("1. Review Gate errors below")
        lines.append("2. Fix Agent B output (outline.yaml)")
        lines.append("3. Re-run: `python -m pipeline.orchestrator_cli --book-id {} --steps Gate,G,E`".format(summary.book_id))
    else:
        lines.append("❌ **Pipeline failed during execution**")
        lines.append("")
        failed_step = next((s for s in summary.steps if s.status == "fail"), None)
        if failed_step:
            lines.append(f"- Failed step: **{failed_step.name}**")
            if failed_step.error:
                lines.append(f"- Error: `{failed_step.error}`")
        lines.append("")
        lines.append("**Next actions**:")
        lines.append("1. Check error details below")
        lines.append("2. Fix the issue in agent code or input data")
        lines.append("3. Re-run full pipeline")
    lines.append("")
    
    # Steps summary
    lines.append("## Pipeline Steps")
    lines.append("")
    lines.append(f"**Total**: {summary.total_steps} | **Completed**: {summary.completed_steps} | **Failed**: {summary.failed_steps} | **Skipped**: {summary.skipped_steps}")
    lines.append("")
    lines.append("| Step | Status | Duration | Artifacts |")
    lines.append("|------|--------|----------|-----------|")
    
    for step in summary.steps:
        status_icon = {"ok": "✅", "fail": "❌", "skipped": "⏭️"}.get(step.status, "❓")
        artifacts_str = f"{len(step.artifacts)} files" if step.artifacts else "-"
        lines.append(f"| {step.name} | {status_icon} {step.status} | {step.duration_sec:.2f}s | {artifacts_str} |")
    
    lines.append("")
    
    # Gate details (if executed)
    if summary.gate_status:
        lines.append("## Quality Gate")
        lines.append("")
        lines.append(f"**Status**: {summary.gate_status}")
        lines.append("")
        
        if summary.gate_metrics:
            lines.append("### Metrics")
            lines.append("")
            metrics = summary.gate_metrics
            lines.append(f"- **Stages**: {metrics.get('n_stages', 'N/A')}")
            lines.append(f"- **Empty stage descriptions**: {metrics.get('empty_stage_desc_ratio', 0):.1%}")
            lines.append(f"- **Stage order correct**: {'✅ Yes' if metrics.get('order_ok') else '❌ No'}")
            lines.append(f"- **Indicators**: {metrics.get('n_indicators', 'N/A')}")
            lines.append(f"- **Empty indicator descriptions**: {metrics.get('empty_indicator_desc_ratio', 0):.1%}")
            lines.append(f"- **Formula coverage**: {metrics.get('formula_non_empty_ratio', 0):.1%}")
            lines.append(f"- **Severity enum valid**: {'✅ Yes' if metrics.get('severity_ok') else '❌ No'}")
            lines.append(f"- **Duplicate indicators**: {metrics.get('duplicate_indicators', 0)}")
            lines.append("")
        
        if summary.gate_errors:
            lines.append("### Errors")
            lines.append("")
            for err in summary.gate_errors:
                lines.append(f"- **{err.get('code')}**: {err.get('message')}")
            lines.append("")
    
    # QA details (if executed)
    if summary.approved is not None:
        lines.append("## QA Review (Agent D)")
        lines.append("")
        lines.append(f"**Approved**: {'✅ Yes' if summary.approved else '❌ No'}")
        lines.append(f"**Blockers**: {summary.blockers}")
        lines.append(f"**Warnings**: {summary.warnings}")
        lines.append("")
        if summary.blockers > 0:
            lines.append("⚠️ **Action required**: Review QA report in `work/{}/qa/qa_report.md`".format(summary.book_id))
            lines.append("")
    
    # Artifacts
    lines.append("## Artifacts")
    lines.append("")
    has_artifacts = False
    for step in summary.steps:
        if step.artifacts:
            has_artifacts = True
            lines.append(f"### {step.name}")
            lines.append("")
            for artifact in step.artifacts:
                lines.append(f"- `{artifact}`")
            lines.append("")
    
    if not has_artifacts:
        lines.append("*No artifacts produced*")
        lines.append("")
    
    # Error details (if any)
    errors = [s for s in summary.steps if s.error]
    if errors:
        lines.append("## Error Details")
        lines.append("")
        for step in errors:
            lines.append(f"### Step: {step.name}")
            lines.append("")
            lines.append("```")
            lines.append(step.error or "Unknown error")
            lines.append("```")
            lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Generated by Agent F0 (Release Summary Publisher)*")
    
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent F0: Release Summary Publisher")
    parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    parser.add_argument("--output", help="Output path for summary.md (default: <manifest_dir>/release/summary.md)")
    
    args = parser.parse_args()
    
    manifest_path = Path(args.manifest)
    
    if not manifest_path.exists():
        print(f"❌ Manifest not found: {manifest_path}")
        return 1
    
    # Parse manifest
    summary = parse_manifest(manifest_path)
    
    # Render summary
    md = render_summary(summary)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = manifest_path.parent / "release" / "summary.md"
    
    # Write summary
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    
    print(f"✅ Release summary generated: {output_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
