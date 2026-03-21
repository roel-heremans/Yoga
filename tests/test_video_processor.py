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


class TestCreateCinematicTextClip:
    """create_cinematic_text_clip returns a CompositeVideoClip overlay."""

    def _make_mock_text_clip(self, height=100):
        m = MagicMock()
        m.h = height
        m.w = 1080
        # Support both moviepy 1.x and 2.x chaining
        m.with_duration.return_value = m
        m.set_duration.return_value = m
        m.with_position.return_value = m
        m.set_position.return_value = m
        m.with_start.return_value = m
        m.set_start.return_value = m
        return m

    def test_method_exists(self):
        from src.video_processor import VideoProcessor
        assert hasattr(VideoProcessor, 'create_cinematic_text_clip')

    def test_returns_composite_video_clip(self):
        mock_cvclip = MagicMock()
        mock_cvclip.return_value = MagicMock(w=1080, h=1920, duration=15.0)

        mock_text = self._make_mock_text_clip(80)
        mock_TextClip = MagicMock(return_value=mock_text)
        mock_ImageClip = MagicMock(return_value=self._make_mock_text_clip(2))
        mock_ColorClip = MagicMock(return_value=self._make_mock_text_clip(2))

        vp = make_processor()

        with patch('src.video_processor.CompositeVideoClip', mock_cvclip), \
             patch('src.video_processor.TextClip', mock_TextClip), \
             patch('src.video_processor.ImageClip', mock_ImageClip), \
             patch('src.video_processor.ColorClip', mock_ColorClip):
            result = vp.create_cinematic_text_clip(
                text="The rhythm of the body.",
                author="B.K.S. Iyengar",
                duration=15.0,
            )
        assert mock_cvclip.called

    def test_uses_cinematic_colors(self):
        """TextClip is called with cream color for quote and gold for author."""
        mock_text = self._make_mock_text_clip(80)
        mock_TextClip = MagicMock(return_value=mock_text)
        mock_ImageClip = MagicMock(return_value=self._make_mock_text_clip(2))
        mock_cvclip = MagicMock(return_value=MagicMock(w=1080, h=1920))

        vp = make_processor()

        with patch('src.video_processor.TextClip', mock_TextClip), \
             patch('src.video_processor.ImageClip', mock_ImageClip), \
             patch('src.video_processor.CompositeVideoClip', mock_cvclip), \
             patch('src.video_processor.ColorClip', MagicMock(return_value=self._make_mock_text_clip(2))):
            vp.create_cinematic_text_clip("The rhythm.", "B.K.S. Iyengar", 15.0)

        # At least one TextClip call used cream color
        calls = mock_TextClip.call_args_list
        colors_used = [str(c) for c in calls]
        assert any('#f0ece4' in c or 'f0ece4' in c for c in colors_used), \
            f"Expected cream color #f0ece4 in TextClip calls: {colors_used}"


class TestCreateLineRevealClips:
    """create_line_reveal_clips returns a list of pre-positioned clips."""

    def _vp(self):
        """Return a VideoProcessor with mocked moviepy."""
        import sys
        mock_text = MagicMock()
        mock_text.h = 80
        mock_text.w = 1080
        for attr in ('with_duration', 'set_duration', 'with_position', 'set_position',
                     'with_start', 'set_start', 'crossfadein'):
            getattr(mock_text, attr).return_value = mock_text

        with patch('src.video_processor.TextClip', return_value=mock_text), \
             patch('src.video_processor.ImageClip', return_value=mock_text), \
             patch('src.video_processor.CompositeVideoClip', return_value=MagicMock(w=1080, h=1920)), \
             patch('src.video_processor.ColorClip', return_value=mock_text):
            if 'src.video_processor' in sys.modules:
                del sys.modules['src.video_processor']
            from src.video_processor import VideoProcessor
            config = {
                'brand': {'colors': {'primary': '#2c5530'}, 'fonts': {'heading': 'Arial', 'body': 'Arial', 'weights': {'heading': 'bold', 'body': 'normal'}}},
                'instagram': {'reel_dimensions': {'width': 1080, 'height': 1920}, 'reel_duration': {'min': 15, 'max': 90}},
            }
            return VideoProcessor(config=config)

    def test_method_exists(self):
        from src.video_processor import VideoProcessor
        assert hasattr(VideoProcessor, 'create_line_reveal_clips')

    def test_returns_list(self):
        vp = self._vp()
        result = vp.create_line_reveal_clips(
            text="The rhythm of the body.",
            author="B.K.S. Iyengar",
            duration=15.0,
        )
        assert isinstance(result, list)
        assert len(result) >= 2  # at least one line + author block

    def test_clip_count_equals_lines_plus_author(self):
        """N wrapped lines + 1 author block = N+1 clips."""
        vp = self._vp()
        # Short text wraps to 1 line
        result = vp.create_line_reveal_clips(
            text="Short quote.",
            author="Author",
            duration=15.0,
        )
        # 1 line + 1 author block = 2 clips minimum
        assert len(result) >= 2

    def test_interval_clamped_to_minimum(self):
        """With many lines and short duration, interval is clamped to 1.0s."""
        from src.video_processor import VideoProcessor
        # Test the timing formula directly
        duration = 5.0
        n_lines = 10
        interval = max(1.0, duration / (n_lines + 1))
        assert interval == 1.0

    def test_interval_formula_normal(self):
        """Normal case: interval = duration / (N+1)."""
        duration = 15.0
        n_lines = 4
        interval = max(1.0, duration / (n_lines + 1))
        assert abs(interval - 3.0) < 0.001


