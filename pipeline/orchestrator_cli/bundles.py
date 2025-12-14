"""
Bundle helper module for Orchestrator CLI.

Provides utilities for:
- Loading bundle definitions from data/bundles/
- Loading source manifests
- Picking methodology_id from source manifest
- Resolving bundles to source paths
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import yaml


def load_source_manifest(source_path: Path) -> Optional[Dict]:
    """
    Load source_manifest.json from source directory.
    
    Returns:
        Manifest dict or None if not found
    """
    manifest_path = source_path / 'source_manifest.json'
    
    if not manifest_path.exists():
        return None
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def pick_methodology_id_from_manifest(
    manifest: Dict,
    min_confidence: float = 0.3
) -> Optional[str]:
    """
    Pick methodology_id from source manifest signals.
    
    Args:
        manifest: Source manifest dict
        min_confidence: Minimum confidence threshold
    
    Returns:
        methodology_id (top candidate) or None if confidence too low
    """
    signals = manifest.get('signals', {})
    candidates = signals.get('candidate_methodology_ids', [])
    confidence = signals.get('confidence', 0.0)
    
    if not candidates:
        return None
    
    if confidence < min_confidence:
        return None
    
    return candidates[0]  # Return top candidate


def load_bundle(bundle_path: Path) -> Dict:
    """
    Load bundle definition from YAML.
    
    Expected format:
        bundle_id: power-of-one
        methodology_id: power-of-one
        sources:
          - book_01_core
          - book_02_cases
          - book_03_templates
    
    Returns:
        Bundle dict with bundle_id, methodology_id, sources
    """
    with open(bundle_path, 'r', encoding='utf-8') as f:
        bundle = yaml.safe_load(f)
    
    if not bundle:
        raise ValueError(f"Empty bundle file: {bundle_path}")
    
    required_fields = ['bundle_id', 'methodology_id', 'sources']
    for field in required_fields:
        if field not in bundle:
            raise ValueError(f"Bundle missing required field '{field}': {bundle_path}")
    
    if not isinstance(bundle['sources'], list) or not bundle['sources']:
        raise ValueError(f"Bundle 'sources' must be non-empty list: {bundle_path}")
    
    return bundle


def bundle_sources(
    bundle_id: str,
    bundles_dir: Path = Path('data/bundles'),
    sources_dir: Path = Path('sources')
) -> tuple[str, List[Path]]:
    """
    Resolve bundle_id to (methodology_id, source_paths).
    
    Args:
        bundle_id: Bundle identifier
        bundles_dir: Directory with bundle YAML files
        sources_dir: Directory with source folders
    
    Returns:
        (methodology_id, [source_path1, source_path2, ...])
    
    Raises:
        FileNotFoundError: If bundle or sources not found
    """
    bundle_path = bundles_dir / f'{bundle_id}.yaml'
    
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")
    
    bundle = load_bundle(bundle_path)
    methodology_id = bundle['methodology_id']
    source_ids = bundle['sources']
    
    # Resolve source paths
    source_paths = []
    for source_id in source_ids:
        source_path = sources_dir / source_id
        if not source_path.exists():
            raise FileNotFoundError(f"Source not found: {source_path}")
        source_paths.append(source_path)
    
    return methodology_id, source_paths


def auto_bundle_sources(
    sources_dir: Path = Path('sources'),
    min_confidence: float = 0.3
) -> Dict[str, List[Path]]:
    """
    Auto-group sources by methodology_id from their manifests.
    
    Args:
        sources_dir: Directory with source folders
        min_confidence: Minimum confidence for auto-detection
    
    Returns:
        {methodology_id: [source_path1, source_path2, ...]}
    """
    bundles = {}
    
    if not sources_dir.exists():
        return bundles
    
    for source_path in sorted(sources_dir.iterdir()):
        if not source_path.is_dir():
            continue
        
        # Load source manifest
        manifest = load_source_manifest(source_path)
        if not manifest:
            continue
        
        # Pick methodology_id
        methodology_id = pick_methodology_id_from_manifest(manifest, min_confidence)
        if not methodology_id:
            continue
        
        # Add to bundles
        if methodology_id not in bundles:
            bundles[methodology_id] = []
        bundles[methodology_id].append(source_path)
    
    return bundles
