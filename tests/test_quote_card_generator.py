"""Tests for QuoteCardGenerator quote_style passthrough."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile, os
from PIL import Image as PILImage


def make_generator():
    config = {
        'brand': {'name': 'Test', 'website': '', 'colors': {'primary': '#2c5530', 'secondary': '#4a7c59', 'accent': '#8fbc8f', 'text': '#2c2c2c', 'background': '#ffffff'}, 'fonts': {'heading': 'Arial', 'body': 'Arial', 'weights': {'heading': 'bold', 'body': 'normal'}}},
        'instagram': {'feed_dimensions': {'width': 1080, 'height': 1080}, 'reel_dimensions': {'width': 1080, 'height': 1920}, 'reel_duration': {'min': 15, 'max': 90}},
        'quote_cards': {'max_display_length': 120},
        'ai': {'provider': 'anthropic', 'model': 'claude-sonnet-4-6', 'language': 'en'},
    }
    with patch('src.quote_card_generator.VideoProcessor'), \
         patch('src.quote_card_generator.ImageProcessor'):
        from src.quote_card_generator import QuoteCardGenerator
        return QuoteCardGenerator(config=config)


class TestQuoteStylePassthrough:
    def test_generate_image_video_accepts_quote_style(self):
        import inspect
        from src.quote_card_generator import QuoteCardGenerator
        sig = inspect.signature(QuoteCardGenerator.generate_image_video_quote_card)
        assert 'quote_style' in sig.parameters
        assert sig.parameters['quote_style'].default == 'cinematic'

    def test_generate_quote_cards_accepts_quote_style(self):
        import inspect
        from src.quote_card_generator import QuoteCardGenerator
        sig = inspect.signature(QuoteCardGenerator.generate_quote_cards)
        assert 'quote_style' in sig.parameters
        assert sig.parameters['quote_style'].default == 'cinematic'

    def test_quote_style_passed_to_video_processor(self):
        """generate_image_video_quote_card passes quote_style to create_image_quote_video."""
        gen = make_generator()

        tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        PILImage.new('RGB', (100, 100), color=(50, 80, 50)).save(tmp.name)
        tmp_path = Path(tmp.name)

        mock_result = Path(tempfile.mktemp(suffix='.mp4'))
        gen.video_processor.create_image_quote_video = MagicMock(return_value=mock_result)

        quote = {'text': 'The rhythm of the body.', 'author': 'B.K.S. Iyengar', 'id': 'q1', 'group': 'TestGroup'}
        gen.generate_image_video_quote_card(
            quote=quote,
            image_paths=[tmp_path],
            output_path=mock_result,
            quote_style='reveal',
        )

        call_kwargs = gen.video_processor.create_image_quote_video.call_args
        assert call_kwargs is not None
        all_args = {**call_kwargs.kwargs}
        if call_kwargs.args:
            import inspect
            from src.video_processor import VideoProcessor
            param_names = list(inspect.signature(VideoProcessor.create_image_quote_video).parameters.keys())[1:]
            all_args.update(dict(zip(param_names, call_kwargs.args)))
        assert all_args.get('quote_style') == 'reveal', f"quote_style not passed through: {all_args}"
        assert 'text_overlay' not in all_args

        os.unlink(tmp.name)

    def test_overlay_text_not_constructed(self):
        """generate_image_video_quote_card passes text and author separately, not combined."""
        gen = make_generator()
        tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        PILImage.new('RGB', (100, 100), color=(50, 80, 50)).save(tmp.name)
        tmp_path = Path(tmp.name)
        mock_result = Path(tempfile.mktemp(suffix='.mp4'))
        gen.video_processor.create_image_quote_video = MagicMock(return_value=mock_result)

        quote = {'text': 'The rhythm of the body.', 'author': 'B.K.S. Iyengar', 'id': 'q1', 'group': 'TestGroup'}
        gen.generate_image_video_quote_card(quote=quote, image_paths=[tmp_path], output_path=mock_result)

        call_kwargs = gen.video_processor.create_image_quote_video.call_args
        assert call_kwargs is not None
        all_args = {**call_kwargs.kwargs}
        assert 'text' in all_args or (len(call_kwargs.args) >= 2)
        assert 'text_overlay' not in str(call_kwargs)

        os.unlink(tmp.name)


def test_append_generated_cards_records_images_used(tmp_path):
    """images_used list is stored in generated_cards entry when provided."""
    # Set up a minimal quotes.json
    knowledge_dir = tmp_path / "assets" / "10_knowledge"
    group_dir = knowledge_dir / "TestGroup"
    group_dir.mkdir(parents=True)
    quotes_file = group_dir / "quotes.json"
    quotes_file.write_text(json.dumps({
        "source": "Test",
        "author": "Tester",
        "quotes": [{"id": "q001", "text": "Test quote", "status": "accepted"}]
    }))

    from src.quote_card_generator import QuoteCardGenerator
    generator = QuoteCardGenerator.__new__(QuoteCardGenerator)
    generator.knowledge_dir = knowledge_dir
    generator.assets_base_path = tmp_path / "assets"

    quote = {"id": "q001", "group": "TestGroup"}
    results = {"image_videos": [tmp_path / "out.mp4"]}
    images_used = ["assets/01-ajuda/Yoga_Funchal21.jpg", "assets/01-ajuda/Yoga_Funchal10.jpg"]

    generator._append_generated_cards_to_quote(quote, results, images_used=images_used)

    data = json.loads(quotes_file.read_text())
    card = data["quotes"][0]["generated_cards"][0]
    assert card["images_used"] == images_used
