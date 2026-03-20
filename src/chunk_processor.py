"""
Chunk Processor Agent Module

Processes document chunks to summarize main ideas and identify quote candidates.
"""

import re
import json
from typing import List, Dict, Optional
from .ai_caption_generator import AICaptionGenerator
from .utils import load_config


class ChunkProcessor:
    """Process chunks to extract main ideas and quote candidates."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize chunk processor.
        
        Args:
            config: Configuration dictionary. If None, loads from file.
        """
        if config is None:
            config = load_config()
        
        self.config = config
        self.ai_generator = AICaptionGenerator(config)
        extraction_config = config.get('quote_extraction', {})
        self.max_quotes_per_chunk = extraction_config.get('max_quotes_per_chunk', 10)
    
    def process_chunk(
        self,
        chunk: Dict,
        source_name: str,
        author: str,
        chunk_index: int
    ) -> Dict:
        """
        Process a single chunk: summarize main ideas and extract quotes.
        
        Args:
            chunk: Chunk dictionary with 'text' and metadata.
            source_name: Name of the source.
            author: Author name.
            chunk_index: Index of the chunk (for ID generation).
        
        Returns:
            Dictionary with main ideas, quotes, and metadata.
        """
        chunk_text = chunk.get('text', '')
        if not chunk_text or len(chunk_text.strip()) < 100:
            return {
                'chunk_id': chunk.get('chunk_id', f'chunk_{chunk_index:03d}'),
                'position': chunk.get('position', chunk_index),
                'main_ideas': [],
                'quotes': [],
                'context': chunk.get('context', '')
            }
        
        # Step 1: Summarize main ideas
        main_ideas = self.summarize_main_ideas(chunk_text, source_name, author)
        
        # Step 2: Identify quote candidates based on main ideas
        quote_candidates = self.identify_quote_candidates(
            chunk_text,
            main_ideas,
            source_name,
            author,
            chunk.get('context', '')
        )

        # Step 3: Resolve dangling pronouns using chunk context
        quote_candidates = self.resolve_dangling_pronouns(quote_candidates, chunk_text)

        # Step 4: Extract contextual quotes
        quotes = self.extract_contextual_quotes(
            quote_candidates,
            main_ideas,
            chunk.get('context', ''),
            chunk_index
        )
        
        return {
            'chunk_id': chunk.get('chunk_id', f'chunk_{chunk_index:03d}'),
            'position': chunk.get('position', chunk_index),
            'main_ideas': main_ideas,
            'quotes': quotes,
            'context': chunk.get('context', ''),
            'chapters': chunk.get('chapters', [])
        }
    
    def summarize_main_ideas(
        self,
        chunk_text: str,
        source_name: str,
        author: str
    ) -> List[str]:
        """
        Extract main ideas/themes from chunk using AI.
        
        Args:
            chunk_text: Text content of the chunk.
            source_name: Name of the source.
            author: Author name.
        
        Returns:
            List of main ideas/themes.
        """
        if not self.ai_generator.client:
            # Fallback: simple extraction
            sentences = chunk_text.split('.')
            return [s.strip()[:100] for s in sentences[:3] if len(s.strip()) > 20]
        
        prompt = f"""Analyze the following chunk of yoga literature and identify the main ideas and themes.

Source: {source_name}
Author: {author}

Text:
{chunk_text[:6000]}

Identify 3-5 main ideas or themes in this chunk. Focus on:
- Key philosophical concepts (especially: sattva, rajas, tamas, gunas, prakriti, purusha, dharma, karma, moksha, samadhi, dhyana, pranayama, asana, yama, niyama)
- Practical teachings or guidance
- Important concepts about yoga practice
- Spiritual insights
- Core yoga philosophy and wisdom

Pay special attention to quotes that explain or discuss fundamental yoga concepts like the three gunas (sattva, rajas, tamas), spiritual evolution, self-realization, and the nature of consciousness.

Format your response as a JSON array of strings, where each string is a main idea (1-2 sentences max).

Example: ["The importance of proper alignment in asana practice", "Breath control as a bridge between body and mind", "The three gunas (sattva, rajas, tamas) and their role in spiritual evolution"]

Return ONLY a valid JSON array, no other text."""

        try:
            result_text = self.ai_generator.complete(
                system='You are an expert at analyzing yoga and spiritual literature. You identify key themes and main ideas concisely.',
                user=prompt,
                temperature=0.5,
                max_tokens=500
            )

            # Parse JSON response
            if result_text.startswith('```'):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)

            main_ideas = json.loads(result_text)
            if isinstance(main_ideas, list):
                return [idea.strip() for idea in main_ideas if idea.strip()][:5]

        except Exception as e:
            print(f"Warning: Error summarizing main ideas: {e}")
        
        # Fallback
        return []
    
    def identify_quote_candidates(
        self,
        chunk_text: str,
        main_ideas: List[str],
        source_name: str,
        author: str,
        context: str
    ) -> List[Dict]:
        """
        Identify potential quotes based on main ideas.
        
        Args:
            chunk_text: Text content of the chunk.
            main_ideas: List of main ideas from the chunk.
            source_name: Name of the source.
            author: Author name.
            context: Context information (chapter, section, etc.).
        
        Returns:
            List of quote candidate dictionaries.
        """
        if not self.ai_generator.client:
            return []
        
        ideas_text = "\n".join([f"- {idea}" for idea in main_ideas]) if main_ideas else "General yoga wisdom"
        
        prompt = f"""Based on the main ideas identified in this chunk of yoga literature, identify the most meaningful quotes.

Source: {source_name}
Author: {author}
Context: {context if context else "General text"}

Main Ideas:
{ideas_text}

Text:
{chunk_text[:6000]}

Identify quotes that:
- Are inspirational or motivational
- Express philosophical wisdom
- Provide practical guidance
- Are memorable and suitable for sharing
- **PRIORITIZE quotes about key yoga concepts**: sattva, rajas, tamas, gunas, prakriti, purusha, dharma, karma, moksha, samadhi, dhyana, pranayama, asana, yama, niyama, chitta, vrittis, etc.

**IMPORTANT**: If the text discusses fundamental yoga concepts (especially sattva, rajas, tamas, gunas), prioritize extracting quotes that explain or illuminate these concepts. These are highly valuable for yoga content.

**CRITICAL — Self-contained quotes only**: Every quote must be fully understandable on its own without any surrounding context. Do NOT extract sentences that begin with a pronoun whose referent is outside the quote (e.g. "It is...", "They are...", "This is...", "That is...", "These are..." where the noun being referred to is not mentioned within the quote itself). If a sentence starts with "It", "They", "This", "That", "These", or "Those" followed directly by a verb, skip it unless the quote itself makes clear what "it/they/this/that" refers to.

For each quote, provide:
1. The exact quote text (preserve original wording)
2. The type: "quote", "statement", "slogan", or "fact"
3. Relevance to the main ideas

Format your response as a JSON array, where each item has:
- "text": the quote text
- "type": one of "quote", "statement", "slogan", "fact"
- "relevance": brief explanation of how it relates to main ideas

Return ONLY a valid JSON array, no other text. Maximum {self.max_quotes_per_chunk} quotes."""

        try:
            result_text = self.ai_generator.complete(
                system='You are an expert at identifying meaningful quotes from yoga and spiritual literature. You select quotes that are inspiring, clear, and relevant to the main themes.',
                user=prompt,
                temperature=0.7,
                max_tokens=1500
            )

            # Parse JSON response
            if result_text.startswith('```'):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)

            candidates = json.loads(result_text)
            if isinstance(candidates, list):
                return candidates[:self.max_quotes_per_chunk]

        except Exception as e:
            print(f"Warning: Error identifying quote candidates: {e}")
        
        return []
    
    _DANGLING_PRONOUN_RE = re.compile(
        r'^(it|they|this|that|these|those)\s+(is|are|was|were|has|have|had|can|could|will|would|does|do|did|may|might|shall|should)\b',
        re.IGNORECASE
    )

    def resolve_dangling_pronouns(
        self,
        candidates: List[Dict],
        chunk_text: str
    ) -> List[Dict]:
        """
        For any candidate whose text opens with a dangling pronoun, ask the AI to
        substitute the pronoun with the actual concept it refers to, using the chunk
        text as context.  All dangling quotes are resolved in a single batched AI call.

        Args:
            candidates: Quote candidate dicts (each has a 'text' key).
            chunk_text: The full chunk text from which the quotes were drawn.

        Returns:
            Updated candidate list with pronouns resolved where possible.
        """
        if not self.ai_generator.client:
            return candidates

        # Identify which candidates need resolution
        to_resolve = [
            (i, c) for i, c in enumerate(candidates)
            if self._DANGLING_PRONOUN_RE.match(c.get('text', '').strip())
        ]
        if not to_resolve:
            return candidates

        quotes_block = "\n".join(
            f'{n+1}. {c["text"]}' for n, (_, c) in enumerate(to_resolve)
        )

        prompt = f"""The quotes below were extracted from a yoga text but each opens with a pronoun
("It", "This", "That", "They", "These", "Those") whose referent is in the surrounding passage,
not inside the quote itself.

Using the passage as context, rewrite each quote by replacing the opening pronoun with the
specific concept, noun, or phrase it refers to.  Keep every other word exactly as written.
If you genuinely cannot determine the referent, leave the quote unchanged.

Source passage:
{chunk_text[:4000]}

Quotes to resolve:
{quotes_block}

Return a JSON array with one object per quote, in the same order:
- "original": the original quote text
- "resolved": the rewritten quote

Return ONLY valid JSON, no other text."""

        try:
            result_text = self.ai_generator.complete(
                system='You are an expert editor. You resolve ambiguous pronoun references in quotes by substituting the pronoun with the noun or concept it refers to, based on surrounding context.',
                user=prompt,
                temperature=0.3,
                max_tokens=1000
            )
            if result_text.startswith('```'):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)

            resolutions = json.loads(result_text)
            if isinstance(resolutions, list):
                for n, (orig_idx, _) in enumerate(to_resolve):
                    if n < len(resolutions):
                        resolved_text = resolutions[n].get('resolved', '').strip()
                        if resolved_text:
                            candidates[orig_idx]['text'] = resolved_text
        except Exception as e:
            print(f"Warning: Pronoun resolution failed: {e}")

        return candidates

    def extract_contextual_quotes(
        self,
        quote_candidates: List[Dict],
        main_ideas: List[str],
        context: str,
        chunk_index: int
    ) -> List[Dict]:
        """
        Extract quotes with context and metadata.
        
        Args:
            quote_candidates: List of quote candidate dictionaries.
            main_ideas: List of main ideas from the chunk.
            context: Context information.
            chunk_index: Index of the chunk.
        
        Returns:
            List of refined quote dictionaries with full metadata.
        """
        quotes = []
        
        for idx, candidate in enumerate(quote_candidates):
            quote_text = candidate.get('text', '').strip()
            if not quote_text or len(quote_text) < 20:
                continue
            
            # Generate quote ID
            quote_id = f"chunk{chunk_index:03d}_quote{idx+1:03d}"
            
            # Extract themes from main ideas (simplified)
            themes = []
            for idea in main_ideas[:3]:  # Use top 3 ideas
                # Extract key words from idea
                words = idea.lower().split()
                themes.extend([w for w in words if len(w) > 4][:2])  # Take meaningful words
            
            quote = {
                'id': quote_id,
                'text': quote_text,
                'type': candidate.get('type', 'quote'),
                'context': context,
                'chunk_id': f"chunk_{chunk_index:03d}",
                'themes': list(set(themes))[:5],  # Deduplicate and limit
                'relevance': candidate.get('relevance', ''),
                'importance_score': 0.5,  # Will be refined later
                'approved': False,
                'notes': ''
            }
            
            quotes.append(quote)
        
        return quotes


def main():
    """Test function."""
    processor = ChunkProcessor()
    
    test_chunk = {
        'text': 'Yoga is the journey of the self, through the self, to the self. It requires discipline and dedication.',
        'chunk_id': 'chunk_001',
        'position': 1,
        'context': 'Chapter 1'
    }
    
    result = processor.process_chunk(test_chunk, 'Bhagavad Gita', 'Eknath Easwaran', 1)
    print(f"Main ideas: {result['main_ideas']}")
    print(f"Quotes extracted: {len(result['quotes'])}")


if __name__ == '__main__':
    main()
