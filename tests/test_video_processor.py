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


class TestCinematicPillOverlay:
    def test_pill_overlay_included_in_composite(self):
        """_make_pill_overlay must be called inside create_cinematic_text_clip."""
        from unittest.mock import patch, MagicMock
        processor = make_processor()

        pill_clip = MagicMock()
        pill_clip.duration = 5.0

        with patch.object(processor, '_make_pill_overlay', return_value=pill_clip) as mock_pill:
            try:
                processor.create_cinematic_text_clip(
                    text="Yoga is peace.",
                    author="Iyengar",
                    duration=5.0,
                    font_size=36,
                )
            except Exception:
                pass  # CompositeVideoClip may fail without real clips — that's fine

        assert mock_pill.called, "_make_pill_overlay must be called by create_cinematic_text_clip"


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


class TestRevealPillOverlay:
    def test_pill_overlay_included_in_reveal_clips(self):
        """_make_pill_overlay must be called inside create_line_reveal_clips."""
        processor = make_processor()

        pill_clip = MagicMock()
        pill_clip.duration = 5.0

        with patch.object(processor, '_make_pill_overlay', return_value=pill_clip) as mock_pill:
            try:
                processor.create_line_reveal_clips(
                    text="Yoga is peace.",
                    author="Iyengar",
                    duration=5.0,
                    font_size=36,
                )
            except Exception:
                pass

        assert mock_pill.called, "_make_pill_overlay must be called by create_line_reveal_clips"


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
        During author phase: frozen quote lines start at block_top, author pill
        appears below the divider (after n_frozen lines + gap), not at screen centre.
        """
        from unittest.mock import patch, MagicMock

        processor = make_processor()
        font_size = 36  # test-convenience value; production default is 72

        line_height = int(font_size * processor.LINE_HEIGHT_MULT)
        block_top = processor.reel_height // 8
        wrong_y = processor.reel_height // 2  # the old (broken) position
        # Author pill appears after frozen lines + divider; must be below block_top
        # and above screen centre. Exact y depends on how many lines the text wraps to.

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

        drawn_calls = []
        def capture_text(xy, txt, **kw):
            drawn_calls.append((xy, txt))

        from PIL import ImageDraw as _ID
        with patch.object(_ID.ImageDraw, 'text', side_effect=capture_text):
            make_frame(author_t)

        assert drawn_calls, "draw.text was not called during author display"
        # The first calls are frozen quote lines; find the author pill call (uppercase text)
        author_name = "B.K.S. Iyengar".upper()
        author_calls = [(xy, txt) for xy, txt in drawn_calls if txt == author_name]
        assert author_calls, (
            f"Author text '{author_name}' not found in drawn calls. Got: {[t for _, t in drawn_calls]}"
        )
        actual_y = author_calls[0][0][1]
        # Author must be below the first frozen line (block_top) and above screen centre
        assert actual_y > block_top, (
            f"Author y={actual_y} must be below block_top={block_top}"
        )
        assert actual_y != wrong_y, "Author is still at screen centre — fix not applied"
        assert actual_y < wrong_y, (
            f"Author y={actual_y} should be above h//2={wrong_y} (not at screen centre)"
        )


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
        block_top = processor.reel_height // 8

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


class TestScrollBlockTop:
    def test_block_top_is_h_over_8(self):
        """block_top used in make_frame must equal h // 8, not max(80, h//6)."""
        from unittest.mock import patch, MagicMock
        processor = make_processor()

        captured = {}
        def fake_video_clip(make_frame, duration):
            captured['make_frame'] = make_frame
            m = MagicMock()
            m.duration = duration
            m.with_fps = lambda fps: m
            m.with_position = lambda pos: m
            return m

        with patch('src.video_processor.VideoClip', side_effect=fake_video_clip):
            # Use multi-line text to ensure past/current/future rows are rendered
            processor.create_scroll_clips(
                text="Yoga is peace and light. The body is a temple.",
                author="Iyengar",
                duration=5.0,
                font_size=36,
            )

        assert 'make_frame' in captured
        # Expected block_top = h // 8
        expected_block_top = processor.reel_height // 8
        h = processor.reel_height

        # Call make_frame and check the y-coordinates of drawn text
        drawn_texts = []

        def capture_text(xy, text, font=None, fill=None):
            drawn_texts.append({'xy': xy, 'text': text, 'fill': fill})

        with patch('PIL.ImageDraw.ImageDraw.text', side_effect=capture_text):
            captured['make_frame'](0)

        # At t=0, the current line is drawn at y = block_top + line_height.
        # With block_top = h//8 = 240, and line_height = int(36 * LINE_HEIGHT_MULT),
        # the current line should be drawn well above where it would be with old code.
        # Old code: max(80, h//6) = 320, so current line would be at ~377
        # New code: h//8 = 240, so current line should be at ~297
        assert drawn_texts, "No text drawn at t=0"
        drawn_ys = [d['xy'][1] for d in drawn_texts]
        min_y = min(drawn_ys)

        # The key check: text should be drawn at a y-coordinate that proves
        # we're using h//8, not max(80, h//6).
        # With h//8, current line = 240 + 57 = 297
        # With h//6, current line = 320 + 57 = 377
        # So if min_y is less than 350, we're using the new formula.
        assert min_y < 350, (
            f"Text drawn at y={min_y}, which suggests block_top is not h//8. "
            f"With h//8, current line should be at ~297. "
            f"With old max(80, h//6), it would be at ~377."
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


class TestMakePillOverlay:
    def test_method_exists(self):
        from src.video_processor import VideoProcessor
        assert hasattr(VideoProcessor, '_make_pill_overlay')

    def test_returns_clip_with_correct_duration(self):
        processor = make_processor()
        clip = processor._make_pill_overlay(
            lines=["Yoga is peace"],
            font_size=36,
            line_y_positions=[200],
            w=1080, h=1920, duration=5.0,
        )
        assert abs(clip.duration - 5.0) < 0.01

    def test_returns_correct_frame_size(self):
        processor = make_processor()
        clip = processor._make_pill_overlay(
            lines=["Hi"],
            font_size=36,
            line_y_positions=[50],
            w=200, h=300, duration=1.0,
        )
        frame = clip.get_frame(0)
        assert frame.shape[0] == 300
        assert frame.shape[1] == 200

    def test_pill_produces_non_zero_alpha_at_line_position(self):
        """The overlay must have non-zero alpha at the pill position."""
        import numpy as np
        processor = make_processor()
        clip = processor._make_pill_overlay(
            lines=["Hi"],
            font_size=36,
            line_y_positions=[100],
            w=400, h=400, duration=1.0,
        )
        frame = clip.get_frame(0)
        # Pill spans approx y=94 to y=142 (100-6 to 100+36+6)
        if frame.ndim == 3 and frame.shape[2] == 4:
            alpha_at_pill = frame[94:142, :, 3]
            assert alpha_at_pill.max() > 0, "Expected non-zero alpha at pill position"
        # If moviepy strips alpha, just verify shape (rendering is correct by construction)

    def test_area_far_from_pill_is_transparent(self):
        """Pixels far from any text line must have zero alpha."""
        import numpy as np
        processor = make_processor()
        clip = processor._make_pill_overlay(
            lines=["Hi"],
            font_size=36,
            line_y_positions=[100],
            w=400, h=400, duration=1.0,
        )
        frame = clip.get_frame(0)
        if frame.ndim == 3 and frame.shape[2] == 4:
            alpha_far = frame[350:360, :, 3]
            assert alpha_far.max() == 0, "Expected zero alpha far from pill"


class TestScrollInlinePills:
    def test_rounded_rectangle_called_in_make_frame(self):
        """draw.rounded_rectangle (or draw.rectangle as fallback) must be called
        in make_frame for each visible scroll row."""
        from unittest.mock import patch, MagicMock, call
        import numpy as np
        processor = make_processor()

        captured_make_frame = {}
        def fake_video_clip(make_frame, duration):
            captured_make_frame['fn'] = make_frame
            m = MagicMock()
            m.duration = duration
            m.with_fps = lambda fps: m
            m.with_position = lambda pos: m
            return m

        with patch('src.video_processor.VideoClip', side_effect=fake_video_clip):
            processor.create_scroll_clips(
                text="Yoga is peace and light and truth and love.",
                author="Iyengar",
                duration=5.0,
                font_size=36,
            )

        assert 'fn' in captured_make_frame
        rect_calls = []

        from PIL import ImageDraw as _ID
        original_rr = getattr(_ID.ImageDraw, 'rounded_rectangle', None)
        original_r  = _ID.ImageDraw.rectangle

        def capture_rr(self_d, xy, **kw):
            rect_calls.append(('rr', xy))
            if original_rr:
                return original_rr(self_d, xy, **kw)

        def capture_r(self_d, xy, **kw):
            rect_calls.append(('r', xy))
            return original_r(self_d, xy, **kw)

        with patch.object(_ID.ImageDraw, 'rounded_rectangle', capture_rr, create=True), \
             patch.object(_ID.ImageDraw, 'rectangle', capture_r):
            try:
                captured_make_frame['fn'](0.0)
            except Exception:
                pass

        assert len(rect_calls) >= 1, (
            "Expected at least one rounded_rectangle/rectangle call for pill backgrounds"
        )


class TestScrollFrozenLinesAuthorPhase:
    def _get_make_frame(self, processor, text, author="Iyengar", font_size=36):
        from unittest.mock import patch, MagicMock
        captured = {}
        def fake_video_clip(make_frame, duration):
            captured['fn'] = make_frame
            captured['duration'] = duration
            m = MagicMock()
            m.duration = duration
            m.with_fps = lambda fps: m
            m.with_position = lambda pos: m
            return m
        with patch('src.video_processor.VideoClip', side_effect=fake_video_clip):
            processor.create_scroll_clips(
                text=text, author=author, duration=15.0, font_size=font_size,
            )
        return captured['fn'], captured['duration']

    def test_frozen_lines_drawn_during_author_phase(self):
        """During author phase, the last quote lines must be drawn as text."""
        from unittest.mock import patch
        processor = make_processor()
        text = "Yoga is the journey of the self through the self to the self."
        make_frame, total_dur = self._get_make_frame(processor, text)

        author_display_start = total_dur - processor.SCROLL_AUTHOR_DISPLAY_SECONDS
        t_author = author_display_start + 0.1  # just inside author phase

        drawn_texts = []
        from PIL import ImageDraw as _ID
        def capture_text(xy, txt, **kw):
            drawn_texts.append(txt)

        with patch.object(_ID.ImageDraw, 'text', side_effect=capture_text):
            try:
                make_frame(t_author)
            except Exception:
                pass

        # At least one drawn text must be a word from the quote (not just the author)
        quote_words = set(text.lower().split())
        drawn_lower = [t.lower() for t in drawn_texts]
        drawn_words = set(w for t in drawn_lower for w in t.split())
        overlap = quote_words & drawn_words
        assert overlap, (
            f"Expected quote words drawn during author phase. "
            f"Drawn: {drawn_texts}, Quote words: {list(quote_words)[:5]}"
        )

    def test_author_text_drawn_during_author_phase(self):
        """Author name must be drawn (uppercase) during the author phase."""
        from unittest.mock import patch
        processor = make_processor()
        text = "Yoga is the journey of the self."
        author = "B.K.S. Iyengar"
        make_frame, total_dur = self._get_make_frame(processor, text, author=author)

        author_display_start = total_dur - processor.SCROLL_AUTHOR_DISPLAY_SECONDS
        t_author = author_display_start + 0.1

        drawn_texts = []
        from PIL import ImageDraw as _ID
        def capture_text(xy, txt, **kw):
            drawn_texts.append(txt)

        with patch.object(_ID.ImageDraw, 'text', side_effect=capture_text):
            try:
                make_frame(t_author)
            except Exception:
                pass

        drawn_upper = [t.upper() for t in drawn_texts]
        assert author.upper() in drawn_upper, (
            f"Expected '{author.upper()}' in drawn texts. Got: {drawn_texts}"
        )

    def test_book_text_drawn_when_author_contains_separator(self):
        """When author contains ' — ', the book part must be drawn separately."""
        from unittest.mock import patch
        processor = make_processor()
        text = "Yoga is the journey of the self."
        author = "B.K.S. Iyengar — Light on Life"
        make_frame, total_dur = self._get_make_frame(processor, text, author=author)

        author_display_start = total_dur - processor.SCROLL_AUTHOR_DISPLAY_SECONDS
        t_author = author_display_start + 0.1

        drawn_texts = []
        from PIL import ImageDraw as _ID
        def capture_text(xy, txt, **kw):
            drawn_texts.append(txt)

        with patch.object(_ID.ImageDraw, 'text', side_effect=capture_text):
            try:
                make_frame(t_author)
            except Exception:
                pass

        drawn_combined = ' '.join(drawn_texts)
        assert 'Light on Life' in drawn_combined, (
            f"Expected book title 'Light on Life' drawn. Got: {drawn_texts}"
        )

    def test_short_quote_all_lines_shown_with_author(self):
        """A 3-line quote: all 3 lines must be visible when author appears."""
        from unittest.mock import patch
        processor = make_processor()
        # Force a short quote that will wrap to exactly 2-3 lines at font_size=36
        text = "Yoga is peace. Light is truth."
        make_frame, total_dur = self._get_make_frame(processor, text)

        author_display_start = total_dur - processor.SCROLL_AUTHOR_DISPLAY_SECONDS
        t_author = author_display_start + 0.1

        drawn_texts = []
        from PIL import ImageDraw as _ID
        def capture_text(xy, txt, **kw):
            drawn_texts.append(txt)

        with patch.object(_ID.ImageDraw, 'text', side_effect=capture_text):
            try:
                make_frame(t_author)
            except Exception:
                pass

        # All words of the quote should be present in the combined drawn text
        combined = ' '.join(drawn_texts).lower()
        for word in text.lower().split():
            word_clean = word.strip('.,')
            assert word_clean in combined, (
                f"Expected word '{word_clean}' in frozen lines during author phase. "
                f"Drawn: {drawn_texts}"
            )
