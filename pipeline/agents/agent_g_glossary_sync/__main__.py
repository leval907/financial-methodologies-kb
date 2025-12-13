# pipeline/agents/agent_g_glossary_sync/__main__.py
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add repo root to path
script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent.parent
sys.path.insert(0, str(repo_root))

from arangodb.client import ArangoDBClient
from dotenv import load_dotenv

from pipeline.agents.agent_g_glossary_sync.glossary_reader import load_glossary_terms
from pipeline.agents.agent_g_glossary_sync.normalize import normalize_term_id, normalize_text


def utc_now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def compute_content_hash(text: str) -> str:
    """Compute SHA256 hash of content_text."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def build_source_meta(args: argparse.Namespace) -> Dict[str, Any]:
    """Build source lineage metadata."""
    return {
        "repo": args.source_repo,
        "ref": args.source_ref,
        "path": args.source_path,
        "agent": "agent_g_glossary_sync"
    }


def make_term_doc(raw: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create canonical glossary_terms document.
    Enforces stable _key = term_id (normalized).
    
    Input fields (flexible):
      - term_id / id / _key / slug / name (для ID)
      - name / title (для отображения)
      - definition / desc / description
      - aliases / synonyms (list or str)
      - tags / domain (list or str)
      - version
      - status
    """
    # Determine term_id from various possible fields
    term_id = (
        raw.get("term_id") or 
        raw.get("id") or 
        raw.get("_key") or 
        raw.get("slug") or 
        raw.get("term") or  # ADD: support 'term' field
        raw.get("name") or
        raw.get("title")
    )
    
    if not term_id:
        raise ValueError(f"Cannot determine term_id from: {raw}")
    
    term_id = normalize_term_id(term_id)
    
    # Name (display)
    name = raw.get("name") or raw.get("title") or term_id
    
    # Definition
    definition = (
        raw.get("definition") or 
        raw.get("desc") or 
        raw.get("description") or 
        ""
    )
    
    # Aliases (normalize to list)
    aliases = raw.get("aliases") or raw.get("synonyms") or []
    if isinstance(aliases, str):
        aliases = [a.strip() for a in aliases.split(",") if a.strip()]
    
    # Tags (normalize to list)
    tags = raw.get("tags") or raw.get("domain") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    
    # Version
    version = raw.get("version") or "1.0"
    
    # Status (default to active for canonical terms)
    status = raw.get("status") or "active"
    
    # Build content_text for full-text search
    content_text = "\n".join([
        str(name).strip(),
        str(definition).strip(),
        " ".join([str(a).strip() for a in aliases if a]),
        " ".join([str(t).strip() for t in tags if t]),
    ]).strip()
    
    # Compute content hash
    content_hash = compute_content_hash(content_text)
    
    return {
        "_key": term_id,
        "term_id": term_id,
        "name": name,
        "definition": definition,
        "aliases": aliases,
        "tags": tags,
        "status": status,
        "version": version,
        "entity_type": "term",
        "content_text": content_text,
        "content_hash": content_hash,
        "source": source,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }


