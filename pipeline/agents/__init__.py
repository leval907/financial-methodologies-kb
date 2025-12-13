"""
AI Agents for Financial Methodologies Knowledge Base

Agents:
- ExtractorAgent: PDF/DOCX/PPTX → structured text + metadata
- OutlineAgent: Text → methodology outline
- CompilerAgent: Outline → MD/YAML files
- QAAgent: Validation and quality checks
- PRAgent: GitHub PR creation
"""

from .extractor import ExtractorAgent

__all__ = ["ExtractorAgent"]