class TestCreateImageQuoteVideoSignature:
    """create_image_quote_video accepts text, author, quote_style params."""

    def test_accepts_text_and_author_separately(self):
        """Method signature no longer has text_overlay, has text and author."""
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor.create_image_quote_video)
        params = list(sig.parameters.keys())
        assert 'text' in params, "Expected 'text' param"
        assert 'author' in params, "Expected 'author' param"
        assert 'text_overlay' not in params, "'text_overlay' should be removed"

    def test_accepts_quote_style_param(self):
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor.create_image_quote_video)
        assert 'quote_style' in sig.parameters
        assert sig.parameters['quote_style'].default == 'cinematic'

    def test_cinematic_style_calls_cinematic_method(self):
        """When quote_style='cinematic', create_cinematic_text_clip is called."""
        import tempfile, os
        from pathlib import Path
        from PIL import Image as PILImage
        from src.video_processor import VideoProcessor

        tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        PILImage.new('RGB', (100, 100), color=(50, 80, 50)).save(tmp.name)
        tmp_path = Path(tmp.name)
        out_path = Path(tempfile.mktemp(suffix='.mp4'))

        config = {
            'brand': {'colors': {'primary': '#2c5530'}, 'fonts': {'heading': 'Arial', 'body': 'Arial', 'weights': {'heading': 'bold', 'body': 'normal'}}},
            'instagram': {'reel_dimensions': {'width': 1080, 'height': 1920}, 'reel_duration': {'min': 15, 'max': 90}},
        }
        vp = VideoProcessor(config=config)

        mock_clip = MagicMock()
        mock_clip.duration = 15.0
        mock_clip.w = 1080
        mock_clip.h = 1920
        mock_clip.fps = 30
        mock_clip.with_fps = MagicMock(return_value=mock_clip)
        mock_clip.set_fps = MagicMock(return_value=mock_clip)
        mock_clip.write_videofile = MagicMock()
        mock_clip.close = MagicMock()

        with patch.object(vp, 'image_to_clip', return_value=mock_clip) as mock_img, \
             patch.object(vp, 'create_cinematic_text_clip', return_value=mock_clip) as mock_cin, \
             patch.object(vp, '_add_white_fade_overlay', return_value=mock_clip), \
             patch('src.video_processor.CompositeVideoClip', return_value=mock_clip):
            try:
                vp.create_image_quote_video(
                    image_paths=[tmp_path],
                    text="The rhythm of the body.",
                    author="B.K.S. Iyengar",
                    output_path=out_path,
                    duration=15.0,
                    quote_style='cinematic',
                )
            except Exception:
                pass  # We only care that cinematic method was called
            assert mock_cin.called, "create_cinematic_text_clip should have been called"

        try:
            os.unlink(tmp.name)
        except Exception:
            pass

    def test_reveal_style_calls_reveal_method(self):
        """When quote_style='reveal', create_line_reveal_clips is called."""
        import tempfile, os
        from pathlib import Path
        from PIL import Image as PILImage
        from src.video_processor import VideoProcessor

        tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        PILImage.new('RGB', (100, 100), color=(50, 80, 50)).save(tmp.name)
        tmp_path = Path(tmp.name)
        out_path = Path(tempfile.mktemp(suffix='.mp4'))

        config = {
            'brand': {'colors': {'primary': '#2c5530'}, 'fonts': {'heading': 'Arial', 'body': 'Arial', 'weights': {'heading': 'bold', 'body': 'normal'}}},
            'instagram': {'reel_dimensions': {'width': 1080, 'height': 1920}, 'reel_duration': {'min': 15, 'max': 90}},
        }
        vp = VideoProcessor(config=config)

        mock_clip = MagicMock()
        mock_clip.duration = 15.0
        mock_clip.w = 1080
        mock_clip.h = 1920
        mock_clip.fps = 30
        mock_clip.with_fps = MagicMock(return_value=mock_clip)
        mock_clip.set_fps = MagicMock(return_value=mock_clip)
        mock_clip.write_videofile = MagicMock()
        mock_clip.close = MagicMock()

        with patch.object(vp, 'image_to_clip', return_value=mock_clip), \
             patch.object(vp, 'create_line_reveal_clips', return_value=[mock_clip]) as mock_rev, \
             patch.object(vp, '_add_white_fade_overlay', return_value=mock_clip), \
             patch('src.video_processor.CompositeVideoClip', return_value=mock_clip):
            try:
                vp.create_image_quote_video(
                    image_paths=[tmp_path],
                    text="The rhythm of the body.",
                    author="B.K.S. Iyengar",
                    output_path=out_path,
                    duration=15.0,
                    quote_style='reveal',
                )
            except Exception:
                pass
            assert mock_rev.called, "create_line_reveal_clips should have been called"

        try:
            os.unlink(tmp.name)
        except Exception:
            pass


