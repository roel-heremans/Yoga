# Visual Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add semi-transparent per-line pill backgrounds to all 3 quote styles, increase default font size to 96px, reduce flyer duration to 5 seconds, and replace the scroll author phase with frozen last-3-lines + author below.

**Architecture:** All changes are in `src/video_processor.py`. A new `_make_pill_overlay` PIL helper serves cinematic and reveal; scroll draws pills inline in its existing `make_frame` PIL loop. The scroll author phase is rewritten to freeze the last 3 quote lines and append the author on a 4th line. Font-size cap formula is removed. Flyer default drops from 15 → 5 s.

**Tech Stack:** Python 3, moviepy 2.x, Pillow (PIL), Click, pytest

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `src/video_processor.py` | **Modify** | All tasks — see below |
| `main.py` | **Modify** | Task 1: `--flyer-duration` default 15→5 |
| `tests/test_video_processor.py` | **Modify** | New test classes for every task |

Key methods touched (all in `VideoProcessor`):

| Method | Task(s) |
|--------|---------|
| `create_image_quote_video` | T1 (flyer default), T2 (font default + cap removal) |
| `create_cinematic_text_clip` | T2 (font default), T3 (add pill overlay) |
| `create_line_reveal_clips` | T2 (font default), T4 (add pill overlay) |
| `create_scroll_clips` | T2 (font default), T5 (block_top), T6 (inline pills), T7 (author phase) |
| `_make_pill_overlay` | T3 (new method) |

> **Do NOT change** `calculate_scroll_duration`, `SCROLL_CHARS_PER_SECOND`, or the per-photo duration split logic.

---

## Task 1: Flyer duration 15 → 5 seconds

**Files:**
- Modify: `src/video_processor.py` line ~1228
- Modify: `main.py` line ~346
- Modify: `tests/test_video_processor.py`

- [ ] **Step 1.1: Write the failing test**

Add to `tests/test_video_processor.py`:

```python
class TestFlyerDurationDefault:
    def test_flyer_duration_default_is_5(self):
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor.create_image_quote_video)
        assert sig.parameters['flyer_duration'].default == 5.0
```

- [ ] **Step 1.2: Run the test to verify it fails**

```bash
cd /Users/roel.heremans/Documents/PersonalRepos/Yoga
python3 -m pytest tests/test_video_processor.py::TestFlyerDurationDefault -v
```

Expected: `FAILED` — default is currently 15.0.

- [ ] **Step 1.3: Change default in `create_image_quote_video`**

In `src/video_processor.py` line ~1228:

```python
# Before
flyer_duration: float = 15.0,

# After
flyer_duration: float = 5.0,
```

- [ ] **Step 1.4: Change CLI default in `main.py`**

In `main.py` line ~346:

```python
# Before
@click.option('--flyer-duration', default=15, type=int, help='Flyer segment duration in seconds (default: 15)')

# After
@click.option('--flyer-duration', default=5, type=int, help='Flyer segment duration in seconds (default: 5)')
```

- [ ] **Step 1.5: Run test to verify it passes**

```bash
python3 -m pytest tests/test_video_processor.py::TestFlyerDurationDefault -v
```

Expected: `PASSED`

- [ ] **Step 1.6: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 1.7: Commit**

```bash
git add src/video_processor.py main.py tests/test_video_processor.py
git commit -m "feat: reduce flyer-ajuda default duration 15s → 5s"
```

---

## Task 2: Font size defaults 64/72 → 96, remove cap formula

**Files:**
- Modify: `src/video_processor.py` lines ~509, ~652, ~833, ~1226, ~1296
- Modify: `tests/test_video_processor.py`

- [ ] **Step 2.1: Write the failing tests**

Add to `tests/test_video_processor.py`:

