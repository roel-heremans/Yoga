#!/usr/bin/env python3
"""
Quick script to generate a quote card from the yoga quotes collection.
"""

import sys
from pathlib import Path
from src.quote_generator import QuoteGenerator
from src.image_processor import ImageProcessor
from datetime import datetime

def main():
    """Generate a quote card."""
    if len(sys.argv) > 1:
        # Use provided quote
        quote_text = " ".join(sys.argv[1:])
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
