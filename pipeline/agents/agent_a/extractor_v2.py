"""
Agent A v2: Document Extractor с blocks.jsonl и manifest.json

Обновления:
- Генерация blocks.jsonl вместо raw_text.md
- Подсчет quality metrics
- Создание manifest.json с routing flags
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Import existing extractor (from parent directory)
sys.path.insert(0, str(Path(__file__).parent.parent))
from extractor import DocumentExtractor

# Import new modules (from same directory)
from .blocks_converter import BlocksConverter, load_blocks_jsonl
from .quality_metrics import QualityMetricsCalculator


class DocumentExtractorV2:
    """
    Agent A v2 с поддержкой blocks.jsonl и quality metrics
    """
    
    def __init__(self, output_base_dir: str = "sources"):
        self.extractor = DocumentExtractor(use_markitdown=True)
        self.output_base_dir = Path(output_base_dir)
    
    def process_document(self, filepath: Path, book_id: str) -> dict:
        """
        Полная обработка документа:
        1. Extraction (markitdown/openpyxl)
        2. Conversion → blocks.jsonl
        3. Quality metrics calculation
        4. manifest.json generation
        
        Args:
            filepath: Путь к исходному файлу
            book_id: ID книги (например, 'accounting-basics')
            
        Returns:
            manifest dict
        """
        print(f"📄 Processing: {filepath.name}")
        
        # 1. Extract raw content
        print("  1️⃣ Extracting content...")
        extracted = self.extractor.extract(filepath)
        raw_markdown = extracted['content']
        
        # 2. Setup output directory
        book_dir = self.output_base_dir / book_id
        extracted_dir = book_dir / "extracted"
        raw_dir = book_dir / "raw"
        
        extracted_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        # 3. Save raw files
        print("  2️⃣ Saving raw files...")
        
        # Raw original
        raw_original_path = raw_dir / f"original{filepath.suffix}"
        if not raw_original_path.exists():
            import shutil
            shutil.copy(filepath, raw_original_path)
        
        # Raw markdown
        raw_md_path = extracted_dir / "full_text.md"
        raw_md_path.write_text(raw_markdown, encoding='utf-8')
        
        # Tables (if Excel)
        if 'tables' in extracted and extracted['tables']:
            tables_dir = extracted_dir / "tables"
            tables_dir.mkdir(exist_ok=True)
            
            for i, table_dict in enumerate(extracted['tables']):
                # Конвертируем dict обратно в DataFrame для сохранения
                import pandas as pd
                df = pd.DataFrame(table_dict['data'])
                table_path = tables_dir / f"table_{i+1:02d}_{table_dict['sheet']}.csv"
                df.to_csv(table_path, index=False, encoding='utf-8')
        
        # Formulas (if Excel)
        if 'formulas' in extracted and extracted['formulas']:
            formulas_path = extracted_dir / "formulas.json"
            formulas_path.write_text(
                json.dumps(extracted['formulas'], ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        
        # 4. Convert to blocks.jsonl
        print("  3️⃣ Converting to blocks.jsonl...")
        converter = BlocksConverter(source_file=filepath.name)
        blocks = converter.convert(raw_markdown)
        
        blocks_path = extracted_dir / "blocks.jsonl"
        converter.save_jsonl(str(blocks_path))
        
        print(f"     ✅ Generated {len(blocks)} blocks")
        
        # 5. Calculate quality metrics
        print("  4️⃣ Calculating quality metrics...")
        metrics = QualityMetricsCalculator.calculate(blocks, raw_markdown)
        
        print(f"     📊 Score: {metrics['score']}/100")
        print(f"     - Text density: {metrics['text_density']:.2%}")
        print(f"     - Garbage ratio: {metrics['garbage_ratio']:.2%}")
        print(f"     - Repeated lines: {metrics['repeated_lines_ratio']:.2%}")
        print(f"     - Table coverage: {metrics['table_extract_coverage']:.2%}")
        
        # 6. Count block types
        block_stats = {}
        for block in blocks:
            btype = block['type']
            block_stats[btype] = block_stats.get(btype, 0) + 1
        
        # 7. Generate manifest.json
        print("  5️⃣ Generating manifest.json...")
        manifest = {
            'book_id': book_id,
            'extraction_date': datetime.now().isoformat(),
            'agent': 'Agent A v2.0',
            'source': {
                'filename': filepath.name,
                'format': filepath.suffix.upper().replace('.', ''),
                'size_bytes': filepath.stat().st_size,
                'path': str(filepath.absolute())
            },
            'quality': {
                'score': metrics['score'],
                'text_density': metrics['text_density'],
                'garbage_ratio': metrics['garbage_ratio'],
                'repeated_lines_ratio': metrics['repeated_lines_ratio'],
                'table_extract_coverage': metrics['table_extract_coverage']
            },
            'routing': metrics['routing'],
            'warnings': metrics['warnings'],
            'statistics': {
                'total_blocks': len(blocks),
                'blocks_by_type': block_stats
            },
            'output_files': {
                'blocks': str(blocks_path.relative_to(self.output_base_dir)),
                'full_text': str(raw_md_path.relative_to(self.output_base_dir)),
                'raw_original': str(raw_original_path.relative_to(self.output_base_dir))
            }
        }
        
        manifest_path = book_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        # 8. Display routing decision
        routing = metrics['routing']
        if routing['ok_for_outline']:
            print(f"     ✅ ROUTING: ok_for_outline (score >= 80)")
        elif routing['ok_with_warnings']:
            print(f"     ⚠️  ROUTING: ok_with_warnings (60 <= score < 80)")
        else:
            print(f"     ❌ ROUTING: needs_repair (score < 60)")
        
        if metrics['warnings']:
            print(f"     ⚠️  Warnings:")
            for warning in metrics['warnings']:
                print(f"        {warning}")
        
        print(f"✅ Done: {book_id}")
        print(f"   Output: {book_dir}")
        print()
        
        return manifest


def main():
    """CLI interface"""
    if len(sys.argv) < 3:
        print("Usage: python extractor_v2.py <input_file> <book_id>")
        print()
        print("Example:")
        print("  python extractor_v2.py cache/books/accounting-basics.pdf accounting-basics")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    book_id = sys.argv[2]
    
    if not input_file.exists():
        print(f"❌ File not found: {input_file}")
        sys.exit(1)
    
    extractor = DocumentExtractorV2(output_base_dir="sources")
    manifest = extractor.process_document(input_file, book_id)
    
    # Summary
    print("=" * 60)
    print("📊 EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Book ID: {manifest['book_id']}")
    print(f"Source: {manifest['source']['filename']}")
    print(f"Quality Score: {manifest['quality']['score']}/100")
    print(f"Total Blocks: {manifest['statistics']['total_blocks']}")
    print(f"Routing: {manifest['routing']}")
    print()
    
    if manifest['quality']['score'] < 60:
        print("⚠️  WARNING: Low quality score - consider repair mode")
    elif manifest['quality']['score'] < 80:
        print("⚠️  NOTE: Moderate quality - Agent B should be cautious")
    else:
        print("✅ HIGH QUALITY: Ready for Agent B")


if __name__ == '__main__':
    main()
