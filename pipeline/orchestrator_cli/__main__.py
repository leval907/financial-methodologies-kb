# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.orchestrator_cli.runner import (
    OrchestratorConfig,
    OrchestratorRunner,
    now_run_id,
)


def main() -> None:
    p = argparse.ArgumentParser(description="KB Orchestrator CLI (MVP)")

    p.add_argument("--book-id", help="Book/methodology id (e.g. accounting-basics-test)")
    p.add_argument("--source-path", help="Path to sources/<book_id> (alternative to --book-id)")

    p.add_argument(
        "--steps",
        default="B,C,D,Gate,G,E,F",
        help="Comma-separated steps: B,C,D,Gate,G,E,F",
    )
    p.add_argument("--run-id", default=None, help="Run id (default kb_<timestamp>)")

    # policy
    p.add_argument("--require-gate-pass", action="store_true", help="Stop on Gate FAIL (default)")
    p.add_argument("--no-require-gate-pass", action="store_true", help="Allow continuing even if Gate FAIL")

    # agent B
    p.add_argument("--use-gigachat", action="store_true", help="Use GigaChat in Agent B")

    # agent E
    p.add_argument("--skip-qa", action="store_true", help="Pass --skip-qa to Agent E")

    # agent G
    p.add_argument("--g-reconcile", action="store_true", help="Pass --reconcile to Agent G")
    p.add_argument("--g-dry-run", action="store_true", help="Pass --dry-run to Agent G")

    args = p.parse_args()

    # resolve book_id + source_path
    if args.source_path:
        source_path = Path(args.source_path)
        book_id = args.book_id or source_path.name
    else:
        if not args.book_id:
            raise SystemExit("ERROR: provide --book-id or --source-path")
        book_id = args.book_id
        source_path = Path("sources") / book_id

    run_id = args.run_id or now_run_id()

    # policy default = True unless explicitly disabled
    require_gate_pass = True
    if args.no_require_gate_pass:
        require_gate_pass = False
    elif args.require_gate_pass:
        require_gate_pass = True

    cfg = OrchestratorConfig(
        book_id=book_id,
        source_path=source_path,
        run_id=run_id,
        steps=[s.strip() for s in args.steps.split(",") if s.strip()],
        require_gate_pass=require_gate_pass,
        use_gigachat=bool(args.use_gigachat),
        skip_qa_for_e=bool(args.skip_qa),
        g_reconcile=bool(args.g_reconcile),
        g_dry_run=bool(args.g_dry_run),
    )

    run_dir = Path("qa") / "runs" / run_id
    runner = OrchestratorRunner(cfg, run_dir)
    code = runner.run()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
