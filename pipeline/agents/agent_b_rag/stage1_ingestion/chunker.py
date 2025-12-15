"""
Text chunking for RAG system
"""
from typing import List, Dict
from pathlib import Path
import re

class SemanticChunker:
    """
    Chunker that preserves semantic structure
    """
    
    def __init__(self, chunk_size: int = 400, overlap: int = 50):
        """
        Args:
            chunk_size: Target size in tokens (~words)
            overlap: Overlap between chunks in tokens
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, book_id: str) -> List[Dict]:
        """
        Chunk text into overlapping segments with metadata
        
        Args:
            text: Full text to chunk
            book_id: Identifier for the book
        
        Returns:
            List of chunk dictionaries with metadata
        """
        # Split into paragraphs first
        paragraphs = self._split_paragraphs(text)
        
        # Extract page numbers from OCR markers
        page_map = self._extract_page_numbers(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_id = 0
        char_position = 0
        
        for para in paragraphs:
            para_length = len(para.split())
            
            # If paragraph alone exceeds chunk_size, split it
            if para_length > self.chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk, chunk_id, book_id, 
                        char_position, page_map
                    ))
                    chunk_id += 1
                    current_chunk = []
                    current_length = 0
                
                # Split large paragraph
                sentences = self._split_sentences(para)
                for sentence in sentences:
                    sent_length = len(sentence.split())
                    current_chunk.append(sentence)
                    current_length += sent_length
                    
                    if current_length >= self.chunk_size:
                        chunks.append(self._create_chunk(
                            current_chunk, chunk_id, book_id,
                            char_position, page_map
                        ))
                        chunk_id += 1
                        
                        # Keep overlap
                        overlap_text = ' '.join(current_chunk[-3:])  # Last 3 sentences
                        current_chunk = [overlap_text] if overlap_text else []
                        current_length = len(overlap_text.split())
                
            # Normal paragraph
            elif current_length + para_length > self.chunk_size:
                # Save current chunk
                chunks.append(self._create_chunk(
                    current_chunk, chunk_id, book_id,
                    char_position, page_map
                ))
                chunk_id += 1
                
                # Start new chunk with overlap
                overlap_text = ' '.join(current_chunk[-2:])  # Last 2 paragraphs
                current_chunk = [overlap_text, para] if overlap_text else [para]
                current_length = len(overlap_text.split()) + para_length
            else:
                current_chunk.append(para)
                current_length += para_length
            
            char_position += len(para)
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk, chunk_id, book_id,
                char_position, page_map
            ))
        
        return chunks
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Remove OCR page markers
        text = re.sub(r'=== Страница \d+ ===\n', '', text)
        
        # Split on double newlines or single newline followed by capital letter
        paragraphs = re.split(r'\n\n+|\n(?=[A-ZА-Я])', text)
        
        return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_page_numbers(self, text: str) -> Dict[int, int]:
        """
        Extract mapping of character position to page number
        
        Returns:
            Dict[char_position, page_number]
        """
        page_map = {}
        current_page = 1
        char_pos = 0
        
        for line in text.split('\n'):
            if '=== Страница' in line:
                try:
                    page_num = int(re.search(r'Страница (\d+)', line).group(1))
                    current_page = page_num
                except:
                    pass
            page_map[char_pos] = current_page
            char_pos += len(line) + 1
        
        return page_map
    
    def _create_chunk(
        self, 
        paragraphs: List[str], 
        chunk_id: int, 
        book_id: str,
        char_position: int,
        page_map: Dict[int, int]
    ) -> Dict:
        """Create chunk dictionary with metadata"""
        text = '\n\n'.join(paragraphs)
        
        # Find page number for this chunk
        page = page_map.get(char_position, 1)
        
        return {
            'id': f'{book_id}_chunk_{chunk_id:04d}',
            'book_id': book_id,
            'chunk_id': chunk_id,
            'text': text,
            'page': page,
            'char_length': len(text),
            'word_count': len(text.split()),
        }
