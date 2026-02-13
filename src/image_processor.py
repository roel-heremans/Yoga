"""
Image Processor Module

Creates Instagram feed posts with text overlays, brand colors, and optimized dimensions.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Optional, Tuple, Dict
import textwrap
import re
from .utils import load_config, get_brand_colors, get_brand_fonts


class ImageProcessor:
    """Process images for Instagram feed posts."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize image processor.
        
        Args:
            config: Configuration dictionary. If None, loads from file.
        """
        if config is None:
            config = load_config()
        
        self.config = config
        self.brand_colors = get_brand_colors(config)
        self.brand_fonts = get_brand_fonts(config)
        
        # Instagram dimensions
        instagram_config = config.get('instagram', {})
        feed_dims = instagram_config.get('feed_dimensions', {})
        self.feed_width = feed_dims.get('width', 1080)
        self.feed_height = feed_dims.get('height', 1080)
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def load_font(self, font_name: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """
        Load font with fallback options.
        
        Args:
            font_name: Name of the font.
            size: Font size.
            bold: Whether to use bold weight.
        
        Returns:
            PIL Font object.
        """
        # Clean font name - remove invalid characters and CSS variables
        if font_name:
            font_name = re.sub(r'var\([^)]+\)', '', font_name)
            font_name = re.sub(r'--[a-zA-Z0-9-]+', '', font_name)
            font_name = re.sub(r'[{}:;]', '', font_name)
            font_name = font_name.strip()
            # Extract first valid font name if comma-separated
            if ',' in font_name:
                font_name = font_name.split(',')[0].strip()
        
        # Validate font name - if invalid, use default
        if (not font_name or 
            len(font_name) > 50 or 
            '{' in font_name or 
            '}' in font_name or 
            font_name.startswith('rgb') or
            'placeholder' in font_name.lower() or
            'var(' in font_name.lower()):
            font_name = 'Arial'
        
        try:
            # Try to load the specified font
            if bold:
                font_paths = [
                    f"/usr/share/fonts/truetype/{font_name.lower()}-bold.ttf",
                    f"/usr/share/fonts/truetype/{font_name.lower()}-Bold.ttf",
                    f"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    f"/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                    f"/System/Library/Fonts/{font_name}.ttc",
                ]
            else:
                font_paths = [
                    f"/usr/share/fonts/truetype/{font_name.lower()}.ttf",
                    f"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    f"/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    f"/System/Library/Fonts/{font_name}.ttc",
                ]
            
            for font_path in font_paths:
                if Path(font_path).exists():
                    return ImageFont.truetype(font_path, size)
            
            # Try common system fonts
            common_fonts = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/TTF/DejaVuSans.ttf",
            ]
            
            for font_path in common_fonts:
                if Path(font_path).exists():
                    return ImageFont.truetype(font_path, size)
            
            # Last resort: use a scalable default font
            # ImageFont.load_default() doesn't scale, so we'll try to find any truetype font
            # Search in common font directories
            font_dirs = [
                "/usr/share/fonts/truetype/dejavu",
                "/usr/share/fonts/truetype/liberation",
                "/usr/share/fonts/TTF",
                "/System/Library/Fonts",
            ]
            
            for font_dir in font_dirs:
                font_dir_path = Path(font_dir)
                if font_dir_path.exists():
                    # Look for any .ttf file
                    ttf_files = list(font_dir_path.glob("*.ttf"))
                    if ttf_files:
                        return ImageFont.truetype(str(ttf_files[0]), size)
            
            # If all else fails, use default but warn
            print(f"Warning: Could not load scalable font, using default (size may not be accurate)")
            return ImageFont.load_default()
        
        except Exception as e:
            print(f"Warning: Font loading error: {e}, using default")
            return ImageFont.load_default()
    
    def create_text_overlay(
        self,
        image: Image.Image,
        text: str,
        position: str = 'bottom',
        max_width: Optional[int] = None,
        font_size: int = 20,
        padding: int = 40,
        left_padding: Optional[int] = None
    ) -> Image.Image:
        """
        Add text overlay to image.
        
        Args:
            image: PIL Image object.
            text: Text to overlay.
            position: Position of text ('top', 'center', 'bottom').
            max_width: Maximum width for text wrapping.
            font_size: Font size.
            padding: Padding from edges.
        
        Returns:
            Image with text overlay.
        """
        # Set left padding - use provided value or default to larger value for right alignment
        if left_padding is None:
            left_padding = padding * 3  # Default to 3x padding for more right positioning
        else:
            left_padding = left_padding
        
        if max_width is None:
            # Since we're centering text, use full width minus padding on both sides
            # Add extra safety margin to prevent text from being cut off at edges
            # Font rendering can have margins and kerning, so we need very conservative padding
            # Use 80px total safety margin (40px on each side) to ensure no cutoff
            max_width = image.width - (padding * 2) - 80  # Extra 80px safety margin for font rendering
        
        # Load font - ensure we get a scalable font for proper sizing
        font = self.load_font(
            self.brand_fonts.get('heading', 'Arial'),
            font_size,
            bold=True
        )
        
        # Verify font size is being applied (for debugging)
        # If using default font, it won't scale properly
        if hasattr(font, 'size') and font.size != font_size:
            # Try to reload with explicit size if possible
            pass
        
        # Split text by sentences and commas first, then wrap if needed
        wrapped_lines = []
        
        # First, split by commas (but keep the comma with the preceding part)
        # This creates natural breaks for phrases
        comma_split = re.split(r'(,\s*)', text)
        # Recombine commas with their preceding text
        comma_parts = []
        for i in range(0, len(comma_split) - 1, 2):
            if i + 1 < len(comma_split):
                comma_parts.append(comma_split[i] + comma_split[i + 1])
            else:
                comma_parts.append(comma_split[i])
        if len(comma_split) % 2 == 1:
            comma_parts.append(comma_split[-1])
        
        # Now split each comma-separated part by sentence boundaries
        all_parts = []
        for part in comma_parts:
            # Split by sentence boundaries (periods, exclamation, question marks)
            sentence_pattern = r'([^.!?]+[.!?]+(?:\s+|$))'
            sentences = re.findall(sentence_pattern, part)
            
            if sentences:
                all_parts.extend(sentences)
            else:
                # If no sentence boundaries, check if this part ends with a period
                if part.strip().endswith('.'):
                    all_parts.append(part)
                else:
                    # Split by periods only
                    period_split = re.split(r'(\.\s+)', part)
                    combined = []
                    for i in range(0, len(period_split) - 1, 2):
                        if i + 1 < len(period_split):
                            combined.append(period_split[i] + period_split[i + 1])
                        else:
                            combined.append(period_split[i])
                    if len(period_split) % 2 == 1:
                        combined.append(period_split[-1])
                    all_parts.extend([c for c in combined if c.strip()])
        
        # Filter out empty parts and strip whitespace
        all_parts = [s.strip() for s in all_parts if s.strip()]
        
        # If still no parts found, use original text
        if not all_parts:
            all_parts = [text]
        
        # Use all_parts as sentences for wrapping
        sentences = all_parts
        
        # Create draw object for measuring text width
        # We'll create a temporary draw object for measurements
        temp_img = Image.new('RGB', (image.width, image.height))
        draw = ImageDraw.Draw(temp_img)
        
        # Wrap each sentence using actual pixel width measurements
        # This ensures text fits properly within the image width
        for sentence in sentences:
            # Use binary search approach to find the right character count per line
            # that fits within max_width pixels
            words = sentence.split()
            if not words:
                continue
            
            current_line = []
            for word in words:
                # Test if adding this word would exceed max_width
                # Use a more conservative max_width during wrapping (subtract 20px for safety)
                safe_max_width = max_width - 20  # Extra 20px safety during wrapping
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                test_width = bbox[2] - bbox[0]
                
                if test_width <= safe_max_width:
                    # Word fits, add it to current line
                    current_line.append(word)
                else:
                    # Word doesn't fit, save current line and start new one
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    # If single word is too long, we need to break it
                    if len(word) > 0:
                        # Check if word itself exceeds max_width (use safe_max_width)
                        word_bbox = draw.textbbox((0, 0), word, font=font)
                        word_width = word_bbox[2] - word_bbox[0]
                        if word_width > safe_max_width:
                            # Word is too long, break it character by character
                            chars = list(word)
                            temp_word = ''
                            for char in chars:
                                test_char = temp_word + char
                                char_bbox = draw.textbbox((0, 0), test_char, font=font)
                                char_width = char_bbox[2] - char_bbox[0]
                                if char_width <= safe_max_width:
                                    temp_word = test_char
                                else:
                                    if temp_word:
                                        wrapped_lines.append(temp_word)
                                    temp_word = char
                            if temp_word:
                                current_line = [temp_word]
                            else:
                                current_line = []
                        else:
                            current_line = [word]
                    else:
                        current_line = []
            
            # Add remaining line
            if current_line:
                wrapped_lines.append(' '.join(current_line))
        
        # Verify all lines fit within max_width and recalculate dimensions
        line_heights = []
        verified_lines = []
        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            
            # If line exceeds max_width (with safety margin), try to break it further
            # Use even more conservative check here
            if line_width > (max_width - 30):  # 30px safety margin for verification
                # Break the line more aggressively
                words = line.split()
                if len(words) > 1:
                    # Try splitting in half
                    mid = len(words) // 2
                    first_half = ' '.join(words[:mid])
                    second_half = ' '.join(words[mid:])
                    verified_lines.append(first_half)
                    verified_lines.append(second_half)
                    # Calculate heights for both halves
                    bbox1 = draw.textbbox((0, 0), first_half, font=font)
                    bbox2 = draw.textbbox((0, 0), second_half, font=font)
                    line_heights.append(bbox1[3] - bbox1[1])
                    line_heights.append(bbox2[3] - bbox2[1])
                else:
                    # Single word that's too long - keep it but warn
                    verified_lines.append(line)
                    line_heights.append(line_height)
            else:
                verified_lines.append(line)
                line_heights.append(line_height)
        
        wrapped_lines = verified_lines
        
        total_height = sum(line_heights) + (len(wrapped_lines) - 1) * 10
        
        # Calculate position
        if position == 'top':
            y_start = padding
        elif position == 'center':
            y_start = (image.height - total_height) // 2
        else:  # bottom
            y_start = image.height - total_height - padding
        
        # Create semi-transparent background for text
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        text_color = self.hex_to_rgb(self.brand_colors.get('text', '#000000'))
        bg_color = self.hex_to_rgb(self.brand_colors.get('background', '#ffffff'))
        
        # Draw background rectangle - center it horizontally with bounds checking
        rect_y1 = max(0, y_start - padding // 2)
        rect_y2 = min(image.height, y_start + total_height + padding // 2)
        # Calculate max line width to center the background rectangle
        max_line_width = 0
        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            max_line_width = max(max_line_width, line_width)
        
        # Ensure background rectangle stays within bounds
        rect_x1 = max(padding, (image.width - max_line_width) // 2 - padding)
        rect_x2 = min(image.width - padding, (image.width + max_line_width) // 2 + padding)
        
        # Ensure rectangle is at least as wide as the text area
        if rect_x2 - rect_x1 < max_line_width + (padding * 2):
            rect_x1 = max(padding, (image.width - max_line_width) // 2 - padding)
            rect_x2 = min(image.width - padding, rect_x1 + max_line_width + (padding * 2))
        overlay_draw.rectangle(
            [(rect_x1, rect_y1), (rect_x2, rect_y2)],
            fill=(*bg_color, 200)  # Semi-transparent
        )
        
        # Draw text - center each line horizontally with strict bounds checking
        # Use very conservative padding to account for font rendering margins and kerning
        y_offset = y_start
        # Very generous padding to prevent any character cutoff
        # Font rendering can have up to 5-10px margin per side, plus kerning
        min_x_padding = padding + 50  # Minimum padding from left edge (50px safety)
        max_x_padding = image.width - padding - 50  # Maximum x position (50px safety)
        
        for i, line in enumerate(wrapped_lines):
            # Calculate text width - add generous safety margin for font rendering
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            # Add larger safety margin to measured width (fonts can render wider due to kerning/margins)
            line_width_with_margin = line_width + 10  # 10px safety margin for font rendering/kerning
            
            x = (image.width - line_width_with_margin) // 2  # Center horizontally
            
            # Strict bounds checking - ensure text stays well within bounds
            # Check if text would extend beyond left edge
            if x < min_x_padding:
                x = min_x_padding
            # Check if text would extend beyond right edge (using margin-adjusted width)
            if x + line_width_with_margin > max_x_padding:
                x = max_x_padding - line_width_with_margin
                # If still too wide, we need to break it further
                if x < min_x_padding:
                    x = min_x_padding
                    # Calculate available width with generous safety margins
                    available_width = max_x_padding - min_x_padding - 20  # Extra 20px safety
                    # Truncate line if absolutely necessary (last resort)
                    if line_width > available_width:
                        # Measure character by character to fit within available width
                        chars = list(line)
                        fitting_chars = []
                        test_text = ''
                        for char in chars:
                            test_text += char
                            test_bbox = draw.textbbox((0, 0), test_text, font=font)
                            test_width = test_bbox[2] - test_bbox[0] + 10  # Add margin
                            if test_width <= available_width:
                                fitting_chars.append(char)
                            else:
                                break
                        line = ''.join(fitting_chars) + '...' if len(fitting_chars) < len(chars) else ''.join(fitting_chars)
                        # Recalculate width
                        bbox = draw.textbbox((0, 0), line, font=font)
                        line_width = bbox[2] - bbox[0]
                        line_width_with_margin = line_width + 10
                        x = min_x_padding
            
            # Final strict bounds check before drawing - absolute minimums
            absolute_min_x = 50  # Absolute minimum from left edge
            absolute_max_x = image.width - 50  # Absolute minimum from right edge
            
            if x < absolute_min_x:
                x = absolute_min_x
            if x + line_width_with_margin > absolute_max_x:
                x = absolute_max_x - line_width_with_margin
                # If still doesn't fit, reduce line further
                if x < absolute_min_x:
                    x = absolute_min_x
                    # Re-measure and truncate if needed
                    available = absolute_max_x - absolute_min_x - 20
                    if line_width > available:
                        # Truncate more aggressively
                        bbox = draw.textbbox((0, 0), line[:len(line)//2], font=font)
                        half_width = bbox[2] - bbox[0] + 10
                        if half_width <= available:
                            line = line[:len(line)//2] + '...'
                            bbox = draw.textbbox((0, 0), line, font=font)
                            line_width = bbox[2] - bbox[0]
                            line_width_with_margin = line_width + 10
            
            overlay_draw.text((x, y_offset), line, font=font, fill=(*text_color, 255))
            y_offset += line_heights[i] + 10
        
        # Composite overlay onto image
        image = Image.alpha_composite(image.convert('RGBA'), overlay)
        return image.convert('RGB')
    
    def process_image(
        self,
        image_path: Path,
        output_path: Path,
        text_overlay: Optional[str] = None,
        text_position: str = 'bottom',
        font_size: int = 20
    ) -> Path:
        """
        Process an image for Instagram feed post.
        
        Args:
            image_path: Path to source image.
            output_path: Path to save processed image.
            text_overlay: Optional text to overlay on image.
            text_position: Position of text overlay.
        
        Returns:
            Path to saved image.
        """
        # Open and resize image
        img = Image.open(image_path)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize to Instagram feed dimensions (maintain aspect ratio, crop if needed)
        img.thumbnail((self.feed_width, self.feed_height), Image.Resampling.LANCZOS)
        
        # Create new image with exact dimensions
        new_img = Image.new('RGB', (self.feed_width, self.feed_height), 
                           self.hex_to_rgb(self.brand_colors.get('background', '#ffffff')))
        
        # Center the image
        x_offset = (self.feed_width - img.width) // 2
        y_offset = (self.feed_height - img.height) // 2
        new_img.paste(img, (x_offset, y_offset))
        
        # Add text overlay if provided
        if text_overlay:
            # Use larger left padding to position text more to the right
            new_img = self.create_text_overlay(
                new_img, 
                text_overlay, 
                text_position, 
                font_size=font_size,
                left_padding=120  # Start text more to the right
            )
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        new_img.save(output_path, 'JPEG', quality=95)
        
        return output_path
    
    def create_quote_card(
        self,
        quote: str,
        author: Optional[str] = None,
        output_path: Path = None
    ) -> Path:
        """
        Create a quote card image with yoga-appropriate styling.
        
        Args:
            quote: Quote text.
            author: Optional author name or source (e.g., "B.K.S. Iyengar" or "Bhagavad Gita").
            output_path: Path to save the image.
        
        Returns:
            Path to saved image.
        """
        if output_path is None:
            output_path = Path(__file__).parent.parent / 'output' / 'feed_posts' / 'quote_card.jpg'
        
        # Create image with yoga-appropriate background
        bg_color = self.hex_to_rgb(self.brand_colors.get('background', '#ffffff'))
        img = Image.new('RGB', (self.feed_width, self.feed_height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        quote_font = self.load_font(
            self.brand_fonts.get('heading', 'Arial'),
            60,
            bold=True
        )
        author_font = self.load_font(
            self.brand_fonts.get('body', 'Arial'),
            36,
            bold=False
        )
        
        # Wrap quote text - use better wrapping for longer quotes
        max_width = self.feed_width - 160
        # Use textwrap with better width calculation
        avg_char_width = 30  # Approximate character width for font size 60
        wrap_width = max_width // avg_char_width
        wrapped_quote = textwrap.wrap(quote, width=wrap_width)
        
        # Calculate positions with proper line height
        line_heights = []
        for line in wrapped_quote:
            bbox = draw.textbbox((0, 0), line, font=quote_font)
            line_heights.append(bbox[3] - bbox[1])
        
        quote_height = sum(line_heights) + (len(wrapped_quote) - 1) * 20
        
        if author:
            author_bbox = draw.textbbox((0, 0), f"— {author}", font=author_font)
            author_height = author_bbox[3] - author_bbox[1]
            total_height = quote_height + author_height + 40
        else:
            total_height = quote_height
        
        start_y = (self.feed_height - total_height) // 2
        
        # Draw quote with yoga-appropriate colors
        text_color = self.hex_to_rgb(self.brand_colors.get('text', '#2c2c2c'))
        primary_color = self.hex_to_rgb(self.brand_colors.get('primary', '#2c5530'))
        
        y_offset = start_y
        for i, line in enumerate(wrapped_quote):
            bbox = draw.textbbox((0, 0), line, font=quote_font)
            line_width = bbox[2] - bbox[0]
            x = (self.feed_width - line_width) // 2
            draw.text((x, y_offset), line, font=quote_font, fill=primary_color)
            y_offset += line_heights[i] + 20
        
        # Draw author/source attribution if provided
        if author:
            author_text = f"— {author}"
            author_bbox = draw.textbbox((0, 0), author_text, font=author_font)
            author_width = author_bbox[2] - author_bbox[0]
            author_x = (self.feed_width - author_width) // 2
            draw.text((author_x, y_offset + 20), author_text, font=author_font, fill=text_color)
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, 'JPEG', quality=95)
        
        return output_path


def main():
    """Test function."""
    processor = ImageProcessor()
    
    # Test quote card creation
    quote = "Yoga is the journey of the self, through the self, to the self."
    output = processor.create_quote_card(quote, "Bhagavad Gita")
    print(f"Created quote card: {output}")


if __name__ == '__main__':
    main()
