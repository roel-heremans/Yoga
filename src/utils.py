"""
Utility functions for the Instagram Content Generator.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv


def shorten_quote_for_display(text: str, max_length: int = 120) -> str:
    """
    Shorten quote text for display, breaking at sentence or word boundary.
    Used for quote cards and for storing shorter quotes in the review pipeline.
    """
    if not text or len(text.strip()) <= max_length:
        return (text or '').strip()
    text = text.strip()
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_sentence = max(
        truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?')
    )
    if last_sentence > max_length // 2:
        return text[: last_sentence + 1].strip()
    last_space = truncated.rfind(' ')
    if last_space > max_length // 2:
        return text[: last_space].strip() + '…'
    return truncated.strip() + '…'

# Load environment variables
load_dotenv()


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file. If None, uses default location.
    
    Returns:
        Configuration dictionary.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
    
    if not config_path.exists():
        # Create default config if it doesn't exist
        create_default_config(config_path)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    # Load API keys from environment
    if 'ai' in config:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            config['ai']['api_key'] = api_key
    
    return config


def create_default_config(config_path: Path):
    """Create default configuration file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    default_config = {
        'brand': {
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
        },
        'themes': [
            {
                'name': 'kombucha_benefits',
                'target_audience': ['health_conscious', 'restaurants'],
                'hashtags': {
                    'base': ['#kombucha', '#madeira', '#healthy', '#realhealthkombucha'],
                    'custom': ['#kombuchamadeira', '#saude', '#madeiraisland']
                }
            },
            {
                'name': 'kombucha_research',
                'target_audience': ['health_conscious', 'restaurants'],
                'hashtags': {
                    'base': ['#kombucha', '#madeira', '#research', '#realhealthkombucha'],
                    'custom': ['#kombucharesearch', '#saude', '#ciencia']
                }
            }
        ],
        'ai': {
            'provider': 'anthropic',
            'model': 'claude-sonnet-4-6',
            'language': 'pt',
            'api_key': None
        },
        'instagram': {
            'feed_dimensions': {
                'width': 1080,
                'height': 1080
            },
            'reel_dimensions': {
                'width': 1080,
                'height': 1920
            },
            'reel_duration': {
                'min': 15,
                'max': 90
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Created default configuration at {config_path}")


def get_theme_config(config: Dict[str, Any], theme_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific theme."""
    themes = config.get('themes', [])
    for theme in themes:
        if theme.get('name') == theme_name:
            return theme
    return None


def get_brand_colors(config: Dict[str, Any]) -> Dict[str, str]:
    """Get brand colors from config."""
    return config.get('brand', {}).get('colors', {})


def get_brand_fonts(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get brand fonts from config."""
    return config.get('brand', {}).get('fonts', {})


def ensure_output_dirs():
    """Ensure output directories exist."""
    base_path = Path(__file__).parent.parent
    (base_path / 'output' / 'reels').mkdir(parents=True, exist_ok=True)
    (base_path / 'output' / 'feed_posts').mkdir(parents=True, exist_ok=True)
    (base_path / 'output' / 'posted-on-social-media').mkdir(parents=True, exist_ok=True)