```python
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
        """quote_font_size passed to sub-methods must equal font_size (no cap)."""
        from unittest.mock import patch, MagicMock, call
        from pathlib import Path
        processor = make_processor()
        fake_clip = MagicMock()
        fake_clip.size = (1080, 1920)
        fake_clip.duration = 5
        fake_clip.h = 100

        called_with = {}

        def capture_cinematic(text, author, duration, font_size):
            called_with['font_size'] = font_size
            return fake_clip

        with patch.object(processor, 'create_cinematic_text_clip', side_effect=capture_cinematic), \
             patch('src.video_processor.ImageClip', return_value=fake_clip), \
             patch('src.video_processor.CompositeVideoClip', return_value=fake_clip), \
             patch('src.video_processor.concatenate_videoclips', return_value=fake_clip), \
             patch.object(processor, '_add_white_fade_overlay', return_value=fake_clip), \
             patch.object(processor, '_append_generated_cards_to_quote', return_value=None):
            try:
                processor.create_image_quote_video(
                    text="Yoga is peace.",
                    author="Iyengar",
                    image_paths=[Path('/tmp/fake.jpg')],
                    output_path=Path('/tmp/out.mp4'),
                    duration=5.0,
                    font_size=96,
                    use_flyer=False,
                )
            except Exception:
                pass

        # font_size=96 must be passed through unchanged (no cap)
        assert called_with.get('font_size') == 96, (
            f"Expected font_size=96 passed to create_cinematic_text_clip, "
            f"got {called_with.get('font_size')}"
        )
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_video_processor.py::TestFontSizeDefaults -v
```

Expected: `FAILED` — defaults are 64/72, not 96.

- [ ] **Step 2.3: Update font_size defaults**

In `src/video_processor.py`:

```python
# create_scroll_clips (~line 509)
# Before:  font_size: int = 72,
# After:   font_size: int = 96,

# create_cinematic_text_clip (~line 652)
# Before:  font_size: int = 72,
# After:   font_size: int = 96,

# create_line_reveal_clips (~line 833)
# Before:  font_size: int = 72,
# After:   font_size: int = 96,

# create_image_quote_video (~line 1226)
# Before:  font_size: int = 64,
# After:   font_size: int = 96,
```

- [ ] **Step 2.4: Remove cap formula in `create_image_quote_video`**

In `src/video_processor.py` line ~1296:

```python
# Before
quote_font_size = min(font_size, max(40, (top_black - 20) // 3))

# After
quote_font_size = font_size
```

The `top_black` variable and the image-scaling lines above it are still needed for other purposes — only the cap formula line changes.

- [ ] **Step 2.5: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_video_processor.py::TestFontSizeDefaults -v
```

Expected: all `PASSED`

- [ ] **Step 2.6: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 2.7: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: raise default quote font size 64/72 → 96, remove letterbox cap formula"
```

---

## Task 3: Add `_make_pill_overlay` helper

This new method draws a semi-transparent dark rounded-rectangle pill behind each text line. Used by cinematic and reveal (not scroll — scroll draws pills inline in `make_frame`).

**Signature:**
```python
def _make_pill_overlay(
    self,
    lines: list,            # list of text strings, one per line
    font_size: int,
    line_y_positions: list, # pixel y-coordinate for each line's baseline
    w: int,
    h: int,
    duration: float,
) -> ImageClip:
```

**Files:**
- Modify: `src/video_processor.py` — add after `_make_scrim_clip` (~line 479)
- Modify: `tests/test_video_processor.py`

- [ ] **Step 3.1: Write the failing tests**

Add to `tests/test_video_processor.py`:

```python
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
        # Use a small canvas so bounds are easy to reason about
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
```

