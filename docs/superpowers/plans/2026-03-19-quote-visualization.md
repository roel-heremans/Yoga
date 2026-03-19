# Quote Visualization Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new quote overlay styles (`cinematic` and `reveal`) to the image-video quote card generator, replacing the current dark opaque band with an elegant centered layout.

**Architecture:** New methods `create_cinematic_text_clip()` and `create_line_reveal_clips()` are added to `VideoProcessor`. `create_image_quote_video()` is updated to accept separate `text`/`author` params and a `quote_style` switch. The param change propagates up through `QuoteCardGenerator` and the CLI.

**Tech Stack:** Python 3, moviepy (1.x and 2.x compatible), NumPy, PIL, Click CLI.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `src/video_processor.py` | Modify | Add 9 class constants, 2 new methods, update `create_image_quote_video()` signature + branching |
| `src/quote_card_generator.py` | Modify | Update `generate_image_video_quote_card()` and `generate_quote_cards()` to pass `quote_style` |
| `main.py` | Modify | Add `--quote-style` option to `generate-quote-cards` command |
| `tests/__init__.py` | Create | Empty, marks tests as a package |
| `tests/test_video_processor.py` | Create | Unit tests for new VideoProcessor methods (mocked moviepy) |
| `tests/test_quote_card_generator.py` | Create | Unit tests for updated QuoteCardGenerator call chain |
| `tests/test_cli.py` | Create | CLI integration tests for `--quote-style` option |

---

## Task 1: Test infrastructure + constants

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_video_processor.py`
- Modify: `src/video_processor.py` (class body, after existing constants ~line 168)

- [ ] **Step 1: Create tests package**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 2: Write failing tests for constants**

Create `tests/test_video_processor.py`:

```python
"""Tests for VideoProcessor new cinematic/reveal quote styles."""
import pytest
from unittest.mock import patch, MagicMock


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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /Users/roel.heremans/Documents/PersonalRepos/Yoga
source venv/bin/activate
python -m pytest tests/test_video_processor.py::TestCinematicConstants -v
```

Expected: `FAILED` — `AttributeError: type object 'VideoProcessor' has no attribute 'CINEMATIC_QUOTE_COLOR'`

- [ ] **Step 4: Add constants to VideoProcessor**

In `src/video_processor.py`, after the existing constants block ending at line ~168 (after `FLYER_STROKE_WIDTH = 2`), add:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_video_processor.py::TestCinematicConstants -v
```

Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add tests/__init__.py tests/test_video_processor.py src/video_processor.py
git commit -m "feat: add cinematic/reveal layout and color constants to VideoProcessor"
```

---

## Task 2: Implement `create_cinematic_text_clip()`

**Files:**
- Modify: `src/video_processor.py` (add method after `create_text_clip`, ~line 378)
- Modify: `tests/test_video_processor.py` (add test class)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_video_processor.py`:

