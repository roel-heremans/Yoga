"""
PDF Processor Module

Extracts text content from PDFs in theme directories for use in content generation.
Can also load preprocessed JSON files for faster access.
"""

import json
import pdfplumber
from pathlib import Path
from typing import List, Dict, Optional
import re


class PDFProcessor:
    """Process PDF files to extract text content."""
    
    def __init__(self, assets_base_path: Optional[Path] = None):
        """
        Initialize PDF processor.
        
        Args:
            assets_base_path: Base path to assets directory. If None, uses default.
        """
        if assets_base_path is None:
            assets_base_path = Path(__file__).parent.parent / 'assets'
        self.assets_base_path = assets_base_path
    
    def find_pdfs(self, theme_name: str) -> List[Path]:
        """
        Find all PDF files in a theme directory.
        
        Args:
            theme_name: Name of the theme directory (e.g., '04_immune_system').
        
        Returns:
            List of PDF file paths.
        """
        # PDFs are in assets/[theme]/pdfs/ subfolder
        theme_path = self.assets_base_path / theme_name / 'pdfs'
        if not theme_path.exists():
            return []
        
        pdf_files = list(theme_path.glob('*.pdf'))
        return pdf_files
    
    def extract_text(self, pdf_path: Path, max_pages: Optional[int] = None) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to PDF file.
            max_pages: Maximum number of pages to extract. If None, extracts all.
        
        Returns:
            Extracted text content.
        """
        text_content = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_to_process = len(pdf.pages)
                if max_pages:
                    pages_to_process = min(pages_to_process, max_pages)
                
                for i in range(pages_to_process):
                    page = pdf.pages[i]
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)
        
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""
        
        return "\n\n".join(text_content)
    
    def extract_key_points(self, text: str, max_points: int = 5) -> List[str]:
        """
        Extract key points from text using simple heuristics.
        
        Args:
            text: Text content to analyze.
            max_points: Maximum number of key points to extract.
        
        Returns:
            List of key points.
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Simple heuristic: prioritize sentences with keywords
        keywords = [
            'kombucha', 'benefit', 'health', 'probiotic', 'antioxidant',
            'research', 'study', 'scientific', 'improve', 'reduce',
            'digest', 'immune', 'gut', 'bacteria'
        ]
        
        scored_sentences = []
        for sentence in sentences:
            score = sum(1 for keyword in keywords if keyword.lower() in sentence.lower())
            if score > 0:
                scored_sentences.append((score, sentence))
        
        # Sort by score and take top sentences
        scored_sentences.sort(reverse=True, key=lambda x: x[0])
        key_points = [sentence for _, sentence in scored_sentences[:max_points]]
        
        # If not enough key points, add more sentences
        if len(key_points) < max_points:
            remaining = [s for s in sentences if s not in key_points]
            key_points.extend(remaining[:max_points - len(key_points)])
        
        return key_points
    
    def process_theme_pdfs(self, theme_name: str, max_pages_per_pdf: Optional[int] = 10) -> Dict[str, str]:
        """
        Process all PDFs in a theme directory.
        
        Args:
            theme_name: Name of the theme directory.
            max_pages_per_pdf: Maximum pages to extract from each PDF.
        
        Returns:
            Dictionary mapping PDF filenames to extracted text.
        """
        pdf_files = self.find_pdfs(theme_name)
        results = {}
        
        for pdf_path in pdf_files:
            print(f"Processing PDF: {pdf_path.name}")
            text = self.extract_text(pdf_path, max_pages=max_pages_per_pdf)
            if text:
                results[pdf_path.name] = text
        
        return results
    
    def get_combined_text(self, theme_name: str, max_pages_per_pdf: Optional[int] = 10) -> str:
        """
        Get combined text from all PDFs in a theme.
        
        Args:
            theme_name: Name of the theme directory.
            max_pages_per_pdf: Maximum pages to extract from each PDF.
        
        Returns:
            Combined text from all PDFs.
        """
        pdf_texts = self.process_theme_pdfs(theme_name, max_pages_per_pdf)
        return "\n\n---\n\n".join(pdf_texts.values())
    
    def get_summary(self, theme_name: str, max_pages_per_pdf: Optional[int] = 10) -> Dict[str, any]:
        """
        Get a summary of PDF content for a theme.
        
        Args:
            theme_name: Name of the theme directory.
            max_pages_per_pdf: Maximum pages to extract from each PDF.
        
        Returns:
            Dictionary with summary information.
        """
        combined_text = self.get_combined_text(theme_name, max_pages_per_pdf)
        key_points = self.extract_key_points(combined_text)
        
        return {
            'full_text': combined_text,
            'key_points': key_points,
            'word_count': len(combined_text.split()),
            'character_count': len(combined_text)
        }
    
    def load_processed_content(self, theme_name: str) -> Optional[Dict]:
        """
        Load preprocessed content from JSON file if it exists.
        
        Args:
            theme_name: Name of the theme directory.
        
        Returns:
            Dictionary with processed content, or None if JSON doesn't exist.
        """
        json_path = self.assets_base_path / theme_name / 'content.json'
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading JSON for {theme_name}: {e}")
                return None
        return None
    
    def get_key_points_from_json(self, theme_name: str, max_points: Optional[int] = None) -> List[str]:
        """
        Get key points from preprocessed JSON file, or extract from PDFs if JSON doesn't exist.
        
        Args:
            theme_name: Name of the theme directory.
            max_points: Optional limit on number of key points to return.
        
        Returns:
            List of key points (already refined and accessible).
        """
        processed_content = self.load_processed_content(theme_name)
        if processed_content and 'summary' in processed_content:
            key_points = processed_content['summary'].get('combined_key_points', [])
            if max_points:
                return key_points[:max_points]
            return key_points
        
        # Fallback to processing PDFs
        combined_text = self.get_combined_text(theme_name)
        return self.extract_key_points(combined_text, max_points=max_points or 5)
    
    def get_random_key_point_from_json(self, theme_name: str) -> Optional[str]:
        """
        Get a random refined key point from JSON for variety in content generation.
        
        Args:
            theme_name: Name of the theme directory.
        
        Returns:
            A random key point string, or None if not available.
        """
        import random
        key_points = self.get_key_points_from_json(theme_name)
        if key_points:
            return random.choice(key_points)
        return None
    
    def get_combined_text_from_json(self, theme_name: str) -> str:
        """
        Get combined text from preprocessed JSON file, or extract from PDFs if JSON doesn't exist.
        
        Note: Since we removed full text from JSON to keep files manageable,
        this method now creates a summary from key points if JSON exists.
        
        Args:
            theme_name: Name of the theme directory.
        
        Returns:
            Combined text from all PDFs or summary from key points.
        """
        processed_content = self.load_processed_content(theme_name)
        if processed_content and 'summary' in processed_content:
            # Since we removed combined_text, create a summary from key points
            key_points = processed_content['summary'].get('combined_key_points', [])
            if key_points:
                # Join key points to create a summary text for caption generation
                return ". ".join(key_points[:5]) + "."
            return ''
        
        # Fallback to processing PDFs
        return self.get_combined_text(theme_name)
    
    def get_combined_text(self, theme_name: str, max_pages_per_pdf: Optional[int] = 10) -> str:
        """
        Get combined text from all PDFs in a theme.
        First tries to load from JSON, then falls back to processing PDFs.
        
        Args:
            theme_name: Name of the theme directory.
            max_pages_per_pdf: Maximum pages to extract from each PDF (only used if JSON doesn't exist).
        
        Returns:
            Combined text from all PDFs.
        """
        # Try to load from JSON first
        processed_content = self.load_processed_content(theme_name)
        if processed_content and 'summary' in processed_content:
            return processed_content['summary'].get('combined_text', '')
        
        # Fallback to processing PDFs
        pdf_texts = self.process_theme_pdfs(theme_name, max_pages_per_pdf)
        return "\n\n---\n\n".join(pdf_texts.values())


def main():
    """Test function."""
    processor = PDFProcessor()
    
    # Test with kombucha_benefits theme (using numbered version)
    theme = '05_kombucha_benefits'
    pdfs = processor.find_pdfs(theme)
    
    if pdfs:
        print(f"Found {len(pdfs)} PDF(s) in {theme}:")
        for pdf in pdfs:
            print(f"  - {pdf.name}")
        
        # Process first PDF
        if pdfs:
            text = processor.extract_text(pdfs[0], max_pages=2)
            print(f"\nExtracted text (first 500 chars):\n{text[:500]}...")
    else:
        print(f"No PDFs found in {theme} theme.")


if __name__ == '__main__':
    main()
