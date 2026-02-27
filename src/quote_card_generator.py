"""
Quote Card Generator Module

Generates quote cards from accepted quotes with options for:
- White background quote cards
- Quote cards overlaid on photos
- Quote cards overlaid on videos
"""

import random
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .image_processor import ImageProcessor
try:
    from .video_processor import VideoProcessor
except ImportError:
    VideoProcessor = None
from .utils import load_config


class QuoteCardGenerator:
    """Generate quote cards from accepted quotes."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize quote card generator.
        
        Args:
            config: Configuration dictionary. If None, loads from file.
        """
        if config is None:
            config = load_config()
        
        self.config = config
        self.assets_base_path = Path(__file__).parent.parent / 'assets'
        self.output_base_path = Path(__file__).parent.parent / 'output'
        self.knowledge_dir = self.assets_base_path / '10_knowledge'
        
        # Initialize processors
        self.image_processor = ImageProcessor(config)
        try:
            if VideoProcessor:
                self.video_processor = VideoProcessor(config)
            else:
                self.video_processor = None
        except Exception as e:
            print(f"Warning: Video processor not available: {e}")
            self.video_processor = None
        
        # Ensure output directories exist
        (self.output_base_path / 'quote_cards').mkdir(parents=True, exist_ok=True)
    
    def get_quote_status(self, quote: Dict) -> str:
        """Get quote status: pending, accepted, or rejected."""
        if 'status' in quote:
            status = quote['status'].lower()
            if status in ['pending', 'accepted', 'rejected']:
                return status
        # Legacy support: convert approved boolean to status
        if quote.get('approved', False):
            return 'accepted'
        return 'pending'
    
    def load_accepted_quotes(self, group_name: Optional[str] = None) -> List[Dict]:
        """
        Load all accepted quotes from literature groups.
        
        Args:
            group_name: Optional specific group name. If None, loads from all groups.
        
        Returns:
            List of accepted quote dictionaries.
        """
        accepted_quotes = []
        
        if group_name:
            # Load from specific group
            quotes_file = self.knowledge_dir / group_name / 'quotes.json'
            if quotes_file.exists():
                with open(quotes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    quotes = data.get('quotes', [])
                    for quote in quotes:
                        if self.get_quote_status(quote) == 'accepted':
                            quote['group'] = group_name
                            accepted_quotes.append(quote)
        else:
            # Load from all groups
            if not self.knowledge_dir.exists():
                return []
            
            for group_dir in self.knowledge_dir.iterdir():
                if group_dir.is_dir():
                    quotes_file = group_dir / 'quotes.json'
                    if quotes_file.exists():
                        with open(quotes_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            quotes = data.get('quotes', [])
                            for quote in quotes:
                                if self.get_quote_status(quote) == 'accepted':
                                    quote['group'] = group_dir.name
                                    accepted_quotes.append(quote)
        
        return accepted_quotes
    
    def get_random_accepted_quote(self, group_name: Optional[str] = None) -> Optional[Dict]:
        """
        Get a random accepted quote.
        
        Args:
            group_name: Optional specific group name.
        
        Returns:
            Random accepted quote dictionary or None if no quotes found.
        """
        accepted_quotes = self.load_accepted_quotes(group_name)
        if not accepted_quotes:
            return None
        return random.choice(accepted_quotes)
    
    def get_available_media_files(self, directory: Path, extensions: List[str]) -> List[Path]:
        """
        Get available media files from a directory.
        
        Args:
            directory: Directory path to search.
            extensions: List of file extensions to include (e.g., ['.jpg', '.png']).
        
        Returns:
            List of file paths.
        """
        if not directory.exists() or not directory.is_dir():
            return []
        
        media_files = []
        for ext in extensions:
            media_files.extend(directory.glob(f'*{ext}'))
            media_files.extend(directory.glob(f'*{ext.upper()}'))
        
        return sorted(media_files)
    
    def generate_white_background_card(
        self,
        quote: Dict,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate a quote card with white background.
        
        Args:
            quote: Quote dictionary with 'text' and optionally 'author' or 'source'.
            output_path: Optional output path. If None, generates timestamped filename.
        
        Returns:
            Path to generated image.
        """
        quote_text = quote.get('text', '')
        author = quote.get('author') or quote.get('source') or quote.get('group', 'Yoga Wisdom')
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_base_path / 'quote_cards' / f'quote_white_{timestamp}.jpg'
        
        return self.image_processor.create_quote_card(
            quote=quote_text,
            author=author,
            output_path=output_path
        )
    
    def generate_photo_overlay_card(
        self,
        quote: Dict,
        photo_paths: List[Path],
        output_path: Optional[Path] = None
    ) -> List[Path]:
        """
        Generate quote cards overlaid on photos.
        
        Args:
            quote: Quote dictionary with 'text' and optionally 'author' or 'source'.
            photo_paths: List of photo paths to overlay quote on.
            output_path: Optional base output path. If None, generates timestamped filenames.
        
        Returns:
            List of paths to generated images.
        """
        quote_text = quote.get('text', '')
        author = quote.get('author') or quote.get('source') or quote.get('group', 'Yoga Wisdom')
        overlay_text = f"{quote_text}\n\n— {author}"
        
        generated_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, photo_path in enumerate(photo_paths):
            if output_path is None:
                output_file = self.output_base_path / 'quote_cards' / f'quote_photo_{timestamp}_{i+1}.jpg'
            else:
                # If single output path provided, append index for multiple photos
                if len(photo_paths) > 1:
                    output_file = output_path.parent / f"{output_path.stem}_{i+1}{output_path.suffix}"
                else:
                    output_file = output_path
            
            processed_path = self.image_processor.process_image(
                image_path=photo_path,
                output_path=output_file,
                text_overlay=overlay_text,
                text_position='bottom',
                font_size=24  # Slightly larger for photo overlays
            )
            generated_paths.append(processed_path)
        
        return generated_paths
    
    def generate_video_overlay_card(
        self,
        quote: Dict,
        video_paths: List[Path],
        output_path: Optional[Path] = None,
        video_duration: float = 5.0,
        music_path: Optional[Path] = None
    ) -> List[Path]:
        """
        Generate quote cards overlaid on videos.
        
        Args:
            quote: Quote dictionary with 'text' and optionally 'author' or 'source'.
            video_paths: List of video paths to overlay quote on.
            output_path: Optional base output path. If None, generates timestamped filenames.
            video_duration: Duration for each video clip in seconds.
            music_path: Optional path to background music file (.mp3, .wav, etc.).
        
        Returns:
            List of paths to generated videos.
        """
        if not self.video_processor:
            raise ValueError("Video processor not available. Install moviepy to use video overlays.")
        
        quote_text = quote.get('text', '')
        author = quote.get('author') or quote.get('source') or quote.get('group', 'Yoga Wisdom')
        overlay_text = f"{quote_text}\n\n— {author}"
        
        generated_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, video_path in enumerate(video_paths):
            if output_path is None:
                output_file = self.output_base_path / 'quote_cards' / f'quote_video_{timestamp}_{i+1}.mp4'
            else:
                # If single output path provided, append index for multiple videos
                if len(video_paths) > 1:
                    output_file = output_path.parent / f"{output_path.stem}_{i+1}{output_path.suffix}"
                else:
                    output_file = output_path
            
            # Create video with text overlay (and optional background music)
            processed_path = self.video_processor.create_video_with_text_overlay(
                video_path=video_path,
                text_overlay=overlay_text,
                output_path=output_file,
                duration=video_duration,
                text_position='bottom',
                music_path=music_path
            )
            generated_paths.append(processed_path)
        
        return generated_paths
    
    # Flyer text: Ajuda Public Garden
    DEFAULT_FLYER_LINES = [
        "Hatha Yoga",
        "",
        "Sundays 11h15 - 12h45",
        "",
        "Contact: Roel Heremans",
        "",
        "      (+351) 913 00 00 48",
        "",
        "Hope to welcome you!",
    ]

    # Flyer text: Casa Velha do Palheiro
    FLYER_LINES_PALHEIRO = [
        "Hatha Yoga @ Casa Velha do Palheiro",
        "Wednesdays 18h00 - 19h00",
        "Contact: Roel Heremans",
        "(+351) 913 00 00 48",
        "",
        "Hope to welcome you!",
    ]

    def generate_image_video_quote_card(
        self,
        quote: Dict,
        image_paths: List[Path],
        output_path: Optional[Path] = None,
        duration: float = 15.0,
        music_path: Optional[Path] = None,
        audio_fade_duration: float = 3.0,
        video_fade_duration: float = 2.0,
        flyer_lines: Optional[list] = None,
        flyer_duration: float = 15.0,
        flyer_font_size: int = 46
    ) -> Path:
        """
        Generate a video quote card from one or more background images: quote overlay,
        optional music, optional yoga flyer segment (white + text), fades to white.
        When multiple images are given, --duration is split equally across them.
        
        Args:
            quote: Quote dict with 'text' and optionally 'author' or 'source'.
            image_paths: Path(s) to background image file(s).
            output_path: Optional output path. If None, uses default in quote_cards/.
            duration: Total quote segment duration in seconds (default 15); split across images.
            music_path: Optional background music file.
            audio_fade_duration: Seconds for music to fade to silence at end (default 3).
            video_fade_duration: Seconds for video to fade to white at segment ends (default 2).
            flyer_lines: Optional list of lines for yoga flyer (adds second segment); use default if True.
            flyer_duration: Duration of flyer segment in seconds (default 15).
            flyer_font_size: Font size for flyer text (default 46).
        
        Returns:
            Path to the generated video file.
        """
        if not self.video_processor:
            raise ValueError("Video processor not available. Install moviepy to use image video quote cards.")
        if not image_paths:
            raise ValueError("At least one image path is required.")
        for p in image_paths:
            if not Path(p).exists():
                raise FileNotFoundError(f"Image not found: {p}")
        
        quote_text = quote.get('text', '')
        author = quote.get('author') or quote.get('source') or quote.get('group', 'Yoga Wisdom')
        overlay_text = f"{quote_text}\n\n— {author}"
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_base_path / 'quote_cards' / f'quote_image_video_{timestamp}.mp4'
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if flyer_lines is True:
            flyer_lines = self.DEFAULT_FLYER_LINES
        elif flyer_lines is None:
            flyer_lines = []
        
        return self.video_processor.create_image_quote_video(
            image_paths=image_paths,
            text_overlay=overlay_text,
            output_path=output_path,
            duration=duration,
            music_path=music_path,
            audio_fade_duration=audio_fade_duration,
            video_fade_duration=video_fade_duration,
            text_position='bottom',
            font_size=60,
            flyer_lines=flyer_lines if flyer_lines else None,
            flyer_duration=flyer_duration,
            flyer_font_size=flyer_font_size
        )
    
    def generate_quote_cards(
        self,
        group_name: Optional[str] = None,
        quote_id: Optional[str] = None,
        photo_dir: Optional[Path] = None,
        video_dir: Optional[Path] = None,
        num_photos: int = 1,
        num_videos: int = 1,
        white_background: bool = False,
        output_dir: Optional[Path] = None,
        music_path: Optional[Path] = None,
        image_paths: Optional[List[Path]] = None,
        image_video_duration: float = 15.0,
        image_audio_fade_duration: float = 3.0,
        image_video_fade_duration: float = 2.0,
        use_flyer: bool = False,
        flyer_lines: Optional[list] = None,
        flyer_duration: float = 15.0,
        flyer_font_size: int = 52
    ) -> Dict[str, List[Path]]:
        """
        Generate quote cards based on options.
        
        Args:
            ...
            use_flyer: If True, add yoga flyer segment (white + text) after quote segment.
            flyer_lines: Optional list of lines for flyer; if use_flyer and None, use default Ajuda text.
            flyer_duration: Duration of flyer segment in seconds (default 15).
            flyer_font_size: Font size for flyer text (default 46).
        
        Returns:
            Dictionary with 'white_background', 'photos', 'videos', 'image_videos' keys containing lists of paths.
        """
        results = {
            'white_background': [],
            'photos': [],
            'videos': [],
            'image_videos': []
        }
        
        # Get quote
        if quote_id:
            # Find specific quote by ID
            accepted_quotes = self.load_accepted_quotes(group_name)
            quote = next((q for q in accepted_quotes if q.get('id') == quote_id), None)
            if not quote:
                raise ValueError(f"Quote with ID '{quote_id}' not found in accepted quotes.")
        else:
            # Get random quote
            quote = self.get_random_accepted_quote(group_name)
            if not quote:
                raise ValueError("No accepted quotes found. Please approve quotes first using the quote reviewer.")
        
        print(f"Using quote: {quote.get('text', '')[:100]}...")
        print(f"Source: {quote.get('group', 'Unknown')}")
        
        # Set output directory
        if output_dir is None:
            output_dir = self.output_base_path / 'quote_cards'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate white background card if requested
        if white_background:
            output_path = output_dir / f'quote_white_{timestamp}.jpg'
            card_path = self.generate_white_background_card(quote, output_path)
            results['white_background'].append(card_path)
            print(f"✓ Generated white background card: {card_path}")
        
        # Generate image-as-video quote card (one or more images, quote overlay, music, fade to white)
        if image_paths:
            if not self.video_processor:
                print("Warning: Video processor not available. Skipping image video card.")
            else:
                image_paths = [Path(p) for p in image_paths]
                output_path = output_dir / f'quote_image_video_{timestamp}.mp4'
                flyer_lines_arg = (flyer_lines or self.DEFAULT_FLYER_LINES) if use_flyer else None
                card_path = self.generate_image_video_quote_card(
                    quote,
                    image_paths=image_paths,
                    output_path=output_path,
                    duration=image_video_duration,
                    music_path=music_path,
                    audio_fade_duration=image_audio_fade_duration,
                    video_fade_duration=image_video_fade_duration,
                    flyer_lines=flyer_lines_arg,
                    flyer_duration=flyer_duration,
                    flyer_font_size=flyer_font_size
                )
                results['image_videos'].append(card_path)
                print(f"✓ Generated image video quote card: {card_path}")
        
        # Generate photo overlay cards if photo directory provided
        if photo_dir:
            photo_dir = Path(photo_dir)
            available_photos = self.get_available_media_files(
                photo_dir,
                ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
            )
            
            if not available_photos:
                print(f"Warning: No photos found in {photo_dir}")
            else:
                # Select photos
                selected_photos = random.sample(
                    available_photos,
                    min(num_photos, len(available_photos))
                )
                
                for i, photo_path in enumerate(selected_photos):
                    output_path = output_dir / f'quote_photo_{timestamp}_{i+1}.jpg'
                    card_paths = self.generate_photo_overlay_card(
                        quote,
                        [photo_path],
                        output_path
                    )
                    results['photos'].extend(card_paths)
                    print(f"✓ Generated photo overlay card: {card_paths[0]}")
        
        # Generate video overlay cards if video directory provided
        if video_dir:
            if not self.video_processor:
                print("Warning: Video processor not available. Skipping video overlays.")
            else:
                video_dir = Path(video_dir)
                available_videos = self.get_available_media_files(
                    video_dir,
                    ['.mp4', '.mov', '.avi', '.MP4', '.MOV', '.AVI']
                )
                
                if not available_videos:
                    print(f"Warning: No videos found in {video_dir}")
                else:
                    # Select videos
                    selected_videos = random.sample(
                        available_videos,
                        min(num_videos, len(available_videos))
                    )
                    
                    for i, video_path in enumerate(selected_videos):
                        output_path = output_dir / f'quote_video_{timestamp}_{i+1}.mp4'
                        video_paths = self.generate_video_overlay_card(
                            quote,
                            [video_path],
                            output_path,
                            music_path=music_path
                        )
                        results['videos'].extend(video_paths)
                        print(f"✓ Generated video overlay card: {video_paths[0]}")
        
        return results