def reconcile_stubs(client: ArangoDBClient, canonical_terms: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Reconcile existing stubs (needs_definition) with canonical terms.
    
    Strategy:
    1. Find all stubs in DB (status=needs_definition)
    2. Match against canonical terms by:
       - term_id (exact)
       - name (normalized)
       - aliases (normalized)
    3. If matched:
       - Update stub: status=merged, merged_into=<canonical_term_id>
       - Rewire edges to canonical term (TODO: separate function)
    4. If not matched:
       - Keep stub as is
       - Add to unknown_terms list
    
    Returns reconciliation report.
    """
    print("\n🔍 Reconciling stubs with canonical terms...")
    
    # Build canonical index: term_id → doc
    canonical_index = {t["_key"]: t for t in canonical_terms}
    
    # Build normalized name index for fuzzy matching
    name_index: Dict[str, str] = {}
    for t in canonical_terms:
        norm_name = normalize_text(t["name"])
        name_index[norm_name] = t["_key"]
        
        # Also index aliases
        for alias in t.get("aliases", []):
            norm_alias = normalize_text(alias)
            name_index[norm_alias] = t["_key"]
    
    # Find stubs in DB
    result = client.db.aql.execute('''
        FOR t IN glossary_terms
            FILTER t.status == "needs_definition"
            RETURN t
    ''')
    
    stubs = list(result)
    
    matched = []
    unmatched = []
    
    for stub in stubs:
        stub_id = stub["_key"]
        stub_name = normalize_text(stub.get("name", ""))
        
        # Try exact term_id match
        if stub_id in canonical_index:
            matched.append({
                "stub_id": stub_id,
                "canonical_id": stub_id,
                "match_type": "exact_id"
            })
            continue
        
        # Try normalized name match
        if stub_name in name_index:
            canonical_id = name_index[stub_name]
            matched.append({
                "stub_id": stub_id,
                "canonical_id": canonical_id,
                "match_type": "name"
            })
            continue
        
        # No match found
        unmatched.append({
            "stub_id": stub_id,
            "stub_name": stub.get("name", ""),
            "status": "unknown_term"
        })
    
    # Update matched stubs
    updated_count = 0
    for match in matched:
        client.db.aql.execute('''
            FOR t IN glossary_terms
                FILTER t._key == @stub_id
                UPDATE t WITH {
                    status: "merged",
                    merged_into: @canonical_id,
                    merged_at: @now
                } IN glossary_terms
        ''', bind_vars={
            "stub_id": match["stub_id"],
            "canonical_id": match["canonical_id"],
            "now": utc_now_iso()
        })
        updated_count += 1
    
    report = {
        "total_stubs": len(stubs),
        "matched": len(matched),
        "unmatched": len(unmatched),
        "updated_count": updated_count,
        "matched_details": matched,
        "unknown_terms": unmatched
    }
    
    print(f"✅ Reconciliation complete:")
    print(f"  - Total stubs: {len(stubs)}")
    print(f"  - Matched: {len(matched)}")
    print(f"  - Unknown: {len(unmatched)}")
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Agent G: Glossary Sync (canonical glossary_terms → ArangoDB)"
    )
    
    # Paths
    parser.add_argument(
        "--glossary-dir",
        default="data/glossary",
        help="Path to glossary directory"
    )
    parser.add_argument(
        "--env-file",
        default=".env.arango",
        help="Arango env file"
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Repo base dir (for arangodb/schema, views, etc.)"
    )
    
    # Lineage/source meta
    parser.add_argument(
        "--source-repo",
        default="financial-methodologies-kb",
        help="Source repo name"
    )
    parser.add_argument(
        "--source-ref",
        default="main",
        help="Git ref (commit/tag)"
    )
    parser.add_argument(
        "--source-path",
        default="data/glossary",
        help="Relative path within repo"
    )
    
    # Behavior
    parser.add_argument(
        "--apply-schema",
        action="store_true",
        help="Apply Arango schema before sync"
    )
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Reconcile stubs (needs_definition) with canonical terms"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write to Arango, only report"
    )
    parser.add_argument(
        "--output-report",
        default="data/published/glossary_sync_report.json",
        help="Where to write report json"
    )
    
    args = parser.parse_args()
    
    # Determine base_dir
    if args.base_dir == ".":
        args.base_dir = str(repo_root)
    
    # Build absolute paths
    glossary_dir = os.path.join(args.base_dir, args.glossary_dir)
    env_file = os.path.join(args.base_dir, args.env_file)
    
    print("📚 Agent G: Glossary Sync")
    print("=" * 60)
    print(f"Glossary dir: {glossary_dir}")
    print(f"Env file: {env_file}")
    print(f"Base dir: {args.base_dir}")
    print(f"Dry run: {args.dry_run}")
    print(f"Reconcile: {args.reconcile}")
    
    # Build source metadata
    source = build_source_meta(args)
    
    # Load terms from filesystem
    print(f"\n📖 Loading glossary terms from {glossary_dir}...")
    loaded_terms = load_glossary_terms(glossary_dir)
    print(f"✅ Loaded {len(loaded_terms)} terms")
    
    # Normalize + build canonical docs
    docs: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    seen = set()
    
    print("\n🔧 Building canonical documents...")
    for t in loaded_terms:
        try:
            doc = make_term_doc(t, source=source)
            
            # De-dup inside batch (merge aliases/tags if duplicates)
            if doc["_key"] in seen:
                existing = next(d for d in docs if d["_key"] == doc["_key"])
                existing_aliases = set(existing.get("aliases", []))
                existing_tags = set(existing.get("tags", []))
                existing["aliases"] = sorted(list(existing_aliases.union(set(doc.get("aliases", [])))))
                existing["tags"] = sorted(list(existing_tags.union(set(doc.get("tags", [])))))
                
                # Prefer non-empty definition
                if not existing.get("definition") and doc.get("definition"):
                    existing["definition"] = doc["definition"]
                continue
            
            seen.add(doc["_key"])
            docs.append(doc)
        except Exception as ex:
            errors.append({"term": t, "error": str(ex)})
    
    print(f"✅ Prepared {len(docs)} canonical documents ({len(errors)} errors)")
    
    # Build report
    report: Dict[str, Any] = {
        "agent": "agent_g_glossary_sync",
        "glossary_dir": args.glossary_dir,
        "source": source,
        "loaded_terms": len(loaded_terms),
        "prepared_docs": len(docs),
        "errors": errors,
        "dry_run": args.dry_run,
        "timestamp": utc_now_iso(),
        "result": {}
    }
    
    if args.dry_run:
        print("\n🚫 Dry run mode - not writing to DB")
        _write_report(args.output_report, report)
        print(f"\n📄 Report saved: {args.output_report}")
        return
    
    # Connect to Arango
    print(f"\n🔌 Connecting to ArangoDB...")
    load_dotenv(env_file, override=True)
    client = ArangoDBClient(base_dir=args.base_dir)
    client.connect()
    print("✅ Connected")
    
    # Apply schema if requested
    if args.apply_schema:
        print("\n📐 Applying schema...")
        schema_result = client.apply_schema()
        report["schema"] = schema_result
        print("✅ Schema applied")
    
    # Upsert glossary_terms
    print(f"\n📝 Upserting {len(docs)} terms to glossary_terms...")
    bundle = {
        "entities": {
            "glossary_terms": docs
        },
        "qa_warnings": []
    }
    
    upsert_result = client.upsert_entities(bundle)
    report["result"]["upsert_entities"] = upsert_result
    report["result"]["qa_warnings_count"] = len(bundle.get("qa_warnings", []))
    
    print(f"✅ Upsert complete:")
    if isinstance(upsert_result, dict):
        for coll, res in upsert_result.items():
            if isinstance(res, dict):
                ins = res.get('inserted', 0)
                upd = res.get('updated', 0)
                print(f"  - {coll}: {ins} inserted, {upd} updated")
            else:
                print(f"  - {coll}: {res}")
    
    # Reconcile stubs if requested
    if args.reconcile:
        reconcile_report = reconcile_stubs(client, docs)
        report["result"]["reconciliation"] = reconcile_report
    
    # Write report
    _write_report(args.output_report, report)
    print(f"\n📄 Report saved: {args.output_report}")
    print("\n✅ Agent G: Glossary Sync complete!")


def _write_report(path: str, report: Dict[str, Any]) -> None:
    """Write report JSON to file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