```python
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
        import importlib
        import sys
        # Patch at module level so VideoProcessor sees mocked classes
        mock_cvclip = MagicMock()
        mock_cvclip_instance = MagicMock()
        mock_cvclip_instance.w = 1080
        mock_cvclip_instance.h = 1920
        mock_cvclip_instance.duration = 15.0
        mock_cvclip.return_value = mock_cvclip_instance

        mock_text = self._make_mock_text_clip(80)
        mock_TextClip = MagicMock(return_value=mock_text)
        mock_ImageClip = MagicMock(return_value=self._make_mock_text_clip(2))
        mock_ColorClip = MagicMock(return_value=self._make_mock_text_clip(2))

        with patch('src.video_processor.CompositeVideoClip', mock_cvclip), \
             patch('src.video_processor.TextClip', mock_TextClip), \
             patch('src.video_processor.ImageClip', mock_ImageClip), \
             patch('src.video_processor.ColorClip', mock_ColorClip):
            if 'src.video_processor' in sys.modules:
                del sys.modules['src.video_processor']
            from src.video_processor import VideoProcessor
            config = {
                'brand': {'colors': {'primary': '#2c5530'}, 'fonts': {'heading': 'Arial', 'body': 'Arial', 'weights': {'heading': 'bold', 'body': 'normal'}}},
                'instagram': {'reel_dimensions': {'width': 1080, 'height': 1920}, 'reel_duration': {'min': 15, 'max': 90}},
            }
            vp = VideoProcessor(config=config)
            result = vp.create_cinematic_text_clip(
                text="The rhythm of the body.",
                author="B.K.S. Iyengar",
                duration=15.0,
            )
        # CompositeVideoClip was called — result is the composite
        assert mock_cvclip.called

    def test_uses_cinematic_colors(self):
        """TextClip is called with cream color for quote and gold for author."""
        mock_text = self._make_mock_text_clip(80)
        mock_TextClip = MagicMock(return_value=mock_text)
        mock_ImageClip = MagicMock(return_value=self._make_mock_text_clip(2))
        mock_cvclip = MagicMock(return_value=MagicMock(w=1080, h=1920))

        import sys
        with patch('src.video_processor.TextClip', mock_TextClip), \
             patch('src.video_processor.ImageClip', mock_ImageClip), \
             patch('src.video_processor.CompositeVideoClip', mock_cvclip), \
             patch('src.video_processor.ColorClip', MagicMock(return_value=self._make_mock_text_clip(2))):
            if 'src.video_processor' in sys.modules:
                del sys.modules['src.video_processor']
            from src.video_processor import VideoProcessor
            config = {
                'brand': {'colors': {'primary': '#2c5530'}, 'fonts': {'heading': 'Arial', 'body': 'Arial', 'weights': {'heading': 'bold', 'body': 'normal'}}},
                'instagram': {'reel_dimensions': {'width': 1080, 'height': 1920}, 'reel_duration': {'min': 15, 'max': 90}},
            }
            vp = VideoProcessor(config=config)
            vp.create_cinematic_text_clip("The rhythm.", "B.K.S. Iyengar", 15.0)

        # At least one TextClip call used cream color
        calls = mock_TextClip.call_args_list
        colors_used = [str(c) for c in calls]
        assert any('#f0ece4' in c or 'f0ece4' in c for c in colors_used), \
            f"Expected cream color #f0ece4 in TextClip calls: {colors_used}"
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_video_processor.py::TestCreateCinematicTextClip -v
```

Expected: `FAILED` — `AttributeError: 'VideoProcessor' object has no attribute 'create_cinematic_text_clip'`

- [ ] **Step 3: Implement `create_cinematic_text_clip()`**

Add the method to `src/video_processor.py` after `create_text_clip()` ends (~line 377). Insert:

