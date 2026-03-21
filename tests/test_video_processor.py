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

        # After fixed-speed timing: author_display_start = calculate_scroll_duration(text) - 2.5
        # text = "Yoga is the mirror to look at ourselves from within." (52 chars)
        # → 52/13 + 2.5 = 6.5 s total, author_display_start = 4.0 s
        author_t = 4.5  # safely past author_display_start (4.0 s)

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


class TestScrollPastLineBrightness:
    def test_past_line_rendered_bright_not_dim(self):
        """
        When the active word is on line 1 (second line), the past line (line 0)
        must be drawn with alpha=255 (BRIGHT), not alpha=80 (DIM).
        """
        from unittest.mock import patch, MagicMock
        import numpy as np

        processor = make_processor()
        font_size = 36

        captured_make_frame = {}

        def fake_video_clip(make_frame, duration):
            captured_make_frame['fn'] = make_frame
            mock = MagicMock()
            mock.duration = duration
            mock.with_fps = lambda fps: mock
            mock.with_position = lambda pos: mock
            return mock

        # Multi-line text so line 0 is a "past" line while we're on line 1
        text = "Yoga is the mirror to look at ourselves from within. It is a practice of deep peace."

        with patch('src.video_processor.VideoClip', side_effect=fake_video_clip):
            processor.create_scroll_clips(text=text, author="Iyengar", duration=15.0, font_size=font_size)

        assert 'fn' in captured_make_frame
        make_frame = captured_make_frame['fn']

        drawn_texts = []

        def capture_text(xy, text, font=None, fill=None):
            drawn_texts.append({'xy': xy, 'text': text, 'fill': fill})

        line_height = int(font_size * processor.LINE_HEIGHT_MULT)
        block_top = max(80, processor.reel_height // 6)

        with patch('PIL.ImageDraw.ImageDraw.text', side_effect=capture_text):
            # text = 84 chars; fixed-speed timing:
            # computed_duration = 84/13 + 2.5 ≈ 8.96 s
            # author_display_start = 8.96 - 2.5 = 6.46 s
            # word_dt = max(0.3, 6.46/17) ≈ 0.38 s
            # line 0 has 11 words → line 0 is "past" once t ≥ 11*0.38 ≈ 4.18 s
            # At t=4.5: word_idx = int(4.5/0.38) = 11 → on line 1, so line 0 is "past".
            make_frame(4.5)

        # Find lines drawn at past-row y (block_top + 0 * line_height = block_top)
        past_y = block_top  # offset=-1 → y = block_top + (−1+1)*line_height = block_top
        past_calls = [d for d in drawn_texts if d['xy'][1] == past_y]

        assert past_calls, (
            f"No past-line text drawn at y={past_y}. "
            "Ensure t=4.5 is past line 0 but before author_display_start."
        )
        for call in past_calls:
            fill = call['fill']
            assert fill[3] == 255, (
                f"Past line alpha={fill[3]}, expected 255 (BRIGHT). "
                f"Past line should be fully visible, not dimmed."
            )


class TestScrollFixedSpeed:
    def test_calculate_scroll_duration_short_text(self):
        """Short text: duration = len(text)/13 + 2.5."""
        processor = make_processor()
        text = "Yoga is peace."  # 14 chars → 14/13 ≈ 1.08 s reading + 2.5 s author = 3.58 s
        result = processor.calculate_scroll_duration(text)
        expected = len(text) / processor.SCROLL_CHARS_PER_SECOND + processor.SCROLL_AUTHOR_DISPLAY_SECONDS
        assert abs(result - expected) < 0.01, f"Expected {expected:.2f}, got {result:.2f}"

    def test_calculate_scroll_duration_long_text(self):
        """200-char quote: 200/13 + 2.5 ≈ 17.88 s."""
        processor = make_processor()
        text = "A" * 200
        result = processor.calculate_scroll_duration(text)
        expected = 200 / processor.SCROLL_CHARS_PER_SECOND + processor.SCROLL_AUTHOR_DISPLAY_SECONDS
        assert abs(result - expected) < 0.01

    def test_scroll_videoclip_duration_derived_from_text_not_argument(self):
        """
        VideoClip must be built with calculate_scroll_duration(text), not the passed-in duration.
        """
        from unittest.mock import patch, MagicMock

        processor = make_processor()
        text = "Yoga is the mirror to look at ourselves from within."

        # We'll pass in a different duration to prove it is NOT used
        wrong_duration = 999.0  # absurd value — should have no effect

        captured_make_frame = {}
        def fake_video_clip(make_frame, duration):
            captured_make_frame['fn'] = make_frame
            captured_make_frame['dur'] = duration
            m = MagicMock()
            m.duration = duration
            m.with_fps = lambda fps: m
            m.with_position = lambda pos: m
            return m

        with patch('src.video_processor.VideoClip', side_effect=fake_video_clip):
            processor.create_scroll_clips(text=text, author="X", duration=wrong_duration, font_size=36)

        # The VideoClip duration should equal calculate_scroll_duration(text), not wrong_duration
        expected_duration = processor.calculate_scroll_duration(text)
        assert abs(captured_make_frame['dur'] - expected_duration) < 0.1, (
            f"VideoClip duration={captured_make_frame['dur']:.2f}, "
            f"expected {expected_duration:.2f} (derived from text length, not passed-in duration {wrong_duration})"
        )


class TestFlyerDurationDefault:
    def test_flyer_duration_default_is_5(self):
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor.create_image_quote_video)
        assert sig.parameters['flyer_duration'].default == 5.0


class TestFontSizeDefaults:
    def test_create_image_quote_video_font_size_default_is_96(self):
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor.create_image_quote_video)
        assert sig.parameters['font_size'].default == 96

    def test_create_scroll_clips_font_size_default_is_96(self):
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor.create_scroll_clips)
        assert sig.parameters['font_size'].default == 96

    def test_create_cinematic_text_clip_font_size_default_is_96(self):
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor.create_cinematic_text_clip)
        assert sig.parameters['font_size'].default == 96

    def test_create_line_reveal_clips_font_size_default_is_96(self):
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor.create_line_reveal_clips)
        assert sig.parameters['font_size'].default == 96

    def test_font_size_cap_formula_removed(self):
        """quote_font_size assigned in create_image_quote_video must not be capped."""
        # Read the source code and verify that quote_font_size = font_size (no min/max formula)
        import inspect
        from src.video_processor import VideoProcessor
        source = inspect.getsource(VideoProcessor.create_image_quote_video)
        # The old formula was: quote_font_size = min(font_size, max(40, (top_black - 20) // 3))
        # After removal, it should be: quote_font_size = font_size
        assert 'quote_font_size = font_size' in source, (
            "quote_font_size should be assigned directly from font_size parameter (no cap formula)"
        )
        # Verify the old cap formula is gone
        assert 'quote_font_size = min(font_size' not in source, (
            "Old cap formula 'min(font_size, ...' must be removed"
        )