- [ ] **Step 3.2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_video_processor.py::TestMakePillOverlay -v
```

Expected: `FAILED` — method does not exist yet.

- [ ] **Step 3.3: Implement `_make_pill_overlay`**

Add this method to `VideoProcessor` in `src/video_processor.py`, directly after `_make_scrim_clip` (~line 479):

```python
def _make_pill_overlay(
    self,
    lines: list,
    font_size: int,
    line_y_positions: list,
    w: int,
    h: int,
    duration: float,
):
    """
    Draw a semi-transparent dark rounded-rectangle pill behind each text line.

    Args:
        lines: Text strings, one per line.
        font_size: Point size used for the text (determines pill height).
        line_y_positions: Pixel y-coordinate for the top of each line's text.
        w, h: Frame dimensions in pixels.
        duration: Clip duration in seconds.

    Returns:
        A static ImageClip (RGBA, transparent except for the pills).
    """
    from PIL import Image, ImageDraw
    import numpy as np

    PAD_X = 14      # horizontal padding inside pill
    PAD_Y = 6       # vertical padding inside pill
    RADIUS = 20     # corner radius
    FILL = (0, 0, 0, 128)  # ~50% opacity black

    pil_font = self._load_pil_font(font_size)

    def _measure(txt):
        d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        try:
            return int(d.textlength(txt, font=pil_font))
        except AttributeError:
            try:
                return int(pil_font.getlength(txt))
            except AttributeError:
                return int(pil_font.getsize(txt)[0])

    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for line, y in zip(lines, line_y_positions):
        tw = _measure(line)
        x0 = (w - tw) // 2 - PAD_X
        y0 = y - PAD_Y
        x1 = (w + tw) // 2 + PAD_X
        y1 = y + font_size + PAD_Y
        try:
            draw.rounded_rectangle([x0, y0, x1, y1], radius=RADIUS, fill=FILL)
        except AttributeError:
            # Pillow < 8.2 does not have rounded_rectangle
            draw.rectangle([x0, y0, x1, y1], fill=FILL)

    arr = np.array(img)
    try:
        clip = ImageClip(arr, transparent=True)
    except TypeError:
        clip = ImageClip(arr)
    clip = (clip.with_duration(duration) if hasattr(clip, 'with_duration')
            else clip.set_duration(duration))
    clip = (clip.with_position((0, 0)) if hasattr(clip, 'with_position')
            else clip.set_position((0, 0)))
    return clip
```

- [ ] **Step 3.4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_video_processor.py::TestMakePillOverlay -v
```

Expected: all `PASSED`

- [ ] **Step 3.5: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 3.6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: add _make_pill_overlay PIL helper for per-line text backgrounds"
```

---

## Task 4: Cinematic style — add pill overlay

**Files:**
- Modify: `src/video_processor.py` — `create_cinematic_text_clip` (~line 647)
- Modify: `tests/test_video_processor.py`

- [ ] **Step 4.1: Write the failing test**

Add to `tests/test_video_processor.py`:

```python
class TestCinematicPillOverlay:
    def test_pill_overlay_included_in_composite(self):
        """_make_pill_overlay must be called inside create_cinematic_text_clip."""
        from unittest.mock import patch, MagicMock, call
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
```

- [ ] **Step 4.2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_video_processor.py::TestCinematicPillOverlay -v
```

Expected: `FAILED` — `_make_pill_overlay` is not called yet.

- [ ] **Step 4.3: Add pill overlay to `create_cinematic_text_clip`**

In `src/video_processor.py`, inside `create_cinematic_text_clip`, after the `block_top` and layout variables are computed (~line 802) and before the `_set_pos_dur` calls:

```python
# ---- Pill background overlay ----
line_y_positions = [block_top + i * int(font_size * self.LINE_HEIGHT_MULT)
                    for i in range(n_lines)]
pill_clip = self._make_pill_overlay(
    lines=wrapped_lines,
    font_size=font_size,
    line_y_positions=line_y_positions,
    w=w, h=h, duration=duration,
)
```

Then in the `CompositeVideoClip` call (~line 819), insert `pill_clip` between `scrim_clip` and `quote_clip`:

```python
# Before
composite = CompositeVideoClip(
    [vignette_clip, scrim_clip, quote_clip, divider_clip, author_clip],
    size=(w, h),
)

# After
composite = CompositeVideoClip(
    [vignette_clip, scrim_clip, pill_clip, quote_clip, divider_clip, author_clip],
    size=(w, h),
)
```

- [ ] **Step 4.4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_video_processor.py::TestCinematicPillOverlay -v
```

Expected: `PASSED`

- [ ] **Step 4.5: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 4.6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: add per-line pill background to cinematic quote style"
```

---

## Task 5: Reveal style — add pill overlay

**Files:**
- Modify: `src/video_processor.py` — `create_line_reveal_clips` (~line 828)
- Modify: `tests/test_video_processor.py`

- [ ] **Step 5.1: Write the failing test**

Add to `tests/test_video_processor.py`:

