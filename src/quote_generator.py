"""
Quote Generator Module

Utilities for working with yoga quotes from literature collections.
"""

import random
import json
from pathlib import Path
from typing import List, Dict, Optional


class QuoteGenerator:
    """Generate and manage yoga quotes from literature."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize quote generator.
        
        Args:
            config: Configuration dictionary. If None, loads from file.
        """
        if config is None:
            from .utils import load_config
            config = load_config()
        
        self.config = config
        self.assets_base_path = Path(__file__).parent.parent / 'assets'
        self.quotes = self._load_quotes()
    
    def _load_quotes(self) -> Dict[str, List[Dict]]:
        """
        Load quotes from JSON files organized by literature groups.
        
        Returns:
            Dictionary mapping group names to lists of approved quote dictionaries.
        """
        quotes_by_group = {}
        
        # Get literature groups from config
        literature_groups = self.config.get('literature_groups', [])
        
        for group in literature_groups:
            group_name = group.get('name')
            source_path = Path(group.get('source_path', ''))
            
            # Convert relative path to absolute
            if not source_path.is_absolute():
                source_path = self.assets_base_path.parent / source_path
            
            # Look for quotes.json in the group directory
            quotes_file = source_path / 'quotes.json'
            
            if quotes_file.exists():
                try:
                    with open(quotes_file, 'r', encoding='utf-8') as f:
                        quotes_data = json.load(f)
                    
                    # Filter only approved quotes
                    approved_quotes = [
                        quote for quote in quotes_data.get('quotes', [])
                        if quote.get('approved', False)
                    ]
                    
                    if approved_quotes:
                        quotes_by_group[group_name] = approved_quotes
                
                except Exception as e:
                    print(f"Warning: Could not load quotes from {quotes_file}: {e}")
        
        return quotes_by_group
    
    def get_random_quote(self, group: Optional[str] = None, exclude_posted: bool = True) -> Optional[Dict]:
        """
        Get a random approved quote.
        
        Args:
            group: Optional group name to filter by.
            exclude_posted: If True, exclude quotes that have been posted (requires checking metadata).
        
        Returns:
            Quote dictionary with 'text', 'source', 'author', 'id', etc., or None if no quotes available.
        """
        # Filter quotes by group if specified
        if group and group in self.quotes:
            available_quotes = self.quotes[group]
        else:
            # Get all quotes from all groups
            available_quotes = []
            for group_quotes in self.quotes.values():
                available_quotes.extend(group_quotes)
        
        if not available_quotes:
            return None
        
        # If exclude_posted is True, filter out posted quotes
        if exclude_posted:
            posted_quote_ids = self._get_posted_quote_ids()
            available_quotes = [
                q for q in available_quotes
                if q.get('id') not in posted_quote_ids
            ]
            
            # If all quotes are posted, return None (don't reuse)
            if not available_quotes:
                return None
        
        selected_quote = random.choice(available_quotes)
        
        # Add source and author info from config
        literature_groups = self.config.get('literature_groups', [])
        for group_config in literature_groups:
            if group_config.get('name') == (group or self._find_group_for_quote(selected_quote)):
                selected_quote['source'] = group_config.get('display_name', '')
                selected_quote['author'] = group_config.get('author', '')
                break
        
        return selected_quote
    
    def _find_group_for_quote(self, quote: Dict) -> Optional[str]:
        """Find which group a quote belongs to."""
        quote_id = quote.get('id', '')
        for group_name, quotes in self.quotes.items():
            for q in quotes:
                if q.get('id') == quote_id:
                    return group_name
        return None
    
    def _get_posted_quote_ids(self) -> set:
        """
        Get set of quote IDs that have been posted (from metadata files).
        
        Returns:
            Set of quote IDs that have been posted.
        """
        posted_ids = set()
        output_base_path = Path(__file__).parent.parent / 'output'
        posted_dir = output_base_path / 'posted-on-social-media'
        
        # Check posted-on-social-media folder
        if posted_dir.exists():
            for metadata_file in posted_dir.glob('*_metadata.json'):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        quote_id = metadata.get('quote_id')
                        if quote_id:
                            posted_ids.add(quote_id)
                except Exception:
                    pass
        
        # Also check feed_posts folder for metadata
        feed_posts_dir = output_base_path / 'feed_posts'
        if feed_posts_dir.exists():
            for metadata_file in feed_posts_dir.glob('*_metadata.json'):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        quote_id = metadata.get('quote_id')
                        if quote_id:
                            posted_ids.add(quote_id)
                except Exception:
                    pass
        
        return posted_ids
    
    def get_quotes_by_group(self, group: str) -> List[Dict]:
        """
        Get all approved quotes from a specific group.
        
        Args:
            group: Group name.
        
        Returns:
            List of quote dictionaries.
        """
        return self.quotes.get(group, [])
    
    def get_all_groups(self) -> List[str]:
        """Get list of all available literature groups with quotes."""
        return list(self.quotes.keys())
    
    def get_quotes_by_source(self, source_name: str) -> List[Dict]:
        """
        Get quotes by source display name.
        
        Args:
            source_name: Display name of the source (e.g., "Bhagavad Gita").
        
        Returns:
            List of quote dictionaries.
        """
        literature_groups = self.config.get('literature_groups', [])
        for group in literature_groups:
            if group.get('display_name') == source_name:
                group_name = group.get('name')
                return self.quotes.get(group_name, [])
        return []
    
    def get_quotes_by_author(self, author: str) -> List[Dict]:
        """
        Get quotes by author name.
        
        Args:
            author: Author name.
        
        Returns:
            List of quote dictionaries.
        """
        all_quotes = []
        literature_groups = self.config.get('literature_groups', [])
        
        for group in literature_groups:
            if group.get('author') == author:
                group_name = group.get('name')
                all_quotes.extend(self.quotes.get(group_name, []))
        
        return all_quotes
    
    def search_quotes(self, keyword: str) -> List[Dict]:
        """
        Search quotes by keyword.
        
        Args:
            keyword: Keyword to search for.
        
        Returns:
            List of matching quote dictionaries.
        """
        keyword_lower = keyword.lower()
        matching_quotes = []
        
        for quotes_list in self.quotes.values():
            for quote in quotes_list:
                quote_text = quote.get('text', '').lower()
                if keyword_lower in quote_text:
                    matching_quotes.append(quote)
        
        return matching_quotes
    
    def get_quote_text(self, quote: Optional[Dict]) -> str:
        """
        Extract text from a quote dictionary, with fallback.
        
        Args:
            quote: Quote dictionary or None.
        
        Returns:
            Quote text string.
        """
        if quote and isinstance(quote, dict):
            return quote.get('text', '')
        elif isinstance(quote, str):
            return quote
        else:
            return "Yoga is the journey of the self, through the self, to the self."


def main():
    """Test function."""
    generator = QuoteGenerator()
    
    print("Available literature groups:")
    for group in generator.get_all_groups():
        count = len(generator.get_quotes_by_group(group))
        print(f"  - {group}: {count} approved quotes")
    
    print("\nRandom quote:")
    quote = generator.get_random_quote()
    if quote:
        print(f"  Text: {quote.get('text', '')[:100]}...")
        print(f"  Source: {quote.get('source', 'Unknown')}")
        print(f"  Author: {quote.get('author', 'Unknown')}")
    else:
        print("  No approved quotes available. Extract and approve quotes first.")


if __name__ == '__main__':
    main()
