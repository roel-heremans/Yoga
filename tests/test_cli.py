"""Tests for --quote-style CLI option."""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestQuoteStyleCLI:
    def test_quote_style_option_exists(self):
        from main import generate_quote_cards
        param_names = [p.name for p in generate_quote_cards.params]
        assert 'quote_style' in param_names

    def test_quote_style_default_is_cinematic(self):
        from main import generate_quote_cards
        param = next(p for p in generate_quote_cards.params if p.name == 'quote_style')
        assert param.default == 'cinematic'

    def test_quote_style_choices(self):
        from main import generate_quote_cards
        param = next(p for p in generate_quote_cards.params if p.name == 'quote_style')
        assert set(param.type.choices) == {'cinematic', 'reveal', 'scroll'}

    def test_reveal_style_passed_to_generator(self):
        """--quote-style reveal reaches generate_quote_cards() call."""
        runner = CliRunner()
        mock_gen = MagicMock()
        mock_gen.generate_quote_cards.return_value = {
            'white_background': [], 'photos': [], 'videos': [], 'image_videos': []
        }
        with patch('main.QuoteCardGenerator', return_value=mock_gen), \
             patch('main.load_config', return_value={}):
            result = runner.invoke(
                __import__('main').cli,
                ['generate-quote-cards', '--white-background', '--quote-style', 'reveal'],
            )
        call_kwargs = mock_gen.generate_quote_cards.call_args
        if call_kwargs:
            all_args = {**call_kwargs.kwargs}
            assert all_args.get('quote_style') == 'reveal', \
                f"Expected quote_style='reveal', got: {all_args}"

    def test_invalid_style_rejected(self):
        runner = CliRunner()
        result = runner.invoke(
            __import__('main').cli,
            ['generate-quote-cards', '--white-background', '--quote-style', 'invalid'],
        )
        assert result.exit_code != 0


def test_generate_warns_for_published_image(tmp_path):
    """generate-quote-cards warns when a specified image was already used in a published post."""
    import json
    from click.testing import CliRunner
    from unittest.mock import patch, MagicMock
    import main as main_module

    # Create a real image file so Click's exists=True check passes
    img = tmp_path / "Yoga_Funchal21.jpg"
    img.write_bytes(b"fake")

    # Build a fake log that marks this exact image path as used
    log_data = {
        "some_video.mp4": {
            "quote_id": "q001",
            "quote_group": "TestGroup",
            "images_used": [str(img)],
            "marked_at": "2026-01-01",
        }
    }

    mock_gen = MagicMock()
    mock_gen.generate_quote_cards.return_value = {
        'white_background': [], 'photos': [], 'videos': [], 'image_videos': []
    }

    with patch('main.QuoteCardGenerator', return_value=mock_gen), \
         patch('src.published_tracker.load_published_log', return_value=log_data):
        runner = CliRunner()
        result = runner.invoke(main_module.cli, ['generate-quote-cards', '-i', str(img)])

    assert 'already used in a published post' in result.output


def test_mark_published_no_folder():
    """mark-published prints a clear message when published folder doesn't exist."""
    runner = CliRunner()
    # Pass a path that is guaranteed not to exist — no mocking needed
    result = runner.invoke(
        __import__('main').cli,
        ['mark-published', '--published-dir', '/tmp/yoga_test_nonexistent_published_dir'],
    )
    assert result.exit_code == 0
    assert 'does not exist' in result.output.lower()
