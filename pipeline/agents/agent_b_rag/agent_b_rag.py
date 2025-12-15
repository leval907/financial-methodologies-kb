#!/usr/bin/env python3
"""
RAG-based Agent B - Main Orchestrator
Extracts methodology from books using Qdrant + LLM + ArangoDB pipeline
"""
import sys
from pathlib import Path
import yaml
import json
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from pipeline.agents.agent_b_rag.config import Config
from pipeline.agents.agent_b_rag.stage1_ingestion.chunker import SemanticChunker
from pipeline.agents.agent_b_rag.stage1_ingestion.embedder import EmbeddingGenerator
from pipeline.agents.agent_b_rag.stage1_ingestion.qdrant_client import QdrantManager
from pipeline.agents.agent_b_rag.stage2_extraction.rag_searcher import RAGSearcher
from pipeline.agents.agent_b_rag.stage2_extraction.llm_extractor import LLMExtractor


class AgentBRAG:
    """
    RAG-based methodology extraction agent
    """
    
    def __init__(self):
        """Initialize agent with configuration"""
        self.config = Config
        
        # Stage 1 components
        self.chunker = SemanticChunker(
            chunk_size=self.config.CHUNK_SIZE,
            overlap=self.config.CHUNK_OVERLAP
        )
        self.embedder = EmbeddingGenerator(
            api_key=self.config.REQUESTY_API_KEY,
            model=self.config.EMBEDDING_MODEL
        )
        self.qdrant = QdrantManager(
            host=self.config.QDRANT_HOST,
            port=self.config.QDRANT_PORT,
            api_key=self.config.QDRANT_API_KEY
        )
        
        # Stage 2 components (initialized after collection is ready)
        self.searcher = None
        self.extractor = LLMExtractor(
            api_key=self.config.REQUESTY_API_KEY,
            model=self.config.LLM_MODEL,
            temperature=self.config.LLM_TEMPERATURE
        )
    
    def stage1_ingest(self, book_path: Path, book_id: str, collection_name: str):
        """
        Stage 1: Chunk text, generate embeddings, upload to Qdrant
        
        Args:
            book_path: Path to OCR text file
            book_id: Book identifier
            collection_name: Qdrant collection name
        """
        print(f"\n=== STAGE 1: INGESTION ===")
        print(f"Book: {book_id}")
        print(f"Collection: {collection_name}")
        
        # Load text
        print("\n[1/4] Loading text...")
        with open(book_path, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"Loaded {len(text)} characters")
        
        # Chunk text
        print("\n[2/4] Chunking text...")
        chunks = self.chunker.chunk_text(text, book_id)
        print(f"Created {len(chunks)} chunks")
        
        # Generate embeddings
        print("\n[3/4] Generating embeddings...")
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embedder.embed_batch(texts, batch_size=100)
        print(f"Generated {len(embeddings)} embeddings")
        
        # Create collection and upload
        print("\n[4/4] Uploading to Qdrant...")
        self.qdrant.create_collection(
            collection_name=collection_name,
            vector_size=self.config.EMBEDDING_DIMENSIONS,
            recreate=True
        )
        self.qdrant.upsert_chunks(
            collection_name=collection_name,
            chunks=chunks,
            embeddings=embeddings,
            batch_size=100
        )
        
        # Show stats
        info = self.qdrant.get_collection_info(collection_name)
        print(f"\nCollection stats: {info}")
        print("\n✅ Stage 1 complete!")
        
        return len(chunks)
    
    def stage2_extract(self, collection_name: str, book_id: str) -> Dict[str, List]:
        """
        Stage 2: RAG-based extraction of methodology components
        
        Args:
            collection_name: Qdrant collection to search
            book_id: Book identifier
        
        Returns:
            Dict with extracted stages, tools, indicators, rules
        """
        print(f"\n=== STAGE 2: EXTRACTION ===")
        
        # Initialize searcher
        self.searcher = RAGSearcher(
            qdrant_manager=self.qdrant,
            embedding_generator=self.embedder,
            collection_name=collection_name
        )
        
        results = {}
        
        for category in self.config.CATEGORIES:
            print(f"\n--- Extracting: {category} ---")
            
            # Load prompt template
            prompt_path = self.config.PROMPTS_DIR / f'extract_{category}.txt'
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Search relevant chunks
            print(f"[1/2] Searching relevant chunks...")
            chunks = self.searcher.search_by_category(
                category=category,
                top_k=self.config.TOP_K_CHUNKS,
                min_similarity=self.config.MIN_SIMILARITY
            )
            print(f"Found {len(chunks)} relevant chunks")
            
            # Extract with LLM
            print(f"[2/2] Extracting with LLM...")
            entities = self.extractor.extract_from_chunks(
                chunks=chunks,
                category=category,
                prompt_template=prompt_template
            )
            print(f"Extracted {len(entities)} {category}")
            
            results[category] = entities
        
        print("\n✅ Stage 2 complete!")
        print(f"Total extracted:")
        for cat, items in results.items():
            print(f"  - {cat}: {len(items)}")
        
        return results
    
    def save_results(self, results: Dict, output_path: Path):
        """
        Save extraction results to YAML file
        
        Args:
            results: Extraction results
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(results, f, allow_unicode=True, sort_keys=False, indent=2)
        
        print(f"\n💾 Results saved to: {output_path}")


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RAG-based methodology extraction')
    parser.add_argument('--book', required=True, help='Path to book OCR text file')
    parser.add_argument('--book-id', required=True, help='Book identifier')
    parser.add_argument('--collection', required=True, help='Qdrant collection name')
    parser.add_argument('--output', required=True, help='Output YAML file path')
    parser.add_argument('--skip-ingestion', action='store_true', help='Skip stage 1 (use existing collection)')
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = AgentBRAG()
    
    # Stage 1: Ingestion
    if not args.skip_ingestion:
        book_path = Path(args.book)
        if not book_path.exists():
            print(f"❌ Error: Book file not found: {book_path}")
            sys.exit(1)
        
        agent.stage1_ingest(
            book_path=book_path,
            book_id=args.book_id,
            collection_name=args.collection
        )
    else:
        print("\n⏭️  Skipping Stage 1 (using existing collection)")
    
    # Stage 2: Extraction
    results = agent.stage2_extract(
        collection_name=args.collection,
        book_id=args.book_id
    )
    
    # Save results
    output_path = Path(args.output)
    agent.save_results(results, output_path)
    
    print("\n" + "="*60)
    print("🎉 RAG EXTRACTION COMPLETE!")
    print("="*60)


if __name__ == '__main__':
    main()