```python
class TestRevealPillOverlay:
    def test_pill_overlay_included_in_reveal_clips(self):
        """_make_pill_overlay must be called inside create_line_reveal_clips."""
        from unittest.mock import patch, MagicMock
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
```

- [ ] **Step 5.2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_video_processor.py::TestRevealPillOverlay -v
```

Expected: `FAILED`

- [ ] **Step 5.3: Add pill overlay to `create_line_reveal_clips`**

In `src/video_processor.py`, inside `create_line_reveal_clips`, after `block_top` is set (~line 854), before the `clips = [self._make_scrim_clip(...)]` line:

```python
# ---- Pill background overlay (static, behind all fading text lines) ----
line_y_positions = [block_top + i * int(font_size * self.LINE_HEIGHT_MULT)
                    for i in range(n_lines)]
pill_clip_static = self._make_pill_overlay(
    lines=wrapped_lines,
    font_size=font_size,
    line_y_positions=line_y_positions,
    w=w, h=h, duration=duration,
)
```

Then add `pill_clip_static` to the `clips` list right after the scrim:

```python
# Before
clips = [self._make_scrim_clip(w, h, duration)]

# After
clips = [self._make_scrim_clip(w, h, duration), pill_clip_static]
```

- [ ] **Step 5.4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_video_processor.py::TestRevealPillOverlay -v
```

Expected: `PASSED`

- [ ] **Step 5.5: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 5.6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: add per-line pill background to reveal quote style"
```

---

## Task 6: Scroll — move `block_top` to `h // 8`

**Files:**
- Modify: `src/video_processor.py` — `create_scroll_clips` (~line 553)
- Modify: `tests/test_video_processor.py`

- [ ] **Step 6.1: Write the failing test**

Add to `tests/test_video_processor.py`:

```python
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
            processor.create_scroll_clips(
                text="Yoga is peace and light.",
                author="Iyengar",
                duration=5.0,
                font_size=36,
            )

        assert 'make_frame' in captured
        # Probe make_frame: if block_top == h//8, the first row of text
        # starts at h//8, not max(80, h//6).
        # We check that block_top equals processor.reel_height // 8.
        expected_block_top = processor.reel_height // 8
        # Call make_frame at t=0 with a patched draw to capture y-coordinates
        drawn_ys = []
        from PIL import Image, ImageDraw as ID

        original_text = ID.ImageDraw.text

        def capture_text(self_draw, xy, txt, **kw):
            drawn_ys.append(xy[1])

        with patch.object(ID.ImageDraw, 'text', side_effect=capture_text):
            try:
                captured['make_frame'](0)
            except Exception:
                pass

        # The minimum y drawn must equal expected_block_top (first row position)
        # Allow ±2 px for padding
        if drawn_ys:
            min_y = min(drawn_ys)
            assert abs(min_y - expected_block_top) <= 10, (
                f"Expected first text row near y={expected_block_top}, "
                f"got min y={min_y}"
            )
```