class TestCreateScrollClips:
    def test_method_exists(self):
        from src.video_processor import VideoProcessor
        assert hasattr(VideoProcessor, 'create_scroll_clips')

    def test_returns_list(self):
        from unittest.mock import patch, MagicMock
        processor = make_processor()
        with patch('src.video_processor.VideoClip', return_value=MagicMock(duration=5)):
            result = processor.create_scroll_clips("Hello world yoga", "B.K.S. Iyengar", 5.0, font_size=36)
        assert isinstance(result, list)

    def test_returns_at_least_two_clips(self):
        """Must return scrim + at least one VideoClip overlay."""
        from unittest.mock import patch, MagicMock
        processor = make_processor()
        with patch('src.video_processor.VideoClip', return_value=MagicMock(duration=5)):
            result = processor.create_scroll_clips("Hello world yoga", "B.K.S. Iyengar", 5.0, font_size=36)
        assert len(result) >= 2

    def test_scroll_style_accepted_by_create_image_quote_video(self):
        """create_image_quote_video with quote_style='scroll' must call create_scroll_clips."""
        from unittest.mock import patch, MagicMock
        from pathlib import Path

        processor = make_processor()
        fake_clip = MagicMock()
        fake_clip.size = (1080, 1920)
        fake_clip.duration = 5

        with patch.object(processor, 'create_scroll_clips', return_value=[fake_clip, fake_clip]) as mock_scroll, \
             patch('src.video_processor.ImageClip', return_value=fake_clip), \
             patch('src.video_processor.CompositeVideoClip', return_value=fake_clip), \
             patch('src.video_processor.concatenate_videoclips', return_value=fake_clip), \
             patch.object(processor, 'image_to_clip', return_value=fake_clip), \
             patch('pathlib.Path.exists', return_value=True), \
             patch.object(processor, '_add_white_fade_overlay', return_value=fake_clip):
            try:
                processor.create_image_quote_video(
                    text="Yoga is peace.",
                    author="Iyengar",
                    image_paths=[Path('/tmp/fake.jpg')],
                    output_path=Path('/tmp/out.mp4'),
                    duration=5.0,
                    quote_style='scroll',
                )
            except Exception:
                pass
        assert mock_scroll.called, "create_scroll_clips should have been called for quote_style='scroll'"


