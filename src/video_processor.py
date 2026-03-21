"""
Video Processor Module

Creates Instagram Reels with clips, music, text overlays, and transitions.
"""

try:
    from moviepy import VideoFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, ImageClip, AudioFileClip, concatenate_audioclips, ColorClip, VideoClip
except ImportError:
    # Fallback for older moviepy versions
    try:
        from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, ImageClip, AudioFileClip, concatenate_audioclips, ColorClip, VideoClip
    except ImportError:
        raise ImportError("moviepy is not installed. Please install it with: pip install moviepy")
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import textwrap
import tempfile
import os
import numpy as np
from PIL import Image, ImageOps
from .utils import load_config, get_brand_colors, get_brand_fonts


class VideoProcessor:
    """Process videos for Instagram Reels."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize video processor.
        
        Args:
            config: Configuration dictionary. If None, loads from file.
        """
        if config is None:
            config = load_config()
        
        self.config = config
        self.assets_base_path = Path(__file__).parent.parent / 'assets'
        self.brand_colors = get_brand_colors(config)
        self.brand_fonts = get_brand_fonts(config)
        
        # Instagram Reel dimensions
        instagram_config = config.get('instagram', {})
        reel_dims = instagram_config.get('reel_dimensions', {})
        self.reel_width = reel_dims.get('width', 1080)
        self.reel_height = reel_dims.get('height', 1920)
        
        reel_duration = instagram_config.get('reel_duration', {})
        self.min_duration = reel_duration.get('min', 15)
        self.max_duration = reel_duration.get('max', 90)
        
        # Configure MoviePy to use system temp directory instead of current working directory
        # This prevents temporary files from being created in the project root
        try:
            import moviepy.config
            # Set MoviePy's temporary directory to system temp
            temp_dir = tempfile.gettempdir()
            os.environ['MOVIEPY_TEMP_DIR'] = temp_dir
            # Also try setting it via config if available
            if hasattr(moviepy.config, 'TEMP_DIR'):
                moviepy.config.TEMP_DIR = temp_dir
        except Exception:
            # If setting temp dir fails, continue anyway
            pass
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def prepare_clip(
        self,
        video_path: Path,
        duration: Optional[float] = None,
        start_time: float = 0
    ) -> VideoFileClip:
        """
        Load and prepare a video clip.
        
        Args:
            video_path: Path to video file.
            duration: Duration to extract. If None, uses full clip.
            start_time: Start time in seconds.
        
        Returns:
            Prepared VideoFileClip.
        """
        clip = VideoFileClip(str(video_path))
        
        # Extract segment if needed
        if start_time > 0 or duration:
            end_time = start_time + duration if duration else clip.duration
            # Use subclipped for moviepy 2.x, fallback to subclip for older versions
            if hasattr(clip, 'subclipped'):
                clip = clip.subclipped(start_time, min(end_time, clip.duration))
            elif hasattr(clip, 'subclip'):
                clip = clip.subclip(start_time, min(end_time, clip.duration))
            # If neither method exists, just use the full clip
        
        # Resize to fit Reel dimensions (maintain aspect ratio, crop if needed)
        # Use resized for moviepy 2.x, fallback to resize for older versions
        if hasattr(clip, 'resized'):
            clip = clip.resized(height=self.reel_height)
        elif hasattr(clip, 'resize'):
            clip = clip.resize(height=self.reel_height)
        
        # Center crop if width exceeds
        if clip.w > self.reel_width:
            x_center = clip.w / 2
            if hasattr(clip, 'cropped'):
                clip = clip.cropped(x_center=x_center, width=self.reel_width)
            elif hasattr(clip, 'crop'):
                clip = clip.crop(x_center=x_center, width=self.reel_width)
        
        return clip
    
    def calculate_text_duration(self, text: str, min_duration: float = 3.0, max_duration: float = 10.0) -> float:
        """
        Calculate appropriate duration for text based on reading speed.
        
        Args:
            text: Text to display.
            min_duration: Minimum duration in seconds.
            max_duration: Maximum duration in seconds.
        
        Returns:
            Calculated duration in seconds.
        """
        # Count words and characters
        words = len(text.split())
        chars = len(text)
        
        # Reading speed: approximately 2-3 words per second for comfortable reading
        # Also account for character count (longer words need more time)
        # Base calculation: 2.5 words per second + 0.1 seconds per 10 characters
        word_based_duration = words / 2.5
        char_based_duration = chars / 100.0  # 100 chars per second
        
        # Use the longer of the two calculations to ensure readability
        calculated_duration = max(word_based_duration, char_based_duration)
        
        # Add extra time for multi-line text (more lines = more reading time; match wrap width)
        num_lines = len(textwrap.wrap(text, width=60))
        if num_lines > 1:
            calculated_duration += (num_lines - 1) * 0.5
        
        # Ensure duration is within bounds
        duration = max(min_duration, min(calculated_duration, max_duration))

        return duration

    def calculate_scroll_duration(self, text: str) -> float:
        """
        Compute the total video duration needed to teleprompter `text` at a fixed
        reading pace of SCROLL_CHARS_PER_SECOND, plus a fixed author-display tail.

        Args:
            text: Full quote body text (no truncation for scroll style).

        Returns:
            Total duration in seconds.
        """
        reading_time = len(text) / self.SCROLL_CHARS_PER_SECOND
        return reading_time + self.SCROLL_AUTHOR_DISPLAY_SECONDS

    # Quote overlay: dark fill + light stroke + transparent backdrop (aligned with Palheiro / luxury serif)
    QUOTE_OVERLAY_FILL = '#1a1a1a'
    QUOTE_OVERLAY_STROKE = '#e8e8e8'
    QUOTE_OVERLAY_STROKE_WIDTH = 4
    QUOTE_BACKDROP_ALPHA = 160  # 0-255, transparent dark bar behind full text area
    # Font in line with Casa Velha do Palheiro logo (elegant serif); try in order
    # First: often preinstalled on Linux (Liberation, DejaVu). Then optional: Playfair, Lora, Georgia.
    QUOTE_OVERLAY_FONT_CANDIDATES = (
        'Liberation Serif', 'DejaVu Serif', 'Playfair Display', 'Lora',
        'Cormorant Garamond', 'Georgia', 'Arial'
    )
    # Flyer: crisp dark text with subtle stroke on white
    FLYER_FILL = '#1a1a1a'
    FLYER_STROKE = '#b0b0b0'
    FLYER_STROKE_WIDTH = 2

    # Scroll (teleprompter) timing
    SCROLL_CHARS_PER_SECOND = 13       # comfortable on-screen reading pace (~130 wpm)
    SCROLL_AUTHOR_DISPLAY_SECONDS = 2.5

    # Cinematic / reveal quote style constants
    CINEMATIC_QUOTE_COLOR = '#f0ece4'    # cream
    CINEMATIC_AUTHOR_COLOR = '#c9a96e'   # warm gold
    CINEMATIC_DIVIDER_COLOR = '#c9a96e'  # warm gold
    CINEMATIC_VIGNETTE_ALPHA = 120       # 0-255, max darkness at frame edges

    # Shared layout constants for cinematic and reveal
    LINE_HEIGHT_MULT = 1.6   # line_height = font_size * LINE_HEIGHT_MULT
    DIVIDER_GAP = 20         # pixels between last quote line and divider
    AUTHOR_GAP = 12          # pixels between divider and author text
    DIVIDER_WIDTH = 30       # pixels wide
    DIVIDER_HEIGHT = 2       # pixels tall

    def create_text_clip(
        self,
        text: str,
        duration: Optional[float] = None,
        position: str = 'bottom',
        font_size: int = 60,
        start_time: float = 0,
        auto_duration: bool = True,
        text_color_override: Optional[str] = None,
        override_y_center: Optional[float] = None,
        preserve_newlines: bool = False,
        quote_overlay_style: bool = False,
        flyer_style: bool = False,
        skip_position: bool = False
    ) -> TextClip:
        """
        Create a text overlay clip.
        
        Args:
            text: Text to display.
            duration: Duration of text clip. If None and auto_duration=True, calculates based on text length.
            position: Position ('top', 'center', 'bottom').
            font_size: Font size.
            start_time: Start time in seconds.
            auto_duration: If True and duration is None, automatically calculate duration based on text length.
            override_y_center: If set, place text so its vertical center is at this y (e.g. center of letterbox band).
            preserve_newlines: If True, split on '\\n' and wrap each line separately so blank lines are preserved.
            quote_overlay_style: If True, use dark fill + light stroke + semi-transparent backdrop (Canva-style).
            flyer_style: If True, use crisp dark text with subtle stroke for flyer on white.
        
        Returns:
            TextClip or CompositeVideoClip (quote overlay with backdrop).
        """
        # Calculate duration if not provided and auto_duration is enabled
        if duration is None and auto_duration:
            duration = self.calculate_text_duration(text, min_duration=3.0, max_duration=10.0)
        elif duration is None:
            duration = 5.0  # Default fallback
        # Wrap text: derive line length from font size and reel width (smaller font = more chars per line)
        usable_width = self.reel_width - 240  # horizontal padding
        char_width_ratio = 0.55  # typical proportional font: char width ~ 0.55 * font_size
        max_chars_per_line = int(usable_width / (font_size * char_width_ratio))
        max_chars_per_line = int(max_chars_per_line * 1.2)  # 1/5th longer lines
        max_chars_per_line = max(20, min(max_chars_per_line, 145))  # clamp for sanity
        if preserve_newlines:
            # Split by newline, wrap each line (or keep blank lines), rejoin so structure is preserved
            display_lines = []
            for line in text.split('\n'):
                if line.strip() == '':
                    display_lines.append('')
                else:
                    display_lines.extend(textwrap.wrap(line, width=max_chars_per_line))
            display_text = '\n'.join(display_lines)
            wrapped_lines = display_lines
        else:
            wrapped_lines = textwrap.wrap(text, width=max_chars_per_line)
            # Extra line spacing for quote overlay (Canva-style breathing room)
            display_text = '\n\n'.join(wrapped_lines) if quote_overlay_style else '\n'.join(wrapped_lines)
        
        # Calculate position - ensure text fits fully on screen
        # Estimate text height (more spacing for quote overlay)
        num_lines = len(wrapped_lines)
        line_height_mult = 1.65 if quote_overlay_style else 1.5
        estimated_text_height = num_lines * (font_size * line_height_mult)
        
        if override_y_center is not None:
            # Place text so its vertical center is at override_y_center (e.g. center of letterbox area)
            y_pos = int(override_y_center - estimated_text_height / 2)
            y_pos = max(20, min(y_pos, self.reel_height - estimated_text_height - 20))
        elif position == 'top':
            y_pos = 150  # More space from top to ensure text isn't cut off
        elif position == 'center':
            # Center vertically accounting for text height
            y_pos = (self.reel_height - estimated_text_height) // 2
            # Ensure it doesn't go off screen
            y_pos = max(100, min(y_pos, self.reel_height - estimated_text_height - 100))
        else:  # bottom
            # Leave more space from bottom to ensure text isn't cut off
            y_pos = int(self.reel_height - estimated_text_height - 200)
            # Ensure it doesn't go off screen
            y_pos = max(100, y_pos)
        
        # Text fill and stroke: quote overlay, flyer, or brand
        if quote_overlay_style:
            text_fill_color = self.QUOTE_OVERLAY_FILL
            stroke_color = self.QUOTE_OVERLAY_STROKE
            stroke_width = self.QUOTE_OVERLAY_STROKE_WIDTH
        elif flyer_style or text_color_override is not None:
            text_fill_color = self.FLYER_FILL if flyer_style else text_color_override
            stroke_color = self.FLYER_STROKE if flyer_style else '#2c2c2c'
            stroke_width = self.FLYER_STROKE_WIDTH if flyer_style else 2
        else:
            text_fill_color = (
                self.brand_colors.get('primary') or
                self.brand_colors.get('secondary') or
                self.brand_colors.get('text', '#000000')
            )
            stroke_color = '#ffffff'
            stroke_width = 3
        
        # Transparent backdrop over full text area for quote overlay
        backdrop_clip = None
        if quote_overlay_style and y_pos is not None:
            bar_h = int(estimated_text_height) + 120  # full coverage of quote text
            bar_y = max(0, int(y_pos) - 55)
            margin_x = 50  # side margin
            x1, x2 = int(margin_x), int(self.reel_width - margin_x)
            y1, y2 = int(bar_y), int(min(bar_y + bar_h, self.reel_height))
            arr = np.zeros((self.reel_height, self.reel_width, 4), dtype=np.uint8)
            arr[:, :, 3] = 0
            arr[y1:y2, x1:x2, 0] = 0
            arr[y1:y2, x1:x2, 1] = 0
            arr[y1:y2, x1:x2, 2] = 0
            arr[y1:y2, x1:x2, 3] = self.QUOTE_BACKDROP_ALPHA
            try:
                backdrop_clip = ImageClip(arr, transparent=True)
            except TypeError:
                backdrop_clip = ImageClip(arr)
            if hasattr(backdrop_clip, 'with_duration'):
                backdrop_clip = backdrop_clip.with_duration(duration)
            else:
                backdrop_clip = backdrop_clip.set_duration(duration)
            if hasattr(backdrop_clip, 'with_start'):
                backdrop_clip = backdrop_clip.with_start(start_time)
            else:
                backdrop_clip = backdrop_clip.set_start(start_time)
            if hasattr(backdrop_clip, 'with_position'):
                backdrop_clip = backdrop_clip.with_position((0, 0))
            else:
                backdrop_clip = backdrop_clip.set_position((0, 0))
        
        # Get font: for quote overlay use Palheiro-style serif (elegant); otherwise brand heading
        if quote_overlay_style:
            font_name = self.QUOTE_OVERLAY_FONT_CANDIDATES[0]
        else:
            font_name = self.brand_fonts.get('heading', 'Arial')
            if (not font_name or len(font_name) > 50 or '{' in font_name or '}' in font_name or
                font_name.startswith('rgb') or 'placeholder' in font_name.lower() or 'var(' in font_name.lower()):
                font_name = 'Arial'
        
        # Create text clip - moviepy 2.x uses font_size instead of fontsize
        # For quote overlay or flyer try serif font candidates in order
        candidates = (self.QUOTE_OVERLAY_FONT_CANDIDATES if (quote_overlay_style or flyer_style) else (font_name,)) + ('Arial',)
        txt_clip = None
        for fn in candidates:
            if fn == 'Arial' and quote_overlay_style and font_name == 'Arial':
                continue
            try:
                txt_clip = TextClip(
                    text=display_text,
                    font_size=font_size,
                    color=text_fill_color,
                    font=fn,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    size=(self.reel_width - 120, None),
                    margin=(20, 20)
                )
                break
            except (TypeError, OSError, Exception):
                continue
        if txt_clip is None:
            try:
                txt_clip = TextClip(
                    display_text,
                    fontsize=font_size,
                    color=text_fill_color,
                    font='Arial',
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    method='caption',
                    size=(self.reel_width - 120, None),
                    align='center'
                )
            except TypeError:
                txt_clip = TextClip(
                    text=display_text,
                    font_size=font_size,
                    color=text_fill_color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    size=(self.reel_width - 120, None),
                    margin=(20, 20)
                )
        # Set position (unless caller will set it), duration, and start time
        if not skip_position:
            if hasattr(txt_clip, 'with_position'):
                txt_clip = txt_clip.with_position(('center', y_pos))
            else:
                txt_clip = txt_clip.set_position(('center', y_pos))
        
        if hasattr(txt_clip, 'with_duration'):
            txt_clip = txt_clip.with_duration(duration)
        else:
            txt_clip = txt_clip.set_duration(duration)
        
        if hasattr(txt_clip, 'with_start'):
            txt_clip = txt_clip.with_start(start_time)
        else:
            txt_clip = txt_clip.set_start(start_time)
        
        if backdrop_clip is not None:
            composite = CompositeVideoClip([backdrop_clip, txt_clip])
            if hasattr(composite, 'with_duration'):
                composite = composite.with_duration(duration)
            if hasattr(composite, 'with_start'):
                composite = composite.with_start(start_time)
            return composite
        return txt_clip

    def _smart_wrap(self, text: str, max_chars: int) -> list:
        """
        Wrap text at natural phrase boundaries with balanced line lengths.
        Prefers breaking after commas/semicolons or before conjunctions.
        """
        words = text.split()
        if not words:
            return ['']
        total_len = sum(len(w) for w in words) + len(words) - 1
        if total_len <= max_chars:
            return [text]

        CONJUNCTIONS = {
            'and', 'but', 'or', 'nor', 'yet', 'so',
            'that', 'which', 'when', 'as', 'if', 'because',
            'though', 'although', 'while', 'where',
        }
        # natural[i] = True means "breaking after word i is natural"
        natural = set()
        for i, w in enumerate(words[:-1]):
            if w.endswith((',', ';', ':', '—', '...')):
                natural.add(i)
            if words[i + 1].lower() in CONJUNCTIONS:
                natural.add(i)

        n_lines = max(2, (total_len + max_chars - 1) // max_chars)
        target = total_len / n_lines

        lines = []
        start = 0
        while start < len(words):
            remaining_words = len(words) - start
            remaining_lines = max(1, n_lines - len(lines))
            if remaining_lines == 1 or remaining_words <= 1:
                lines.append(' '.join(words[start:]))
                break
            best_i, best_score = None, float('inf')
            cumlen = 0
            for i in range(start, len(words) - 1):
                cumlen += len(words[i]) + (0 if i == start else 1)
                if cumlen < target * 0.5:
                    continue
                score = abs(cumlen - target) + (0 if i in natural else target * 0.4)
                if score < best_score:
                    best_score, best_i = score, i
                if cumlen > target * 1.5:
                    break
            if best_i is None:
                best_i = start + max(1, remaining_words // remaining_lines) - 1
            lines.append(' '.join(words[start:best_i + 1]))
            start = best_i + 1
        return lines if lines else [text]

    def _make_scrim_clip(self, w: int, h: int, duration: float):
        """Top-scrim: black→transparent linear gradient over top 45% of frame."""
        scrim_arr = np.zeros((h, w, 4), dtype=np.uint8)
        scrim_h = int(h * 0.45)
        y_idx = np.arange(scrim_h)
        alphas = (180 * (1 - y_idx / scrim_h)).astype(np.uint8)
        scrim_arr[:scrim_h, :, 3] = alphas[:, np.newaxis]
        try:
            clip = ImageClip(scrim_arr, transparent=True)
        except TypeError:
            clip = ImageClip(scrim_arr)
        clip = (clip.with_duration(duration) if hasattr(clip, 'with_duration')
                else clip.set_duration(duration))
        clip = (clip.with_position((0, 0)) if hasattr(clip, 'with_position')
                else clip.set_position((0, 0)))
        return clip

    def _make_pill_overlay(
        self,
        lines: list,
        font_size: int,
        line_y_positions: list,
        w: int,
        h: int,
        duration: float,
    ):
        """
        Draw a semi-transparent dark rounded-rectangle pill behind each text line.

        Args:
            lines: Text strings, one per line.
            font_size: Point size used for the text (determines pill height).
            line_y_positions: Pixel y-coordinate for the top of each line's text.
            w, h: Frame dimensions in pixels.
            duration: Clip duration in seconds.

        Returns:
            A static ImageClip (RGBA, transparent except for the pills).
        """
        from PIL import Image, ImageDraw
        import numpy as np

        PAD_X = 14      # horizontal padding inside pill
        PAD_Y = 6       # vertical padding inside pill
        RADIUS = 20     # corner radius
        FILL = (0, 0, 0, 128)  # ~50% opacity black

        pil_font = self._load_pil_font(font_size)

        def _measure(txt):
            d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
            try:
                return int(d.textlength(txt, font=pil_font))
            except AttributeError:
                try:
                    return int(pil_font.getlength(txt))
                except AttributeError:
                    return int(pil_font.getsize(txt)[0])

        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        for line, y in zip(lines, line_y_positions):
            tw = _measure(line)
            x0 = (w - tw) // 2 - PAD_X
            y0 = y - PAD_Y
            x1 = (w + tw) // 2 + PAD_X
            y1 = y + font_size + PAD_Y
            try:
                draw.rounded_rectangle([x0, y0, x1, y1], radius=RADIUS, fill=FILL)
            except AttributeError:
                # Pillow < 8.2 does not have rounded_rectangle
                draw.rectangle([x0, y0, x1, y1], fill=FILL)

        arr = np.array(img)
        try:
            clip = ImageClip(arr, transparent=True)
        except TypeError:
            clip = ImageClip(arr)
        clip = (clip.with_duration(duration) if hasattr(clip, 'with_duration')
                else clip.set_duration(duration))
        clip = (clip.with_position((0, 0)) if hasattr(clip, 'with_position')
                else clip.set_position((0, 0)))
        return clip

    def _load_pil_font(self, size: int):
        """Load a PIL TrueType font at the given pixel size.

        Tries common system paths; falls back to PIL's built-in bitmap font
        (which ignores size but always works).
        """
        from PIL import ImageFont
        candidates = [
            # macOS
            '/Library/Fonts/Georgia.ttf',
            '/System/Library/Fonts/Supplemental/Georgia.ttf',
            '/System/Library/Fonts/Times.ttc',
            # Linux
            '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
            '/usr/share/fonts/truetype/fonts-dejavu/DejaVuSerif.ttf',
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except (IOError, OSError):
                continue
        return ImageFont.load_default()

    def create_scroll_clips(
        self,
        text: str,
        author: str,
        duration: float,
        font_size: int = 96,
    ) -> list:
        """
        Teleprompter-style 3-line scroll overlay.

        At any moment the display shows:
          - Top row:    previous line, all words bright/cream (past — already read)
          - Middle row: current line, read words bright/cream, active word gold, unread words dim
          - Bottom row: next line, all words dim (future — not yet reached)

        Lines outside the 3-line window are hidden. After all words are shown, the
        author name appears centered in gold for the last ~2.5 s of the clip.

        Returns a list of transparent overlay clips to composite over the background.
        """
        import numpy as np

        w, h = self.reel_width, self.reel_height

        # ---- Text wrapping ----
        char_width_ratio = 0.55
        usable_width = w - 120
        max_chars = max(20, int(usable_width / (font_size * char_width_ratio) * 1.2))
        wrapped_lines = self._smart_wrap(text, max_chars)
        words_per_line = [line.split() for line in wrapped_lines if line.strip()]

        # Flat word list: each entry is (line_idx, word_idx_within_line)
        flat_words = [
            (li, wi)
            for li, words in enumerate(words_per_line)
            for wi in range(len(words))
        ]
        n_words = max(1, len(flat_words))

        # ---- Timing ----
        # Duration is derived from text length at a fixed chars/sec rate.
        # Ignore the passed-in duration; compute from text instead so speed never changes.
        computed_duration = self.calculate_scroll_duration(text)
        author_display_start = computed_duration - self.SCROLL_AUTHOR_DISPLAY_SECONDS
        # Each word gets equal time; floor at 0.3 s to avoid imperceptibly fast flashes.
        word_dt = max(0.3, author_display_start / n_words)

        # ---- Layout ----
        line_height = int(font_size * self.LINE_HEIGHT_MULT)
        block_top = h // 8
        # Row offsets: past=-1 (top), current=0 (middle), future=+1 (bottom)
        # Visible rows are at block_top, block_top+line_height, block_top+2*line_height

        # ---- Colours ----
        cream_rgb = self.hex_to_rgb(self.CINEMATIC_QUOTE_COLOR)    # (#f0ece4)
        gold_rgb  = self.hex_to_rgb(self.CINEMATIC_AUTHOR_COLOR)   # (#c9a96e)
        BRIGHT = 255
        DIM    = 80

        # ---- Pre-load fonts ----
        pil_font   = self._load_pil_font(font_size)
        author_font = self._load_pil_font(max(28, font_size // 2))

        # ---- Measure helper (handles Pillow API differences) ----
        def _measure(fnt, txt: str) -> int:
            from PIL import ImageDraw, Image
            d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
            try:
                return int(d.textlength(txt, font=fnt))
            except AttributeError:
                try:
                    return int(fnt.getlength(txt))
                except AttributeError:
                    return int(fnt.getsize(txt)[0])

        # Pre-compute word widths to avoid per-frame PIL allocations
        word_widths = {}
        all_words_flat = [wd for line in words_per_line for wd in line]
        for wd in set(all_words_flat):
            word_widths[wd] = _measure(pil_font, wd + ' ')

        # ---- Pill drawing helper ----
        _PILL_PAD_X = 14
        _PILL_PAD_Y = 6
        _PILL_RADIUS = 20
        _PILL_FILL = (0, 0, 0, 128)  # ~50% opacity black

        def _draw_pill(draw, center_x, text_w, y, fs):
            """Draw a rounded-rectangle pill behind a text line."""
            x0 = center_x - text_w // 2 - _PILL_PAD_X
            y0 = y - _PILL_PAD_Y
            x1 = center_x + text_w // 2 + _PILL_PAD_X + (text_w % 2)
            y1 = y + fs + _PILL_PAD_Y
            try:
                draw.rounded_rectangle([x0, y0, x1, y1], radius=_PILL_RADIUS, fill=_PILL_FILL)
            except AttributeError:
                draw.rectangle([x0, y0, x1, y1], fill=_PILL_FILL)

        # ---- Per-frame renderer ----
        def make_frame(t):
            from PIL import Image, ImageDraw
            img  = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            if t >= author_display_start:
                # Show author name below scroll window, horizontally centred
                if author:
                    author_text = author.upper()
                    tw = _measure(author_font, author_text)
                    x  = (w - tw) // 2
                    y  = block_top + 3 * line_height
                    draw.text((x, y), author_text, font=author_font,
                              fill=(*gold_rgb, BRIGHT))
                return np.array(img)

            # Which word is active at time t?
            word_idx = min(int(t / word_dt), n_words - 1)
            cur_line, cur_word = flat_words[word_idx]

            # Render past / current / future rows
            for offset in (-1, 0, 1):
                li = cur_line + offset
                if li < 0 or li >= len(words_per_line):
                    continue
                words = words_per_line[li]
                y = block_top + (offset + 1) * line_height  # offset -1→top, 0→mid, 1→bottom

                if offset == 0:
                    # Current line: word-by-word colouring
                    total_w = sum(word_widths[wd] for wd in words)
                    _draw_pill(draw, w // 2, total_w, y, font_size)   # pill first
                    x = (w - total_w) // 2
                    for wi, wd in enumerate(words):
                        if wi < cur_word:
                            rgba = (*cream_rgb, BRIGHT)   # already read
                        elif wi == cur_word:
                            rgba = (*gold_rgb,  BRIGHT)   # active word
                        else:
                            rgba = (*cream_rgb, DIM)      # not yet read
                        draw.text((x, y), wd, font=pil_font, fill=rgba)
                        x += word_widths[wd]
                else:
                    # Past line: bright (already read). Future line: dim (not yet reached).
                    line_text = ' '.join(words)
                    tw = _measure(pil_font, line_text)
                    _draw_pill(draw, w // 2, tw, y, font_size)         # pill first
                    x  = (w - tw) // 2
                    alpha = BRIGHT if offset == -1 else DIM
                    draw.text((x, y), line_text, font=pil_font,
                              fill=(*cream_rgb, alpha))

            return np.array(img)

        # ---- Build the VideoClip overlay ----
        scroll_clip = VideoClip(make_frame, duration=computed_duration)
        scroll_clip = (scroll_clip.with_fps(30) if hasattr(scroll_clip, 'with_fps')
                       else scroll_clip.set_fps(30))
        scroll_clip = (scroll_clip.with_position((0, 0)) if hasattr(scroll_clip, 'with_position')
                       else scroll_clip.set_position((0, 0)))

        return [self._make_scrim_clip(w, h, computed_duration), scroll_clip]

    def create_cinematic_text_clip(
        self,
        text: str,
        author: str,
        duration: float,
        font_size: int = 96,
    ):
        """
        Create a cinematic quote overlay positioned in the top third of the frame.
        Includes a top scrim for readability on bright images.
        Returns a CompositeVideoClip of size (reel_width, reel_height).
        """
        w, h = self.reel_width, self.reel_height

        # ---- Vignette layer: radial gradient, dark at edges ----
        arr = np.zeros((h, w, 4), dtype=np.uint8)
        cx, cy = w / 2, h / 2
        Y, X = np.mgrid[0:h, 0:w]
        dist = np.hypot((X - cx) / cx, (Y - cy) / cy)
        alpha = np.clip(dist * self.CINEMATIC_VIGNETTE_ALPHA, 0, self.CINEMATIC_VIGNETTE_ALPHA).astype(np.uint8)
        arr[:, :, 3] = alpha  # RGB stays 0 (black) — dark vignette
        try:
            vignette_clip = ImageClip(arr, transparent=True)
        except TypeError:
            vignette_clip = ImageClip(arr)
        vignette_clip = (vignette_clip.with_duration(duration)
                         if hasattr(vignette_clip, 'with_duration')
                         else vignette_clip.set_duration(duration))
        vignette_clip = (vignette_clip.with_position((0, 0))
                         if hasattr(vignette_clip, 'with_position')
                         else vignette_clip.set_position((0, 0)))

        # ---- Top scrim: ensures text readability on bright images ----
        scrim_clip = self._make_scrim_clip(w, h, duration)

        # ---- Text wrapping ----
        usable_width = w - 120
        char_width_ratio = 0.55
        max_chars = max(20, int(usable_width / (font_size * char_width_ratio) * 1.2))
        wrapped_lines = self._smart_wrap(text, max_chars)
        display_text = '\n'.join(wrapped_lines)
        n_lines = len(wrapped_lines) if wrapped_lines else 1

        # ---- Quote TextClip (italic) ----
        serif_candidates = self.QUOTE_OVERLAY_FONT_CANDIDATES + ('Arial',)
        quote_clip = None
        for fn in serif_candidates:
            try:
                quote_clip = TextClip(
                    text=display_text,
                    font_size=font_size,
                    color=self.CINEMATIC_QUOTE_COLOR,
                    font=fn,
                    italic=True,
                    size=(usable_width, None),
                    margin=(20, 20),
                )
                break
            except Exception:
                try:
                    quote_clip = TextClip(
                        display_text,
                        fontsize=font_size,
                        color=self.CINEMATIC_QUOTE_COLOR,
                        font=fn,
                        method='caption',
                        size=(usable_width, None),
                        align='center',
                    )
                    break
                except Exception:
                    continue
        if quote_clip is None:
            try:
                quote_clip = TextClip(
                    text=display_text,
                    font_size=font_size,
                    color=self.CINEMATIC_QUOTE_COLOR,
                    italic=True,
                    size=(usable_width, None),
                    margin=(20, 20),
                )
            except Exception:
                quote_clip = TextClip(
                    text=display_text,
                    font_size=font_size,
                    color=self.CINEMATIC_QUOTE_COLOR,
                    size=(usable_width, None),
                    margin=(20, 20),
                )

        # ---- Author TextClip (uppercase, gold) ----
        author_upper = author.upper()
        author_font_size = max(28, font_size // 2)
        author_clip = None
        for fn in serif_candidates:
            try:
                author_clip = TextClip(
                    text=author_upper,
                    font_size=author_font_size,
                    color=self.CINEMATIC_AUTHOR_COLOR,
                    font=fn,
                    size=(usable_width, None),
                    margin=(10, 10),
                )
                break
            except Exception:
                try:
                    author_clip = TextClip(
                        author_upper,
                        fontsize=author_font_size,
                        color=self.CINEMATIC_AUTHOR_COLOR,
                        font=fn,
                        method='caption',
                        size=(usable_width, None),
                        align='center',
                    )
                    break
                except Exception:
                    continue
        if author_clip is None:
            try:
                author_clip = TextClip(
                    text=author_upper,
                    font_size=author_font_size,
                    color=self.CINEMATIC_AUTHOR_COLOR,
                    size=(usable_width, None),
                    margin=(10, 10),
                )
            except Exception:
                author_clip = TextClip(
                    author_upper,
                    fontsize=author_font_size,
                    color=self.CINEMATIC_AUTHOR_COLOR,
                    method='caption',
                    size=(usable_width, None),
                    align='center',
                )

        # ---- Divider ImageClip (thin gold line) ----
        div_arr = np.zeros((self.DIVIDER_HEIGHT, self.DIVIDER_WIDTH, 4), dtype=np.uint8)
        r, g, b = self.hex_to_rgb(self.CINEMATIC_DIVIDER_COLOR)
        div_arr[:, :, 0] = r
        div_arr[:, :, 1] = g
        div_arr[:, :, 2] = b
        div_arr[:, :, 3] = 255
        try:
            divider_clip = ImageClip(div_arr, transparent=True)
        except TypeError:
            divider_clip = ImageClip(div_arr)

        # ---- Position: top third of frame ----
        line_height = font_size * self.LINE_HEIGHT_MULT
        quote_h = int(getattr(quote_clip, 'h', n_lines * line_height))
        author_h = int(getattr(author_clip, 'h', author_font_size * 1.5))
        block_top = max(80, h // 6)

        div_y = block_top + quote_h + self.DIVIDER_GAP
        author_y = div_y + self.DIVIDER_HEIGHT + self.AUTHOR_GAP
        div_x = (w - self.DIVIDER_WIDTH) // 2

        # ---- Pill background overlay ----
        line_y_positions = [block_top + i * int(font_size * self.LINE_HEIGHT_MULT)
                            for i in range(n_lines)]
        pill_clip = self._make_pill_overlay(
            lines=wrapped_lines,
            font_size=font_size,
            line_y_positions=line_y_positions,
            w=w, h=h, duration=duration,
        )

        def _set_pos_dur(clip, pos, dur):
            clip = (clip.with_duration(dur) if hasattr(clip, 'with_duration')
                    else clip.set_duration(dur))
            clip = (clip.with_position(pos) if hasattr(clip, 'with_position')
                    else clip.set_position(pos))
            return clip

        quote_clip = _set_pos_dur(quote_clip, ('center', block_top), duration)
        divider_clip = _set_pos_dur(divider_clip, (div_x, div_y), duration)
        author_clip = _set_pos_dur(author_clip, ('center', author_y), duration)

        composite = CompositeVideoClip(
            [vignette_clip, scrim_clip, pill_clip, quote_clip, divider_clip, author_clip],
            size=(w, h),
        )
        composite = (composite.with_duration(duration)
                     if hasattr(composite, 'with_duration')
                     else composite.set_duration(duration))
        return composite

    def create_line_reveal_clips(
        self,
        text: str,
        author: str,
        duration: float,
        font_size: int = 96,
    ) -> list:
        """
        Create a list of pre-positioned, pre-timed clips for line-by-line quote reveal.
        Lines fade in one by one, accumulating. Author block appears last.
        Includes a top scrim for readability on bright images.
        All clips are transparent overlays; caller composites them on the background.
        """
        w, h = self.reel_width, self.reel_height
        usable_width = w - 120
        char_width_ratio = 0.55
        max_chars = max(20, int(usable_width / (font_size * char_width_ratio) * 1.2))
        wrapped_lines = self._smart_wrap(text, max_chars)
        n_lines = len(wrapped_lines)

        # ---- Timing ----
        interval = max(1.0, duration / (n_lines + 1))

        # ---- Layout: top third of frame ----
        line_height = font_size * self.LINE_HEIGHT_MULT
        author_font_size = max(28, font_size // 2)
        block_top = max(80, h // 6)

        # ---- Pill background overlay (static, behind all fading text lines) ----
        line_y_positions = [block_top + i * int(line_height)
                            for i in range(n_lines)]
        pill_clip_static = self._make_pill_overlay(
            lines=wrapped_lines,
            font_size=font_size,
            line_y_positions=line_y_positions,
            w=w, h=h, duration=duration,
        )

        serif_candidates = self.QUOTE_OVERLAY_FONT_CANDIDATES + ('Arial',)

        def _make_text_clip(t, size, color):
            for fn in serif_candidates:
                try:
                    c = TextClip(
                        text=t,
                        font_size=size,
                        color=color,
                        font=fn,
                        size=(usable_width, None),
                        margin=(10, 10),
                    )
                    return c
                except Exception:
                    try:
                        c = TextClip(
                            t,
                            fontsize=size,
                            color=color,
                            font=fn,
                            method='caption',
                            size=(usable_width, None),
                            align='center',
                        )
                        return c
                    except Exception:
                        continue
            return TextClip(text=t, font_size=size, color=color, size=(usable_width, None), margin=(10, 10))

        def _apply(clip, start_time, y_pos):
            if hasattr(clip, 'crossfadein'):
                clip = clip.crossfadein(0.5)
            clip = (clip.with_duration(duration - start_time)
                    if hasattr(clip, 'with_duration')
                    else clip.set_duration(duration - start_time))
            clip = (clip.with_start(start_time)
                    if hasattr(clip, 'with_start')
                    else clip.set_start(start_time))
            clip = (clip.with_position(('center', int(y_pos)))
                    if hasattr(clip, 'with_position')
                    else clip.set_position(('center', int(y_pos))))
            return clip

        clips = [self._make_scrim_clip(w, h, duration), pill_clip_static]

        # ---- Line clips ----
        for i, line in enumerate(wrapped_lines):
            y = block_top + i * line_height
            clip = _make_text_clip(line, font_size, self.CINEMATIC_QUOTE_COLOR)
            clips.append(_apply(clip, i * interval, y))

        # ---- Divider clip ----
        div_y = block_top + n_lines * line_height + self.DIVIDER_GAP
        div_arr = np.zeros((self.DIVIDER_HEIGHT, self.DIVIDER_WIDTH, 4), dtype=np.uint8)
        r, g, b = self.hex_to_rgb(self.CINEMATIC_DIVIDER_COLOR)
        div_arr[:, :, 0] = r
        div_arr[:, :, 1] = g
        div_arr[:, :, 2] = b
        div_arr[:, :, 3] = 255
        try:
            div_clip = ImageClip(div_arr, transparent=True)
        except TypeError:
            div_clip = ImageClip(div_arr)
        author_start = n_lines * interval
        clips.append(_apply(div_clip, author_start, div_y))

        # ---- Author clip ----
        author_y = div_y + self.DIVIDER_HEIGHT + self.AUTHOR_GAP
        author_clip = _make_text_clip(author.upper(), author_font_size, self.CINEMATIC_AUTHOR_COLOR)
        clips.append(_apply(author_clip, author_start, author_y))

        return clips

    def create_cinematic_flyer_clip(
        self,
        flyer_lines: list,
        duration: float,
        font_size: int = 80,
        logo_path=None,
    ):
        """
        Create a cinematic flyer segment: deep-green background, cream title,
        gold divider, gold body lines. Used as segment 2 after the quote card.
        """
        w, h = self.reel_width, self.reel_height

        # ---- Dark green background ----
        brand_r, brand_g, brand_b = self.hex_to_rgb(
            self.config.get('brand', {}).get('colors', {}).get('primary', '#2c5530')
        )
        try:
            bg = ColorClip(size=(w, h), color=(brand_r, brand_g, brand_b), duration=duration)
        except TypeError:
            bg = ColorClip(size=(w, h), color=(brand_r, brand_g, brand_b))
            bg = (bg.with_duration(duration) if hasattr(bg, 'with_duration')
                  else bg.set_duration(duration))
        layers = [bg]

        serif_candidates = self.QUOTE_OVERLAY_FONT_CANDIDATES + ('Arial',)
        usable_width = w - 160

        def _text(t, size, color, margin=(10, 20)):
            for fn in serif_candidates:
                try:
                    return TextClip(text=t, font_size=size, color=color, font=fn,
                                    size=(usable_width, None), margin=margin)
                except Exception:
                    try:
                        return TextClip(t, fontsize=size, color=color, font=fn,
                                        method='caption', size=(usable_width, None), align='center')
                    except Exception:
                        continue
            return TextClip(text=t, font_size=size, color=color,
                            size=(usable_width, None), margin=margin)

        def _dur_pos(clip, pos):
            clip = (clip.with_duration(duration) if hasattr(clip, 'with_duration')
                    else clip.set_duration(duration))
            clip = (clip.with_position(pos) if hasattr(clip, 'with_position')
                    else clip.set_position(pos))
            return clip

        # ---- Optional logo ----
        logo_bottom = 0
        logo_top_margin = 80
        if logo_path and Path(logo_path).exists():
            try:
                logo_img = Image.open(logo_path)
                logo_img = ImageOps.exif_transpose(logo_img)
                logo_img = logo_img.convert('RGBA')
                max_logo_w = int(w * 0.55)
                lw, lh = logo_img.size
                scale = min(1.0, max_logo_w / lw)
                new_lw, new_lh = int(lw * scale), int(lh * scale)
                try:
                    resample = Image.Resampling.LANCZOS
                except AttributeError:
                    resample = Image.LANCZOS
                logo_img = logo_img.resize((new_lw, new_lh), resample)
                logo_arr = np.array(logo_img)
                try:
                    logo_clip = ImageClip(logo_arr, transparent=True)
                except TypeError:
                    logo_clip = ImageClip(logo_arr)
                logo_x = (w - new_lw) // 2
                layers.append(_dur_pos(logo_clip, (logo_x, logo_top_margin)))
                logo_bottom = logo_top_margin + new_lh
            except Exception as e:
                print(f"Warning: Could not load flyer logo: {e}")

        if not flyer_lines:
            composite = CompositeVideoClip(layers, size=(w, h))
            return (composite.with_duration(duration) if hasattr(composite, 'with_duration')
                    else composite.set_duration(duration))

        # ---- Title (first non-empty line) ----
        non_empty = [l for l in flyer_lines if l.strip()]
        title = non_empty[0] if non_empty else ''
        body_lines = non_empty[1:] if len(non_empty) > 1 else []

        title_font_size = font_size + 28
        body_font_size = max(font_size, 36)

        title_clip = _text(title.upper(), title_font_size, self.CINEMATIC_QUOTE_COLOR)
        title_h = int(getattr(title_clip, 'h', title_font_size * 1.5))

        # ---- Gold divider ----
        div_arr = np.zeros((self.DIVIDER_HEIGHT, self.DIVIDER_WIDTH, 4), dtype=np.uint8)
        r, g, b = self.hex_to_rgb(self.CINEMATIC_DIVIDER_COLOR)
        div_arr[:, :, 0] = r
        div_arr[:, :, 1] = g
        div_arr[:, :, 2] = b
        div_arr[:, :, 3] = 255
        try:
            divider = ImageClip(div_arr, transparent=True)
        except TypeError:
            divider = ImageClip(div_arr)

        # ---- Body lines ----
        body_clips = [_text(line, body_font_size, self.CINEMATIC_AUTHOR_COLOR)
                      for line in body_lines]
        body_line_h = body_font_size * self.LINE_HEIGHT_MULT
        total_body_h = len(body_clips) * body_line_h

        # ---- Vertical layout: center below logo ----
        total_block_h = (title_h + self.DIVIDER_GAP + self.DIVIDER_HEIGHT
                         + self.AUTHOR_GAP + total_body_h)
        text_area_top = logo_bottom + 60 if logo_bottom else 0
        block_top = max(text_area_top, (h - total_block_h) // 2)

        div_y = block_top + title_h + self.DIVIDER_GAP
        div_x = (w - self.DIVIDER_WIDTH) // 2
        body_y = div_y + self.DIVIDER_HEIGHT + self.AUTHOR_GAP

        layers.append(_dur_pos(title_clip, ('center', block_top)))
        layers.append(_dur_pos(divider, (div_x, div_y)))
        for c in body_clips:
            layers.append(_dur_pos(c, ('center', int(body_y))))
            body_y += body_line_h

        composite = CompositeVideoClip(layers, size=(w, h))
        return (composite.with_duration(duration) if hasattr(composite, 'with_duration')
                else composite.set_duration(duration))

    def create_video_with_text_overlay(
        self,
        video_path: Path,
        text_overlay: str,
        output_path: Path,
        duration: Optional[float] = None,
        text_position: str = 'bottom',
        font_size: int = 60,
        music_path: Optional[Path] = None
    ) -> Path:
        """
        Create a video with text overlay.
        
        Args:
            video_path: Path to source video file.
            text_overlay: Text to overlay on video.
            output_path: Path to save the output video.
            duration: Duration of the video clip. If None, uses full video.
            text_position: Position of text ('top', 'center', 'bottom').
            font_size: Font size for text overlay.
            music_path: Optional path to background music file (.mp3, .wav, etc.).
        
        Returns:
            Path to saved video.
        """
        # Prepare video clip
        video_clip = self.prepare_clip(video_path, duration=duration)
        
        # Create text clip
        text_clip = self.create_text_clip(
            text=text_overlay,
            duration=video_clip.duration,
            position=text_position,
            font_size=font_size,
            start_time=0
        )
        
        # Composite video and text
        if hasattr(CompositeVideoClip, '__call__'):
            # moviepy 2.x style
            final_clip = CompositeVideoClip([video_clip, text_clip])
        else:
            # moviepy 1.x style
            final_clip = CompositeVideoClip([video_clip, text_clip])
        
        # Add background music if provided (replaces or adds to video audio)
        if music_path and music_path.exists():
            try:
                audio = AudioFileClip(str(music_path))
                if audio.duration < final_clip.duration:
                    loops = int(final_clip.duration / audio.duration) + 1
                    audio = concatenate_audioclips([audio] * loops)
                    if hasattr(audio, 'subclipped'):
                        audio = audio.subclipped(0, final_clip.duration)
                    else:
                        audio = audio.subclip(0, final_clip.duration)
                else:
                    if hasattr(audio, 'subclipped'):
                        audio = audio.subclipped(0, final_clip.duration)
                    else:
                        audio = audio.subclip(0, final_clip.duration)
                if hasattr(audio, 'with_volume_scaled'):
                    audio = audio.with_volume_scaled(0.3)
                elif hasattr(audio, 'volumex'):
                    audio = audio.volumex(0.3)
                else:
                    try:
                        from moviepy.audio.fx import volumex
                        audio = audio.fx(volumex, 0.3)
                    except Exception:
                        pass
                audio_fade_duration = 1.5
                if audio.duration > audio_fade_duration:
                    try:
                        fade_start_time = audio.duration - audio_fade_duration
                        def volume_func(t):
                            if t < fade_start_time:
                                return 1.0
                            fade_progress = (t - fade_start_time) / audio_fade_duration
                            return max(0.0, 1.0 - fade_progress)
                        try:
                            audio = audio.with_volume(volume_func)
                        except AttributeError:
                            try:
                                from moviepy.audio.AudioClip import AudioArrayClip
                                audio_array = audio.to_soundarray(fps=audio.fps)
                                for i in range(len(audio_array)):
                                    t = i / audio.fps
                                    audio_array[i] = audio_array[i] * volume_func(t)
                                audio = AudioArrayClip(audio_array, fps=audio.fps)
                            except Exception as e:
                                print(f"Warning: Could not apply audio fade-out: {e}")
                    except Exception as e:
                        print(f"Warning: Could not apply audio fade-out: {e}")
                if hasattr(final_clip, 'with_audio'):
                    final_clip = final_clip.with_audio(audio)
                else:
                    final_clip = final_clip.set_audio(audio)
            except Exception as e:
                print(f"Warning: Could not add music: {e}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write video file
        final_clip.write_videofile(
            str(output_path),
            fps=30,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            bitrate='8000k'
        )
        
        # Clean up
        video_clip.close()
        text_clip.close()
        final_clip.close()
        
        return output_path
    
    def _add_white_fade_overlay(self, clip, video_fade_duration: float, fps: float = 30,
                                color=(255, 255, 255)):
        """Add a solid-color overlay that fades in over the last video_fade_duration seconds.
        Defaults to white; pass color=(r,g,b) to fade to a different color.
        Caller is responsible for closing the original clip when done."""
        if clip.duration <= video_fade_duration:
            return clip
        fade_start = clip.duration - video_fade_duration
        w, h = int(clip.w), int(clip.h)
        try:
            white_clip = ColorClip(size=(w, h), color=color, duration=video_fade_duration)
        except TypeError:
            white_clip = ColorClip(size=(w, h), color=color)
            white_clip = white_clip.with_duration(video_fade_duration) if hasattr(white_clip, 'with_duration') else white_clip.set_duration(video_fade_duration)
        if hasattr(white_clip, 'with_fps'):
            white_clip = white_clip.with_fps(fps)
        elif hasattr(white_clip, 'set_fps'):
            white_clip = white_clip.set_fps(fps)
        if hasattr(white_clip, 'with_start'):
            white_clip = white_clip.with_start(fade_start)
        else:
            white_clip = white_clip.set_start(fade_start)
        if hasattr(white_clip, 'crossfadein'):
            white_clip = white_clip.crossfadein(video_fade_duration)
        elif hasattr(white_clip, 'fadein'):
            white_clip = white_clip.fadein(video_fade_duration)
        composite = CompositeVideoClip([clip, white_clip])
        if hasattr(composite, 'with_duration'):
            composite = composite.with_duration(clip.duration)
        elif hasattr(composite, 'set_duration'):
            composite = composite.set_duration(clip.duration)
        return composite

    def create_image_quote_video(
        self,
        image_paths: List[Path],
        text: str,
        author: str,
        output_path: Path,
        duration: float = 15.0,
        music_path: Optional[Path] = None,
        audio_fade_duration: float = 3.0,
        video_fade_duration: float = 0.8,
        text_position: str = 'bottom',
        font_size: int = 96,
        flyer_lines: Optional[List[str]] = None,
        flyer_duration: float = 5.0,
        flyer_font_size: int = 80,
        flyer_logo_path: Optional[Path] = None,
        quote_style: str = 'cinematic',
    ) -> Path:
        """
        Create a video from one or more images with quote overlay, optional music,
        optional yoga flyer segment (white + text, optional logo), and fades to white.
        When multiple images are given, duration is split equally across them.

        Args:
            image_paths: Path(s) to background image file(s).
            text: Quote body text.
            author: Attribution line (author name).
            quote_style: 'cinematic' (default) or 'reveal'.
            output_path: Path to save the output video.
            duration: Quote segment duration in seconds (default 15); split across images.
                Ignored when quote_style='scroll' — duration is then computed automatically
                from text length at SCROLL_CHARS_PER_SECOND characters per second.
            music_path: Optional path to background music (.mp3, .wav, etc.).
            audio_fade_duration: Seconds over which music fades to silence at end (default 3).
            video_fade_duration: Seconds over which video fades to white at segment ends (default 0.8).
            text_position: Position of text ('top', 'center', 'bottom').
            font_size: Font size for quote overlay (default 32).
            flyer_lines: Optional list of lines for yoga flyer (white BG + text); adds second segment.
            flyer_duration: Duration of flyer segment in seconds (default 5).
            flyer_font_size: Font size for flyer body text (default 40); title line is larger.
            flyer_logo_path: Optional path to logo image (e.g. Palheiro) shown above flyer text.
        
        Returns:
            Path to saved video.
        """
        image_paths = [Path(p) for p in image_paths]
        if not image_paths:
            raise ValueError("At least one image path is required.")
        for p in image_paths:
            if not p.exists():
                raise FileNotFoundError(f"Image not found: {p}")
        
        fps = 30
        use_flyer = flyer_lines and len(flyer_lines) > 0
        # For scroll style, duration is derived from text length at a fixed reading pace
        # so all photos together fill exactly the time needed to read the full quote.
        # --duration from the CLI is ignored for scroll.
        if quote_style == 'scroll':
            duration = self.calculate_scroll_duration(text)
        total_duration = (duration + flyer_duration) if use_flyer else duration
        
        # ---- Segment 1: image(s) + quote ----
        n = len(image_paths)
        segment_duration = duration / n
        if n == 1:
            image_clip = self.image_to_clip(image_paths[0], duration=duration)
        else:
            clips = [self.image_to_clip(p, duration=segment_duration) for p in image_paths]
            image_clip = concatenate_videoclips(clips, method='compose')
        # Compute top black letterbox height from first image for quote positioning
        first_image_path = image_paths[0]
        try:
            with Image.open(first_image_path) as img:
                img = ImageOps.exif_transpose(img)
                w, h = img.size
        except Exception:
            w, h = self.reel_width, self.reel_height
        scale = min(self.reel_width / w, self.reel_height / h)
        new_h = int(h * scale)
        top_black = (self.reel_height - new_h) // 2
        # Quote font: use requested size directly (no cap)
        quote_font_size = font_size
        # Place quote overlay using selected style
        if quote_style == 'reveal':
            reveal_clips = self.create_line_reveal_clips(
                text=text,
                author=author,
                duration=duration,
                font_size=quote_font_size,
            )
            segment_1 = CompositeVideoClip([image_clip] + reveal_clips)
        elif quote_style == 'scroll':
            scroll_clips = self.create_scroll_clips(
                text=text,
                author=author,
                duration=duration,
                font_size=quote_font_size,
            )
            segment_1 = CompositeVideoClip([image_clip] + scroll_clips)
        else:
            # 'cinematic' (default)
            text_clip = self.create_cinematic_text_clip(
                text=text,
                author=author,
                duration=duration,
                font_size=quote_font_size,
            )
            segment_1 = CompositeVideoClip([image_clip, text_clip])
        if hasattr(segment_1, 'with_fps'):
            segment_1 = segment_1.with_fps(fps)
        elif hasattr(segment_1, 'set_fps'):
            segment_1 = segment_1.set_fps(fps)
        _fade_r, _fade_g, _fade_b = self.hex_to_rgb(
            self.config.get('brand', {}).get('colors', {}).get('primary', '#2c5530'))
        _fade_color = (_fade_r, _fade_g, _fade_b)
        segment_1 = self._add_white_fade_overlay(segment_1, video_fade_duration, fps,
                                                 color=_fade_color)

        if not use_flyer:
            final_clip = segment_1
        else:
            # ---- Segment 2: cinematic dark-background flyer ----
            segment_2 = self.create_cinematic_flyer_clip(
                flyer_lines=flyer_lines,
                duration=flyer_duration,
                font_size=flyer_font_size,
                logo_path=flyer_logo_path,
            )
            if hasattr(segment_2, 'with_fps'):
                segment_2 = segment_2.with_fps(fps)
            segment_2 = self._add_white_fade_overlay(segment_2, video_fade_duration, fps,
                                                     color=_fade_color)
            # Use method='chain' to avoid CompositeVideoClip bg=None issues with nested composites
            final_clip = concatenate_videoclips([segment_1, segment_2], method='chain')
            if hasattr(final_clip, 'with_duration'):
                final_clip = final_clip.with_duration(total_duration)
            elif hasattr(final_clip, 'set_duration'):
                final_clip = final_clip.set_duration(total_duration)
        
        # ---- Audio for full duration, fade out at end ----
        if music_path and Path(music_path).exists():
            try:
                audio = AudioFileClip(str(music_path))
                if audio.duration < total_duration:
                    loops = int(total_duration / audio.duration) + 1
                    audio = concatenate_audioclips([audio] * loops)
                if hasattr(audio, 'subclipped'):
                    audio = audio.subclipped(0, total_duration)
                else:
                    audio = audio.subclip(0, total_duration)
                if hasattr(audio, 'with_volume_scaled'):
                    audio = audio.with_volume_scaled(0.3)
                elif hasattr(audio, 'volumex'):
                    audio = audio.volumex(0.3)
                else:
                    try:
                        from moviepy.audio.fx import volumex
                        audio = audio.fx(volumex, 0.3)
                    except Exception:
                        pass
                if audio.duration > audio_fade_duration:
                    try:
                        fade_start_time = audio.duration - audio_fade_duration
                        def volume_func(t):
                            if t < fade_start_time:
                                return 1.0
                            return max(0.0, 1.0 - (t - fade_start_time) / audio_fade_duration)
                        try:
                            audio = audio.with_volume(volume_func)
                        except AttributeError:
                            try:
                                from moviepy.audio.AudioClip import AudioArrayClip
                                audio_array = audio.to_soundarray(fps=audio.fps)
                                for i in range(len(audio_array)):
                                    t = i / audio.fps
                                    audio_array[i] = audio_array[i] * volume_func(t)
                                audio = AudioArrayClip(audio_array, fps=audio.fps)
                            except Exception as e:
                                print(f"Warning: Could not apply audio fade-out: {e}")
                    except Exception as e:
                        print(f"Warning: Could not apply audio fade-out: {e}")
                if hasattr(final_clip, 'with_audio'):
                    final_clip = final_clip.with_audio(audio)
                else:
                    final_clip = final_clip.set_audio(audio)
            except Exception as e:
                print(f"Warning: Could not add music: {e}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_clip.write_videofile(
            str(output_path),
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            bitrate='8000k',
            audio_bitrate='192k'
        )
        
        tmp_path = getattr(image_clip, 'tmp_path', None)
        image_clip.close()
        if quote_style != 'reveal' and 'text_clip' in dir():
            text_clip.close()
        final_clip.close()
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        return output_path
    
    def create_reel(
        self,
        video_paths: List[Path],
        output_path: Path,
        text_overlays: Optional[List[Dict]] = None,
        music_path: Optional[Path] = None,
        transition_duration: float = 0.5
    ) -> Path:
        """
        Create an Instagram Reel from multiple video clips.
        
        Args:
            video_paths: List of paths to video files.
            output_path: Path to save the Reel.
            text_overlays: List of text overlay dicts with 'text', 'start_time', 'duration', 'position'.
            music_path: Optional path to background music file.
            transition_duration: Duration of transitions between clips.
        
        Returns:
            Path to saved Reel.
        """
        if not video_paths:
            raise ValueError("At least one video path is required")
        
        # Load and prepare clips
        clips = []
        current_time = 0
        
        for i, video_path in enumerate(video_paths):
            # Calculate clip duration to fit within max duration
            remaining_time = self.max_duration - current_time
            if remaining_time <= 0:
                break
            
            # Distribute time evenly among remaining clips
            clip_duration = min(remaining_time / (len(video_paths) - i), 10)  # Max 10 seconds per clip
            
            clip = self.prepare_clip(video_path, duration=clip_duration)
            # In moviepy 2.x, timing is handled differently - clips are positioned during composition
            # Store start time for later use in composition
            # Position clip at the right time
            if hasattr(clip, 'with_start'):
                clip = clip.with_start(current_time)
            elif hasattr(clip, 'set_start'):
                clip = clip.set_start(current_time)
            clips.append(clip)
            
            current_time += clip_duration - transition_duration
        
        # Concatenate clips
        if len(clips) > 1:
            final_clip = concatenate_videoclips(clips, method="compose")
        else:
            final_clip = clips[0]
        
        # Ensure minimum duration
        if final_clip.duration < self.min_duration:
            # Loop the clip if too short
            loops_needed = int(self.min_duration / final_clip.duration) + 1
            looped_clips = [final_clip] * loops_needed
            final_clip = concatenate_videoclips(looped_clips, method="compose")
            if hasattr(final_clip, 'subclipped'):
                final_clip = final_clip.subclipped(0, self.min_duration)
            else:
                final_clip = final_clip.subclip(0, self.min_duration)
        
        # Ensure maximum duration
        if final_clip.duration > self.max_duration:
            final_clip = final_clip.subclip(0, self.max_duration)
        
        # Add text overlays
        if text_overlays:
            text_clips = []
            for overlay in text_overlays:
                txt_clip = self.create_text_clip(
                    overlay.get('text', ''),
                    overlay.get('duration', 3),
                    overlay.get('position', 'bottom'),
                    overlay.get('font_size', 60),
                    overlay.get('start_time', 0)
                )
                text_clips.append(txt_clip)
            
            final_clip = CompositeVideoClip([final_clip] + text_clips)
        
        # Add background music if provided
        if music_path and music_path.exists():
            try:
                audio = AudioFileClip(str(music_path))
                # Loop audio if needed
                if audio.duration < final_clip.duration:
                    loops = int(final_clip.duration / audio.duration) + 1
                    audio = concatenate_audioclips([audio] * loops)
                    if hasattr(audio, 'subclipped'):
                        audio = audio.subclipped(0, final_clip.duration)
                    else:
                        audio = audio.subclip(0, final_clip.duration)
                else:
                    if hasattr(audio, 'subclipped'):
                        audio = audio.subclipped(0, final_clip.duration)
                    else:
                        audio = audio.subclip(0, final_clip.duration)
                
                # Lower volume to 30% for background
                # moviepy 2.x uses with_volume_scaled instead of volumex
                if hasattr(audio, 'with_volume_scaled'):
                    audio = audio.with_volume_scaled(0.3)
                elif hasattr(audio, 'volumex'):
                    audio = audio.volumex(0.3)
                else:
                    # Fallback: try to use fx module
                    try:
                        from moviepy.audio.fx import volumex
                        audio = audio.fx(volumex, 0.3)
                    except:
                        pass  # Continue without volume adjustment
                
                # Add fade-out to audio (volume decrease at the end)
                audio_fade_duration = 1.5  # 1.5 second audio fade-out
                if audio.duration > audio_fade_duration:
                    try:
                        # Create a volume function that fades from 1.0 to 0.0
                        fade_start_time = audio.duration - audio_fade_duration
                        def volume_func(t):
                            if t < fade_start_time:
                                return 1.0  # Full volume before fade
                            else:
                                # Fade from 1.0 to 0.0 over audio_fade_duration
                                fade_progress = (t - fade_start_time) / audio_fade_duration
                                return max(0.0, 1.0 - fade_progress)
                        
                        # Apply volume fade using with_volume
                        try:
                            audio = audio.with_volume(volume_func)
                        except AttributeError:
                            # Fallback: try using volumex with a lambda
                            try:
                                # Create a new audio clip with volume applied per frame
                                from moviepy.audio.AudioClip import AudioArrayClip
                                import numpy as np
                                
                                # Get audio array
                                audio_array = audio.to_soundarray(fps=audio.fps)
                                
                                # Apply volume fade
                                for i in range(len(audio_array)):
                                    t = i / audio.fps
                                    vol = volume_func(t)
                                    audio_array[i] = audio_array[i] * vol
                                
                                # Create new audio clip
                                audio = AudioArrayClip(audio_array, fps=audio.fps)
                            except Exception as e:
                                print(f"Warning: Could not apply audio fade-out: {e}")
                    except Exception as e:
                        print(f"Warning: Could not apply audio fade-out: {e}")
                
                # Handle moviepy 2.x API changes
                if hasattr(final_clip, 'with_audio'):
                    final_clip = final_clip.with_audio(audio)
                else:
                    final_clip = final_clip.set_audio(audio)
            except Exception as e:
                print(f"Warning: Could not add music: {e}")
        
        # Write video file with fade-out effects using ffmpeg filters
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Apply fade-out using ffmpeg filters if duration is sufficient
        fade_duration = 1.0  # 1 second video fade-out
        # Audio fade-out is already applied via with_volume method above
        
        if final_clip.duration > fade_duration:
            # Calculate fade start time
            fade_start = final_clip.duration - fade_duration
            
            # Build ffmpeg filter string for video fade-out to white
            # Use geq filter to blend white (255,255,255) into the video over time
            # Formula: blend each RGB channel towards 255 based on fade progress
            fade_end = final_clip.duration
            video_filter = (
                f"geq="
                f"r='if(between(T,{fade_start:.2f},{fade_end:.2f}),"
                f"r+(255-r)*((T-{fade_start:.2f})/{fade_duration:.2f}),r)':"
                f"g='if(between(T,{fade_start:.2f},{fade_end:.2f}),"
                f"g+(255-g)*((T-{fade_start:.2f})/{fade_duration:.2f}),g)':"
                f"b='if(between(T,{fade_start:.2f},{fade_end:.2f}),"
                f"b+(255-b)*((T-{fade_start:.2f})/{fade_duration:.2f}),b)'"
            )
            
            # Write with video fade effect - force re-encoding to apply filter
            final_clip.write_videofile(
                str(output_path),
                fps=30,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                bitrate='8000k',
                audio_bitrate='192k',
                ffmpeg_params=['-vf', video_filter, '-c:v', 'libx264', '-c:a', 'aac']
            )
        else:
            final_clip.write_videofile(
                str(output_path),
                fps=30,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                bitrate='8000k'
            )
        
        # Clean up
        final_clip.close()
        for clip in clips:
            clip.close()
        
        # Clean up any MoviePy temporary files in the project root
        self._cleanup_moviepy_temp_files()
        
        return output_path
    
    def add_subtitles(
        self,
        video_path: Path,
        output_path: Path,
        subtitles: List[Dict],
        font_size: int = 50
    ) -> Path:
        """
        Add subtitles to a video.
        
        Args:
            video_path: Path to source video.
            output_path: Path to save video with subtitles.
            subtitles: List of subtitle dicts with 'text', 'start_time', 'duration'.
            font_size: Font size for subtitles.
        
        Returns:
            Path to saved video.
        """
        clip = VideoFileClip(str(video_path))
        
        # Resize if needed
        if clip.h != self.reel_height or clip.w != self.reel_width:
            if hasattr(clip, 'resized'):
                clip = clip.resized(height=self.reel_height)
            elif hasattr(clip, 'resize'):
                clip = clip.resize(height=self.reel_height)
            if clip.w > self.reel_width:
                x_center = clip.w / 2
                if hasattr(clip, 'cropped'):
                    clip = clip.cropped(x_center=x_center, width=self.reel_width)
                elif hasattr(clip, 'crop'):
                    clip = clip.crop(x_center=x_center, width=self.reel_width)
        
        # Create subtitle clips
        subtitle_clips = []
        for subtitle in subtitles:
            txt_clip = self.create_text_clip(
                subtitle.get('text', ''),
                subtitle.get('duration', 3),
                'bottom',
                font_size,
                subtitle.get('start_time', 0)
            )
            subtitle_clips.append(txt_clip)
        
        # Composite
        final_clip = CompositeVideoClip([clip] + subtitle_clips)
        
        # Write
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_clip.write_videofile(
            str(output_path),
            fps=30,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            bitrate='8000k'
        )
        
        # Clean up
        final_clip.close()
        clip.close()
        
        # Clean up any MoviePy temporary files in the project root
        self._cleanup_moviepy_temp_files()
        
        return output_path
    
    def image_to_clip(
        self,
        image_path: Path,
        duration: float = 3.0,
        letterbox: bool = True
    ):
        """
        Convert an image to a video clip, handling EXIF orientation.
        When letterbox=True (default), keeps full width visible and adds black bars
        on top/bottom (or left/right) as needed to fill reel dimensions.
        
        Args:
            image_path: Path to image file.
            duration: Duration of the clip in seconds.
            letterbox: If True, fit full image in frame with black bars; if False, crop to fill.
        
        Returns:
            ImageClip or CompositeVideoClip (with black background when letterbox=True).
        """
        # Load image with PIL to handle EXIF orientation
        img = Image.open(image_path)
        
        # Apply EXIF orientation correction
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        
        # Convert to RGB if necessary (required for moviepy).
        # RGBA/transparent PNGs: composite onto white first so transparent areas aren't black.
        if img.mode != 'RGB':
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and img.info.get('transparency') is not None):
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                background = Image.new('RGBA', img.size, (255, 255, 255, 255))
                img = Image.alpha_composite(background, img)
            img = img.convert('RGB')
        
        # Save to temporary file with correct orientation
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            img.save(tmp_path, 'JPEG', quality=95)
        
        # Create ImageClip from the corrected image
        clip = ImageClip(tmp_path)
        
        if letterbox:
            # Scale to fit full width (no cropping); add black bars top/bottom or left/right
            # Scale so image fits inside (reel_width, reel_height)
            scale_w = self.reel_width / clip.w
            scale_h = self.reel_height / clip.h
            scale = min(scale_w, scale_h)  # fit entirely, no crop
            new_w = int(clip.w * scale)
            new_h = int(clip.h * scale)
            if hasattr(clip, 'resized'):
                clip = clip.resized((new_w, new_h))
            elif hasattr(clip, 'resize'):
                clip = clip.resize((new_w, new_h))
            # Center image on black background
            try:
                black_bg = ColorClip(size=(self.reel_width, self.reel_height), color=(0, 0, 0), duration=duration)
            except TypeError:
                black_bg = ColorClip(size=(self.reel_width, self.reel_height), color=(0, 0, 0))
                black_bg = black_bg.with_duration(duration) if hasattr(black_bg, 'with_duration') else black_bg.set_duration(duration)
            if hasattr(clip, 'with_duration'):
                clip = clip.with_duration(duration)
            elif hasattr(clip, 'set_duration'):
                clip = clip.set_duration(duration)
            # Center position
            x_center = (self.reel_width - new_w) // 2
            y_center = (self.reel_height - new_h) // 2
            if hasattr(clip, 'with_position'):
                clip = clip.with_position((x_center, y_center))
            else:
                clip = clip.set_position((x_center, y_center))
            composite = CompositeVideoClip([black_bg, clip])
            if hasattr(composite, 'with_duration'):
                composite = composite.with_duration(duration)
            composite.tmp_path = tmp_path
            return composite
        else:
            # Legacy: resize to height then center crop width
            if hasattr(clip, 'resized'):
                clip = clip.resized(height=self.reel_height)
            elif hasattr(clip, 'resize'):
                clip = clip.resize(height=self.reel_height)
            if clip.w > self.reel_width:
                x_center = clip.w / 2
                if hasattr(clip, 'cropped'):
                    clip = clip.cropped(x_center=x_center, width=self.reel_width)
                elif hasattr(clip, 'crop'):
                    clip = clip.crop(x_center=x_center, width=self.reel_width)
            if hasattr(clip, 'with_duration'):
                clip = clip.with_duration(duration)
            elif hasattr(clip, 'set_duration'):
                clip = clip.set_duration(duration)
            clip.tmp_path = tmp_path
            return clip
    
    def create_combined_reel(
        self,
        video_paths: List[Path],
        image_paths: Optional[List[Path]] = None,
        quote_text: Optional[str] = None,
        health_benefit_text: Optional[str] = None,
        output_path: Path = None,
        video_duration: float = 5.0,
        image_duration: float = 3.0,
        music_path: Optional[Path] = None
    ) -> Path:
        """
        Create a reel combining videos, images, quotes, and health benefits.
        
        Args:
            video_paths: List of video files to use.
            image_paths: Optional list of image files to include.
            quote_text: Optional quote text to overlay.
            health_benefit_text: Optional health benefit text to overlay.
            output_path: Path to save the reel.
            video_duration: Duration for each video clip segment.
            image_duration: Duration for each image segment.
            music_path: Optional background music.
        
        Returns:
            Path to saved reel.
        """
        clips = []
        current_time = 0
        temp_files = []  # Track temp files for cleanup
        
        # Process videos
        for video_path in video_paths:
            clip = self.prepare_clip(video_path, duration=video_duration)
            # In moviepy 2.x, timing is handled differently - clips are positioned during composition
            # Store start time for later use in composition
            # Position clip at the right time
            if hasattr(clip, 'with_start'):
                clip = clip.with_start(current_time)
            elif hasattr(clip, 'set_start'):
                clip = clip.set_start(current_time)
            clips.append(clip)
            current_time += video_duration
        
        # Process images
        if image_paths:
            for image_path in image_paths:
                img_clip = self.image_to_clip(image_path, duration=image_duration)
                # Store temp file path for cleanup if it exists
                if hasattr(img_clip, 'tmp_path'):
                    temp_files.append(img_clip.tmp_path)
                # Position image clip at the right time
                if hasattr(img_clip, 'with_start'):
                    img_clip = img_clip.with_start(current_time)
                elif hasattr(img_clip, 'set_start'):
                    img_clip = img_clip.set_start(current_time)
                clips.append(img_clip)
                current_time += image_duration
        
        # Concatenate all clips
        if len(clips) > 1:
            final_clip = concatenate_videoclips(clips, method="compose")
        else:
            final_clip = clips[0]
        
        # Ensure minimum duration
        if final_clip.duration < self.min_duration:
            loops_needed = int(self.min_duration / final_clip.duration) + 1
            looped_clips = [final_clip] * loops_needed
            final_clip = concatenate_videoclips(looped_clips, method="compose")
            if hasattr(final_clip, 'subclipped'):
                final_clip = final_clip.subclipped(0, self.min_duration)
            else:
                final_clip = final_clip.subclip(0, self.min_duration)
        
        # Ensure maximum duration
        if final_clip.duration > self.max_duration:
            final_clip = final_clip.subclip(0, self.max_duration)
        
        # Add text overlays
        text_clips = []
        
        # Add quote overlay (appears early in the video)
        if quote_text:
            # Calculate duration based on text length, but ensure it doesn't exceed video duration
            quote_duration = self.calculate_text_duration(quote_text, min_duration=3.0, max_duration=min(10.0, final_clip.duration * 0.4))
            quote_start_time = final_clip.duration * 0.1
            # Ensure quote doesn't extend beyond video end
            if quote_start_time + quote_duration > final_clip.duration:
                quote_duration = max(3.0, final_clip.duration - quote_start_time - 0.5)
            
            quote_clip = self.create_text_clip(
                quote_text,
                duration=quote_duration,
                position='center',
                font_size=65,  # Slightly smaller to ensure it fits
                start_time=quote_start_time,
                auto_duration=False  # Already calculated above
            )
            text_clips.append(quote_clip)
        
        # Add health benefit overlay (appears later)
        if health_benefit_text:
            # Clean up the health benefit text - remove newlines and ensure it's readable
            clean_benefit = health_benefit_text.replace('\n', ' ').strip()
            # Calculate duration based on text length
            benefit_duration = self.calculate_text_duration(clean_benefit, min_duration=3.0, max_duration=min(12.0, final_clip.duration * 0.5))
            benefit_start_time = final_clip.duration * 0.5
            # Ensure benefit text doesn't extend beyond video end
            if benefit_start_time + benefit_duration > final_clip.duration:
                benefit_duration = max(3.0, final_clip.duration - benefit_start_time - 0.5)
            
            benefit_clip = self.create_text_clip(
                clean_benefit,
                duration=benefit_duration,
                position='bottom',
                font_size=55,  # Slightly smaller for bottom text
                start_time=benefit_start_time,
                auto_duration=False  # Already calculated above
            )
            text_clips.append(benefit_clip)
        
        if text_clips:
            final_clip = CompositeVideoClip([final_clip] + text_clips)
        
        # Video fade-out will be applied via ffmpeg filters during write_videofile
        # This is more reliable than trying to use MoviePy's opacity methods on CompositeVideoClip
        
        # Add background music if provided
        if music_path and music_path.exists():
            try:
                audio = AudioFileClip(str(music_path))
                if audio.duration < final_clip.duration:
                    loops = int(final_clip.duration / audio.duration) + 1
                    audio = concatenate_audioclips([audio] * loops)
                    if hasattr(audio, 'subclipped'):
                        audio = audio.subclipped(0, final_clip.duration)
                    else:
                        audio = audio.subclip(0, final_clip.duration)
                else:
                    if hasattr(audio, 'subclipped'):
                        audio = audio.subclipped(0, final_clip.duration)
                    else:
                        audio = audio.subclip(0, final_clip.duration)
                # Lower volume to 30% for background
                # moviepy 2.x uses with_volume_scaled instead of volumex
                if hasattr(audio, 'with_volume_scaled'):
                    audio = audio.with_volume_scaled(0.3)
                elif hasattr(audio, 'volumex'):
                    audio = audio.volumex(0.3)
                else:
                    # Fallback: try to use fx module
                    try:
                        from moviepy.audio.fx import volumex
                        audio = audio.fx(volumex, 0.3)
                    except:
                        pass  # Continue without volume adjustment
                
                # Add fade-out to audio (volume decrease at the end)
                audio_fade_duration = 1.5  # 1.5 second audio fade-out
                if audio.duration > audio_fade_duration:
                    try:
                        # Create a volume function that fades from 1.0 to 0.0
                        fade_start_time = audio.duration - audio_fade_duration
                        def volume_func(t):
                            if t < fade_start_time:
                                return 1.0  # Full volume before fade
                            else:
                                # Fade from 1.0 to 0.0 over audio_fade_duration
                                fade_progress = (t - fade_start_time) / audio_fade_duration
                                return max(0.0, 1.0 - fade_progress)
                        
                        # Apply volume fade using with_volume
                        try:
                            audio = audio.with_volume(volume_func)
                        except AttributeError:
                            # Fallback: try using volumex with a lambda
                            try:
                                # Create a new audio clip with volume applied per frame
                                from moviepy.audio.AudioClip import AudioArrayClip
                                import numpy as np
                                
                                # Get audio array
                                audio_array = audio.to_soundarray(fps=audio.fps)
                                
                                # Apply volume fade
                                for i in range(len(audio_array)):
                                    t = i / audio.fps
                                    vol = volume_func(t)
                                    audio_array[i] = audio_array[i] * vol
                                
                                # Create new audio clip
                                audio = AudioArrayClip(audio_array, fps=audio.fps)
                            except Exception as e:
                                print(f"Warning: Could not apply audio fade-out: {e}")
                    except Exception as e:
                        print(f"Warning: Could not apply audio fade-out: {e}")
                
                # Handle moviepy 2.x API changes
                if hasattr(final_clip, 'with_audio'):
                    final_clip = final_clip.with_audio(audio)
                else:
                    final_clip = final_clip.set_audio(audio)
            except Exception as e:
                print(f"Warning: Could not add music: {e}")
        
        # Write video file with fade-out effects using ffmpeg filters
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Apply fade-out using ffmpeg filters if duration is sufficient
        fade_duration = 1.0  # 1 second video fade-out
        # Audio fade-out is already applied via with_volume method above
        
        if final_clip.duration > fade_duration:
            # Calculate fade start time
            fade_start = final_clip.duration - fade_duration
            
            # Build ffmpeg filter string for video fade-out to white
            # Use geq filter to blend white (255,255,255) into the video over time
            # Formula: blend each RGB channel towards 255 based on fade progress
            fade_end = final_clip.duration
            video_filter = (
                f"geq="
                f"r='if(between(T,{fade_start:.2f},{fade_end:.2f}),"
                f"r+(255-r)*((T-{fade_start:.2f})/{fade_duration:.2f}),r)':"
                f"g='if(between(T,{fade_start:.2f},{fade_end:.2f}),"
                f"g+(255-g)*((T-{fade_start:.2f})/{fade_duration:.2f}),g)':"
                f"b='if(between(T,{fade_start:.2f},{fade_end:.2f}),"
                f"b+(255-b)*((T-{fade_start:.2f})/{fade_duration:.2f}),b)'"
            )
            
            # Write with video fade effect - force re-encoding to apply filter
            final_clip.write_videofile(
                str(output_path),
                fps=30,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                bitrate='8000k',
                audio_bitrate='192k',
                ffmpeg_params=['-vf', video_filter, '-c:v', 'libx264', '-c:a', 'aac']
            )
        else:
            final_clip.write_videofile(
                str(output_path),
                fps=30,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                bitrate='8000k'
            )
        
        # Clean up
        final_clip.close()
        for clip in clips:
            clip.close()
        
        # Clean up temporary image files
        for tmp_file in temp_files:
            try:
                if os.path.exists(tmp_file):
                    os.unlink(tmp_file)
            except Exception:
                pass  # Ignore cleanup errors
        
        # Clean up any MoviePy temporary files in the project root
        self._cleanup_moviepy_temp_files()
        
        return output_path
    
    def _cleanup_moviepy_temp_files(self):
        """Clean up MoviePy temporary files that may have been created in the project root."""
        try:
            project_root = Path(__file__).parent.parent
            # Find all TEMP_MPY files in project root
            temp_files = list(project_root.glob('*TEMP_MPY*.mp4'))
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                        print(f"Cleaned up temporary file: {temp_file.name}")
                except Exception:
                    pass  # Ignore cleanup errors
        except Exception:
            pass  # Ignore cleanup errors


def main():
    """Test function."""
    processor = VideoProcessor()
    print("Video processor initialized.")
    print(f"Reel dimensions: {processor.reel_width}x{processor.reel_height}")
    print(f"Duration range: {processor.min_duration}-{processor.max_duration} seconds")


if __name__ == '__main__':
    main()
