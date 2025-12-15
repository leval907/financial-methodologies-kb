"""
Agent H: Semantic Linker
Создает семантические связи между stages, indicators, tools и rules
используя LLM для анализа релевантности.
"""

from .semantic_linker import SemanticLinker

__all__ = ['SemanticLinker']
