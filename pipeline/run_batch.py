#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Pipeline Runner

Purpose:
- Run orchestrator on multiple books
- Collect PASS/FAIL summary
- Generate batch report

Usage:
  python pipeline/run_batch.py --books accounting-basics-test,simple-numbers
  python pipeline/run_batch.py --auto  # Auto-discover from sources/
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class BookResult:
    book_id: str
    success: bool
    exit_code: int
    duration_sec: float
    run_id: str
    
    gate_status: Optional[str] = None
    gate_blockers: int = 0
    qa_approved: Optional[bool] = None
    qa_blockers: int = 0
    
    error: Optional[str] = None


def discover_books(sources_dir: Path) -> List[str]:
    """Auto-discover books from sources/ directory."""
    if not sources_dir.exists():
        return []
    
    books = []
    for item in sources_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Check if it has extracted/blocks.jsonl
            blocks = item / "extracted" / "blocks.jsonl"
            if blocks.exists():
                books.append(item.name)
    
    return sorted(books)


def run_book(
    book_id: str,
    steps: str,
    require_gate_pass: bool,
    run_id_prefix: str,
) -> BookResult:
    """Run orchestrator on a single book."""
    print(f"\n{'='*60}")
    print(f"📚 Processing: {book_id}")
    print(f"{'='*60}")
    
    run_id = f"{run_id_prefix}_{book_id}"
    
    cmd = [
        "python", "-m", "pipeline.orchestrator_cli",
        "--book-id", book_id,
        "--steps", steps,
        "--run-id", run_id,
    ]
    
    if not require_gate_pass:
        cmd.append("--no-require-gate-pass")
    
    start = time.time()
    result = subprocess.run(cmd, check=False, capture_output=False)
    duration = time.time() - start
    
    exit_code = result.returncode
    success = (exit_code == 0)
    
    # Try to read manifest for details
    manifest_path = Path("qa") / "runs" / run_id / "manifest.json"
    gate_status = None
    gate_blockers = 0
    qa_approved = None
    qa_blockers = 0
    error = None
    
    if manifest_path.exists():
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                manifest = json.load(f)
            
            qa = manifest.get("qa", {})
            gate_status = qa.get("gate_status")
            qa_approved = qa.get("approved")
            qa_blockers = qa.get("blockers", 0)
            
            # Gate blockers from gate report
            gate_report = manifest_path.parent / "b_quality_gate.json"
            if gate_report.exists():
                with gate_report.open("r", encoding="utf-8") as f:
                    gate_data = json.load(f)
                    gate_blockers = len(gate_data.get("errors", []))
            
            # Check for step errors
            failed_steps = [s for s in manifest.get("steps", []) if s.get("status") == "fail"]
            if failed_steps:
                error = f"Failed step: {failed_steps[0]['name']}"
                if failed_steps[0].get("error"):
                    error = failed_steps[0]["error"]
        except Exception as e:
            error = f"Failed to read manifest: {e}"
    
    return BookResult(
        book_id=book_id,
        success=success,
        exit_code=exit_code,
        duration_sec=round(duration, 2),
        run_id=run_id,
        gate_status=gate_status,
        gate_blockers=gate_blockers,
        qa_approved=qa_approved,
        qa_blockers=qa_blockers,
        error=error,
    )


