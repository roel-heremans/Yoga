# Scroll Style Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two bugs in the `scroll` quote style: (1) long quotes are silently truncated at 120 chars before reaching the video; (2) the author name appears at screen centre instead of below the 3-line scroll window.

**Architecture:** Change 1 adds a one-line conditional guard in `generate_image_video_quote_card` (`src/quote_card_generator.py`) so that `_shorten_quote_for_display` is skipped when `quote_style == 'scroll'`. Change 2 replaces a single literal `y = h // 2` with `y = block_top + 3 * line_height` inside the `make_frame` closure in `create_scroll_clips` (`src/video_processor.py`). Both variables are already in closure scope — no structural changes needed.

**Tech Stack:** Python 3, moviepy 2.x, Pillow (PIL), Click, pytest

**Spec:** `docs/superpowers/specs/2026-03-21-scroll-fixes-design.md`

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `src/quote_card_generator.py` | **Modify** | Line 412: conditional guard bypasses `_shorten_quote_for_display` for scroll style |
| `src/video_processor.py` | **Modify** | Line 578: `y = h // 2` → `y = block_top + 3 * line_height` |
| `tests/test_quote_card_generator.py` | **Modify** | New test class for truncation bypass behaviour |
| `tests/test_video_processor.py` | **Modify** | New test for author y-position in scroll style |

---

## Task 1: Bypass quote truncation for scroll style

**Files:**
- Modify: `src/quote_card_generator.py:412`
- Modify: `tests/test_quote_card_generator.py`

---

- [ ] **Step 1.1: Write the failing tests**

Add this class to `tests/test_quote_card_generator.py`. The long text (~170 chars) exceeds the 120-char limit to make the truncation visible. Follow the existing mock-and-inspect-call-args pattern (see `test_quote_style_passed_to_video_processor` in the same file).

```python
class TestScrollTruncationBypass:
    LONG_QUOTE = (
        "A scientist sets out to conquer nature through knowledge—external nature, "
        "external knowledge. By these means he may split the atom and achieve external "
        "power. A yogi sets out to explore his own internal nature."
    )  # 174 chars — well over the 120-char limit

    def test_scroll_receives_full_text(self):
        """scroll style must bypass max_display_length and pass the full quote text."""
        from unittest.mock import MagicMock, patch
        from pathlib import Path
        from src.quote_card_generator import QuoteCardGenerator

        gen = make_generator()
        mock_result = {'image_videos': [Path('/tmp/out.mp4')], 'flyer_videos': []}
        gen.video_processor.create_image_quote_video = MagicMock(return_value=mock_result)

        with patch.object(gen, '_append_generated_cards_to_quote', return_value=None):
            gen.generate_image_video_quote_card(
                quote={'text': self.LONG_QUOTE, 'author': 'B.K.S. Iyengar', 'id': 'q1', 'group': 'TestGroup'},
                image_paths=[Path('/tmp/fake.jpg')],
                output_path=Path('/tmp/out.mp4'),
                quote_style='scroll',
            )

        call_kwargs = gen.video_processor.create_image_quote_video.call_args
        assert call_kwargs is not None
        all_args = {**call_kwargs.kwargs}
        if call_kwargs.args:
            import inspect
            from src.video_processor import VideoProcessor
            param_names = list(inspect.signature(VideoProcessor.create_image_quote_video).parameters.keys())[1:]
            all_args.update(dict(zip(param_names, call_kwargs.args)))
        assert all_args.get('text') == self.LONG_QUOTE, (
            f"scroll style should pass full text, got: {all_args.get('text')!r}"
        )

    def test_cinematic_still_truncates(self):
        """cinematic style must still truncate via _shorten_quote_for_display (regression guard)."""
        from unittest.mock import MagicMock, patch
        from pathlib import Path
        from src.utils import shorten_quote_for_display

        gen = make_generator()
        mock_result = {'image_videos': [Path('/tmp/out.mp4')], 'flyer_videos': []}
        gen.video_processor.create_image_quote_video = MagicMock(return_value=mock_result)

        with patch.object(gen, '_append_generated_cards_to_quote', return_value=None):
            gen.generate_image_video_quote_card(
                quote={'text': self.LONG_QUOTE, 'author': 'B.K.S. Iyengar', 'id': 'q1', 'group': 'TestGroup'},
                image_paths=[Path('/tmp/fake.jpg')],
                output_path=Path('/tmp/out.mp4'),
                quote_style='cinematic',
            )

        call_kwargs = gen.video_processor.create_image_quote_video.call_args
        assert call_kwargs is not None
        all_args = {**call_kwargs.kwargs}
        if call_kwargs.args:
            import inspect
            from src.video_processor import VideoProcessor
            param_names = list(inspect.signature(VideoProcessor.create_image_quote_video).parameters.keys())[1:]
            all_args.update(dict(zip(param_names, call_kwargs.args)))
        expected = shorten_quote_for_display(self.LONG_QUOTE, 120)
        assert all_args.get('text') == expected, (
            f"cinematic style should truncate via shorten_quote_for_display, got: {all_args.get('text')!r}"
        )
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
cd /Users/roel.heremans/Documents/PersonalRepos/Yoga
python3 -m pytest tests/test_quote_card_generator.py::TestScrollTruncationBypass -v
```

