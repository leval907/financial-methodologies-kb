"""
Pipeline agents для обработки документов

Структура:
- agent_a/ - Document Extractor (PDF/DOCX → blocks.jsonl)
- agent_b/ - Outline Builder (blocks.jsonl → outline.yaml)
- agent_c/ - Compiler (outline.yaml → markdown docs)
- agent_d/ - QA Reviewer (validation)
- agent_e/ - Graph DB Publisher (ArangoDB)
- agent_f/ - PR Publisher (GitHub)
"""

# Agent A: Document Extractor
from .agent_a import DocumentExtractorV2, QualityMetricsCalculator, BlocksConverter

# Agent B: Outline Builder  
from .agent_b import OutlineBuilder

# Agent C: Compiler (в подпапке agent_c_v2)
# NOTE: Импорты закомментированы, чтобы не ломать agent_e
# from .agent_c_v2.compiler import MethodologyCompiler

# Legacy (для обратной совместимости)
from .extractor import DocumentExtractor

__all__ = [
    # Agent A
    'DocumentExtractorV2',
    'QualityMetricsCalculator',
    'BlocksConverter',
    
    # Agent B
    'OutlineBuilder',
    
    # Agent C
    'MethodologyCompiler',
    
    # Legacy
    'DocumentExtractor',
]