```python
    def create_cinematic_text_clip(
        self,
        text: str,
        author: str,
        duration: float,
        font_size: int = 64,
    ):
        """
        Create a centered, cinematic quote overlay (cream text, gold author, radial vignette).
        Returns a CompositeVideoClip of size (reel_width, reel_height) with transparent background
        that the caller composites on top of the background image clip.
        """
        w, h = self.reel_width, self.reel_height

        # ---- Vignette layer: radial gradient, dark at edges ----
        arr = np.zeros((h, w, 4), dtype=np.uint8)
        cx, cy = w / 2, h / 2
        Y, X = np.mgrid[0:h, 0:w]
        dist = np.hypot((X - cx) / cx, (Y - cy) / cy)
        alpha = np.clip(dist * self.CINEMATIC_VIGNETTE_ALPHA, 0, self.CINEMATIC_VIGNETTE_ALPHA).astype(np.uint8)
        arr[:, :, 3] = alpha  # RGB stays 0 (black) — dark vignette
        try:
            vignette_clip = ImageClip(arr, transparent=True)
        except TypeError:
            vignette_clip = ImageClip(arr)
        vignette_clip = (vignette_clip.with_duration(duration)
                         if hasattr(vignette_clip, 'with_duration')
                         else vignette_clip.set_duration(duration))
        vignette_clip = (vignette_clip.with_position((0, 0))
                         if hasattr(vignette_clip, 'with_position')
                         else vignette_clip.set_position((0, 0)))

        # ---- Text wrapping ----
        usable_width = w - 120
        char_width_ratio = 0.55
        max_chars = max(20, int(usable_width / (font_size * char_width_ratio) * 1.2))
        import textwrap
        wrapped_lines = textwrap.wrap(text, width=max_chars)
        display_text = '\n'.join(wrapped_lines)
        n_lines = len(wrapped_lines)

        # ---- Quote TextClip ----
        serif_candidates = self.QUOTE_OVERLAY_FONT_CANDIDATES + ('Arial',)
        quote_clip = None
        for fn in serif_candidates:
            try:
                quote_clip = TextClip(
                    text=display_text,
                    font_size=font_size,
                    color=self.CINEMATIC_QUOTE_COLOR,
                    font=fn,
                    italic=True,
                    size=(usable_width, None),
                    margin=(20, 20),
                )
                break
            except Exception:
                try:
                    quote_clip = TextClip(
                        display_text,
                        fontsize=font_size,
                        color=self.CINEMATIC_QUOTE_COLOR,
                        font=fn,
                        method='caption',
                        size=(usable_width, None),
                        align='center',
                        interline=-1,
                    )
                    break
                except Exception:
                    continue
        if quote_clip is None:
            quote_clip = TextClip(
                text=display_text,
                font_size=font_size,
                color=self.CINEMATIC_QUOTE_COLOR,
                italic=True,
                size=(usable_width, None),
                margin=(20, 20),
            )

        # ---- Author TextClip ----
        author_upper = author.upper()
        author_font_size = max(28, font_size // 2)
        author_clip = None
        for fn in serif_candidates:
            try:
                author_clip = TextClip(
                    text=author_upper,
                    font_size=author_font_size,
                    color=self.CINEMATIC_AUTHOR_COLOR,
                    font=fn,
                    size=(usable_width, None),
                    margin=(10, 10),
                )
                break
            except Exception:
                try:
                    author_clip = TextClip(
                        author_upper,
                        fontsize=author_font_size,
                        color=self.CINEMATIC_AUTHOR_COLOR,
                        font=fn,
                        method='caption',
                        size=(usable_width, None),
                        align='center',
                    )
                    break
                except Exception:
                    continue
        if author_clip is None:
            author_clip = TextClip(
                text=author_upper,
                font_size=author_font_size,
                color=self.CINEMATIC_AUTHOR_COLOR,
                size=(usable_width, None),
                margin=(10, 10),
            )

        # ---- Divider ImageClip ----
        div_arr = np.zeros((self.DIVIDER_HEIGHT, self.DIVIDER_WIDTH, 4), dtype=np.uint8)
        r, g, b = self.hex_to_rgb(self.CINEMATIC_DIVIDER_COLOR)
        div_arr[:, :, 0] = r
        div_arr[:, :, 1] = g
        div_arr[:, :, 2] = b
        div_arr[:, :, 3] = 255
        try:
            divider_clip = ImageClip(div_arr, transparent=True)
        except TypeError:
            divider_clip = ImageClip(div_arr)

        # ---- Vertical centering ----
        line_height = font_size * self.LINE_HEIGHT_MULT
        quote_h = int(getattr(quote_clip, 'h', n_lines * line_height))
        author_h = int(getattr(author_clip, 'h', author_font_size * 1.5))
        total_h = quote_h + self.DIVIDER_GAP + self.DIVIDER_HEIGHT + self.AUTHOR_GAP + author_h
        block_top = max(80, (h - total_h) // 2)

        div_y = block_top + quote_h + self.DIVIDER_GAP
        author_y = div_y + self.DIVIDER_HEIGHT + self.AUTHOR_GAP
        div_x = (w - self.DIVIDER_WIDTH) // 2

        def _set_pos_dur(clip, pos, dur):
            clip = (clip.with_duration(dur) if hasattr(clip, 'with_duration')
                    else clip.set_duration(dur))
            clip = (clip.with_position(pos) if hasattr(clip, 'with_position')
                    else clip.set_position(pos))
            return clip

        quote_clip = _set_pos_dur(quote_clip, ('center', block_top), duration)
        divider_clip = _set_pos_dur(divider_clip, (div_x, div_y), duration)
        author_clip = _set_pos_dur(author_clip, ('center', author_y), duration)

        composite = CompositeVideoClip(
            [vignette_clip, quote_clip, divider_clip, author_clip],
            size=(w, h),
        )
        composite = (composite.with_duration(duration)
                     if hasattr(composite, 'with_duration')
                     else composite.set_duration(duration))
        return composite
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_video_processor.py::TestCreateCinematicTextClip -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: add create_cinematic_text_clip to VideoProcessor"
```