def render_batch_report(
    results: List[BookResult],
    batch_id: str,
    steps: str,
) -> str:
    """Render batch report as markdown."""
    lines = []
    
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count
    
    total_duration = sum(r.duration_sec for r in results)
    
    lines.append(f"# Batch Pipeline Report")
    lines.append("")
    lines.append(f"**Batch ID**: `{batch_id}`  ")
    lines.append(f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
    lines.append(f"**Steps**: {steps}  ")
    lines.append(f"**Total books**: {len(results)}  ")
    lines.append(f"**Success**: {success_count}  ")
    lines.append(f"**Failed**: {fail_count}  ")
    lines.append(f"**Total duration**: {total_duration:.1f}s  ")
    lines.append("")
    
    # Overall verdict
    if fail_count == 0:
        lines.append("## Verdict")
        lines.append("")
        lines.append(f"✅ **All {len(results)} books processed successfully**")
        lines.append("")
    else:
        lines.append("## Verdict")
        lines.append("")
        lines.append(f"⚠️ **{fail_count}/{len(results)} books failed**")
        lines.append("")
        lines.append("**Next actions**:")
        lines.append("1. Review failed books below")
        lines.append("2. Check individual `qa/runs/<run_id>/release/summary.md`")
        lines.append("3. Fix issues and re-run failed books")
        lines.append("")
    
    # Summary table
    lines.append("## Results")
    lines.append("")
    lines.append("| Book | Status | Duration | Gate | QA | Blockers |")
    lines.append("|------|--------|----------|------|----|---------| ")
    
    for r in results:
        status_icon = "✅" if r.success else "❌"
        gate_str = r.gate_status if r.gate_status else "-"
        qa_str = "✅" if r.qa_approved else ("❌" if r.qa_approved is False else "-")
        blockers = r.gate_blockers + r.qa_blockers
        
        lines.append(f"| {r.book_id} | {status_icon} | {r.duration_sec:.1f}s | {gate_str} | {qa_str} | {blockers} |")
    
    lines.append("")
    
    # Failed books details
    failed = [r for r in results if not r.success]
    if failed:
        lines.append("## Failed Books")
        lines.append("")
        for r in failed:
            lines.append(f"### {r.book_id}")
            lines.append("")
            lines.append(f"- **Exit code**: {r.exit_code}")
            lines.append(f"- **Run ID**: `{r.run_id}`")
            if r.error:
                lines.append(f"- **Error**: {r.error}")
            if r.gate_status == "FAIL":
                lines.append(f"- **Gate blockers**: {r.gate_blockers}")
            if r.qa_approved is False:
                lines.append(f"- **QA blockers**: {r.qa_blockers}")
            lines.append(f"- **Details**: `qa/runs/{r.run_id}/release/summary.md`")
            lines.append("")
    
    # Success stats
    if success_count > 0:
        lines.append("## Statistics")
        lines.append("")
        
        passed_gate = sum(1 for r in results if r.gate_status == "PASS")
        if passed_gate > 0:
            lines.append(f"- **Gate PASS**: {passed_gate}/{len(results)}")
        
        approved = sum(1 for r in results if r.qa_approved)
        if approved > 0:
            lines.append(f"- **QA Approved**: {approved}/{len(results)}")
        
        avg_duration = total_duration / len(results)
        lines.append(f"- **Avg duration**: {avg_duration:.1f}s per book")
        lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Generated by Batch Pipeline Runner*")
    
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch Pipeline Runner")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--books", help="Comma-separated list of book IDs")
    group.add_argument("--auto", action="store_true", help="Auto-discover books from sources/")
    
    parser.add_argument("--steps", default="B,C,D,Gate,G,E,F", help="Steps to run (default: full pipeline)")
    parser.add_argument("--batch-id", help="Batch ID (default: batch_<timestamp>)")
    parser.add_argument("--no-require-gate-pass", action="store_true", help="Continue on Gate FAIL")
    parser.add_argument("--sources-dir", default="sources", help="Sources directory (default: sources)")
    
    args = parser.parse_args()
    
    # Determine batch ID
    batch_id = args.batch_id or f"batch_{int(time.time())}"
    
    # Get book list
    if args.auto:
        sources_dir = Path(args.sources_dir)
        books = discover_books(sources_dir)
        if not books:
            print(f"❌ No books found in {sources_dir}")
            return 1
        print(f"📚 Auto-discovered {len(books)} books: {', '.join(books)}")
    else:
        books = [b.strip() for b in args.books.split(",") if b.strip()]
    
    if not books:
        print("❌ No books to process")
        return 1
    
    print(f"\n🚀 Starting batch: {batch_id}")
    print(f"📋 Books: {len(books)}")
    print(f"⚙️  Steps: {args.steps}")
    print(f"🔒 Require Gate PASS: {not args.no_require_gate_pass}")
    
    # Run each book
    results: List[BookResult] = []
    
    for book_id in books:
        result = run_book(
            book_id=book_id,
            steps=args.steps,
            require_gate_pass=(not args.no_require_gate_pass),
            run_id_prefix=batch_id,
        )
        results.append(result)
        
        status = "✅ SUCCESS" if result.success else f"❌ FAILED (exit {result.exit_code})"
        print(f"\n{status} - {book_id} ({result.duration_sec}s)")
    
    # Generate batch report
    report_md = render_batch_report(results, batch_id, args.steps)
    
    report_path = Path("qa") / f"{batch_id}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")
    
    print(f"\n{'='*60}")
    print(f"📊 Batch report: {report_path}")
    print(f"{'='*60}")
    
    # Summary
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count
    
    print(f"\n✅ Success: {success_count}/{len(results)}")
    if fail_count > 0:
        print(f"❌ Failed: {fail_count}/{len(results)}")
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
