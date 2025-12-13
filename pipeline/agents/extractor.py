"""
Extractor Agent - Agent A
Converts documents (PDF, DOCX, PPTX) into structured markdown + metadata

Uses:
- Unstructured.io for universal document processing
- OCR for scanned PDFs
- Table extraction
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Literal
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.constants import START as GRAPH_START
from pydantic import BaseModel, Field

try:
    from unstructured.partition.auto import partition
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    print("⚠️  unstructured not installed. Install: pip install unstructured[all-docs]")


class DocumentMetadata(BaseModel):
    """Metadata extracted from document"""
    file_name: str
    file_size: int
    file_type: str  # pdf, docx, pptx
    pages: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    processed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ExtractorState(BaseModel):
    """State for Extractor Agent"""
    # Input
    file_path: str
    output_dir: str = "sources"
    book_id: Optional[str] = None
    
    # OCR settings
    use_ocr: bool = True
    ocr_languages: str = "rus+eng"
    extract_tables: bool = True
    
    # Processing state
    current_step: str = "init"
    is_scanned_pdf: bool = False
    
    # Output
    raw_text: str = ""
    metadata: Optional[Dict] = None
    tables: List[Dict] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)
    
    # Messages
    messages: List = Field(default_factory=list)
    
    # Status
    success: bool = False
    error: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class ExtractorAgent:
    """
    Agent A: Ingest/Extractor
    
    Converts various document formats into structured markdown with metadata.
    
    Workflow:
    1. detect_type: Determine file type and if OCR needed
    2. extract: Extract text, tables, images
    3. normalize: Convert to clean markdown
    4. save: Write to output directory
    
    Output structure:
    sources/<book_id>/
        ├── raw_text.md       # Clean markdown
        ├── metadata.json     # Document metadata
        ├── tables/           # Extracted tables as CSV
        │   ├── table_001.csv
        │   └── table_002.csv
        └── images/           # Extracted images
            ├── page_001.png
            └── page_002.png
    """
    
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow"""
        workflow = StateGraph(ExtractorState)
        
        # Add nodes
        workflow.add_node("detect_type", self.detect_type_node)
        workflow.add_node("extract", self.extract_node)
        workflow.add_node("normalize", self.normalize_node)
        workflow.add_node("save", self.save_node)
        
        # Add edges
        workflow.add_edge(START, "detect_type")
        workflow.add_edge("detect_type", "extract")
        workflow.add_edge("extract", "normalize")
        workflow.add_edge("normalize", "save")
        workflow.add_edge("save", END)
        
        return workflow.compile()
    
    async def detect_type_node(self, state: ExtractorState, config: RunnableConfig) -> Dict:
        """Detect document type and OCR requirements"""
        file_path = Path(state.file_path)
        
        if not file_path.exists():
            return {
                "current_step": "detect_type",
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        file_type = file_path.suffix.lower().replace(".", "")
        file_size = file_path.stat().st_size
        
        # Generate book_id if not provided
        book_id = state.book_id or file_path.stem.lower().replace(" ", "_").replace("-", "_")
        
        # Check if PDF is scanned (heuristic: low text content)
        is_scanned = False
        if file_type == "pdf":
            try:
                import pymupdf
                doc = pymupdf.open(file_path)
                text_length = sum(len(page.get_text()) for page in doc)
                is_scanned = text_length < 100  # Less than 100 chars = likely scanned
                doc.close()
            except Exception as e:
                print(f"⚠️  Could not check PDF type: {e}")
        
        metadata = {
            "file_name": file_path.name,
            "file_size": file_size,
            "file_type": file_type,
        }
        
        return {
            "current_step": "detect_type",
            "book_id": book_id,
            "is_scanned_pdf": is_scanned,
            "metadata": metadata,
            "messages": [
                AIMessage(content=f"✅ Detected: {file_type.upper()}, {'scanned' if is_scanned else 'text-based'}, size: {file_size / 1024:.1f} KB")
            ]
        }
    
    async def extract_node(self, state: ExtractorState, config: RunnableConfig) -> Dict:
        """Extract content using Unstructured.io"""
        if not UNSTRUCTURED_AVAILABLE:
            return {
                "current_step": "extract",
                "success": False,
                "error": "Unstructured.io not available"
            }
        
        try:
            # Extract with Unstructured
            strategy = "hi_res" if state.use_ocr and state.is_scanned_pdf else "fast"
            
            elements = partition(
                filename=state.file_path,
                strategy=strategy,
                ocr_languages=state.ocr_languages if state.use_ocr else None,
                infer_table_structure=state.extract_tables,
            )
            
            # Separate content types
            text_elements = []
            table_elements = []
            
            for elem in elements:
                elem_type = type(elem).__name__
                if "Table" in elem_type:
                    table_elements.append({
                        "content": str(elem),
                        "metadata": elem.metadata.to_dict() if hasattr(elem, 'metadata') else {}
                    })
                else:
                    text_elements.append(str(elem))
            
            raw_text = "\n\n".join(text_elements)
            
            return {
                "current_step": "extract",
                "raw_text": raw_text,
                "tables": table_elements,
                "messages": state.messages + [
                    AIMessage(content=f"✅ Extracted: {len(text_elements)} text blocks, {len(table_elements)} tables")
                ]
            }
            
        except Exception as e:
            return {
                "current_step": "extract",
                "success": False,
                "error": f"Extraction failed: {str(e)}"
            }
    
    async def normalize_node(self, state: ExtractorState, config: RunnableConfig) -> Dict:
        """Normalize text to clean markdown"""
        text = state.raw_text
        
        # Basic cleaning
        # Remove multiple blank lines
        lines = text.split("\n")
        cleaned_lines = []
        prev_blank = False
        
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            cleaned_lines.append(line)
            prev_blank = is_blank
        
        normalized = "\n".join(cleaned_lines)
        
        return {
            "current_step": "normalize",
            "raw_text": normalized,
            "messages": state.messages + [
                AIMessage(content=f"✅ Normalized: {len(normalized)} chars")
            ]
        }
    
    async def save_node(self, state: ExtractorState, config: RunnableConfig) -> Dict:
        """Save extracted content to output directory"""
        try:
            output_path = Path(state.output_dir) / state.book_id
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Save raw text
            text_file = output_path / "raw_text.md"
            text_file.write_text(state.raw_text, encoding="utf-8")
            
            # Save metadata
            metadata_file = output_path / "metadata.json"
            metadata_file.write_text(
                json.dumps(state.metadata, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            
            # Save tables
            if state.tables:
                tables_dir = output_path / "tables"
                tables_dir.mkdir(exist_ok=True)
                
                for i, table in enumerate(state.tables, 1):
                    table_file = tables_dir / f"table_{i:03d}.txt"
                    table_file.write_text(table["content"], encoding="utf-8")
            
            return {
                "current_step": "save",
                "success": True,
                "messages": state.messages + [
                    AIMessage(content=f"✅ Saved to: {output_path}")
                ]
            }
            
        except Exception as e:
            return {
                "current_step": "save",
                "success": False,
                "error": f"Save failed: {str(e)}"
            }
    
    async def process(self, file_path: str, output_dir: str = "sources", book_id: Optional[str] = None) -> Dict:
        """
        Process a document
        
        Args:
            file_path: Path to document
            output_dir: Output directory (default: sources/)
            book_id: Book identifier (auto-generated if not provided)
        
        Returns:
            Final state dict
        """
        initial_state = ExtractorState(
            file_path=file_path,
            output_dir=output_dir,
            book_id=book_id
        )
        
        result = await self.graph.ainvoke(initial_state)
        return result


# CLI usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <file_path> [output_dir] [book_id]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "sources"
    book_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    agent = ExtractorAgent()
    result = asyncio.run(agent.process(file_path, output_dir, book_id))
    
    if result.get("success"):
        print("\n✅ SUCCESS")
        print(f"Book ID: {result['book_id']}")
        print(f"Output: {output_dir}/{result['book_id']}/")
    else:
        print(f"\n❌ ERROR: {result.get('error')}")
        sys.exit(1)
