"""
Quote Refiner Agent Module

Evaluates, ranks, and deduplicates quotes extracted from literature.
"""

import re
import json
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from .ai_caption_generator import AICaptionGenerator
from .utils import load_config


class QuoteRefiner:
    """Evaluate and refine extracted quotes."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize quote refiner.
        
        Args:
            config: Configuration dictionary. If None, loads from file.
        """
        if config is None:
            config = load_config()
        
        self.config = config
        self.ai_generator = AICaptionGenerator(config)
        extraction_config = config.get('quote_extraction', {})
        self.min_quote_length = extraction_config.get('min_quote_length', 20)
        self.max_quote_length = extraction_config.get('max_quote_length', 500)
        # Get priority concepts from config
        self.priority_concepts = extraction_config.get('priority_concepts', [
            'sattva', 'rajas', 'tamas', 'gunas', 'prakriti', 'purusha',
            'dharma', 'karma', 'moksha', 'samadhi', 'dhyana', 'pranayama',
            'asana', 'yama', 'niyama', 'chitta', 'vrittis'
        ])
    
    # Patterns that indicate a quote starts with a dangling pronoun reference
    _DANGLING_PRONOUN_RE = re.compile(
        r'^(it|they|this|that|these|those)\s+(is|are|was|were|has|have|had|can|could|will|would|does|do|did|may|might|shall|should)\b',
        re.IGNORECASE
    )

    def _has_dangling_pronoun(self, text: str) -> bool:
        """Return True if the quote opens with a pronoun whose antecedent is outside the quote."""
        return bool(self._DANGLING_PRONOUN_RE.match(text.strip()))

    def evaluate_quotes(
        self,
        quotes: List[Dict],
        chunk_summaries: List[str]
    ) -> List[Dict]:
        """
        Evaluate quote quality and add scores.

        Args:
            quotes: List of quote dictionaries.
            chunk_summaries: List of chunk summary strings.

        Returns:
            List of quotes with importance scores.
        """
        if not quotes:
            return []

        # Combine chunk summaries for context
        combined_summary = " ".join(chunk_summaries[:5])  # Use top 5 summaries

        # Evaluate each quote
        evaluated_quotes = []
        for quote in quotes:
            score = self._calculate_importance_score(quote, combined_summary)
            # Safety net: heavily penalise any dangling-pronoun quote that slipped
            # through without being resolved (e.g. via the simple extraction path)
            if self._has_dangling_pronoun(quote.get('text', '')):
                score = max(0.0, score - 0.5)
            quote['importance_score'] = score
            evaluated_quotes.append(quote)

        return evaluated_quotes
    
    def _calculate_importance_score(self, quote: Dict, context: str) -> float:
        """
        Calculate importance score for a quote.
        
        Args:
            quote: Quote dictionary.
            context: Combined context from chunk summaries.
        
        Returns:
            Importance score between 0 and 1.
        """
        score = 0.5  # Base score
        
        quote_text = quote.get('text', '').lower()
        
        # Length check (prefer medium-length quotes)
        quote_length = len(quote_text)
        if self.min_quote_length <= quote_length <= self.max_quote_length:
            score += 0.1
        elif quote_length < self.min_quote_length or quote_length > self.max_quote_length:
            score -= 0.2
        
        # Type scoring
        quote_type = quote.get('type', 'quote')
        type_scores = {
            'quote': 0.15,
            'statement': 0.1,
            'slogan': 0.2,
            'fact': 0.05
        }
        score += type_scores.get(quote_type, 0)
        
        # Theme relevance (if themes exist)
        themes = quote.get('themes', [])
        if themes:
            score += 0.1
        
        # Context relevance
        if quote.get('context'):
            score += 0.05
        
        # Inspirational keywords
        inspirational_keywords = [
            'wisdom', 'practice', 'journey', 'spiritual', 'mind', 'body', 'soul',
            'peace', 'harmony', 'balance', 'truth', 'light', 'path', 'self',
            'awareness', 'consciousness', 'meditation', 'yoga', 'breath', 'asana', 
            'pineal gland', 'pineal', 'kundalini', 'chakra', 'chakras' 
        ]
        keyword_count = sum(1 for keyword in inspirational_keywords if keyword in quote_text)
        score += min(keyword_count * 0.02, 0.1)  # Max 0.1 for keywords
        
        # Key yoga concepts - HIGH PRIORITY (boost score significantly)
        # Use config priority concepts, plus common variations
        all_concepts = self.priority_concepts + [
            'guna', 'vritti', 'dharana', 'pratyahara',
            'brahman', 'atman', 'maya', 'avidya', 'dukkha'
        ]
        concept_count = sum(1 for concept in all_concepts if concept in quote_text.lower())
        if concept_count > 0:
            score += min(concept_count * 0.15, 0.3)  # Significant boost for key concepts (max 0.3)
        
        # Clamp score between 0 and 1
        return max(0.0, min(1.0, score))
    
    def deduplicate_quotes(self, quotes: List[Dict]) -> List[Dict]:
        """
        Remove duplicate or similar quotes.
        
        Args:
            quotes: List of quote dictionaries.
        
        Returns:
            List of unique quotes (keeping highest-scored duplicates).
        """
        if not quotes:
            return []
        
        unique_quotes = []
        seen_texts = {}
        
        for quote in quotes:
            quote_text = quote.get('text', '').strip().lower()
            
            # Normalize text for comparison
            normalized = re.sub(r'[^\w\s]', '', quote_text)
            normalized = ' '.join(normalized.split())
            
            # Check for exact duplicates
            if normalized in seen_texts:
                # Keep the one with higher importance score
                existing = seen_texts[normalized]
                if quote.get('importance_score', 0) > existing.get('importance_score', 0):
                    # Replace existing with better quote
                    unique_quotes.remove(existing)
                    unique_quotes.append(quote)
                    seen_texts[normalized] = quote
                continue
            
            # Check for similar quotes (using sequence matcher)
            is_duplicate = False
            for existing_text, existing_quote in seen_texts.items():
                similarity = SequenceMatcher(None, normalized, existing_text).ratio()
                if similarity > 0.85:  # 85% similarity threshold
                    # Keep the one with higher score
                    if quote.get('importance_score', 0) > existing_quote.get('importance_score', 0):
                        unique_quotes.remove(existing_quote)
                        unique_quotes.append(quote)
                        seen_texts[existing_text] = quote
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_quotes.append(quote)
                seen_texts[normalized] = quote
        
        return unique_quotes
    
    def rank_by_importance(self, quotes: List[Dict]) -> List[Dict]:
        """
        Rank quotes by importance/relevance.
        
        Args:
            quotes: List of quote dictionaries.
        
        Returns:
            List of quotes sorted by importance score (descending).
        """
        return sorted(
            quotes,
            key=lambda q: q.get('importance_score', 0),
            reverse=True
        )
    
    def add_thematic_tags(
        self,
        quotes: List[Dict],
        themes: List[str]
    ) -> List[Dict]:
        """
        Add thematic tags to quotes based on overall themes.
        
        Args:
            quotes: List of quote dictionaries.
            themes: List of overall themes from document.
        
        Returns:
            List of quotes with enhanced thematic tags.
        """
        for quote in quotes:
            quote_text = quote.get('text', '').lower()
            existing_themes = set(quote.get('themes', []))
            
            # Match quote text against themes
            for theme in themes:
                theme_lower = theme.lower()
                theme_words = theme_lower.split()
                
                # Check if theme words appear in quote
                if any(word in quote_text for word in theme_words if len(word) > 4):
                    existing_themes.add(theme_lower)
            
            quote['themes'] = list(existing_themes)[:5]  # Limit to 5 themes
        
        return quotes
    
    def refine_with_ai(self, quotes: List[Dict], max_quotes: int = 50) -> List[Dict]:
        """
        Use AI to further refine and rank quotes.
        
        Args:
            quotes: List of quote dictionaries.
            max_quotes: Maximum number of quotes to return.
        
        Returns:
            List of refined quotes.
        """
        if not self.ai_generator.client or not quotes:
            return quotes[:max_quotes]
        
        # Prepare quotes for AI evaluation
        quotes_text = "\n".join([
            f"{i+1}. [{q.get('importance_score', 0):.2f}] {q.get('text', '')[:200]}"
            for i, q in enumerate(quotes[:100])  # Limit to 100 for AI processing
        ])
        
        prompt = f"""Evaluate and rank these yoga quotes by their quality, uniqueness, and inspirational value.

Consider:
- Uniqueness and distinctiveness
- Clarity and completeness
- Inspirational/philosophical value
- Social media suitability
- Relevance to yoga/spiritual themes

Quotes:
{quotes_text}

Return a JSON array of quote numbers (1-based) in order of quality (best first).
Example: [3, 1, 5, 2, 4]

Return ONLY the JSON array, no other text."""

        try:
            result_text = self.ai_generator.complete(
                system='You are an expert at evaluating quotes for quality, uniqueness, and inspirational value.',
                user=prompt,
                temperature=0.3,
                max_tokens=500
            )

            # Parse JSON response
            if result_text.startswith('```'):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)

            ranked_indices = json.loads(result_text)
            if isinstance(ranked_indices, list):
                # Reorder quotes based on AI ranking
                ranked_quotes = []
                for idx in ranked_indices:
                    if 1 <= idx <= len(quotes):
                        ranked_quotes.append(quotes[idx - 1])
                
                # Add any quotes not in AI ranking
                for i, quote in enumerate(quotes):
                    if i + 1 not in ranked_indices:
                        ranked_quotes.append(quote)
                
                return ranked_quotes[:max_quotes]
            
        except Exception as e:
            print(f"Warning: AI refinement failed, using default ranking: {e}")
        
        # Fallback to importance score ranking
        return self.rank_by_importance(quotes)[:max_quotes]


def main():
    """Test function."""
    refiner = QuoteRefiner()
    
    test_quotes = [
        {'text': 'Yoga is the journey of the self', 'type': 'quote', 'themes': ['yoga', 'journey']},
        {'text': 'Yoga is the journey of the self', 'type': 'quote', 'themes': ['yoga']},  # Duplicate
        {'text': 'Practice makes perfect', 'type': 'statement', 'themes': ['practice']},
    ]
    
    # Evaluate
    evaluated = refiner.evaluate_quotes(test_quotes, ['Yoga practice', 'Self-discovery'])
    print("Evaluated quotes:")
    for q in evaluated:
        print(f"  Score: {q.get('importance_score', 0):.2f} - {q['text']}")
    
    # Deduplicate
    unique = refiner.deduplicate_quotes(evaluated)
    print(f"\nUnique quotes: {len(unique)}")
    
    # Rank
    ranked = refiner.rank_by_importance(unique)
    print("\nRanked quotes:")
    for q in ranked:
        print(f"  Score: {q.get('importance_score', 0):.2f} - {q['text']}")


if __name__ == '__main__':
    main()
