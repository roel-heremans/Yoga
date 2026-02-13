"""
Content Generator Module

Main orchestrator that coordinates all processors to generate Instagram content.
"""

import random
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .pdf_processor import PDFProcessor
from .ai_caption_generator import AICaptionGenerator
from .image_processor import ImageProcessor
try:
    from .video_processor import VideoProcessor
except ImportError:
    VideoProcessor = None  # Video processing optional if moviepy not available
from .utils import load_config, get_theme_config, ensure_output_dirs


class ContentGenerator:
    """Main content generator orchestrator."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize content generator.
        
        Args:
            config: Configuration dictionary. If None, loads from file.
        """
        if config is None:
            config = load_config()
        
        self.config = config
        self.assets_base_path = Path(__file__).parent.parent / 'assets'
        self.output_base_path = Path(__file__).parent.parent / 'output'
        
        # Initialize processors
        self.pdf_processor = PDFProcessor(self.assets_base_path)
        self.ai_generator = AICaptionGenerator(config)
        self.image_processor = ImageProcessor(config)
        try:
            if VideoProcessor:
                self.video_processor = VideoProcessor(config)
            else:
                self.video_processor = None
        except Exception as e:
            print(f"Warning: Video processor not available: {e}")
            self.video_processor = None
        
        ensure_output_dirs()
        
        # Ensure posted-on-social-media directory exists
        (self.output_base_path / 'posted-on-social-media').mkdir(parents=True, exist_ok=True)
    
    def _load_used_assets(self) -> Dict[str, set]:
        """
        Load all previously used assets from metadata files.
        
        Returns:
            Dictionary with sets of used assets:
            - 'images': set of image paths
            - 'videos': set of video paths
            - 'quotes': set of quote texts
            - 'health_benefits': set of health benefit texts
            - 'music': set of music file paths
        """
        used_assets = {
            'images': set(),
            'videos': set(),
            'quotes': set(),
            'health_benefits': set(),
            'music': set()
        }
        
        # Load feed post metadata
        feed_metadata_dir = self.output_base_path / 'feed_posts'
        if feed_metadata_dir.exists():
            for metadata_file in feed_metadata_dir.glob('*_metadata.json'):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        
                        # Track image sources
                        image_source = metadata.get('image_source', '')
                        if image_source and image_source not in ('quote_card_from_collection', 'quote_card_generated'):
                            # It's an actual image path
                            used_assets['images'].add(image_source)
                        
                        # Track quotes if available
                        if 'quote' in metadata:
                            used_assets['quotes'].add(metadata['quote'])
                except Exception:
                    pass  # Skip invalid metadata files
        
        # Load reel metadata
        reel_metadata_dir = self.output_base_path / 'reels'
        if reel_metadata_dir.exists():
            for metadata_file in reel_metadata_dir.glob('*_metadata.json'):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        
                        # Track video sources
                        video_sources = metadata.get('video_sources', [])
                        for video_source in video_sources:
                            used_assets['videos'].add(video_source)
                        
                        # Track image sources
                        image_sources = metadata.get('image_sources', [])
                        for image_source in image_sources:
                            used_assets['images'].add(image_source)
                        
                        # Track quotes
                        quote = metadata.get('quote')
                        if quote:
                            used_assets['quotes'].add(quote)
                        
                        # Track health benefits
                        health_benefit = metadata.get('health_benefit')
                        if health_benefit:
                            # Normalize by removing newlines and extra spaces
                            normalized = ' '.join(health_benefit.split())
                            used_assets['health_benefits'].add(normalized)
                        
                        # Track music (if stored in metadata)
                        music = metadata.get('music')
                        if music:
                            used_assets['music'].add(music)
                except Exception:
                    pass  # Skip invalid metadata files
        
        return used_assets
    
    def _select_unused_asset(self, available_assets: List[Path], used_assets: set, asset_type: str = 'file') -> Optional[Path]:
        """
        Select an asset that hasn't been used before.
        
        Args:
            available_assets: List of available asset paths.
            used_assets: Set of already-used asset paths (can be strings or Paths).
            asset_type: Type of asset ('file' or 'path').
        
        Returns:
            Path to unused asset, or None if all are used.
        """
        if not available_assets:
            return None
        
        # Convert used_assets to normalized paths for comparison
        used_paths = set()
        for p in used_assets:
            try:
                if isinstance(p, (str, Path)):
                    used_paths.add(str(Path(p).resolve()))
                else:
                    used_paths.add(str(p))
            except Exception:
                # If resolve fails, use string representation
                used_paths.add(str(p))
        
        # Filter out used assets
        unused_assets = []
        for asset in available_assets:
            try:
                asset_path = str(asset.resolve()) if isinstance(asset, Path) else str(asset)
                if asset_path not in used_paths:
                    unused_assets.append(asset)
            except Exception:
                # If resolve fails, use string comparison
                asset_str = str(asset)
                if asset_str not in used_paths:
                    unused_assets.append(asset)
        
        # If all assets are used, reset and use all available (allow reuse)
        if not unused_assets:
            print(f"Warning: All {asset_type} assets have been used. Resetting and allowing reuse.")
            unused_assets = available_assets
        
        # Select randomly from unused assets
        return random.choice(unused_assets) if unused_assets else None
    
    def _load_posted_quotes(self) -> set:
        """
        Load all posted quote IDs from metadata files in posted-on-social-media folder.
        
        Returns:
            Set of posted quote IDs.
        """
        posted_ids = set()
        posted_dir = self.output_base_path / 'posted-on-social-media'
        
        if not posted_dir.exists():
            return posted_ids
        
        for metadata_file in posted_dir.glob('*_metadata.json'):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    quote_id = metadata.get('quote_id')
                    if quote_id:
                        posted_ids.add(quote_id)
            except Exception:
                pass
        
        return posted_ids
    
    def _is_quote_posted(self, quote_id: str) -> bool:
        """
        Check if a quote has been posted by examining metadata files.
        
        Args:
            quote_id: Quote ID to check.
        
        Returns:
            True if quote has been posted, False otherwise.
        """
        posted_ids = self._load_posted_quotes()
        return quote_id in posted_ids
    
    def _select_unused_quote(self, used_quotes: set) -> Optional[Dict]:
        """
        Select a quote that hasn't been used before.
        
        Args:
            used_quotes: Set of already-used quote texts (for backward compatibility).
        
        Returns:
            Quote dictionary or None if no unused quotes available.
        """
        try:
            from .quote_generator import QuoteGenerator
            quote_gen = QuoteGenerator()
            
            # Get random quote (automatically excludes posted quotes)
            quote = quote_gen.get_random_quote(exclude_posted=True)
            
            if quote:
                return quote
            
            # Fallback: try without excluding posted
            quote = quote_gen.get_random_quote(exclude_posted=False)
            return quote
            
        except Exception as e:
            print(f"Warning: Could not load quotes: {e}")
            return None
    
    def _select_unused_health_benefit(self, theme_name: str, used_benefits: set) -> Optional[str]:
        """
        Select a health benefit/key point that hasn't been used before.
        
        Args:
            theme_name: Name of the theme.
            used_benefits: Set of already-used health benefit texts.
        
        Returns:
            Unused health benefit text, or None if all are used.
        """
        # Try to get key points from JSON first
        json_content = self.pdf_processor.load_processed_content(theme_name)
        if json_content and 'summary' in json_content:
            all_key_points = json_content['summary'].get('combined_key_points', [])
            # Also check per-PDF key points
            for pdf_data in json_content.get('pdfs', []):
                all_key_points.extend(pdf_data.get('key_points', []))
        else:
            # Fallback: get from PDFs
            pdf_text = self.pdf_processor.get_combined_text(theme_name, max_pages_per_pdf=5)
            if pdf_text:
                all_key_points = self.pdf_processor.extract_key_points(pdf_text, max_points=20)
            else:
                all_key_points = []
        
        if not all_key_points:
            return None
        
        # Normalize used benefits for comparison
        normalized_used = {' '.join(b.split()) for b in used_benefits}
        
        # Filter out used benefits
        unused_benefits = [
            benefit for benefit in all_key_points
            if ' '.join(benefit.split()) not in normalized_used
        ]
        
        # If all benefits are used, reset and use all available
        if not unused_benefits:
            print("Warning: All health benefits have been used. Resetting and allowing reuse.")
            unused_benefits = all_key_points
        
        if not unused_benefits:
            return None
        
        # Select randomly and ensure it fits on screen
        selected = random.choice(unused_benefits)
        
        # Truncate if too long (max 200 chars for video)
        if len(selected) > 200:
            truncated = selected[:200]
            last_period = truncated.rfind('.')
            last_exclamation = truncated.rfind('!')
            last_question = truncated.rfind('?')
            last_sentence_end = max(last_period, last_exclamation, last_question)
            
            if last_sentence_end > 50:
                selected = selected[:last_sentence_end + 1].strip()
            else:
                last_space = truncated.rfind(' ')
                if last_space > 150:
                    selected = selected[:last_space].strip() + "..."
                else:
                    selected = truncated.strip() + "..."
        
        return selected.strip()
    
    def _validate_path(self, path: Path, path_type: str = "file") -> Path:
        """
        Validate that a path exists and convert relative paths to absolute.
        
        Args:
            path: Path to validate (can be string or Path).
            path_type: Type of path ('file' or 'directory').
        
        Returns:
            Absolute Path object.
        
        Raises:
            ValueError: If path doesn't exist or is wrong type.
        """
        if isinstance(path, str):
            path = Path(path)
        
        # Convert to absolute path if relative
        if not path.is_absolute():
            path = Path(__file__).parent.parent / path
        
        if not path.exists():
            raise ValueError(f"{path_type.capitalize()} {path} not found")
        
        if path_type == 'file' and not path.is_file():
            raise ValueError(f"Path {path} is not a file")
        elif path_type == 'directory' and not path.is_dir():
            raise ValueError(f"Path {path} is not a directory")
        
        return path
    
    def find_assets(self, theme_name: str, asset_type: str) -> List[Path]:
        """
        Find assets of a specific type.
        
        New structure:
        - Images: assets/01_images/
        - Videos: assets/02_videos/
        - Quotes: assets/03_kombucha_quotes/
        - PDFs: assets/04_immune_system/, assets/05_kombucha_benefits/, etc.
        
        Args:
            theme_name: Name of the theme (used for PDFs only, e.g., '04_immune_system').
            asset_type: Type of asset ('images', 'videos', 'pdfs', 'quotes').
        
        Returns:
            List of asset paths.
        """
        if asset_type == 'images':
            # Images are in assets/01_images/
            assets_path = self.assets_base_path / '01_images'
            extensions = ['.jpg', '.jpeg', '.png', '.webp']
        elif asset_type == 'videos':
            # Videos are in assets/02_videos/
            assets_path = self.assets_base_path / '02_videos'
            extensions = ['.mp4', '.mov', '.avi', '.mkv']
        elif asset_type == 'quotes':
            # Quotes are in assets/03_kombucha_quotes/
            assets_path = self.assets_base_path / '03_kombucha_quotes'
            extensions = ['.txt']
        elif asset_type == 'pdfs':
            # PDFs are in numbered theme folders/pdfs subfolder (e.g., assets/04_immune_system/pdfs/)
            assets_path = self.assets_base_path / theme_name / 'pdfs'
            extensions = ['.pdf']
        else:
            return []
        
        if not assets_path.exists():
            return []
        
        assets = []
        for ext in extensions:
            assets.extend(assets_path.glob(f'*{ext}'))
            assets.extend(assets_path.glob(f'*{ext.upper()}'))
        
        return sorted(assets)
    
    def generate_feed_post(
        self,
        theme_name: str,
        image_path: Optional[Path] = None,
        text_overlay: Optional[str] = None,
        use_pdf_content: bool = True,
        use_quote: bool = False
    ) -> Dict[str, Path]:
        """
        Generate an Instagram feed post.
        
        Args:
            theme_name: Name of the theme.
            image_path: Optional specific image to use. If None, selects randomly.
            text_overlay: Optional text to overlay. If None, generates from PDFs.
            use_pdf_content: Whether to use PDF content for caption generation.
        
        Returns:
            Dictionary with paths to generated content and caption file.
        """
        # Load previously used assets to avoid duplicates
        used_assets = self._load_used_assets()
        
        # Get quote for text overlay (prefer unused quotes)
        quote_data = None
        quote_text = None
        if use_quote:
            quote_data = self._select_unused_quote(used_assets['quotes'])
            if quote_data:
                quote_text = quote_data.get('text', '')
        else:
            # Still try to get a quote for overlay even if not using for card
            try:
                from .quote_generator import QuoteGenerator
                quote_gen = QuoteGenerator()
                quote_data = quote_gen.get_random_quote(exclude_posted=True)
                if quote_data:
                    quote_text = quote_data.get('text', '')
            except Exception as e:
                print(f"Warning: Could not load quote: {e}")
        
        # Get PDF content for caption only if not using quotes or if explicitly requested
        pdf_text = ""
        if use_pdf_content and not quote_text:
            # Only process PDFs if we don't have a quote to use for caption
            # Try JSON first, then fallback to PDF processing
            pdf_text = self.pdf_processor.get_combined_text_from_json(theme_name)
            if not pdf_text:
                pdf_text = self.pdf_processor.get_combined_text(theme_name, max_pages_per_pdf=5)
        
        # Generate caption - use quote if available, otherwise use PDF content
        caption_source = quote_text if quote_text else (pdf_text or "Kombucha benefits and health information.")
        caption_data = self.ai_generator.generate_caption(
            caption_source,
            theme_name,
            'feed'
        )
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{theme_name}_{timestamp}.jpg"
        output_path = self.output_base_path / 'feed_posts' / output_filename
        
        # Find images
        images = self.find_assets(theme_name, 'images')
        
        # If use_quote is True and we have a quote, create quote card
        if use_quote and quote_text and quote_data:
            # Get author/source from quote data
            author = quote_data.get('author') or quote_data.get('source', '')
            processed_image_path = self.image_processor.create_quote_card(
                quote=quote_text,
                author=author,
                output_path=output_path
            )
            image_source = "quote_card_from_collection"
        # If no images available, create a quote card from PDF content
        elif not images:
            # Extract a good quote from PDF content
            if pdf_text:
                # Try to get key points from JSON first
                key_points = self.pdf_processor.get_key_points_from_json(theme_name)
                if not key_points:
                    key_points = self.pdf_processor.extract_key_points(pdf_text, max_points=3)
                else:
                    key_points = key_points[:3]  # Limit to 3
                if key_points:
                    # Use the first key point as quote (limit to 200 chars)
                    quote = key_points[0][:200]
                    if len(key_points[0]) > 200:
                        quote = key_points[0][:197] + "..."
                else:
                    # Fallback: use first sentence from PDF
                    quote = pdf_text.split('.')[0][:200] if pdf_text else "Descubra os benefícios do kombucha!"
            else:
                quote = "Descubra os benefícios do kombucha para sua saúde!"
            
            # Create quote card
            processed_image_path = self.image_processor.create_quote_card(
                quote=quote,
                author="Yoga Wisdom",
                output_path=output_path
            )
            image_source = "quote_card_generated"
        else:
            # Select image (prefer unused images)
            if image_path is None:
                if not images:
                    raise ValueError(f"No images found for theme '{theme_name}'. Place images in assets/01_images/")
                # Select from unused images if available
                image_path = self._select_unused_asset(images, used_assets['images'])
                if image_path is None:
                    # Fallback to random if selection failed
                    image_path = random.choice(images)
            else:
                # User provided a specific image path - validate it exists
                image_path = self._validate_path(image_path, 'file')
            
            # Always use quote from collection for text overlay (not PDFs)
            if text_overlay is None:
                if quote_text:
                    text_overlay = quote_text  # Use full quote as overlay
                else:
                    # This shouldn't happen since we load quote_text earlier, but keep as fallback
                    text_overlay = "Descubra os benefícios do kombucha para sua saúde!"
            
            # Process image with font size for readability
            processed_image_path = self.image_processor.process_image(
                image_path,
                output_path,
                text_overlay=text_overlay,
                text_position='bottom',  # Keep at bottom
                font_size=20  # Font size for text overlay
            )
            image_source = str(image_path)
        
        # Save caption
        caption_filename = f"{theme_name}_{timestamp}_caption.txt"
        caption_path = self.output_base_path / 'feed_posts' / caption_filename
        
        formatted_caption = self.ai_generator.format_caption_for_instagram(caption_data)
        with open(caption_path, 'w', encoding='utf-8') as f:
            f.write(formatted_caption)
        
        # Save metadata
        metadata_filename = f"{theme_name}_{timestamp}_metadata.json"
        metadata_path = self.output_base_path / 'feed_posts' / metadata_filename
        
        metadata = {
            'theme': theme_name,
            'type': 'feed',
            'image_source': image_source,
            'quote': quote_text if quote_text else None,
            'quote_id': quote_data.get('id') if quote_data else None,
            'quote_source': quote_data.get('source') if quote_data else None,
            'quote_author': quote_data.get('author') if quote_data else None,
            'generated_at': datetime.now().isoformat(),
            'caption_data': caption_data,
            'output_image': str(processed_image_path),
            'caption_file': str(caption_path)
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return {
            'image': processed_image_path,
            'caption': caption_path,
            'metadata': metadata_path
        }
    
    def generate_combined_reel(
        self,
        theme_name: str,
        video_paths: Optional[List[Path]] = None,
        image_paths: Optional[List[Path]] = None,
        use_quote: bool = True,
        use_pdf_content: bool = True,
        use_llm_refinement: bool = False,
        music_path: Optional[Path] = None,
        video_duration: float = 5.0,
        image_duration: float = 3.0
    ) -> Dict[str, Path]:
        """
        Generate a combined reel with video, images, quotes, and health benefits.
        
        Args:
            theme_name: Name of the theme.
            video_paths: Optional specific videos to use.
            image_paths: Optional specific images to use.
            use_quote: Whether to include a quote overlay.
            use_pdf_content: Whether to use PDF content for health benefits.
            use_llm_refinement: Whether to use LLM to refine health benefit text.
            music_path: Optional background music.
            video_duration: Duration for video segments.
            image_duration: Duration for image segments.
        
        Returns:
            Dictionary with paths to generated content.
        """
        if not self.video_processor:
            raise ValueError("Video processor not available. Please install moviepy.")
        
        # Load previously used assets to avoid duplicates
        used_assets = self._load_used_assets()
        
        # Get videos
        videos = self.find_assets(theme_name, 'videos')
        if not videos and not video_paths:
            raise ValueError(f"No videos found in assets/02_videos/")
        
        # Get images
        images = self.find_assets(theme_name, 'images')
        if not images and not image_paths:
            raise ValueError(f"No images found in assets/01_images/")
        
        # Select videos (prefer unused videos)
        if video_paths is None:
            if videos:
                selected_video = self._select_unused_asset(videos, used_assets['videos'])
                selected_videos = [selected_video] if selected_video else [random.choice(videos)]
            else:
                selected_videos = []
        else:
            # Validate provided video paths
            selected_videos = [self._validate_path(vp, 'file') for vp in video_paths]
        
        # Select images (prefer unused images)
        if image_paths is None:
            if images:
                selected_image = self._select_unused_asset(images, used_assets['images'])
                selected_images = [selected_image] if selected_image else [random.choice(images)]
            else:
                selected_images = []
        else:
            # Validate provided image paths
            selected_images = [self._validate_path(ip, 'file') for ip in image_paths]
        
        # Get PDF content for health benefits (prefer unused benefits)
        pdf_text = ""
        health_benefit_text = None
        if use_pdf_content:
            # Select an unused health benefit
            benefit_text = self._select_unused_health_benefit(theme_name, used_assets['health_benefits'])
            
            if benefit_text:
                health_benefit_text = benefit_text
                # Get all key points for caption generation context
                json_content = self.pdf_processor.load_processed_content(theme_name)
                if json_content and 'summary' in json_content:
                    all_key_points = self.pdf_processor.get_key_points_from_json(theme_name, max_points=5)
                    pdf_text = ". ".join(all_key_points[:3]) + "." if all_key_points else ""
                else:
                    pdf_text = self.pdf_processor.get_combined_text(theme_name, max_pages_per_pdf=5)
                
                # Only apply additional LLM refinement if explicitly requested
                if use_llm_refinement and health_benefit_text:
                    try:
                        refined = self.ai_generator.refine_health_benefit(
                            health_benefit_text,
                            theme_name,
                            max_length=200
                        )
                        # Use the language version matching config
                        config_language = self.config.get('ai', {}).get('language', 'en')
                        if config_language in refined:
                            health_benefit_text = refined[config_language]
                        elif 'en' in refined:
                            health_benefit_text = refined['en']
                        elif 'pt' in refined:
                            health_benefit_text = refined['pt']
                    except Exception as e:
                        print(f"Warning: LLM refinement failed, using original text: {e}")
                else:
                    print(f"Using refined key points from JSON (already optimized for accessibility)")
            else:
                # Fallback if no unused benefits available
                json_content = self.pdf_processor.load_processed_content(theme_name)
                using_json = json_content is not None and 'summary' in json_content
                
                if using_json:
                    benefit_text = self.pdf_processor.get_random_key_point_from_json(theme_name)
                    if benefit_text:
                        all_key_points = self.pdf_processor.get_key_points_from_json(theme_name, max_points=5)
                        pdf_text = ". ".join(all_key_points[:3]) + "." if all_key_points else ""
                    else:
                        benefit_text = None
                else:
                    pdf_text = self.pdf_processor.get_combined_text(theme_name, max_pages_per_pdf=5)
                    if pdf_text:
                        key_points = self.pdf_processor.extract_key_points(pdf_text, max_points=1)
                        benefit_text = key_points[0] if key_points else None
                    else:
                        benefit_text = None
                
                if benefit_text:
                    if len(benefit_text) > 200:
                        truncated = benefit_text[:200]
                        last_period = truncated.rfind('.')
                        last_exclamation = truncated.rfind('!')
                        last_question = truncated.rfind('?')
                        last_sentence_end = max(last_period, last_exclamation, last_question)
                        
                        if last_sentence_end > 50:
                            health_benefit_text = benefit_text[:last_sentence_end + 1].strip()
                        else:
                            last_space = truncated.rfind(' ')
                            if last_space > 150:
                                health_benefit_text = benefit_text[:last_space].strip() + "..."
                            else:
                                health_benefit_text = truncated.strip() + "..."
                    else:
                        health_benefit_text = benefit_text.strip()
        
        # Get quote (prefer unused quotes)
        quote_data = None
        quote_text = None
        if use_quote:
            quote_data = self._select_unused_quote(used_assets['quotes'])
            if quote_data:
                quote_text = quote_data.get('text', '')
            if quote_text is None:
                # Fallback if no unused quotes available
                try:
                    from .quote_generator import QuoteGenerator
                    quote_gen = QuoteGenerator()
                    quote_data = quote_gen.get_random_quote(exclude_posted=False)
                    if quote_data:
                        quote_text = quote_data.get('text', '')
                except Exception as e:
                    print(f"Warning: Could not load quote: {e}")
        
        # Generate caption
        caption_data = self.ai_generator.generate_caption(
            pdf_text or "Kombucha health benefits and wellness information.",
            theme_name,
            'reel'
        )
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{theme_name}_combined_{timestamp}.mp4"
        output_path = self.output_base_path / 'reels' / output_filename
        
        # Create combined reel
        processed_video_path = self.video_processor.create_combined_reel(
            selected_videos,
            image_paths=selected_images,
            quote_text=quote_text,
            health_benefit_text=health_benefit_text,
            output_path=output_path,
            video_duration=video_duration,
            image_duration=image_duration,
            music_path=music_path
        )
        
        # Save caption
        caption_filename = f"{theme_name}_combined_{timestamp}_caption.txt"
        caption_path = self.output_base_path / 'reels' / caption_filename
        
        formatted_caption = self.ai_generator.format_caption_for_instagram(caption_data)
        with open(caption_path, 'w', encoding='utf-8') as f:
            f.write(formatted_caption)
        
        # Save metadata
        metadata_filename = f"{theme_name}_combined_{timestamp}_metadata.json"
        metadata_path = self.output_base_path / 'reels' / metadata_filename
        
        metadata = {
            'theme': theme_name,
            'type': 'reel_combined',
            'video_sources': [str(v) for v in selected_videos],
            'image_sources': [str(i) for i in selected_images],
            'quote': quote_text,
            'quote_id': quote_data.get('id') if quote_data else None,
            'quote_source': quote_data.get('source') if quote_data else None,
            'quote_author': quote_data.get('author') if quote_data else None,
            'health_benefit': health_benefit_text.replace('\n', ' ') if health_benefit_text else None,
            'generated_at': datetime.now().isoformat(),
            'caption_data': caption_data,
            'output_video': str(processed_video_path),
            'caption_file': str(caption_path)
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return {
            'video': processed_video_path,
            'caption': caption_path,
            'metadata': metadata_path
        }
    
    def generate_reel(
        self,
        theme_name: str,
        video_paths: Optional[List[Path]] = None,
        num_clips: int = 3,
        use_pdf_content: bool = True,
        music_path: Optional[Path] = None
    ) -> Dict[str, Path]:
        """
        Generate an Instagram Reel.
        
        Args:
            theme_name: Name of the theme.
            video_paths: Optional specific videos to use. If None, selects randomly.
            num_clips: Number of video clips to use.
            use_pdf_content: Whether to use PDF content for caption/subtitle generation.
            music_path: Optional path to background music file.
        
        Returns:
            Dictionary with paths to generated content and caption file.
        """
        # Find videos
        videos = self.find_assets(theme_name, 'videos')
        if not videos:
            raise ValueError(f"No videos found in theme '{theme_name}'")
        
        # Load previously used assets to avoid duplicates
        used_assets = self._load_used_assets()
        
        # Select videos (prefer unused videos)
        if video_paths is None:
            # Filter out used videos
            unused_videos = [
                v for v in videos
                if str(v.resolve()) not in {str(Path(p).resolve()) for p in used_assets['videos']}
            ]
            
            # If all videos are used, reset and use all available
            if not unused_videos:
                print("Warning: All videos have been used. Resetting and allowing reuse.")
                unused_videos = videos
            
            if len(unused_videos) < num_clips:
                # Repeat videos if not enough unused ones
                selected_videos = (unused_videos * ((num_clips // len(unused_videos)) + 1))[:num_clips]
            else:
                selected_videos = random.sample(unused_videos, num_clips)
        else:
            # Validate provided video paths
            selected_videos = [self._validate_path(vp, 'file') for vp in video_paths]
        
        # Get PDF content for captions/subtitles
        pdf_text = ""
        if use_pdf_content:
            # Try JSON first, then fallback to PDF processing
            pdf_text = self.pdf_processor.get_combined_text_from_json(theme_name)
            if not pdf_text:
                pdf_text = self.pdf_processor.get_combined_text(theme_name, max_pages_per_pdf=5)
        
        # Generate caption for post
        caption_data = self.ai_generator.generate_caption(
            pdf_text or "Kombucha benefits and health information.",
            theme_name,
            'reel'
        )
        
        # Create text overlays for video (subtitles)
        text_overlays = []
        if pdf_text:
            key_points = self.pdf_processor.extract_key_points(pdf_text, max_points=num_clips)
            clip_duration = min(90 / num_clips, 10)  # Distribute time
            
            for i, point in enumerate(key_points[:num_clips]):
                text_overlays.append({
                    'text': point[:80],  # Limit text length
                    'start_time': i * clip_duration,
                    'duration': min(clip_duration - 1, 5),
                    'position': 'bottom',
                    'font_size': 50
                })
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{theme_name}_{timestamp}.mp4"
        output_path = self.output_base_path / 'reels' / output_filename
        
        # Create reel
        processed_video_path = self.video_processor.create_reel(
            selected_videos,
            output_path,
            text_overlays=text_overlays if text_overlays else None,
            music_path=music_path
        )
        
        # Save caption
        caption_filename = f"{theme_name}_{timestamp}_caption.txt"
        caption_path = self.output_base_path / 'reels' / caption_filename
        
        formatted_caption = self.ai_generator.format_caption_for_instagram(caption_data)
        with open(caption_path, 'w', encoding='utf-8') as f:
            f.write(formatted_caption)
        
        # Save metadata
        metadata_filename = f"{theme_name}_{timestamp}_metadata.json"
        metadata_path = self.output_base_path / 'reels' / metadata_filename
        
        metadata = {
            'theme': theme_name,
            'type': 'reel',
            'video_sources': [str(v) for v in selected_videos],
            'generated_at': datetime.now().isoformat(),
            'caption_data': caption_data,
            'output_video': str(processed_video_path),
            'caption_file': str(caption_path),
            'text_overlays': text_overlays
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return {
            'video': processed_video_path,
            'caption': caption_path,
            'metadata': metadata_path
        }
    
    def list_themes(self) -> List[str]:
        """List available themes (numbered folders 04-07)."""
        if not self.assets_base_path.exists():
            return []
        
        themes = []
        for item in self.assets_base_path.iterdir():
            if item.is_dir() and item.name.startswith(('04_', '05_', '06_', '07_')):
                themes.append(item.name)
        
        return sorted(themes)
    
    def get_theme_stats(self, theme_name: str) -> Dict:
        """Get statistics about assets in a theme."""
        return {
            'images': len(self.find_assets(theme_name, 'images')),
            'videos': len(self.find_assets(theme_name, 'videos')),
            'pdfs': len(self.find_assets(theme_name, 'pdfs')),
            'quotes': len(self.find_assets(theme_name, 'quotes'))
        }


def main():
    """Test function."""
    generator = ContentGenerator()
    
    themes = generator.list_themes()
    print(f"Available themes: {themes}")
    
    if themes:
        theme = themes[0]
        stats = generator.get_theme_stats(theme)
        print(f"\nStats for '{theme}':")
        print(f"  Images: {stats['images']}")
        print(f"  Videos: {stats['videos']}")
        print(f"  PDFs: {stats['pdfs']}")


if __name__ == '__main__':
    main()
