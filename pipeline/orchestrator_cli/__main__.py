# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from pipeline.orchestrator_cli.runner import (
    OrchestratorConfig,
    OrchestratorRunner,
    now_run_id,
)
from pipeline.orchestrator_cli.bundles import bundle_sources, auto_bundle_sources


def main() -> None:
    p = argparse.ArgumentParser(description="KB Orchestrator CLI (MVP)")

    # Legacy mode: single book
    p.add_argument("--book-id", help="Book/methodology id (e.g. accounting-basics-test)")
    p.add_argument("--source-path", help="Path to sources/<book_id> (alternative to --book-id)")

    # Multi-source mode: explicit bundle
    p.add_argument("--bundle-id", help="Bundle id (e.g. power-of-one)")
    p.add_argument("--source-id", help="Single source id (alternative to --source-path)")
    
    # Multi-source mode: auto-bundle
    p.add_argument("--auto-bundle", action="store_true", help="Auto-detect methodology from source manifest")
    p.add_argument("--min-bundle-confidence", type=float, default=0.3, help="Min confidence for auto-bundle (default: 0.3)")

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

    # Resolve methodology_id and source_paths
    methodology_id: str = None
    source_paths: List[Path] = []
    
    if args.bundle_id:
        # Explicit bundle mode
        methodology_id, source_paths = bundle_sources(
            bundle_id=args.bundle_id,
            bundles_dir=Path("data/bundles"),
            sources_dir=Path("sources")
        )
        print(f"📦 Bundle: {args.bundle_id} → methodology: {methodology_id}, sources: {[sp.name for sp in source_paths]}")
    
    elif args.auto_bundle:
        # Auto-bundle mode: group sources by methodology
        if not args.source_id and not args.source_path:
            raise SystemExit("ERROR: --auto-bundle requires --source-id or --source-path")
        
        from pipeline.orchestrator_cli.bundles import load_source_manifest, pick_methodology_id_from_manifest
        
        if args.source_id:
            source_path = Path("sources") / args.source_id
        else:
            source_path = Path(args.source_path)
        
        manifest = load_source_manifest(source_path)
        if not manifest:
            raise SystemExit(f"ERROR: source_manifest.json not found in {source_path}")
        
        methodology_id = pick_methodology_id_from_manifest(manifest, args.min_bundle_confidence)
        if not methodology_id:
            raise SystemExit(f"ERROR: No methodology detected in {source_path} (confidence too low)")
        
        source_paths = [source_path]
        print(f"🔍 Auto-detected methodology: {methodology_id} from source: {source_path.name} (confidence: {manifest['signals']['confidence']:.2%})")
    
    elif args.source_id:
        # Single source mode (new style)
        source_path = Path("sources") / args.source_id
        methodology_id = args.book_id or args.source_id
        source_paths = [source_path]
    
    elif args.source_path:
        # Legacy: source_path provided
        source_path = Path(args.source_path)
        methodology_id = args.book_id or source_path.name
        source_paths = [source_path]
    
    elif args.book_id:
        # Legacy: book_id provided
        methodology_id = args.book_id
        source_path = Path("sources") / args.book_id
        source_paths = [source_path]
    
    else:
        raise SystemExit("ERROR: provide --book-id, --source-path, --source-id, --bundle-id, or --auto-bundle")

    run_id = args.run_id or now_run_id()

    # policy default = True unless explicitly disabled
    require_gate_pass = True
    if args.no_require_gate_pass:
        require_gate_pass = False
    elif args.require_gate_pass:
        require_gate_pass = True

    cfg = OrchestratorConfig(
        book_id=methodology_id,
        source_path=source_paths[0] if source_paths else Path("sources") / methodology_id,
        source_paths=source_paths if source_paths else None,
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
