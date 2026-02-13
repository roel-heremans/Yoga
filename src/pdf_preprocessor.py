"""
PDF Preprocessor Module

One-time preprocessing of PDFs to extract structured information and save to JSON files.
This allows manual editing and faster content generation.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from .pdf_processor import PDFProcessor
from .ai_caption_generator import AICaptionGenerator


class PDFPreprocessor:
    """Preprocess PDFs and save structured data to JSON files."""
    
    def __init__(self, assets_base_path: Optional[Path] = None, config: Optional[Dict] = None):
        """
        Initialize PDF preprocessor.
        
        Args:
            assets_base_path: Base path to assets directory. If None, uses default.
            config: Configuration dictionary. If None, loads from file.
        """
        if assets_base_path is None:
            assets_base_path = Path(__file__).parent.parent / 'assets'
        self.assets_base_path = assets_base_path
        self.pdf_processor = PDFProcessor(assets_base_path)
        self.ai_generator = AICaptionGenerator(config)
    
    def preprocess_theme(
        self,
        theme_name: str,
        max_pages_per_pdf: int = 10,
        max_key_points_per_pdf: int = 10,
        force: bool = False
    ) -> Dict:
        """
        Preprocess all PDFs in a theme and save to JSON.
        
        Args:
            theme_name: Name of the theme directory (e.g., '05_kombucha_benefits').
            max_pages_per_pdf: Maximum pages to extract from each PDF.
            max_key_points_per_pdf: Maximum key points to extract per PDF.
            force: If True, reprocess even if JSON already exists.
        
        Returns:
            Dictionary with preprocessing results.
        """
        # Validate theme name - must start with number (04-07)
        if not theme_name.startswith(('04_', '05_', '06_', '07_')):
            raise ValueError(
                f"Invalid theme name: {theme_name}. "
                f"Theme names must start with 04_, 05_, 06_, or 07_ "
                f"(e.g., '07_kombucha_research', not 'kombucha_research')"
            )
        
        theme_path = self.assets_base_path / theme_name
        json_path = theme_path / 'content.json'
        
        # Check if JSON already exists
        if json_path.exists() and not force:
            print(f"JSON file already exists for {theme_name}. Use --force to reprocess.")
            return self._load_json(json_path)
        
        # Find PDFs
        pdf_files = self.pdf_processor.find_pdfs(theme_name)
        if not pdf_files:
            print(f"No PDFs found in {theme_name}")
            return {}
        
        print(f"Processing {len(pdf_files)} PDF(s) for theme: {theme_name}")
        
        # Process each PDF
        pdf_data = []
        all_key_points = []
        combined_text_parts = []
        total_word_count = 0
        total_char_count = 0
        
        for pdf_path in pdf_files:
            print(f"  Processing: {pdf_path.name}")
            
            # Extract text
            text = self.pdf_processor.extract_text(pdf_path, max_pages=max_pages_per_pdf)
            if not text:
                print(f"    Warning: No text extracted from {pdf_path.name}")
                continue
            
            # Extract key points from this PDF (raw extraction)
            raw_key_points = self.pdf_processor.extract_key_points(text, max_points=max_key_points_per_pdf)
            
            # Refine key points using LLM to make them more accessible
            print(f"    Refining key points with LLM...")
            refined_key_points = self.refine_key_points_with_llm(
                raw_key_points,
                theme_name,
                max_points=max_key_points_per_pdf
            )
            
            # Calculate statistics
            word_count = len(text.split())
            char_count = len(text)
            
            # Store per-PDF data (use refined key points, but don't store full text)
            pdf_data.append({
                'filename': pdf_path.name,
                'key_points': refined_key_points,
                'word_count': word_count,
                'character_count': char_count,
                'pages_processed': max_pages_per_pdf
            })
            
            # Aggregate for summary (use refined key points)
            all_key_points.extend(refined_key_points)
            combined_text_parts.append(text)
            total_word_count += word_count
            total_char_count += char_count
        
        # Create aggregated summary
        # Combine all text with separators
        combined_text = "\n\n---\n\n".join(combined_text_parts)
        
        # Extract overall key points from combined text (raw extraction)
        raw_summary_key_points = self.pdf_processor.extract_key_points(
            combined_text,
            max_points=max_key_points_per_pdf * len(pdf_files)
        )
        
        # Refine summary key points using LLM
        print(f"Refining summary key points with LLM...")
        summary_key_points = self.refine_key_points_with_llm(
            raw_summary_key_points,
            theme_name,
            max_points=max_key_points_per_pdf * len(pdf_files)
        )
        
        # Create final structure
        # Note: We don't store the full combined_text in summary to keep JSON files manageable
        result = {
            'theme': theme_name,
            'processed_at': datetime.now().isoformat(),
            'pdfs': pdf_data,
            'summary': {
                'combined_key_points': summary_key_points,
                'total_word_count': total_word_count,
                'total_character_count': total_char_count,
                'total_pdfs': len(pdf_data)
            }
        }
        
        # Save to JSON
        # Note: If creating README files in assets subfolders, use _README.md (not README.md)
        # so they appear at the top when listing directories
        theme_path.mkdir(parents=True, exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved processed content to {json_path}")
        print(f"  Processed {len(pdf_data)} PDF(s)")
        print(f"  Total key points: {len(summary_key_points)}")
        print(f"  Total words: {total_word_count}")
        
        return result
    
    def refine_key_points_with_llm(
        self,
        raw_key_points: List[str],
        theme_name: str,
        max_points: int = 10
    ) -> List[str]:
        """
        Refine key points using LLM to make them more accessible and human-friendly.
        
        Args:
            raw_key_points: List of raw extracted key points from PDFs.
            theme_name: Name of the theme (for context).
            max_points: Maximum number of refined points to return.
        
        Returns:
            List of refined, accessible key points.
        """
        if not self.ai_generator.client:
            print("Warning: OpenAI client not available. Using raw key points without LLM refinement.")
            return raw_key_points[:max_points]
        
        # Combine key points into a single text block (limit input size)
        combined_raw = "\n".join([f"- {point}" for point in raw_key_points[:20]])
        
        prompt = f"""You are an expert at translating scientific research into clear, engaging, and accessible information for the general public.

