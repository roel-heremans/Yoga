#!/usr/bin/env python3
"""
Quick script to generate a quote card from the yoga quotes collection.
Supports --shorten-quotes to shorten all quote texts in the review pipeline (quotes.json).
"""

import argparse
import json
import sys
from pathlib import Path
from src.quote_generator import QuoteGenerator
from src.image_processor import ImageProcessor
from src.utils import load_config, shorten_quote_for_display
from datetime import datetime


def shorten_all_quotes_in_review():
    """Shorten quote text in all assets/10_knowledge/*/quotes.json so the review UI shows shorter quotes."""
    base = Path(__file__).parent
    knowledge_dir = base / 'assets' / '10_knowledge'
    config = load_config()
    max_len = (config.get('quote_cards') or {}).get('max_display_length', 120)
    if not knowledge_dir.exists():
        print("No assets/10_knowledge directory found.")
        return
    updated = 0
    for group_dir in knowledge_dir.iterdir():
        if not group_dir.is_dir():
            continue
        quotes_file = group_dir / 'quotes.json'
        if not quotes_file.exists():
            continue
        with open(quotes_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        quotes = data.get('quotes', [])
        for quote in quotes:
            if quote.get('text'):
                shortened = shorten_quote_for_display(quote['text'], max_len)
                if shortened != quote['text']:
                    quote['text'] = shortened
                    updated += 1
        with open(quotes_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  {group_dir.name}: {len(quotes)} quotes (max display length {max_len})")
    print(f"Shortened {updated} quote(s) across all groups. Review UI will show shorter text.")


def main():
    """Generate a quote card or shorten existing quotes (--shorten-quotes)."""
    parser = argparse.ArgumentParser(description='Generate quote cards or shorten quotes for review.')
    parser.add_argument('--shorten-quotes', action='store_true',
                        help='Shorten all quote texts in assets/10_knowledge/*/quotes.json (for review UI)')
    parser.add_argument('quote_words', nargs='*', help='Quote text when generating a card (optional)')
    args = parser.parse_args()

    if args.shorten_quotes:
        print("Shortening quote texts for the review process...")
        shorten_all_quotes_in_review()
        return

    if len(args.quote_words) > 0:
        # Use provided quote
        quote_text = " ".join(args.quote_words)
        author = "Yoga Wisdom"
    else:
        # Use random quote
        generator = QuoteGenerator()
        
        # Show available groups
        print("Available literature groups:")
        groups = generator.get_all_groups()
        if groups:
            for i, group in enumerate(groups, 1):
                count = len(generator.get_quotes_by_group(group))
                print(f"  {i}. {group}: {count} approved quotes")
        else:
            print("  No approved quotes found. Extract and approve quotes first.")
            print("  Run: python3 main.py extract-quotes --all")
            return
        
        # Get random quote
        quote_data = generator.get_random_quote(exclude_posted=True)
        
        if not quote_data:
            print("\nNo unused quotes available. All approved quotes have been posted.")
            print("Extract more quotes or approve additional quotes in the JSON files.")
            return
        
        quote_text = quote_data.get('text', '')
        author = quote_data.get('author') or quote_data.get('source', 'Yoga Wisdom')
        
        print(f"\nSelected quote:")
        print(f"  Text: {quote_text[:100]}...")
        print(f"  Source: {quote_data.get('source', 'Unknown')}")
        print(f"  Author: {author}")
        print(f"  ID: {quote_data.get('id', 'Unknown')}")
    
    # Generate quote card
    processor = ImageProcessor()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(__file__).parent / 'output' / 'feed_posts' / f'quote_{timestamp}.jpg'
    
    print(f"\nGenerating quote card...")
    result_path = processor.create_quote_card(
        quote=quote_text,
        author=author,
        output_path=output_path
    )
    
    print(f"✓ Quote card created: {result_path}")
    print(f"\nReady to post on social media!")
    print(f"\nAfter posting, move the files to output/posted-on-social-media/ to track usage:")
    print(f"  - {result_path.name}")
    print(f"  - {result_path.stem}_metadata.json (if generated)")

if __name__ == '__main__':
    main()
