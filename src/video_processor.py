"""
Video Processor Module

Creates Instagram Reels with clips, music, text overlays, and transitions.
"""

try:
    from moviepy import VideoFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, ImageClip, AudioFileClip, concatenate_audioclips, ColorClip
except ImportError:
    # Fallback for older moviepy versions
    try:
        from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, ImageClip, AudioFileClip, concatenate_audioclips, ColorClip
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
    
    def _add_white_fade_overlay(self, clip, video_fade_duration: float, fps: float = 30):
        """Add a white overlay that fades in over the last video_fade_duration seconds.
        Caller is responsible for closing the original clip when done."""
        if clip.duration <= video_fade_duration:
            return clip
        fade_start = clip.duration - video_fade_duration
        w, h = int(clip.w), int(clip.h)
        try:
            white_clip = ColorClip(size=(w, h), color=(255, 255, 255), duration=video_fade_duration)
        except TypeError:
            white_clip = ColorClip(size=(w, h), color=(255, 255, 255))
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
        text_overlay: str,
        output_path: Path,
        duration: float = 15.0,
        music_path: Optional[Path] = None,
        audio_fade_duration: float = 3.0,
        video_fade_duration: float = 0.8,
        text_position: str = 'bottom',
        font_size: int = 64,
        flyer_lines: Optional[List[str]] = None,
        flyer_duration: float = 15.0,
        flyer_font_size: int = 40,
        flyer_logo_path: Optional[Path] = None
    ) -> Path:
        """
        Create a video from one or more images with quote overlay, optional music,
        optional yoga flyer segment (white + text, optional logo), and fades to white.
        When multiple images are given, duration is split equally across them.
        
        Args:
            image_paths: Path(s) to background image file(s).
            text_overlay: Quote text (and optional author) to overlay.
            output_path: Path to save the output video.
            duration: Total quote segment duration in seconds (default 15); split across images.
            music_path: Optional path to background music (.mp3, .wav, etc.).
            audio_fade_duration: Seconds over which music fades to silence at end (default 3).
            video_fade_duration: Seconds over which video fades to white at segment ends (default 0.8).
            text_position: Position of text ('top', 'center', 'bottom').
            font_size: Font size for quote overlay (default 32).
            flyer_lines: Optional list of lines for yoga flyer (white BG + text); adds second segment.
            flyer_duration: Duration of flyer segment in seconds (default 15).
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
        # Quote font: bigger for readability on photos
        quote_font_size = min(font_size, max(40, (top_black - 20) // 3))
        # Place quote at bottom of frame so transparent box has room and covers text fully
        text_clip = self.create_text_clip(
            text=text_overlay,
            duration=duration,
            position='bottom',
            font_size=quote_font_size,
            start_time=0,
            override_y_center=None,
            quote_overlay_style=True
        )
        segment_1 = CompositeVideoClip([image_clip, text_clip])
        if hasattr(segment_1, 'with_fps'):
            segment_1 = segment_1.with_fps(fps)
        elif hasattr(segment_1, 'set_fps'):
            segment_1 = segment_1.set_fps(fps)
        segment_1 = self._add_white_fade_overlay(segment_1, video_fade_duration, fps)
        
        if not use_flyer:
            final_clip = segment_1
        else:
            # ---- Segment 2: white background + optional logo + flyer text ----
            w, h = self.reel_width, self.reel_height
            try:
                white_bg = ColorClip(size=(w, h), color=(255, 255, 255), duration=flyer_duration)
            except TypeError:
                white_bg = ColorClip(size=(w, h), color=(255, 255, 255))
                white_bg = white_bg.with_duration(flyer_duration) if hasattr(white_bg, 'with_duration') else white_bg.set_duration(flyer_duration)
            if hasattr(white_bg, 'with_fps'):
                white_bg = white_bg.with_fps(fps)
            elif hasattr(white_bg, 'set_fps'):
                white_bg = white_bg.set_fps(fps)
            flyer_layers = [white_bg]
            logo_top_margin = 80
            logo_max_width_ratio = 0.55
            text_y_center_override = None
            if flyer_logo_path and Path(flyer_logo_path).exists():
                try:
                    logo_img = Image.open(flyer_logo_path)
                    logo_img = ImageOps.exif_transpose(logo_img)
                    if logo_img.mode in ('RGBA', 'LA') or (logo_img.mode == 'P' and logo_img.info.get('transparency') is not None):
                        if logo_img.mode != 'RGBA':
                            logo_img = logo_img.convert('RGBA')
                        bg = Image.new('RGBA', logo_img.size, (255, 255, 255, 255))
                        logo_img = Image.alpha_composite(bg, logo_img)
                    logo_img = logo_img.convert('RGB')
                    lw, lh = logo_img.size
                    max_logo_w = int(w * logo_max_width_ratio)
                    scale = min(1.0, max_logo_w / lw)
                    new_lw, new_lh = int(lw * scale), int(lh * scale)
                    try:
                        resample = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample = Image.LANCZOS
                    logo_img = logo_img.resize((new_lw, new_lh), resample)
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                        logo_img.save(tmp.name, 'JPEG', quality=95)
                        logo_tmp = tmp.name
                    logo_clip = ImageClip(logo_tmp)
                    logo_clip = logo_clip.with_duration(flyer_duration) if hasattr(logo_clip, 'with_duration') else logo_clip.set_duration(flyer_duration)
                    if hasattr(logo_clip, 'with_fps'):
                        logo_clip = logo_clip.with_fps(fps)
                    elif hasattr(logo_clip, 'set_fps'):
                        logo_clip = logo_clip.set_fps(fps)
                    logo_x = (w - new_lw) // 2
                    logo_y = logo_top_margin
                    logo_clip = logo_clip.with_position((logo_x, logo_y)) if hasattr(logo_clip, 'with_position') else logo_clip.set_position((logo_x, logo_y))
                    flyer_layers.append(logo_clip)
                    text_region_top = logo_y + new_lh + 40
                    text_region_height = h - text_region_top - 80
                    text_y_center_override = text_region_top + text_region_height // 2
                except Exception as e:
                    print(f"Warning: Could not load flyer logo {flyer_logo_path}: {e}")
            flyer_title_font_size = 72
            flyer_body_font_size = max(flyer_font_size, 40)
            if len(flyer_lines) >= 2:
                title_line = flyer_lines[0]
                body_text = '\n'.join(flyer_lines[1:])
                title_clip = self.create_text_clip(
                    text=title_line,
                    duration=flyer_duration,
                    position='center',
                    font_size=flyer_title_font_size,
                    start_time=0,
                    auto_duration=False,
                    flyer_style=True,
                    preserve_newlines=False,
                    skip_position=True
                )
                body_clip = self.create_text_clip(
                    text=body_text,
                    duration=flyer_duration,
                    position='center',
                    font_size=flyer_body_font_size,
                    start_time=0,
                    auto_duration=False,
                    flyer_style=True,
                    preserve_newlines=True,
                    skip_position=True
                )
                if hasattr(title_clip, 'with_fps'):
                    title_clip = title_clip.with_fps(fps)
                elif hasattr(title_clip, 'set_fps'):
                    title_clip = title_clip.set_fps(fps)
                if hasattr(body_clip, 'with_fps'):
                    body_clip = body_clip.with_fps(fps)
                elif hasattr(body_clip, 'set_fps'):
                    body_clip = body_clip.set_fps(fps)
                title_h = int(getattr(title_clip, 'h', 80))
                body_h = int(getattr(body_clip, 'h', 200))
                gap = 28
                center_y = text_y_center_override if text_y_center_override is not None else h // 2
                block_top = center_y - (title_h + gap + body_h) // 2
                title_clip = title_clip.with_position(('center', block_top)) if hasattr(title_clip, 'with_position') else title_clip.set_position(('center', block_top))
                body_clip = body_clip.with_position(('center', block_top + title_h + gap)) if hasattr(body_clip, 'with_position') else body_clip.set_position(('center', block_top + title_h + gap))
                flyer_layers.append(title_clip)
                flyer_layers.append(body_clip)
            else:
                flyer_text = '\n'.join(flyer_lines)
                flyer_text_clip = self.create_text_clip(
                    text=flyer_text,
                    duration=flyer_duration,
                    position='center',
                    font_size=flyer_body_font_size,
                    start_time=0,
                    auto_duration=False,
                    flyer_style=True,
                    preserve_newlines=True,
                    override_y_center=text_y_center_override
                )
                if hasattr(flyer_text_clip, 'with_fps'):
                    flyer_text_clip = flyer_text_clip.with_fps(fps)
                elif hasattr(flyer_text_clip, 'set_fps'):
                    flyer_text_clip = flyer_text_clip.set_fps(fps)
                flyer_layers.append(flyer_text_clip)
            segment_2 = CompositeVideoClip(flyer_layers)
            if hasattr(segment_2, 'with_fps'):
                segment_2 = segment_2.with_fps(fps)
            segment_2 = self._add_white_fade_overlay(segment_2, video_fade_duration, fps)
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