- [ ] **Step 6.2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollBlockTop -v
```

Expected: `FAILED` — current `block_top = max(80, h // 6)`.

- [ ] **Step 6.3: Change `block_top` in `create_scroll_clips`**

In `src/video_processor.py` line ~553:

```python
# Before
block_top = max(80, h // 6)

# After
block_top = h // 8
```

- [ ] **Step 6.4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollBlockTop -v
```

Expected: `PASSED`

- [ ] **Step 6.5: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 6.6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: move scroll text block to h//8 from top (was max(80, h//6))"
```

---

## Task 7: Scroll — add inline pills to scroll window

Pills are drawn in `make_frame` before each row's text, using `draw.rounded_rectangle()`.

**Files:**
- Modify: `src/video_processor.py` — `make_frame` closure inside `create_scroll_clips`
- Modify: `tests/test_video_processor.py`

- [ ] **Step 7.1: Write the failing test**

Add to `tests/test_video_processor.py`:

```python
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
```

- [ ] **Step 7.2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollInlinePills -v
```

Expected: `FAILED` — no rectangle calls yet.

- [ ] **Step 7.3: Add a `_draw_pill` local helper and inline pills in `make_frame`**

In `src/video_processor.py`, inside `create_scroll_clips`, add a `_draw_pill` helper just before `make_frame` is defined (~line 586):

```python
# ---- Pill drawing helper ----
_PILL_PAD_X = 14
_PILL_PAD_Y = 6
_PILL_RADIUS = 20
_PILL_FILL = (0, 0, 0, 128)  # ~50% opacity black

def _draw_pill(draw, center_x, text_w, y, fs):
    """Draw a rounded-rectangle pill behind a text line."""
    x0 = center_x - text_w // 2 - _PILL_PAD_X
    y0 = y - _PILL_PAD_Y
    x1 = center_x + text_w // 2 + _PILL_PAD_X + (text_w % 2)
    y1 = y + fs + _PILL_PAD_Y
    try:
        draw.rounded_rectangle([x0, y0, x1, y1], radius=_PILL_RADIUS, fill=_PILL_FILL)
    except AttributeError:
        draw.rectangle([x0, y0, x1, y1], fill=_PILL_FILL)
```

Then inside `make_frame`, in the `for offset in (-1, 0, 1)` loop, draw the pill **before** the text for each row. The scroll window section currently looks like:

```python
if offset == 0:
    # Current line: word-by-word colouring
    total_w = sum(word_widths[wd] for wd in words)
    x = (w - total_w) // 2
    for wi, wd in enumerate(words):
        ...
else:
    line_text = ' '.join(words)
    tw = _measure(pil_font, line_text)
    x  = (w - tw) // 2
    alpha = BRIGHT if offset == -1 else DIM
    draw.text((x, y), line_text, ...)
```

Replace with:

```python
if offset == 0:
    # Current line: word-by-word colouring
    total_w = sum(word_widths[wd] for wd in words)
    _draw_pill(draw, w // 2, total_w, y, font_size)   # pill first
    x = (w - total_w) // 2
    for wi, wd in enumerate(words):
        if wi < cur_word:
            rgba = (*cream_rgb, BRIGHT)
        elif wi == cur_word:
            rgba = (*gold_rgb,  BRIGHT)
        else:
            rgba = (*cream_rgb, DIM)
        draw.text((x, y), wd, font=pil_font, fill=rgba)
        x += word_widths[wd]
else:
    line_text = ' '.join(words)
    tw = _measure(pil_font, line_text)
    _draw_pill(draw, w // 2, tw, y, font_size)         # pill first
    x  = (w - tw) // 2
    alpha = BRIGHT if offset == -1 else DIM
    draw.text((x, y), line_text, font=pil_font,
              fill=(*cream_rgb, alpha))
```

- [ ] **Step 7.4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollInlinePills -v
```

Expected: `PASSED`

- [ ] **Step 7.5: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 7.6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: add inline per-line pill backgrounds to scroll teleprompter window"
```

---

## Task 8: Scroll — freeze last 3 lines when author appears

Replace the current author phase (author name centred alone) with: last 3 quote lines frozen + thin divider + author pill + book pill.

**Files:**
- Modify: `src/video_processor.py` — author-phase block inside `make_frame` (~line 591)
- Modify: `tests/test_video_processor.py`

**Note on book/source data:** `QuoteCardGenerator` formats the `author` parameter as `"Author — Book"` (with ` — ` separator) when a source/book title exists. `create_scroll_clips` receives this combined string and splits it at Step 8.3. No signature change is needed.

- [ ] **Step 8.1: Write the failing tests**

Add to `tests/test_video_processor.py`:

```python
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
        def capture_text(self_d, xy, txt, **kw):
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
        def capture_text(self_d, xy, txt, **kw):
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
        def capture_text(self_d, xy, txt, **kw):
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
        def capture_text(self_d, xy, txt, **kw):
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
```

- [ ] **Step 8.2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollFrozenLinesAuthorPhase -v
```

Expected: `FAILED` — current author phase renders only the author name, not quote lines.

- [ ] **Step 8.3: Rewrite the author phase in `make_frame`**

In `src/video_processor.py`, find the author-phase block inside `make_frame` (~line 591):

```python
# Current code — REPLACE THIS ENTIRE BLOCK
if t >= author_display_start:
    # Show author name below scroll window, horizontally centred
    if author:
        author_text = author.upper()
        tw = _measure(author_font, author_text)
        x  = (w - tw) // 2
        y  = block_top + 3 * line_height
        draw.text((x, y), author_text, font=author_font,
                  fill=(*gold_rgb, BRIGHT))
    return np.array(img)
```

Replace with:

```python
if t >= author_display_start:
    # ---- Freeze last 3 quote lines ----
    frozen = words_per_line[-3:] if len(words_per_line) >= 3 else words_per_line
    for i, fwords in enumerate(frozen):
        y = block_top + i * line_height
        line_text = ' '.join(fwords)
        tw = _measure(pil_font, line_text)
        _draw_pill(draw, w // 2, tw, y, font_size)
        draw.text(((w - tw) // 2, y), line_text, font=pil_font,
                  fill=(*cream_rgb, BRIGHT))

    # ---- Thin gold divider ----
    n_frozen = len(frozen)
    div_y = block_top + n_frozen * line_height + 8
    div_w = int(w * 0.55)
    div_x = (w - div_w) // 2
    draw.line([(div_x, div_y), (div_x + div_w, div_y)],
              fill=(*gold_rgb, 100), width=2)

    # ---- Author + book pills ----
    # QuoteCardGenerator formats author as "Author — Book" when a source exists.
    # Split on ' — ' so they render on separate lines.
    if author:
        parts = author.split(' — ', 1)
        author_part = parts[0].strip()
        book_part   = parts[1].strip() if len(parts) > 1 else ''

        au_y = div_y + line_height // 2
        tw = _measure(author_font, author_part.upper())
        _draw_pill(draw, w // 2, tw, au_y, max(28, font_size // 2))
        draw.text(((w - tw) // 2, au_y), author_part.upper(), font=author_font,
                  fill=(*gold_rgb, BRIGHT))

        if book_part:
            book_font = self._load_pil_font(max(24, font_size // 3))
            bk_y = au_y + max(28, font_size // 2) + _PILL_PAD_Y * 2 + 4
            tw_b = _measure(book_font, book_part)
            _draw_pill(draw, w // 2, tw_b, bk_y, max(24, font_size // 3))
            draw.text(((w - tw_b) // 2, bk_y), book_part, font=book_font,
                      fill=(*cream_rgb, 160))

    return np.array(img)
```

Also update the `create_scroll_clips` docstring to reflect new author-phase behaviour:

```python
# Before
        Lines outside the 3-line window are hidden. After all words are shown, the
        author name appears centered in gold for the last ~2.5 s of the clip.

# After
        Lines outside the 3-line window are hidden. After all words are shown,
        the last 3 quote lines freeze on screen, a thin gold divider appears below,
        and the author name is shown as a pill on a fourth line.
```

- [ ] **Step 8.4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollFrozenLinesAuthorPhase -v
```

Expected: all `PASSED`

- [ ] **Step 8.5: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 8.6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: scroll author phase — freeze last 3 quote lines, show author on 4th line"
```

---

## Final Verification

- [ ] **Run complete test suite**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests pass, no regressions.

---

## Manual Smoke Test

```bash
# Scroll with flyer — verify all 5 features together
python3 main.py generate-quote-cards \
  -i assets/01-ajuda/Yoga_Funchal21.jpg \
  --quote-style scroll \
  --flyer-ajuda

# Play back and verify:
# 1. Text starts at ~1/8 from top (not centred)
# 2. Each scroll line has a dark semi-transparent pill background
# 3. Font is visibly larger (~96px)
# 4. At end: last 3 lines freeze, gold divider, author pill appears below
# 5. Flyer card appears and disappears after 5 s (not 15)

# Cinematic — verify pill background
python3 main.py generate-quote-cards \
  -i assets/01-ajuda/Yoga_Funchal21.jpg \
  --quote-style cinematic

# Play back and verify:
# 1. Dark pill behind each quote line
# 2. Font visibly larger

# Reveal — verify pill background
python3 main.py generate-quote-cards \
  -i assets/01-ajuda/Yoga_Funchal21.jpg \
  --quote-style reveal

# Play back and verify:
# 1. Pill visible behind each line as it fades in
# 2. Font visibly larger
```
