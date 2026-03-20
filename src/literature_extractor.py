"""
Literature Extractor Module

AI-powered extraction of quotes, statements, slogans, and interesting facts from yoga literature.
Supports both simple and intelligent agent-based extraction methods.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from .ai_caption_generator import AICaptionGenerator
from .utils import load_config, shorten_quote_for_display
from .document_analyzer import DocumentAnalyzer
from .chunk_processor import ChunkProcessor
from .quote_refiner import QuoteRefiner


class LiteratureExtractor:
    """Extract quotes from literature text files using AI."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize literature extractor.
        
        Args:
            config: Configuration dictionary. If None, loads from file.
        """
        if config is None:
            config = load_config()
        
        self.config = config
        self.ai_generator = AICaptionGenerator(config)
        self.assets_base_path = Path(__file__).parent.parent / 'assets'
        
        # Initialize intelligent extraction components
        extraction_config = config.get('quote_extraction', {})
        self.extraction_method = extraction_config.get('method', 'simple')
        self.document_analyzer = DocumentAnalyzer(config)
        self.chunk_processor = ChunkProcessor(config)
        self.quote_refiner = QuoteRefiner(config)
    
    def extract_quotes_from_text(
        self,
        text: str,
        source_name: str,
        author: str,
        max_quotes: int = 50
    ) -> List[Dict]:
        """
        Extract quotes from text using AI/LLM.
        
        Args:
            text: Text content to extract quotes from.
            source_name: Name of the source (e.g., "Bhagavad Gita").
            author: Author name.
            max_quotes: Maximum number of quotes to extract.
        
        Returns:
            List of quote dictionaries.
        """
        if not text or len(text.strip()) < 100:
            return []
        
        # Build prompt for quote extraction
        prompt = f"""Extract meaningful quotes, statements, slogans, and interesting facts from the following yoga literature text.

Source: {source_name}
Author: {author}

Extract quotes that are:
- Inspirational or motivational
- Philosophically meaningful
- Practical wisdom or guidance
- Memorable phrases or slogans
- Interesting facts about yoga, meditation, or spirituality
- **PRIORITIZE quotes about key yoga concepts**: sattva, rajas, tamas, gunas, prakriti, purusha, dharma, karma, moksha, samadhi, dhyana, pranayama, asana, yama, niyama, chitta, vrittis, etc.

**IMPORTANT**: If the text discusses fundamental yoga concepts (especially sattva, rajas, tamas, gunas), prioritize extracting quotes that explain or illuminate these concepts. These are highly valuable for yoga content.

**CRITICAL — Self-contained quotes only**: Every quote must be fully understandable on its own without any surrounding context. Do NOT extract sentences that begin with a pronoun whose referent is outside the quote (e.g. "It is...", "They are...", "This is...", "That is...", "These are..." where the noun being referred to is not mentioned within the quote itself). If a sentence starts with "It", "They", "This", "That", "These", or "Those" followed directly by a verb, skip it unless the quote itself makes clear what "it/they/this/that" refers to.

For each quote, provide:
1. The exact quote text (preserve original wording)
2. The type: "quote", "statement", "slogan", or "fact"
3. Context if available (chapter, verse, page number, etc.)

Format your response as a JSON array, where each item has:
- "text": the quote text
- "type": one of "quote", "statement", "slogan", "fact"
- "context": any available context (chapter, verse, etc.) or empty string

Return ONLY a valid JSON array, no other text. Maximum {max_quotes} quotes.

