"""
Document Analyzer Module

Analyzes document structure and determines optimal chunking strategy for intelligent quote extraction.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional


class DocumentAnalyzer:
    """Analyze document structure and create intelligent chunks."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize document analyzer.
        
        Args:
            config: Configuration dictionary. If None, uses defaults.
        """
        if config is None:
            from .utils import load_config
            config = load_config()
        
        self.config = config
        extraction_config = config.get('quote_extraction', {})
        self.default_chunk_size = extraction_config.get('chunk_size', 5000)
        self.default_overlap = extraction_config.get('chunk_overlap', 500)
    
    def analyze_structure(self, file_path: Path) -> Dict:
        """
        Analyze document structure (chapters, sections, page breaks).
        
        Args:
            file_path: Path to text file.
        
        Returns:
            Dictionary with structure analysis.
        """
        if not file_path.exists():
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return {}
        
        file_size = len(text)
        chapters = self.detect_chapters_sections(text)
        
        return {
            'file_size': file_size,
            'character_count': file_size,
            'word_count': len(text.split()),
            'chapters_detected': len(chapters),
            'chapters': chapters,
            'has_structure': len(chapters) > 0
        }
    
    def detect_chapters_sections(self, text: str) -> List[Dict]:
        """
        Detect natural chapter/section boundaries.
        
        Args:
            text: Text content to analyze.
        
        Returns:
            List of chapter/section dictionaries with position and title.
        """
        chapters = []
        
        # Pattern 1: Chapter headings (e.g., "Chapter 1", "CHAPTER ONE", "Chapter I")
        chapter_patterns = [
            r'(?i)^\s*chapter\s+(\d+|[ivxlcdm]+|[a-z])\s*[:\-]?\s*(.+?)$',
            r'(?i)^\s*chapter\s+([^\n]+)$',
            r'(?i)^\s*ch\.\s*(\d+)\s*[:\-]?\s*(.+?)$',
        ]
        
        # Pattern 2: Numbered sections (e.g., "1. Introduction", "Section 2")
        section_patterns = [
            r'^\s*(\d+)\.\s+([A-Z][^\n]+)$',
            r'(?i)^\s*section\s+(\d+)\s*[:\-]?\s*(.+?)$',
        ]
        
        # Pattern 3: All caps headings (likely chapter titles)
        caps_pattern = r'^([A-Z][A-Z\s]{10,})$'
        
        lines = text.split('\n')
        current_position = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check for chapter patterns
            for pattern in chapter_patterns:
                match = re.match(pattern, line_stripped)
                if match:
                    chapter_num = match.group(1) if len(match.groups()) > 0 else str(len(chapters) + 1)
                    chapter_title = match.group(2) if len(match.groups()) > 1 else line_stripped
                    chapters.append({
                        'type': 'chapter',
                        'number': chapter_num,
                        'title': chapter_title.strip(),
                        'position': current_position,
                        'line': i
                    })
                    break
            
            # Check for section patterns
            if not chapters or chapters[-1].get('type') != 'section':
                for pattern in section_patterns:
                    match = re.match(pattern, line_stripped)
                    if match:
                        section_num = match.group(1)
                        section_title = match.group(2) if len(match.groups()) > 1 else line_stripped
                        chapters.append({
                            'type': 'section',
                            'number': section_num,
                            'title': section_title.strip(),
                            'position': current_position,
                            'line': i
                        })
                        break
            
            current_position += len(line) + 1  # +1 for newline
        
        return chapters
    
    def determine_chunking_strategy(self, text: str, file_size: int) -> Dict:
        """
        Determine optimal chunk size and overlap based on document characteristics.
        
        Args:
            text: Text content.
            file_size: Size of the file in characters.
        
        Returns:
            Dictionary with chunking strategy.
        """
        # Detect chapters/sections from text directly
        chapters = self.detect_chapters_sections(text)
        chapters_detected = len(chapters)
        
        # If document has clear structure (chapters), use larger chunks
        if chapters_detected > 0:
            # Use chapter boundaries when possible
            chunk_size = max(self.default_chunk_size, file_size // max(chapters_detected, 1))
            chunk_size = min(chunk_size, 10000)  # Cap at 10k chars
            overlap = max(self.default_overlap, chunk_size // 10)  # 10% overlap
        else:
            # No clear structure, use default chunking
            chunk_size = self.default_chunk_size
            overlap = self.default_overlap
        
        return {
            'chunk_size': chunk_size,
            'overlap': overlap,
            'use_semantic_boundaries': chapters_detected > 0,
            'estimated_chunks': max(1, (file_size + overlap - 1) // (chunk_size - overlap))
        }
    
    def split_into_chunks(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        preserve_structure: bool = True
    ) -> List[Dict]:
        """
        Split text into semantic chunks with metadata.
        
        Args:
            text: Text content to split.
            chunk_size: Size of each chunk in characters. If None, uses determined strategy.
            overlap: Overlap between chunks in characters. If None, uses determined strategy.
            preserve_structure: If True, tries to split at chapter/section boundaries.
        
        Returns:
            List of chunk dictionaries with text and metadata.
        """
        if chunk_size is None or overlap is None:
            strategy = self.determine_chunking_strategy(text, len(text))
            chunk_size = strategy['chunk_size']
            overlap = strategy['overlap']
        
        chunks = []
        chapters = self.detect_chapters_sections(text) if preserve_structure else []
        
        # If we have chapters and want to preserve structure, try to align chunks with chapters
        if chapters and preserve_structure:
            chunks = self._split_by_structure(text, chapters, chunk_size, overlap)
        else:
            # Simple sliding window chunking
            chunks = self._split_sliding_window(text, chunk_size, overlap)
        
        # Add metadata to each chunk
        for i, chunk in enumerate(chunks):
            chunk['chunk_id'] = f"chunk_{i+1:03d}"
            chunk['position'] = i + 1
            chunk['start_char'] = chunk.get('start_char', 0)
            chunk['end_char'] = chunk.get('end_char', len(chunk['text']))
        
        return chunks
    
    def _split_by_structure(
        self,
        text: str,
        chapters: List[Dict],
        chunk_size: int,
        overlap: int
    ) -> List[Dict]:
        """Split text respecting chapter/section boundaries."""
        chunks = []
        text_length = len(text)
        
        # Group chapters into chunks
        current_chunk_text = ""
        current_chunk_start = 0
        current_chapters = []
        
        for i, chapter in enumerate(chapters):
            chapter_start = chapter['position']
            chapter_end = chapters[i + 1]['position'] if i + 1 < len(chapters) else text_length
            
            # If adding this chapter would exceed chunk size, save current chunk
            chapter_text = text[chapter_start:chapter_end]
            if len(current_chunk_text) + len(chapter_text) > chunk_size and current_chunk_text:
                chunks.append({
                    'text': current_chunk_text,
                    'start_char': current_chunk_start,
                    'end_char': current_chunk_start + len(current_chunk_text),
                    'chapters': current_chapters.copy(),
                    'context': f"Chapter {current_chapters[0]['number']}" if current_chapters else ""
                })
                
                # Start new chunk with overlap
                overlap_text = current_chunk_text[-overlap:] if len(current_chunk_text) > overlap else current_chunk_text
                current_chunk_text = overlap_text + chapter_text
                current_chunk_start = chapter_start - len(overlap_text)
                current_chapters = [chapter]
            else:
                current_chunk_text += chapter_text
                current_chapters.append(chapter)
        
        # Add final chunk
        if current_chunk_text:
            chunks.append({
                'text': current_chunk_text,
                'start_char': current_chunk_start,
                'end_char': current_chunk_start + len(current_chunk_text),
                'chapters': current_chapters,
                'context': f"Chapter {current_chapters[0]['number']}" if current_chapters else ""
            })
        
        return chunks
    
    def _split_sliding_window(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[Dict]:
        """Split text using sliding window approach."""
        chunks = []
        text_length = len(text)
        step_size = chunk_size - overlap
        
        start = 0
        chunk_num = 1
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk_text = text[start:end]
            
            # Try to end at sentence boundary
            if end < text_length:
                last_period = chunk_text.rfind('.')
                last_exclamation = chunk_text.rfind('!')
                last_question = chunk_text.rfind('?')
                last_sentence = max(last_period, last_exclamation, last_question)
                
                if last_sentence > chunk_size * 0.7:  # If sentence boundary is in last 30%
                    chunk_text = chunk_text[:last_sentence + 1]
                    end = start + len(chunk_text)
            
            chunks.append({
                'text': chunk_text,
                'start_char': start,
                'end_char': end,
                'chapters': [],
                'context': ""
            })
            
            start += step_size
            chunk_num += 1
        
        return chunks


def main():
    """Test function."""
    analyzer = DocumentAnalyzer()
    
    # Test with a sample text
    sample_text = """
    Chapter 1: Introduction to Yoga
    
    Yoga is an ancient practice...
    
    Chapter 2: The Eight Limbs
    
    The eight limbs of yoga are...
    """
    
    chunks = analyzer.split_into_chunks(sample_text, chunk_size=100, overlap=20)
    print(f"Created {len(chunks)} chunks")
    for chunk in chunks:
        print(f"  {chunk['chunk_id']}: {len(chunk['text'])} chars, context: {chunk.get('context', 'None')}")


if __name__ == '__main__':
    main()
