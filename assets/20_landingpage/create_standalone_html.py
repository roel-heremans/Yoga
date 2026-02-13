#!/usr/bin/env python3
"""
Convert HTML file with relative image paths to standalone HTML with embedded base64 images.
This creates a self-contained HTML file that can be shared without needing separate image files.
"""

import os
import re
import base64
from pathlib import Path

def get_image_base64(image_path):
    """Convert image file to base64 data URI."""
    try:
        with open(image_path, 'rb') as img_file:
            img_data = img_file.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # Determine MIME type from file extension
            ext = image_path.suffix.lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.svg': 'image/svg+xml'
            }
            mime_type = mime_types.get(ext, 'image/jpeg')
            
            return f"data:{mime_type};base64,{img_base64}"
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def create_standalone_html(input_html_path, output_html_path=None):
    """Convert HTML with relative image paths to standalone HTML with embedded images."""
    input_path = Path(input_html_path)
    
    if output_html_path is None:
        output_html_path = input_path.parent / f"{input_path.stem}_standalone{input_path.suffix}"
    else:
        output_html_path = Path(output_html_path)
    
    # Read the HTML file
    with open(input_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Find all image src attributes
    # Pattern: src="graphics/filename.jpg" or src='graphics/filename.jpg'
    pattern = r'src=["\'](graphics/[^"\']+)["\']'
    
    def replace_with_base64(match):
        relative_path = match.group(1)
        # Construct full path relative to HTML file location
        image_path = input_path.parent / relative_path
        
        if image_path.exists():
            print(f"Processing: {relative_path}")
            base64_data = get_image_base64(image_path)
            if base64_data:
                return f'src="{base64_data}"'
            else:
                return match.group(0)  # Keep original if conversion fails
        else:
            print(f"Warning: Image not found: {image_path}")
            return match.group(0)  # Keep original if file doesn't exist
    
    # Replace all image src attributes with base64 data URIs
    html_content = re.sub(pattern, replace_with_base64, html_content)
    
    # Write the standalone HTML file
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✓ Standalone HTML created: {output_html_path}")
    print(f"  File size: {output_html_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"\nYou can now share this single HTML file - all images are embedded!")

if __name__ == '__main__':
    # Paths
    script_dir = Path(__file__).parent
    input_html = script_dir / 'sattva-reset-final-v5.html'
    output_html = script_dir / 'sattva-reset-final-v5-standalone.html'
    
    if not input_html.exists():
        print(f"Error: Input file not found: {input_html}")
        exit(1)
    
    create_standalone_html(input_html, output_html)
