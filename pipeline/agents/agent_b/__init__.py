"""
Agent B: Outline Builder
Извлекает stages, tools, indicators, rules из blocks.jsonl
Использует GigaChat (primary) + Qwen3-Max (fallback)
"""

from .agent_b import OutlineBuilder

__all__ = ['OutlineBuilder']