Your task is to extract and refine key takeaways about kombucha from the following research content. The audience is regular people (not scientists) who want to learn about kombucha in simple, understandable terms.

Theme: {theme_name}

Raw Research Content:
{combined_raw}

Requirements:
1. Extract the most important, interesting, and useful takeaways
2. Rewrite each takeaway in simple, everyday language that anyone can understand
3. Avoid technical jargon - if you must use a technical term, explain it simply
4. Keep each takeaway short (1-2 sentences, max 150 characters)
5. Make it engaging and interesting - focus on benefits and practical information
6. Write in a friendly, conversational tone
7. Focus on what kombucha does for people's health, not complex scientific mechanisms
8. Return exactly {max_points} key takeaways

Format your response as a numbered list, one takeaway per line:
1. [first takeaway]
2. [second takeaway]
..."""

        try:
            response = self.ai_generator.client.chat.completions.create(
                model=self.ai_generator.model,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are an expert at translating scientific research into clear, engaging, and accessible information for the general public. You make complex health information easy to understand.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse the numbered list
            refined_points = []
            lines = result_text.split('\n')
            for line in lines:
                line = line.strip()
                # Remove numbering (1., 2., etc.)
                line = re.sub(r'^\d+[\.\)]\s*', '', line)
                # Remove markdown formatting
                line = re.sub(r'^[-*]\s*', '', line)
                if line and len(line) > 10:  # Valid takeaway
                    refined_points.append(line)
            
            # Limit to max_points
            return refined_points[:max_points] if refined_points else raw_key_points[:max_points]
            
        except Exception as e:
            print(f"Warning: Error refining key points with LLM: {e}")
            print("Falling back to raw key points.")
            return raw_key_points[:max_points]
    
    def preprocess_all_themes(
        self,
        max_pages_per_pdf: int = 10,
        max_key_points_per_pdf: int = 10,
        force: bool = False
    ) -> Dict[str, Dict]:
        """
        Preprocess all theme folders (04-07).
        
        Args:
            max_pages_per_pdf: Maximum pages to extract from each PDF.
            max_key_points_per_pdf: Maximum key points to extract per PDF.
            force: If True, reprocess even if JSON already exists.
        
        Returns:
            Dictionary mapping theme names to their preprocessing results.
        """
        themes = [
            '04_immune_system',
            '05_kombucha_benefits',
            '06_digestive_health',
            '07_kombucha_research'
        ]
        
        results = {}
        for theme in themes:
            theme_path = self.assets_base_path / theme
            if theme_path.exists():
                print(f"\n{'='*60}")
                print(f"Processing theme: {theme}")
                print(f"{'='*60}")
                try:
                    results[theme] = self.preprocess_theme(
                        theme,
                        max_pages_per_pdf=max_pages_per_pdf,
                        max_key_points_per_pdf=max_key_points_per_pdf,
                        force=force
                    )
                except Exception as e:
                    print(f"Error processing {theme}: {e}")
                    results[theme] = {'error': str(e)}
            else:
                print(f"Theme {theme} not found, skipping...")
        
        return results
    
    def _load_json(self, json_path: Path) -> Dict:
        """Load JSON file."""
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
