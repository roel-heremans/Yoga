"""
Brand Extractor Module

Extracts brand colors, fonts, and styling from realhealthkombucha.com
and saves them to the configuration file.
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import yaml
from pathlib import Path


class BrandExtractor:
    """Extract brand identity from website."""
    
    def __init__(self, website_url: str = "https://www.realhealthkombucha.com/"):
        self.website_url = website_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_website(self) -> Optional[str]:
        """Fetch website HTML content."""
        try:
            response = self.session.get(self.website_url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching website: {e}")
            return None
    
    def extract_css_colors(self, html: str) -> Dict[str, str]:
        """Extract color values from CSS in HTML."""
        colors = {
            'primary': None,
            'secondary': None,
            'accent': None,
            'text': None,
            'background': None
        }
        
        # Find all style tags and inline styles
        soup = BeautifulSoup(html, 'lxml')
        style_tags = soup.find_all('style')
        inline_styles = soup.find_all(style=True)
        
        all_css = []
        for tag in style_tags:
            if tag.string:
                all_css.append(tag.string)
        for tag in inline_styles:
            if tag.get('style'):
                all_css.append(tag['style'])
        
        # Extract hex colors
        hex_pattern = r'#([0-9a-fA-F]{3,6})\b'
        rgb_pattern = r'rgb\((\d+),\s*(\d+),\s*(\d+)\)'
        rgba_pattern = r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)'
        
        found_colors = set()
        
        for css in all_css:
            # Find hex colors
            hex_matches = re.findall(hex_pattern, css)
            for match in hex_matches:
                if len(match) == 3:
                    color = f"#{match[0]}{match[0]}{match[1]}{match[1]}{match[2]}{match[2]}"
                else:
                    color = f"#{match}"
                found_colors.add(color.lower())
            
            # Find RGB colors
            rgb_matches = re.findall(rgb_pattern, css)
            for r, g, b in rgb_matches:
                color = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
                found_colors.add(color.lower())
            
            # Find RGBA colors
            rgba_matches = re.findall(rgba_pattern, css)
            for match in rgba_matches:
                # Handle both RGB (3 values) and RGBA (4 values) cases
                if isinstance(match, tuple):
                    if len(match) >= 3:
                        r, g, b = match[0], match[1], match[2]
                        color = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
                        found_colors.add(color.lower())
        
        # Try to identify primary colors by frequency and common patterns
        color_list = list(found_colors)
        
        # Filter out common web colors (white, black, grays)
        filtered_colors = [
            c for c in color_list 
            if c not in ['#ffffff', '#fff', '#000000', '#000', '#f5f5f5', '#fafafa']
            and not (c.startswith('#f') and all(x in '0123456789abcdef' for x in c[1:]))
        ]
        
        # Assign colors (simple heuristic - can be improved)
        if filtered_colors:
            colors['primary'] = filtered_colors[0]
            if len(filtered_colors) > 1:
                colors['secondary'] = filtered_colors[1]
            if len(filtered_colors) > 2:
                colors['accent'] = filtered_colors[2]
        
        # Try to find text and background colors from body/html styles
        body_styles = soup.find_all(['body', 'html'], style=True)
        for tag in body_styles:
            style = tag.get('style', '')
            if 'color' in style:
                match = re.search(r'color:\s*(#[0-9a-fA-F]{3,6}|rgb\([^)]+\))', style)
                if match:
                    colors['text'] = self._normalize_color(match.group(1))
            if 'background' in style:
                match = re.search(r'background(?:-color)?:\s*(#[0-9a-fA-F]{3,6}|rgb\([^)]+\))', style)
                if match:
                    colors['background'] = self._normalize_color(match.group(1))
        
        # Set defaults if not found
        if not colors['text']:
            colors['text'] = '#000000'
        if not colors['background']:
            colors['background'] = '#ffffff'
        
        return colors
    
    def _normalize_color(self, color: str) -> str:
        """Normalize color format to hex."""
        if color.startswith('#'):
            if len(color) == 4:
                return f"#{color[1]*2}{color[2]*2}{color[3]*2}"
            return color.lower()
        elif color.startswith('rgb'):
            # Extract RGB values
            match = re.search(r'(\d+),\s*(\d+),\s*(\d+)', color)
            if match:
                r, g, b = match.groups()
                return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
        return color
    
    def extract_fonts(self, html: str) -> Dict[str, str]:
        """Extract font families from HTML/CSS."""
        fonts = {
            'heading': None,
            'body': None,
            'weights': {
                'heading': 'bold',
                'body': 'normal'
            }
        }
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Find all style tags
        style_tags = soup.find_all('style')
        all_css = [tag.string for tag in style_tags if tag.string]
        
        # Common font patterns
        font_pattern = r'font-family:\s*([^;]+)'
        font_weight_pattern = r'font-weight:\s*([^;]+)'
        
        found_fonts = []
        
        for css in all_css:
            # Extract font families
            matches = re.findall(font_pattern, css, re.IGNORECASE)
            for match in matches:
                # Clean up font names (remove quotes, take first font)
                font = match.strip().strip('"\'')
                if ',' in font:
                    font = font.split(',')[0].strip()
                # Remove CSS variables and invalid characters
                font = re.sub(r'var\([^)]+\)', '', font)
                font = re.sub(r'--[a-zA-Z0-9-]+', '', font)
                font = re.sub(r'[{}:;]', '', font)
                font = font.strip()
                # Only add if it's a valid font name (not empty, no special chars, reasonable length)
                if font and len(font) < 50 and font not in found_fonts and not font.startswith('rgb'):
                    # Filter out common generic fonts that are too generic
                    if font.lower() not in ['inherit', 'initial', 'unset']:
                        found_fonts.append(font)
            
            # Extract font weights for headings
            if 'h1' in css or 'h2' in css or 'heading' in css.lower():
                weight_match = re.search(font_weight_pattern, css, re.IGNORECASE)
                if weight_match:
                    weight = weight_match.group(1).strip()
                    if 'bold' in weight.lower() or weight.isdigit() and int(weight) >= 600:
                        fonts['weights']['heading'] = 'bold'
        
        # Filter and clean found fonts - remove invalid ones
        valid_fonts = []
        for font in found_fonts:
            # Check if font name is valid (no special chars, reasonable length, not CSS code)
            if (font and 
                len(font) < 50 and 
                len(font) > 0 and
                not font.startswith('rgb') and
                not font.startswith('var(') and
                not '{' in font and
                not '}' in font and
                not '--' in font and
                font.replace(' ', '').replace('-', '').isalnum()):
                valid_fonts.append(font)
        
        # Assign fonts
        if valid_fonts:
            fonts['heading'] = valid_fonts[0]
            fonts['body'] = valid_fonts[0] if len(valid_fonts) == 1 else valid_fonts[-1]
        
        # Default fonts if not found or invalid
        if not fonts['heading'] or not fonts['heading'].replace(' ', '').replace('-', '').isalnum():
            fonts['heading'] = 'Arial'
        if not fonts['body'] or not fonts['body'].replace(' ', '').replace('-', '').isalnum():
            fonts['body'] = 'Arial'
        
        return fonts
    
    def extract_brand_info(self) -> Dict:
        """Extract all brand information."""
        html = self.fetch_website()
        if not html:
            print("Warning: Could not fetch website. Using defaults.")
            return self._default_brand_info()
        
        colors = self.extract_css_colors(html)
        fonts = self.extract_fonts(html)
        
        # Try to extract brand name from title or h1
        soup = BeautifulSoup(html, 'lxml')
        title_tag = soup.find('title')
        brand_name = "Real Health Kombucha"
        if title_tag:
            title_text = title_tag.get_text()
            if 'kombucha' in title_text.lower():
                brand_name = title_text.strip()
        
        return {
            'name': brand_name,
            'website': self.website_url,
            'colors': colors,
            'fonts': fonts
        }
    
    def _default_brand_info(self) -> Dict:
        """Return default brand info if extraction fails."""
        return {
            'name': 'Real Health Kombucha',
            'website': 'https://www.realhealthkombucha.com/',
            'colors': {
                'primary': '#1a5f3f',
                'secondary': '#8bc34a',
                'accent': '#4caf50',
                'text': '#333333',
                'background': '#ffffff'
            },
            'fonts': {
                'heading': 'Arial',
                'body': 'Arial',
                'weights': {
                    'heading': 'bold',
                    'body': 'normal'
                }
            }
        }
    
    def save_to_config(self, config_path: Path, brand_info: Dict):
        """Save brand info to YAML config file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config if it exists
        config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
        
        # Update brand section
        config['brand'] = brand_info
        
        # Save config
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"Brand information saved to {config_path}")


def main():
    """Main function to run brand extraction."""
    extractor = BrandExtractor()
    print(f"Extracting brand information from {extractor.website_url}...")
    
    brand_info = extractor.extract_brand_info()
    
    print("\nExtracted Brand Information:")
    print(f"  Name: {brand_info['name']}")
    print(f"  Colors:")
    for key, value in brand_info['colors'].items():
        print(f"    {key}: {value}")
    print(f"  Fonts:")
    print(f"    Heading: {brand_info['fonts']['heading']}")
    print(f"    Body: {brand_info['fonts']['body']}")
    
    # Save to config
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
    extractor.save_to_config(config_path, brand_info)
    
    print("\nBrand extraction complete!")


if __name__ == '__main__':
    main()
