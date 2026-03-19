"""Tests for VideoProcessor new cinematic/reveal quote styles."""
from unittest.mock import patch, MagicMock


# Shared factory used by TestCreateCinematicTextClip, TestCreateLineRevealClips,
# and TestCreateImageQuoteVideoSignature (added in Tasks 2-4).
def make_processor():
    """Return a VideoProcessor with all moviepy/PIL calls mocked."""
    with patch('src.video_processor.VideoFileClip'), \
         patch('src.video_processor.ImageClip'), \
         patch('src.video_processor.ColorClip'), \
         patch('src.video_processor.TextClip'), \
         patch('src.video_processor.CompositeVideoClip'), \
         patch('src.video_processor.AudioFileClip'):
        from src.video_processor import VideoProcessor
        config = {
            'brand': {'colors': {'primary': '#2c5530'}, 'fonts': {'heading': 'Arial', 'body': 'Arial', 'weights': {'heading': 'bold', 'body': 'normal'}}},
            'instagram': {'reel_dimensions': {'width': 1080, 'height': 1920}, 'reel_duration': {'min': 15, 'max': 90}},
        }
        return VideoProcessor(config=config)


class TestCinematicConstants:
    def test_color_constants_exist(self):
        from src.video_processor import VideoProcessor
        assert hasattr(VideoProcessor, 'CINEMATIC_QUOTE_COLOR')
        assert hasattr(VideoProcessor, 'CINEMATIC_AUTHOR_COLOR')
        assert hasattr(VideoProcessor, 'CINEMATIC_DIVIDER_COLOR')
        assert hasattr(VideoProcessor, 'CINEMATIC_VIGNETTE_ALPHA')

    def test_layout_constants_exist(self):
        from src.video_processor import VideoProcessor
        assert hasattr(VideoProcessor, 'LINE_HEIGHT_MULT')
        assert hasattr(VideoProcessor, 'DIVIDER_GAP')
        assert hasattr(VideoProcessor, 'AUTHOR_GAP')
        assert hasattr(VideoProcessor, 'DIVIDER_WIDTH')
        assert hasattr(VideoProcessor, 'DIVIDER_HEIGHT')

    def test_color_constant_values(self):
        from src.video_processor import VideoProcessor
        assert VideoProcessor.CINEMATIC_QUOTE_COLOR == '#f0ece4'
        assert VideoProcessor.CINEMATIC_AUTHOR_COLOR == '#c9a96e'
        assert VideoProcessor.CINEMATIC_DIVIDER_COLOR == '#c9a96e'
        assert 0 < VideoProcessor.CINEMATIC_VIGNETTE_ALPHA <= 255

    def test_layout_constant_values(self):
        from src.video_processor import VideoProcessor
        assert VideoProcessor.LINE_HEIGHT_MULT > 1.0
        assert VideoProcessor.DIVIDER_GAP > 0
        assert VideoProcessor.AUTHOR_GAP > 0
        assert VideoProcessor.DIVIDER_WIDTH > 0
        assert VideoProcessor.DIVIDER_HEIGHT > 0
