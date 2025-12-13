#!/usr/bin/env python3
"""
Simple PDF to Markdown converter
Uses pymupdf (already installed in venv)
"""

import sys
import pymupdf

def pdf_to_markdown(pdf_path: str, output_path: str):
    """Convert PDF to Markdown"""
    doc = pymupdf.open(pdf_path)
    
    markdown_lines = []
    markdown_lines.append(f"# {pdf_path.split('/')[-1]}\n")
    markdown_lines.append(f"**Страниц:** {len(doc)}\n\n")
    markdown_lines.append("---\n\n")
    
    for page_num, page in enumerate(doc, 1):
        text = page.get_text()
        
        if text.strip():
            markdown_lines.append(f"## Страница {page_num}\n\n")
            markdown_lines.append(text)
            markdown_lines.append("\n\n---\n\n")
    
    doc.close()
    
    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(markdown_lines)
    
    print(f"✅ Converted: {pdf_path}")
    print(f"📄 Output: {output_path}")
    print(f"📊 Pages: {len(doc)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pdf_to_md.py <pdf_file> <output_file>")
        sys.exit(1)
    
    pdf_to_markdown(sys.argv[1], sys.argv[2])
