"""
Agent A extension: Source Manifest Builder

Analyzes a source (book/document) and suggests which methodology it belongs to.
Uses deterministic keyword matching from data/methodology_aliases.yaml.

Usage:
    python -m pipeline.agents.agent_a.source_manifest --source-path sources/book_01
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

import yaml


def read_jsonl(path: Path, max_blocks: int = 60) -> List[Dict]:
    """Read first N blocks from blocks.jsonl"""
    blocks = []
    if not path.exists():
        return blocks
    
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= max_blocks:
                break
            try:
                blocks.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return blocks


def extract_text(blocks: List[Dict]) -> str:
    """Concatenate text from blocks"""
    texts = []
    for block in blocks:
        if 'text' in block and block['text']:
            texts.append(block['text'])
    return '\n'.join(texts)


def normalize_text(text: str) -> str:
    """Lowercase and normalize for matching"""
    return text.lower().strip()


def load_aliases(aliases_path: Path) -> Dict[str, List[str]]:
    """Load methodology keyword aliases from YAML"""
    if not aliases_path.exists():
        return {}
    
    with open(aliases_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return data or {}


def score_methodologies(
    text: str, 
    aliases: Dict[str, List[str]]
) -> Tuple[List[str], float, List[str]]:
    """
    Score methodologies by keyword matching.
    
    Returns:
        (candidate_ids, confidence, found_keywords)
    """
    text_norm = normalize_text(text)
    
    # Score each methodology
    scores = {}
    found_keywords = {}
    
    for methodology_id, keywords in aliases.items():
        score = 0
        found = []
        
        for keyword in keywords:
            keyword_norm = normalize_text(keyword)
            if keyword_norm in text_norm:
                score += 3  # +3 points per match
                found.append(keyword)
        
        if score > 0:
            scores[methodology_id] = score
            found_keywords[methodology_id] = found
    
    if not scores:
        return [], 0.0, []
    
    # Sort by score desc
    sorted_methodologies = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_methodology, top_score = sorted_methodologies[0]
    
    # Calculate confidence: min(0.95, score / 12.0)
    # 12.0 = 4 strong matches assumed for high confidence
    confidence = min(0.95, top_score / 12.0)
    
    # Return top candidates (with score >= 50% of top score)
    threshold = top_score * 0.5
    candidates = [
        mid for mid, score in sorted_methodologies 
        if score >= threshold
    ]
    
    # Get all found keywords from top candidates
    all_found = []
    for mid in candidates:
        all_found.extend(found_keywords[mid])
    
    return candidates, confidence, all_found


def detect_doc_type(blocks: List[Dict], text: str) -> str:
    """
    Detect document type: template|case|slides|chapter|book
    
    Heuristics:
    - template: many tables, forms, worksheets
    - case: "case study", "example", "практический пример"
    - slides: short blocks, many headings
    - chapter: single long document
    - book: default
    """
    text_norm = normalize_text(text)
    
    # Check for template indicators
    template_markers = ['template', 'шаблон', 'форма', 'worksheet', 'таблица']
    if any(marker in text_norm for marker in template_markers):
        return 'template'
    
    # Check for case study indicators
    case_markers = ['case study', 'кейс', 'практический пример', 'example']
    if any(marker in text_norm for marker in case_markers):
        return 'case'
    
    # Check for slides (many short blocks, many headings)
    if len(blocks) > 20:
        avg_length = sum(len(b.get('text', '')) for b in blocks) / len(blocks)
        if avg_length < 200:  # Average block < 200 chars
            return 'slides'
    
    # Check for chapter
    chapter_markers = ['chapter', 'глава', 'раздел']
    if any(marker in text_norm for marker in chapter_markers):
        return 'chapter'
    
    return 'book'


def compute_fingerprint(blocks: List[Dict]) -> str:
    """Compute SHA256 hash of first 60 blocks for change detection"""
    content = json.dumps([b.get('text', '') for b in blocks], sort_keys=True)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def build_source_manifest(
    source_path: Path,
    aliases_path: Path,
    max_blocks: int = 60
) -> Dict:
    """
    Build source manifest for a given source.
    
    Returns:
        {
            "source_id": "book_01",
            "source_path": "sources/book_01",
            "signals": {
                "candidate_methodology_ids": ["power-of-one"],
                "confidence": 0.85,
                "keywords": ["power of one", "7 рычагов", ...],
                "doc_type": "book"
            },
            "fingerprint": "abc123...",
            "created_at": "2025-12-14T10:30:00Z"
        }
    """
    source_id = source_path.name
    blocks_path = source_path / 'extracted' / 'blocks.jsonl'
    
    # Read blocks
    blocks = read_jsonl(blocks_path, max_blocks=max_blocks)
    
    if not blocks:
        return {
            'source_id': source_id,
            'source_path': str(source_path),
            'signals': {
                'candidate_methodology_ids': [],
                'confidence': 0.0,
                'keywords': [],
                'doc_type': 'unknown'
            },
            'fingerprint': '',
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }
    
    # Extract text
    text = extract_text(blocks)
    
    # Load aliases
    aliases = load_aliases(aliases_path)
    
    # Score methodologies
    candidates, confidence, keywords = score_methodologies(text, aliases)
    
    # Detect doc type
    doc_type = detect_doc_type(blocks, text)
    
    # Compute fingerprint
    fingerprint = compute_fingerprint(blocks)
    
    return {
        'source_id': source_id,
        'source_path': str(source_path),
        'signals': {
            'candidate_methodology_ids': candidates,
            'confidence': round(confidence, 3),
            'keywords': keywords[:15],  # Top 15 keywords
            'doc_type': doc_type
        },
        'fingerprint': fingerprint,
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }


def write_source_manifest(manifest: Dict, source_path: Path) -> Path:
    """Write source_manifest.json to source directory"""
    output_path = source_path / 'source_manifest.json'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    return output_path


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Build source manifest for a source'
    )
    parser.add_argument(
        '--source-path',
        type=Path,
        required=True,
        help='Path to source directory (e.g., sources/book_01)'
    )
    parser.add_argument(
        '--aliases-path',
        type=Path,
        default=Path('data/methodology_aliases.yaml'),
        help='Path to methodology aliases YAML (default: data/methodology_aliases.yaml)'
    )
    parser.add_argument(
        '--max-blocks',
        type=int,
        default=60,
        help='Max blocks to read from blocks.jsonl (default: 60)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output path for manifest (default: {source_path}/source_manifest.json)'
    )
    
    args = parser.parse_args()
    
    # Build manifest
    manifest = build_source_manifest(
        source_path=args.source_path,
        aliases_path=args.aliases_path,
        max_blocks=args.max_blocks
    )
    
    # Write manifest
    output_path = args.output or (args.source_path / 'source_manifest.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Source manifest created: {output_path}")
    print(f"   Source ID: {manifest['source_id']}")
    print(f"   Candidates: {', '.join(manifest['signals']['candidate_methodology_ids']) or 'none'}")
    print(f"   Confidence: {manifest['signals']['confidence']:.2%}")
    print(f"   Doc type: {manifest['signals']['doc_type']}")


if __name__ == '__main__':
    main()