Text to extract from:
{text[:8000]}  # Limit text to avoid token limits
"""
        
        try:
            result_text = self.ai_generator.complete(
                system='You are an expert at identifying meaningful quotes and wisdom from spiritual and philosophical texts. Extract quotes that are inspiring, memorable, and suitable for sharing on social media.',
                user=prompt,
                temperature=0.7,
                max_tokens=2000
            )

            # Try to parse JSON response
            # Remove markdown code blocks if present
            if result_text.startswith('```'):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)
            
            quotes_data = json.loads(result_text)
            
            # Convert to our format
            quotes = []
            for idx, item in enumerate(quotes_data[:max_quotes], 1):
                quote_text = item.get('text', '').strip()
                if quote_text and len(quote_text) > 10:  # Minimum length
                    quote_id = f"{source_name.lower().replace(' ', '_')}_{idx:03d}"
                    quote_id = re.sub(r'[^a-z0-9_]', '', quote_id)
                    
                    quotes.append({
                        'id': quote_id,
                        'text': quote_text,
                        'type': item.get('type', 'quote'),
                        'context': item.get('context', ''),
                        'approved': False,
                        'notes': ''
                    })
            
            return quotes
            
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse AI response as JSON: {e}")
            print(f"Response was: {result_text[:500]}")
            return []
        except Exception as e:
            print(f"Error extracting quotes: {e}")
            return []
    
    def extract_from_file(
        self,
        file_path: Path,
        source_name: str,
        author: str,
        max_quotes: int = 50,
        use_intelligent: Optional[bool] = None
    ) -> List[Dict]:
        """
        Extract quotes from a single text file.
        
        Args:
            file_path: Path to text file.
            source_name: Name of the source.
            author: Author name.
            max_quotes: Maximum number of quotes to extract.
            use_intelligent: Whether to use intelligent extraction. If None, uses config default.
        
        Returns:
            List of quote dictionaries.
        """
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Determine extraction method
            if use_intelligent is None:
                use_intelligent = (self.extraction_method == 'intelligent')
            
            if use_intelligent:
                return self.extract_quotes_intelligent(file_path, source_name, author, max_quotes)
            else:
                return self.extract_quotes_from_text(text, source_name, author, max_quotes)
            
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []
    
    def extract_quotes_intelligent(
        self,
        file_path: Path,
        source_name: str,
        author: str,
        max_quotes: int = 100
    ) -> List[Dict]:
        """
        Extract quotes using intelligent agent-based approach.
        
        Args:
            file_path: Path to text file.
            source_name: Name of the source.
            author: Author name.
            max_quotes: Maximum number of quotes to extract.
        
        Returns:
            List of quote dictionaries with enhanced metadata.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []
        
        # Step 1: Analyze document structure
        structure = self.document_analyzer.analyze_structure(file_path)
        
        # Step 2: Determine chunking strategy
        strategy = self.document_analyzer.determine_chunking_strategy(text, len(text))
        
        # Step 3: Split into chunks
        chunks = self.document_analyzer.split_into_chunks(
            text,
            chunk_size=strategy['chunk_size'],
            overlap=strategy['overlap'],
            preserve_structure=strategy['use_semantic_boundaries']
        )
        
        print(f"  Processing {len(chunks)} chunks...")
        
        # Step 4: Process each chunk
        chunk_results = []
        all_quotes = []
        chunk_summaries = []
        
        for i, chunk in enumerate(chunks):
            print(f"    Processing chunk {i+1}/{len(chunks)}...", end='\r')
            result = self.chunk_processor.process_chunk(chunk, source_name, author, i+1)
            chunk_results.append(result)
            all_quotes.extend(result.get('quotes', []))
            if result.get('main_ideas'):
                chunk_summaries.append(' '.join(result['main_ideas']))
        
        print(f"    Processed {len(chunks)} chunks, extracted {len(all_quotes)} quote candidates")
        
        # Step 5: Refine quotes
        print(f"  Refining quotes...")
        evaluated_quotes = self.quote_refiner.evaluate_quotes(all_quotes, chunk_summaries)
        unique_quotes = self.quote_refiner.deduplicate_quotes(evaluated_quotes)
        ranked_quotes = self.quote_refiner.rank_by_importance(unique_quotes)
        
        # Extract overall themes from chunk summaries
        overall_themes = self._extract_overall_themes(chunk_summaries)
        themed_quotes = self.quote_refiner.add_thematic_tags(ranked_quotes, overall_themes)
        
        # Limit to max_quotes
        final_quotes = themed_quotes[:max_quotes]
        
        print(f"  Final quotes after refinement: {len(final_quotes)}")
        
        return final_quotes
    
    def _extract_overall_themes(self, chunk_summaries: List[str]) -> List[str]:
        """Extract overall themes from chunk summaries."""
        # Simple extraction: look for common words/phrases
        all_words = []
        for summary in chunk_summaries:
            words = summary.lower().split()
            all_words.extend([w for w in words if len(w) > 4])
        
        # Count word frequency
        from collections import Counter
        word_counts = Counter(all_words)
        
        # Return top themes
        return [word for word, count in word_counts.most_common(10)]
    
    def process_document_in_chunks(
        self,
        file_path: Path,
        source_name: str,
        author: str
    ) -> Dict:
        """
        Process entire document using chunking and return full results.
        
        Args:
            file_path: Path to text file.
            source_name: Name of the source.
            author: Author name.
        
        Returns:
            Dictionary with chunks, quotes, and document summary.
        """
        extraction_config = self.config.get('quote_extraction', {})
        max_quotes = extraction_config.get('max_total_quotes', 100)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return {}
        
        # Analyze structure
        structure = self.document_analyzer.analyze_structure(file_path)
        
        # Determine chunking strategy
        strategy = self.document_analyzer.determine_chunking_strategy(text, len(text))
        
        # Split into chunks
        chunks = self.document_analyzer.split_into_chunks(
            text,
            chunk_size=strategy['chunk_size'],
            overlap=strategy['overlap'],
            preserve_structure=strategy['use_semantic_boundaries']
        )
        
        # Process each chunk
        chunk_results = []
        all_quotes = []
        chunk_summaries = []
        
        for i, chunk in enumerate(chunks):
            result = self.chunk_processor.process_chunk(chunk, source_name, author, i+1)
            chunk_results.append(result)
            all_quotes.extend(result.get('quotes', []))
            if result.get('main_ideas'):
                chunk_summaries.append(' '.join(result['main_ideas']))
        
        # Refine quotes
        evaluated_quotes = self.quote_refiner.evaluate_quotes(all_quotes, chunk_summaries)
        unique_quotes = self.quote_refiner.deduplicate_quotes(evaluated_quotes)
        ranked_quotes = self.quote_refiner.rank_by_importance(unique_quotes)
        
        # Extract overall themes
        overall_themes = self._extract_overall_themes(chunk_summaries)
        final_quotes = self.quote_refiner.add_thematic_tags(ranked_quotes, overall_themes)[:max_quotes]
        
        return {
            'chunks': chunk_results,
            'quotes': final_quotes,
            'document_summary': {
                'total_chunks': len(chunks),
                'main_themes': overall_themes[:10],
                'chapters_detected': structure.get('chapters_detected', 0),
                'total_quotes_extracted': len(all_quotes),
                'final_quotes_count': len(final_quotes)
            }
        }
    
    def aggregate_chunk_results(self, chunk_results: List[Dict]) -> Dict:
        """
        Combine results from all chunks.
        
        Args:
            chunk_results: List of chunk result dictionaries.
        
        Returns:
            Aggregated dictionary with all quotes and summaries.
        """
        all_quotes = []
        chunk_summaries = []
        chunks_data = []
        
        for result in chunk_results:
            all_quotes.extend(result.get('quotes', []))
            if result.get('main_ideas'):
                chunk_summaries.append(' '.join(result['main_ideas']))
            chunks_data.append({
                'chunk_id': result.get('chunk_id'),
                'position': result.get('position'),
                'main_ideas': result.get('main_ideas', []),
                'context': result.get('context', ''),
                'quote_count': len(result.get('quotes', []))
            })
        
        # Refine aggregated quotes
        evaluated_quotes = self.quote_refiner.evaluate_quotes(all_quotes, chunk_summaries)
        unique_quotes = self.quote_refiner.deduplicate_quotes(evaluated_quotes)
        ranked_quotes = self.quote_refiner.rank_by_importance(unique_quotes)
        
        # Extract overall themes
        overall_themes = self._extract_overall_themes(chunk_summaries)
        final_quotes = self.quote_refiner.add_thematic_tags(ranked_quotes, overall_themes)
        
        return {
            'chunks': chunks_data,
            'quotes': final_quotes,
            'main_themes': overall_themes[:10]
        }
    
    def extract_from_group(
        self,
        group_name: str,
        force: bool = False,
        use_intelligent: Optional[bool] = None
    ) -> Dict:
        """
        Extract quotes from all files in a literature group.
        
        Args:
            group_name: Name of the literature group (e.g., "BhagavadGita").
            force: If True, re-extract even if JSON exists.
        
        Returns:
            Dictionary with extracted quotes and metadata.
        """
        # Get group configuration
        literature_groups = self.config.get('literature_groups', [])
        group_config = None
        for group in literature_groups:
            if group.get('name') == group_name:
                group_config = group
                break
        
        if not group_config:
            print(f"Literature group '{group_name}' not found in configuration")
            return {}
        
        source_name = group_config.get('display_name', group_name)
        author = group_config.get('author', '')
        source_path_str = group_config.get('source_path', '')
        source_path = Path(source_path_str)
        
        # Convert relative path to absolute
        if not source_path.is_absolute():
            # Remove 'assets/' prefix if present, as assets_base_path already points to assets
            if source_path_str.startswith('assets/'):
                source_path_str = source_path_str.replace('assets/', '', 1)
            source_path = self.assets_base_path / source_path_str
        
        # Check if quotes.json already exists
        quotes_file = source_path / 'quotes.json'
        if quotes_file.exists() and not force:
            print(f"Quotes file already exists for {group_name}. Use --force to re-extract.")
            return {}
        
        # Find all text files in the group directory
        text_files = list(source_path.glob('*.txt'))
        
        if not text_files:
            print(f"No text files found in {source_path}")
            return {}
        
        print(f"Extracting quotes from {len(text_files)} file(s) in {group_name}...")
        
        # Determine extraction method
        if use_intelligent is None:
            use_intelligent = (self.extraction_method == 'intelligent')
        
        extraction_config = self.config.get('quote_extraction', {})
        max_quotes = extraction_config.get('max_total_quotes', 100)
        
        if use_intelligent:
            # Use intelligent extraction
            print(f"  Using intelligent agent-based extraction...")
            all_quotes = []
            chunk_results_list = []
            document_summaries = []
            
            for text_file in text_files:
                print(f"  Processing {text_file.name}...")
                doc_result = self.process_document_in_chunks(text_file, source_name, author)
                
                if doc_result:
                    all_quotes.extend(doc_result.get('quotes', []))
                    chunk_results_list.extend(doc_result.get('chunks', []))
                    if doc_result.get('document_summary'):
                        document_summaries.append(doc_result['document_summary'])
                    print(f"    Extracted {len(doc_result.get('quotes', []))} quotes from {len(doc_result.get('chunks', []))} chunks")
            
            # Aggregate results
            overall_themes = []
            for summary in document_summaries:
                overall_themes.extend(summary.get('main_themes', []))
            
            # Final refinement across all files
            from collections import Counter
            theme_counts = Counter(overall_themes)
            final_themes = [theme for theme, count in theme_counts.most_common(10)]
            
            # Create result dictionary with enhanced structure
            result = {
                'source': source_name,
                'author': author,
                'extracted_at': datetime.now().isoformat(),
                'extraction_method': 'intelligent',
                'document_summary': {
                    'total_chunks': sum(s.get('total_chunks', 0) for s in document_summaries),
                    'main_themes': final_themes,
                    'chapters_detected': sum(s.get('chapters_detected', 0) for s in document_summaries),
                    'total_quotes_extracted': len(all_quotes)
                },
                'chunks': chunk_results_list[:20],  # Limit chunks in output
                'quotes': all_quotes[:max_quotes]
            }
        else:
            # Use simple extraction
            all_quotes = []
            for text_file in text_files:
                print(f"  Processing {text_file.name}...")
                quotes = self.extract_from_file(text_file, source_name, author, max_quotes=50, use_intelligent=False)
                all_quotes.extend(quotes)
                print(f"    Extracted {len(quotes)} quotes")
            
            # Create result dictionary
            result = {
                'source': source_name,
                'author': author,
                'extracted_at': datetime.now().isoformat(),
                'extraction_method': 'simple',
                'quotes': all_quotes[:max_quotes]
            }
        
        # Save to JSON
        self.save_extracted_quotes(result, quotes_file)
        
        print(f"✓ Extracted {len(all_quotes)} quotes total. Saved to {quotes_file}")
        
        return result
    
    def save_extracted_quotes(self, quotes_data: Dict, output_path: Path):
        """
        Save extracted quotes to JSON file.
        Full quote text is preserved; truncation happens at render time in the card generator.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(quotes_data, f, indent=2, ensure_ascii=False)
    
    def extract_all_groups(self, force: bool = False, use_intelligent: Optional[bool] = None) -> Dict[str, Dict]:
        """
        Extract quotes from all literature groups.
        
        Args:
            force: If True, re-extract even if JSON exists.
        
        Returns:
            Dictionary mapping group names to extraction results.
        """
        literature_groups = self.config.get('literature_groups', [])
        results = {}
        
        for group in literature_groups:
            group_name = group.get('name')
            if group_name:
                print(f"\n{'='*60}")
                print(f"Processing group: {group_name}")
                print(f"{'='*60}")
                result = self.extract_from_group(group_name, force=force, use_intelligent=use_intelligent)
                results[group_name] = result
        
        return results


def main():
    """Test function."""
    extractor = LiteratureExtractor()
    
    # Test extraction from a single group
    result = extractor.extract_from_group('BhagavadGita', force=False)
    print(f"\nExtracted {len(result.get('quotes', []))} quotes")


if __name__ == '__main__':
    main()