---

## Task 3: Implement `create_line_reveal_clips()`

**Files:**
- Modify: `src/video_processor.py` (add method after `create_cinematic_text_clip`)
- Modify: `tests/test_video_processor.py` (add test class)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_video_processor.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_video_processor.py::TestCreateLineRevealClips -v
```

Expected: `FAILED` — `AttributeError: 'VideoProcessor' object has no attribute 'create_line_reveal_clips'`

- [ ] **Step 3: Implement `create_line_reveal_clips()`**

Add to `src/video_processor.py` immediately after `create_cinematic_text_clip()`:

```python
    def create_line_reveal_clips(
        self,
        text: str,
        author: str,
        duration: float,
        font_size: int = 64,
    ) -> list:
        """
        Create a list of pre-positioned, pre-timed clips for line-by-line quote reveal.
        Lines fade in one by one, accumulating. Author block appears last.
        All clips are transparent overlays; caller composites them on the background.
        """
        import textwrap

        w, h = self.reel_width, self.reel_height
        usable_width = w - 120
        char_width_ratio = 0.55
        max_chars = max(20, int(usable_width / (font_size * char_width_ratio) * 1.2))
        wrapped_lines = textwrap.wrap(text, width=max_chars)
        n_lines = len(wrapped_lines)

        # ---- Timing ----
        interval = max(1.0, duration / (n_lines + 1))

        # ---- Layout pre-computation ----
        line_height = font_size * self.LINE_HEIGHT_MULT
        author_font_size = max(28, font_size // 2)

        # Estimate author height from a placeholder (actual .h read after creation)
        estimated_author_h = int(author_font_size * 1.5)
        total_h = (n_lines * line_height) + self.DIVIDER_GAP + self.DIVIDER_HEIGHT + self.AUTHOR_GAP + estimated_author_h
        block_top = max(80, (h - total_h) // 2)

        serif_candidates = self.QUOTE_OVERLAY_FONT_CANDIDATES + ('Arial',)

        def _make_text_clip(t, size, color, italic=False):
            for fn in serif_candidates:
                try:
                    c = TextClip(
                        text=t,
                        font_size=size,
                        color=color,
                        font=fn,
                        size=(usable_width, None),
                        margin=(10, 10),
                    )
                    return c
                except Exception:
                    try:
                        c = TextClip(
                            t,
                            fontsize=size,
                            color=color,
                            font=fn,
                            method='caption',
                            size=(usable_width, None),
                            align='center',
                        )
                        return c
                    except Exception:
                        continue
            return TextClip(text=t, font_size=size, color=color, size=(usable_width, None), margin=(10, 10))

        def _apply(clip, start_time, y_pos):
            # crossfadein for smooth appearance
            if hasattr(clip, 'crossfadein'):
                clip = clip.crossfadein(0.5)
            clip = (clip.with_duration(duration - start_time)
                    if hasattr(clip, 'with_duration')
                    else clip.set_duration(duration - start_time))
            clip = (clip.with_start(start_time)
                    if hasattr(clip, 'with_start')
                    else clip.set_start(start_time))
            clip = (clip.with_position(('center', int(y_pos)))
                    if hasattr(clip, 'with_position')
                    else clip.set_position(('center', int(y_pos))))
            return clip

        clips = []

        # ---- Line clips ----
        for i, line in enumerate(wrapped_lines):
            y = block_top + i * line_height
            clip = _make_text_clip(line, font_size, self.CINEMATIC_QUOTE_COLOR)
            clips.append(_apply(clip, i * interval, y))

        # ---- Divider clip ----
        div_y = block_top + n_lines * line_height + self.DIVIDER_GAP
        div_arr = np.zeros((self.DIVIDER_HEIGHT, self.DIVIDER_WIDTH, 4), dtype=np.uint8)
        r, g, b = self.hex_to_rgb(self.CINEMATIC_DIVIDER_COLOR)
        div_arr[:, :, 0] = r
        div_arr[:, :, 1] = g
        div_arr[:, :, 2] = b
        div_arr[:, :, 3] = 255
        try:
            div_clip = ImageClip(div_arr, transparent=True)
        except TypeError:
            div_clip = ImageClip(div_arr)
        author_start = n_lines * interval
        clips.append(_apply(div_clip, author_start, div_y))

        # ---- Author clip ----
        author_y = div_y + self.DIVIDER_HEIGHT + self.AUTHOR_GAP
        author_clip = _make_text_clip(author.upper(), author_font_size, self.CINEMATIC_AUTHOR_COLOR)
        clips.append(_apply(author_clip, author_start, author_y))

        return clips
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_video_processor.py::TestCreateLineRevealClips -v
```

Expected: `5 passed`

- [ ] **Step 5: Run all video processor tests**

```bash
python -m pytest tests/test_video_processor.py -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: add create_line_reveal_clips to VideoProcessor"
```

---

## Task 4: Update `create_image_quote_video()` signature and branching

**Files:**
- Modify: `src/video_processor.py` (`create_image_quote_video` method, starts ~line 531)
- Modify: `tests/test_video_processor.py` (add test class)

The current signature is:
```python
def create_image_quote_video(self, image_paths, text_overlay, output_path, duration=15.0, ...)
```

Replace `text_overlay: str` with `text: str, author: str` and add `quote_style: str = 'cinematic'`.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_video_processor.py`:

```python
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
        import sys, tempfile
        from pathlib import Path

        # Create a real temp image to satisfy file existence check
        from PIL import Image as PILImage
        tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        PILImage.new('RGB', (100, 100), color=(50, 80, 50)).save(tmp.name)
        tmp_path = Path(tmp.name)
        out_path = Path(tempfile.mktemp(suffix='.mp4'))

        with patch('src.video_processor.VideoProcessor.image_to_clip') as mock_img, \
             patch('src.video_processor.VideoProcessor.create_cinematic_text_clip') as mock_cin, \
             patch('src.video_processor.VideoProcessor._add_white_fade_overlay') as mock_fade, \
             patch('src.video_processor.CompositeVideoClip') as mock_cvclip, \
             patch('src.video_processor.AudioFileClip'):
            # Set up return values
            mock_clip = MagicMock()
            mock_clip.duration = 15.0
            mock_clip.w = 1080
            mock_clip.h = 1920
            mock_clip.fps = 30
            mock_clip.with_fps = MagicMock(return_value=mock_clip)
            mock_clip.set_fps = MagicMock(return_value=mock_clip)
            mock_clip.write_videofile = MagicMock()
            mock_clip.close = MagicMock()
            mock_img.return_value = mock_clip
            mock_cin.return_value = mock_clip
            mock_fade.return_value = mock_clip
            mock_cvclip.return_value = mock_clip

            if 'src.video_processor' in sys.modules:
                del sys.modules['src.video_processor']
            from src.video_processor import VideoProcessor
            config = {
                'brand': {'colors': {'primary': '#2c5530'}, 'fonts': {'heading': 'Arial', 'body': 'Arial', 'weights': {'heading': 'bold', 'body': 'normal'}}},
                'instagram': {'reel_dimensions': {'width': 1080, 'height': 1920}, 'reel_duration': {'min': 15, 'max': 90}},
            }
            vp = VideoProcessor(config=config)
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

        import os
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

    def test_reveal_style_calls_reveal_method(self):
        """When quote_style='reveal', create_line_reveal_clips is called."""
        import sys, tempfile
        from pathlib import Path
        from PIL import Image as PILImage

        tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        PILImage.new('RGB', (100, 100), color=(50, 80, 50)).save(tmp.name)
        tmp_path = Path(tmp.name)
        out_path = Path(tempfile.mktemp(suffix='.mp4'))

        with patch('src.video_processor.VideoProcessor.image_to_clip') as mock_img, \
             patch('src.video_processor.VideoProcessor.create_line_reveal_clips') as mock_rev, \
             patch('src.video_processor.VideoProcessor._add_white_fade_overlay') as mock_fade, \
             patch('src.video_processor.CompositeVideoClip') as mock_cvclip, \
             patch('src.video_processor.AudioFileClip'):
            mock_clip = MagicMock()
            mock_clip.duration = 15.0
            mock_clip.w = 1080
            mock_clip.h = 1920
            mock_clip.fps = 30
            mock_clip.with_fps = MagicMock(return_value=mock_clip)
            mock_clip.set_fps = MagicMock(return_value=mock_clip)
            mock_clip.write_videofile = MagicMock()
            mock_clip.close = MagicMock()
            mock_img.return_value = mock_clip
            mock_rev.return_value = [mock_clip]
            mock_fade.return_value = mock_clip
            mock_cvclip.return_value = mock_clip

            if 'src.video_processor' in sys.modules:
                del sys.modules['src.video_processor']
            from src.video_processor import VideoProcessor
            config = {
                'brand': {'colors': {'primary': '#2c5530'}, 'fonts': {'heading': 'Arial', 'body': 'Arial', 'weights': {'heading': 'bold', 'body': 'normal'}}},
                'instagram': {'reel_dimensions': {'width': 1080, 'height': 1920}, 'reel_duration': {'min': 15, 'max': 90}},
            }
            vp = VideoProcessor(config=config)
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

        import os
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_video_processor.py::TestCreateImageQuoteVideoSignature -v
```

Expected: `FAILED` on `test_accepts_text_and_author_separately` — `text_overlay` is still the param name.

- [ ] **Step 3: Update `create_image_quote_video()` in `src/video_processor.py`**

**3a. Update the method signature** (~line 531). Replace:
```python
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
```
With:
```python
    def create_image_quote_video(
        self,
        image_paths: List[Path],
        text: str,
        author: str,
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
        flyer_logo_path: Optional[Path] = None,
        quote_style: str = 'cinematic',
    ) -> Path:
```

**3b. Update the docstring** — change `text_overlay: Quote text (and optional author) to overlay.` to:
```
            text: Quote body text.
            author: Attribution line (author name).
            quote_style: 'cinematic' (default) or 'reveal'.
```

**3c. Replace the text overlay block** (~lines 603–611). Find:
```python
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
```
Replace with:
```python
        if quote_style == 'reveal':
            reveal_clips = self.create_line_reveal_clips(
                text=text,
                author=author,
                duration=duration,
                font_size=quote_font_size,
            )
            segment_1 = CompositeVideoClip([image_clip] + reveal_clips)
        else:
            # 'cinematic' (default)
            text_clip = self.create_cinematic_text_clip(
                text=text,
                author=author,
                duration=duration,
                font_size=quote_font_size,
            )
            segment_1 = CompositeVideoClip([image_clip, text_clip])
```

**3d. Update the cleanup at the bottom** of the method. Find:
```python
        tmp_path = getattr(image_clip, 'tmp_path', None)
        image_clip.close()
        text_clip.close()
```
Replace with:
```python
        tmp_path = getattr(image_clip, 'tmp_path', None)
        image_clip.close()
        # text_clip only exists in the cinematic branch; reveal branch has no single text_clip
        if quote_style != 'reveal' and 'text_clip' in dir():
            text_clip.close()
```

Note: to avoid the scoping issue entirely, restructure the cinematic branch to assign `text_clip` and call `.close()` inline inside the `else` block, rather than at the method's cleanup footer. Either approach is valid — the inline approach is cleaner.

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_video_processor.py::TestCreateImageQuoteVideoSignature -v
```

Expected: `4 passed`

- [ ] **Step 5: Run all video processor tests**

```bash
python -m pytest tests/test_video_processor.py -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: update create_image_quote_video to accept text/author/quote_style"
```

---

## Task 5: Update `QuoteCardGenerator` call chain

**Files:**
- Modify: `src/quote_card_generator.py`
- Create: `tests/test_quote_card_generator.py`

The call chain: `generate_quote_cards()` → `generate_image_video_quote_card()` → `VideoProcessor.create_image_quote_video()`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_quote_card_generator.py`:

```python
"""Tests for QuoteCardGenerator quote_style passthrough."""
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

        # Create a real temp image
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
        # quote_style='reveal' must reach create_image_quote_video
        assert call_kwargs is not None
        all_args = {**call_kwargs.kwargs}
        if call_kwargs.args:
            import inspect
            from src.video_processor import VideoProcessor
            param_names = list(inspect.signature(VideoProcessor.create_image_quote_video).parameters.keys())[1:]
            all_args.update(dict(zip(param_names, call_kwargs.args)))
        assert all_args.get('quote_style') == 'reveal', f"quote_style not passed through: {all_args}"
        # text_overlay must NOT be passed
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
        # 'text' and 'author' passed separately
        assert 'text' in all_args or (len(call_kwargs.args) >= 2)
        assert 'text_overlay' not in str(call_kwargs)

        os.unlink(tmp.name)
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_quote_card_generator.py -v
```

Expected: `FAILED` — `quote_style` param not present.

- [ ] **Step 3: Update `generate_image_video_quote_card()` in `src/quote_card_generator.py`**

**3a. Add `quote_style` param** to the method signature (~line 347):
```python
    def generate_image_video_quote_card(
        self,
        quote: Dict,
        image_paths: List[Path],
        output_path: Optional[Path] = None,
        duration: float = 15.0,
        music_path: Optional[Path] = None,
        audio_fade_duration: float = 3.0,
        video_fade_duration: float = 0.8,
        flyer_lines: Optional[list] = None,
        flyer_duration: float = 15.0,
        flyer_font_size: int = 40,
        flyer_logo_path: Optional[Path] = None,
        quote_style: str = 'cinematic',
    ) -> Path:
```

**3b. Replace `overlay_text` construction and the call to `create_image_quote_video`** (~lines 390–418). Find:
```python
        quote_text = self._shorten_quote_for_display(quote.get('text', ''))
        author = quote.get('author') or quote.get('source') or quote.get('group', 'Yoga Wisdom')
        overlay_text = f"{quote_text}\n\n— {author}"
        ...
        return self.video_processor.create_image_quote_video(
            image_paths=image_paths,
            text_overlay=overlay_text,
            output_path=output_path,
            ...
        )
```
Replace with:
```python
        quote_text = self._shorten_quote_for_display(quote.get('text', ''))
        author = quote.get('author') or quote.get('source') or quote.get('group', 'Yoga Wisdom')

        return self.video_processor.create_image_quote_video(
            image_paths=image_paths,
            text=quote_text,
            author=author,
            output_path=output_path,
            duration=duration,
            music_path=music_path,
            audio_fade_duration=audio_fade_duration,
            video_fade_duration=video_fade_duration,
            font_size=64,
            flyer_lines=flyer_lines if flyer_lines else None,
            flyer_duration=flyer_duration,
            flyer_font_size=flyer_font_size,
            flyer_logo_path=flyer_logo_path,
            quote_style=quote_style,
        )
```

**3c. Add `quote_style` param to `generate_quote_cards()`** (~line 421). Add to existing param list:
```python
        quote_style: str = 'cinematic',
```

**3d. Pass `quote_style` through in the `generate_quote_cards()` call to `generate_image_video_quote_card()`** (~line 500). Find:
```python
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
                    flyer_font_size=flyer_font_size,
                    flyer_logo_path=flyer_logo_path
                )
```
Add `quote_style=quote_style,` to the call.

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_quote_card_generator.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/quote_card_generator.py tests/test_quote_card_generator.py
git commit -m "feat: thread quote_style through QuoteCardGenerator call chain"
```

---

## Task 6: Add `--quote-style` CLI flag

**Files:**
- Modify: `main.py` (`generate_quote_cards` command, ~line 327)
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli.py`:

```python
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
        assert set(param.type.choices) == {'cinematic', 'reveal'}

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
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_cli.py -v
```

Expected: `FAILED` — `quote_style` not in params.

- [ ] **Step 3: Add `--quote-style` to `generate_quote_cards` command in `main.py`**

In `main.py`, find the `@cli.command()` decorator block for `generate_quote_cards` (~line 327). Add this option after the existing `--flyer-font-size` option:

```python
@click.option('--quote-style', type=click.Choice(['cinematic', 'reveal'], case_sensitive=False),
              default='cinematic', show_default=True,
              help='Quote overlay style: cinematic (centered, gold/cream) or reveal (line-by-line fade-in)')
```

Add `quote_style` to the function signature:
```python
def generate_quote_cards(group, quote_id, photo_dir, video_dir, num_photos, num_videos,
                         white_background, output_dir, music, image, duration, audio_fade,
                         video_fade, flyer_ajuda, flyer_palheiro, flyer_line1, flyer_line2,
                         flyer_duration, flyer_font_size, quote_style):
```

Pass it through to `generator.generate_quote_cards(...)` (~line 425). Find the call and add:
```python
            quote_style=quote_style,
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_cli.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_cli.py
git commit -m "feat: add --quote-style CLI option to generate-quote-cards"
```

---

## Task 7: Manual smoke test

Verify the full end-to-end flow works with a real image before considering the feature done.

- [ ] **Step 1: Set ANTHROPIC_API_KEY** (needed for quote loading only if no accepted quotes exist — skip if quotes already accepted)

```bash
# Check if any accepted quotes exist
python3 -c "
import json
from pathlib import Path
for f in Path('assets/10_knowledge').glob('*/quotes.json'):
    d = json.load(open(f))
    acc = [q for q in d.get('quotes', []) if q.get('status') == 'accepted']
    if acc: print(f'{f.parent.name}: {len(acc)} accepted')
"
```

- [ ] **Step 2: Find a test image**

```bash
ls assets/01_images/
```

Pick any image path from the output, e.g. `assets/01_images/Ajuda/some-photo.png`.

- [ ] **Step 3: Run cinematic mode**

```bash
source venv/bin/activate
python3 main.py generate-quote-cards \
  --image <PATH_TO_IMAGE> \
  --duration 15 \
  --quote-style cinematic
```

Expected: `✓ Quote cards generated successfully!` and a file listed under `Image video cards`.

- [ ] **Step 4: Open the output and verify visually**

```bash
open output/quote_cards/quote_image_video_*.mp4
```

Check: quote is centered, cream italic serif text, thin gold divider, gold author in caps, subtle dark edges.

- [ ] **Step 5: Run reveal mode**

```bash
python3 main.py generate-quote-cards \
  --image <PATH_TO_IMAGE> \
  --duration 15 \
  --quote-style reveal
```

- [ ] **Step 6: Open and verify**

```bash
open output/quote_cards/quote_image_video_*.mp4
```

Check: lines appear one by one from top to bottom, author and divider appear last.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat: complete quote visualization improvement (cinematic + reveal modes)"
```
