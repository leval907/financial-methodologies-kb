#!/usr/bin/env python3
"""
Batch processor для Agent A
Обрабатывает все книги из S3 и кеша
"""

import sys
from pathlib import Path
from typing import List, Dict
import json

from pipeline.agents.extractor import process_document


def process_cached_books(cache_dir: Path = Path('cache/books')) -> List[Dict]:
    """Обработать все книги из cache/books/"""
    
    if not cache_dir.exists():
        print(f"❌ Cache directory not found: {cache_dir}")
        return []
    
    # Получить все файлы
    files = list(cache_dir.glob('*'))
    books = [f for f in files if f.is_file() and not f.name.startswith('.')]
    
    print(f"📚 Found {len(books)} books in cache\n")
    
    results = []
    
    for i, book_path in enumerate(books, 1):
        # Генерируем book_id из имени файла
        book_id = book_path.stem.lower().replace(' ', '-').replace('+', '-')
        # Очищаем от спецсимволов
        book_id = ''.join(c for c in book_id if c.isalnum() or c == '-')
        
        output_dir = Path('sources') / book_id
        
        print(f"\n{'='*70}")
        print(f"[{i}/{len(books)}] Processing: {book_path.name}")
        print(f"Book ID: {book_id}")
        print(f"Output: {output_dir}")
        print(f"{'='*70}\n")
        
        try:
            result = process_document(
                input_path=book_path,
                output_dir=output_dir,
                book_id=book_id,
                use_markitdown=True
            )
            
            # Читаем метаданные для отчета
            metadata_file = output_dir / 'metadata.json'
            metadata = json.loads(metadata_file.read_text())
            
            results.append({
                'book_id': book_id,
                'filename': book_path.name,
                'status': 'success',
                'method': metadata.get('method', 'unknown'),
                'lines': metadata.get('lines', 0),
                'format': book_path.suffix,
                'text_file': result['text_file'],
            })
            
            print(f"\n✅ SUCCESS:")
            print(f"   Method: {metadata.get('method')}")
            print(f"   Lines: {metadata.get('lines')}")
            print(f"   Quality: {metadata.get('quality', 'N/A')}")
            if result['tables_count']:
                print(f"   Tables: {result['tables_count']}")
            if result['formulas_count']:
                print(f"   Formulas: {result['formulas_count']}")
            
        except Exception as e:
            print(f"\n❌ FAILED: {e}")
            results.append({
                'book_id': book_id,
                'filename': book_path.name,
                'status': 'failed',
                'error': str(e),
                'format': book_path.suffix,
            })
    
    return results


def print_summary(results: List[Dict]):
    """Напечатать итоговый отчет"""
    
    print("\n" + "="*70)
    print("📊 PROCESSING SUMMARY")
    print("="*70 + "\n")
    
    success = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'failed']
    
    print(f"Total: {len(results)}")
    print(f"✅ Success: {len(success)}")
    print(f"❌ Failed: {len(failed)}\n")
    
    if success:
        print("✅ Successfully processed:\n")
        for r in success:
            print(f"  - {r['book_id']:40} | {r['method']:15} | {r['lines']:6} lines | {r['format']}")
    
    if failed:
        print("\n❌ Failed to process:\n")
        for r in failed:
            print(f"  - {r['book_id']:40} | {r['format']:6} | Error: {r['error'][:50]}")
    
    # Группировка по методам
    if success:
        methods = {}
        for r in success:
            method = r['method']
            methods[method] = methods.get(method, 0) + 1
        
        print("\n📈 Methods used:\n")
        for method, count in sorted(methods.items()):
            print(f"  - {method:20}: {count} files")
    
    # Группировка по форматам
    formats = {}
    for r in results:
        fmt = r['format']
        status = r['status']
        if fmt not in formats:
            formats[fmt] = {'success': 0, 'failed': 0}
        formats[fmt][status] += 1
    
    print("\n📁 Formats:\n")
    for fmt, counts in sorted(formats.items()):
        total = counts['success'] + counts['failed']
        success_rate = (counts['success'] / total * 100) if total else 0
        print(f"  - {fmt:10}: {counts['success']}/{total} ({success_rate:.0f}% success)")


def main():
    """Главная функция"""
    
    print("🚀 Agent A: Batch Document Extractor")
    print("="*70 + "\n")
    
    # Обработать все книги
    results = process_cached_books()
    
    # Напечатать отчет
    print_summary(results)
    
    # Сохранить отчет
    report_file = Path('sources/extraction_report.json')
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\n💾 Report saved to: {report_file}")
    
    # Exit code
    failed_count = len([r for r in results if r['status'] == 'failed'])
    sys.exit(1 if failed_count > 0 else 0)


if __name__ == '__main__':
    main()