Expected: both `FAILED` — scroll currently truncates the same as cinematic.

- [ ] **Step 1.3: Implement the fix**

In `src/quote_card_generator.py`, find line 412:

```python
# Before (line 412)
quote_text = self._shorten_quote_for_display(quote.get('text', ''))
```

Replace with:

```python
# After
raw_text = quote.get('text', '')
quote_text = raw_text if quote_style == 'scroll' else self._shorten_quote_for_display(raw_text)
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_quote_card_generator.py::TestScrollTruncationBypass -v
```

Expected: both `PASSED`.

- [ ] **Step 1.5: Run full test suite to check no regressions**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 1.6: Commit**

```bash
git add src/quote_card_generator.py tests/test_quote_card_generator.py
git commit -m "fix: bypass quote truncation for scroll style — pass full text to VideoProcessor"
```

---

## Task 2: Fix author y-position in scroll style

**Files:**
- Modify: `src/video_processor.py:578`
- Modify: `tests/test_video_processor.py`

---

- [ ] **Step 2.1: Write the failing test**

Add this class to `tests/test_video_processor.py`. The test invokes the `make_frame` closure at the author display time and patches `PIL.ImageDraw.Draw.text` to capture the `xy` argument actually passed.

```python
class TestScrollAuthorPosition:
    def test_author_rendered_below_scroll_window_not_at_center(self):
        """
        Author text must be drawn at y = block_top + 3*line_height (line 4),
        not at y = h // 2 (screen centre).
        """
        from unittest.mock import patch, MagicMock, call
        import numpy as np

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

        drawn_calls = []

        with patch('src.video_processor.VideoClip', side_effect=fake_video_clip):
            processor.create_scroll_clips(
                text="Yoga is the mirror to look at ourselves from within.",
                author="B.K.S. Iyengar",
                duration=5.0,
                font_size=font_size,
            )

        assert 'fn' in captured_make_frame, "VideoClip was not called — make_frame not captured"
        make_frame = captured_make_frame['fn']

        # author_display_start = duration - min(2.5, duration * 0.15) = 5.0 - 0.75 = 4.25
        author_t = 4.5  # safely past author_display_start

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
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollAuthorPosition -v
```

Expected: `FAILED` — author y is currently `h // 2`, not `block_top + 3 * line_height`.

- [ ] **Step 2.3: Implement the fix**

In `src/video_processor.py`, inside `create_scroll_clips`, find the `make_frame` closure (around line 571). Locate line 578:

```python
# Before (line 578)
y  = h // 2
```

Replace with:

```python
# After
y  = block_top + 3 * line_height
```

`block_top` (line 533) and `line_height` (line 532) are already computed in the enclosing method scope and are available to `make_frame` as closed-over variables — no other changes needed.

- [ ] **Step 2.4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollAuthorPosition -v
```

Expected: `PASSED`.

- [ ] **Step 2.5: Run full test suite to check no regressions**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 2.6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "fix: position scroll author at line 4 below scroll window, not screen centre"
```

---

## Final Check

- [ ] **Run the full test suite one last time**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests pass.

---

## Manual Smoke Test (optional)

```bash
python3 main.py generate-quote-cards \
  -i assets/01-ajuda/Yoga_Funchal21.jpg \
  --duration 25 \
  --quote-style scroll

# Play the output and verify:
# 1. The full Iyengar quote (both sentences) scrolls through — not truncated after first sentence
# 2. The author name appears in the top third at the end, directly below the last scroll line — not centred on screen
```