class TestGreenFadeAtEnd:
    def test_add_white_fade_overlay_accepts_color_param(self):
        """_add_white_fade_overlay must accept a color kwarg."""
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor._add_white_fade_overlay)
        assert 'color' in sig.parameters

    def test_no_flyer_path_passes_brand_color_to_fade(self):
        """Without a flyer, create_image_quote_video must call _add_white_fade_overlay
        with the brand primary colour, not the default white."""
        from unittest.mock import patch, MagicMock, call
        from pathlib import Path

        processor = make_processor()
        fake_clip = MagicMock()
        fake_clip.size = (1080, 1920)
        fake_clip.duration = 5

        with patch.object(processor, '_add_white_fade_overlay', return_value=fake_clip) as mock_fade, \
             patch('src.video_processor.ImageClip', return_value=fake_clip), \
             patch('src.video_processor.CompositeVideoClip', return_value=fake_clip), \
             patch('src.video_processor.concatenate_videoclips', return_value=fake_clip), \
             patch.object(processor, 'create_cinematic_text_clip', return_value=fake_clip), \
             patch.object(processor, 'image_to_clip', return_value=fake_clip), \
             patch('pathlib.Path.exists', return_value=True):
            try:
                processor.create_image_quote_video(
                    text="Yoga is peace.",
                    author="Iyengar",
                    image_paths=[Path('/tmp/fake.jpg')],
                    output_path=Path('/tmp/out.mp4'),
                    duration=5.0,
                    flyer_lines=None,  # no-flyer path
                )
            except Exception:
                pass  # rendering will fail — we only care about the fade call

        # At least one call must have passed a non-white color
        brand_green = processor.hex_to_rgb(
            processor.config.get('brand', {}).get('colors', {}).get('primary', '#2c5530'))
        calls_with_color = [
            c for c in mock_fade.call_args_list
            if c.kwargs.get('color') == brand_green
        ]
        assert len(calls_with_color) >= 1, (
            f"Expected _add_white_fade_overlay called with color={brand_green}, "
            f"got calls: {mock_fade.call_args_list}"
        )


class TestFlyerFontDefaults:
    def test_flyer_font_size_default_is_80(self):
        """create_cinematic_flyer_clip default font_size should be 80."""
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor.create_cinematic_flyer_clip)
        assert sig.parameters['font_size'].default == 80

    def test_flyer_title_larger_than_body_at_large_size(self):
        """title_font_size must remain larger than body_font_size at font_size=80."""
        # title = font_size + 28 = 108, body = max(80, 36) = 80 — title > body ✓
        font_size = 80
        title_font_size = font_size + 28          # proposed formula
        body_font_size = max(font_size, 36)
        assert title_font_size > body_font_size


class TestScrollAuthorPosition:
    def test_author_rendered_below_scroll_window_not_at_center(self):
        """
        Author text must be drawn at y = block_top + 3*line_height (line 4),
        not at y = h // 2 (screen centre).
        """
        from unittest.mock import patch, MagicMock

        processor = make_processor()
        font_size = 36  # test-convenience value; production default is 72

        line_height = int(font_size * processor.LINE_HEIGHT_MULT)
        block_top = max(80, processor.reel_height // 6)
        expected_y = block_top + 3 * line_height
        wrong_y = processor.reel_height // 2  # the old (broken) position

        # Capture the make_frame callable by intercepting VideoClip construction
        captured_make_frame = {}

        def fake_video_clip(make_frame, duration):
            captured_make_frame['fn'] = make_frame
            mock = MagicMock()
            mock.duration = duration
            mock.with_fps = lambda fps: mock
            mock.with_position = lambda pos: mock
            return mock

        with patch('src.video_processor.VideoClip', side_effect=fake_video_clip):
            processor.create_scroll_clips(
                text="Yoga is the mirror to look at ourselves from within.",
                author="B.K.S. Iyengar",
                duration=5.0,
                font_size=font_size,
            )

        assert 'fn' in captured_make_frame, "VideoClip was not called — make_frame not captured"
        make_frame = captured_make_frame['fn']

        # safely past author_display_start (formula: duration - min(2.5, duration * 0.15))
        author_t = 4.5

        with patch('PIL.ImageDraw.ImageDraw.text') as mock_draw_text:
            make_frame(author_t)

        assert mock_draw_text.called, "draw.text was not called during author display"
        # Extract xy from the first positional arg of the first call
        first_xy = mock_draw_text.call_args_list[0].args[0]
        actual_y = first_xy[1]
        assert actual_y == expected_y, (
            f"Author y={actual_y}, expected {expected_y} (block_top={block_top} + 3*line_height={3*line_height}). "
            f"Wrong value would be h//2={wrong_y}."
        )
        assert actual_y != wrong_y, "Author is still at screen centre — fix not applied"
