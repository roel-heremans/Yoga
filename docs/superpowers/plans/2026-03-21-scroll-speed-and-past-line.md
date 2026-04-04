# Scroll Style: Fixed Reading Speed + Bright Past Line

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two improvements to the `scroll` teleprompter style: (1) the past line (top row) renders at full brightness instead of dimmed; (2) scroll speed is a fixed number of characters per second so video duration is derived from text length, not from a user-supplied `--duration` value.

**Architecture:** Both changes are self-contained in `create_scroll_clips` and `create_image_quote_video` in `src/video_processor.py`. Task 1 changes one constant in the `make_frame` closure. Task 2 adds two class-level constants, a `calculate_scroll_duration` helper, and overrides `duration` inside `create_image_quote_video` before images are built — so all downstream code (image clips, scroll overlay, fade) automatically uses the computed duration. No CLI changes needed; `--duration` continues to work for cinematic/reveal but is silently ignored for scroll.

**Tech Stack:** Python 3, moviepy 2.x, Pillow (PIL), pytest

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `src/video_processor.py` | **Modify** | Task 1: `make_frame` closure — past-line opacity; Task 2: add `SCROLL_CHARS_PER_SECOND`, `SCROLL_AUTHOR_DISPLAY_SECONDS` constants + `calculate_scroll_duration` method + duration override in `create_image_quote_video` + updated timing in `create_scroll_clips` |
| `tests/test_video_processor.py` | **Modify** | New test classes for each task |

---

## Background: current scroll timing (understand before editing)

In `create_scroll_clips` (line 525–529):

```python
# Reserve the last ~2.5 s (or 15% of duration) for the author name.
author_display_start = duration - min(2.5, duration * 0.15)
# Each word gets equal time; floor at 0.3 s to avoid imperceptibly fast flashes.
word_dt = max(0.3, author_display_start / n_words)
```

`duration` is passed in from `create_image_quote_video` which takes it from the CLI `--duration` flag. This means scrolling speed changes with `--duration` and the number of images — neither is desirable.

In `create_image_quote_video` (line 1248–1255), the image clips are built **before** the style dispatch:

```python
n = len(image_paths)
segment_duration = duration / n
if n == 1:
    image_clip = self.image_to_clip(image_paths[0], duration=duration)
else:
    clips = [self.image_to_clip(p, duration=segment_duration) for p in image_paths]
    image_clip = concatenate_videoclips(clips, method='compose')
```

So to override the duration for scroll, we must do it **before** these lines.

---

## Task 1: Past line renders at full brightness

In `make_frame`, the `else` branch handles both past (offset == -1) and future (offset == +1) rows identically — both dimmed. The user wants the past line (already read) to display at full brightness so the 3-line window reads: bright-past / gold-active / dim-future.

**Files:**
- Modify: `src/video_processor.py` — `make_frame` closure inside `create_scroll_clips` (~line 607–613)
- Modify: `tests/test_video_processor.py`

---

- [ ] **Step 1.1: Write the failing test**

Add to `tests/test_video_processor.py`:

```python
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
            # text = 84 chars, duration=15.0 (current pre-Task-2 formula):
            # author_display_start = 15.0 - min(2.5, 15*0.15) = 15.0 - 2.25 = 12.75 s
            # word_dt = 12.75 / 17 words ≈ 0.75 s
            # line 0 has 9 words → line 0 is "past" once t ≥ 9*0.75 = 6.75 s
            # At t=8.0: word_idx = int(8.0/0.75) = 10 → on line 1, so line 0 is "past".
            make_frame(8.0)

        # Find lines drawn at past-row y (block_top + 0 * line_height = block_top)
        past_y = block_top  # offset=-1 → y = block_top + (−1+1)*line_height = block_top
        past_calls = [d for d in drawn_texts if d['xy'][1] == past_y]

        assert past_calls, (
            f"No past-line text drawn at y={past_y}. "
            "Ensure t=5.0 is past line 0 but before author_display_start."
        )
        for call in past_calls:
            fill = call['fill']
            assert fill[3] == 255, (
                f"Past line alpha={fill[3]}, expected 255 (BRIGHT). "
                f"Past line should be fully visible, not dimmed."
            )
```

- [ ] **Step 1.2: Run the test to verify it fails**

```bash
cd /Users/roel.heremans/Documents/PersonalRepos/Yoga
python3 -m pytest tests/test_video_processor.py::TestScrollPastLineBrightness -v
```

Expected: `FAILED` — past line alpha is currently 80 (DIM), not 255 (BRIGHT).

- [ ] **Step 1.3: Implement the fix**

In `src/video_processor.py`, inside `create_scroll_clips`, find the `else` branch of the `for offset in (-1, 0, 1)` loop (~line 607–613):

```python
# Before
                else:
                    # Past or future: render the full line dimmed
                    line_text = ' '.join(words)
                    tw = _measure(pil_font, line_text)
                    x  = (w - tw) // 2
                    draw.text((x, y), line_text, font=pil_font,
                              fill=(*cream_rgb, DIM))
```

Replace with:

```python
                else:
                    # Past line: bright (already read). Future line: dim (not yet reached).
                    line_text = ' '.join(words)
                    tw = _measure(pil_font, line_text)
                    x  = (w - tw) // 2
                    alpha = BRIGHT if offset == -1 else DIM
                    draw.text((x, y), line_text, font=pil_font,
                              fill=(*cream_rgb, alpha))
```

Also update the docstring of `create_scroll_clips` to reflect the new behaviour:

```python
# Before
        At any moment the display shows:
          - Top row:    previous line, all words dim (past)
          - Middle row: current line, read words bright/cream, active word gold, unread words dim
          - Bottom row: next line, all words dim (future)

# After
        At any moment the display shows:
          - Top row:    previous line, all words bright/cream (past — already read)
          - Middle row: current line, read words bright/cream, active word gold, unread words dim
          - Bottom row: next line, all words dim (future — not yet reached)
```

- [ ] **Step 1.4: Run the test to verify it passes**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollPastLineBrightness -v
```

Expected: `PASSED`.

- [ ] **Step 1.5: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 1.6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: render past scroll line at full brightness (not dimmed)"
```

---

## Task 2: Fixed chars-per-second scroll speed with auto-computed duration

**Default speed:** `13` characters per second ≈ 130 words per minute, a comfortable on-screen reading pace.

At this speed, a 200-character quote takes ~15 s of reading time + 2.5 s author display = ~17.5 s total. A 350-character quote takes ~27 s + 2.5 s = ~29.5 s total. When 3 photos are chosen for a 29.5 s quote, each photo shows for ~9.8 s — all automatically, without the user having to guess a `--duration` value.

**Files:**
- Modify: `src/video_processor.py` — add constants near existing `CINEMATIC_*` constants; add `calculate_scroll_duration` near `calculate_text_duration`; update timing in `create_scroll_clips`; add duration override in `create_image_quote_video`
- Modify: `tests/test_video_processor.py`

---

- [ ] **Step 2.1: Write the failing tests**

Add to `tests/test_video_processor.py`:

```python
class TestScrollFixedSpeed:
    def test_calculate_scroll_duration_short_text(self):
        """Short text: duration = len(text)/13 + 2.5, rounded up."""
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

    def test_scroll_word_dt_matches_chars_per_second(self):
        """
        word_dt must equal (len(text) / n_words) / SCROLL_CHARS_PER_SECOND,
        not duration / n_words.
        """
        from unittest.mock import patch, MagicMock
        import numpy as np

        processor = make_processor()
        text = "Yoga is the mirror to look at ourselves from within."

        # We'll pass in a different duration to prove word_dt is NOT derived from it
        wrong_duration = 999.0  # absurd value — should have no effect on word_dt

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
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollFixedSpeed -v
```

Expected: `FAILED` — `calculate_scroll_duration` doesn't exist yet; `VideoClip` duration equals passed-in duration, not computed.

- [ ] **Step 2.3: Add constants to `VideoProcessor`**

In `src/video_processor.py`, find the block of `CINEMATIC_*` class constants (around line 153–166). Add after `CINEMATIC_AUTHOR_COLOR` (or nearby):

```python
# Scroll (teleprompter) timing
SCROLL_CHARS_PER_SECOND = 13       # comfortable on-screen reading pace (~130 wpm)
SCROLL_AUTHOR_DISPLAY_SECONDS = 2.5
```

- [ ] **Step 2.4: Add `calculate_scroll_duration` method**

In `src/video_processor.py`, add this method right after `calculate_text_duration` (line ~151):

```python
def calculate_scroll_duration(self, text: str) -> float:
    """
    Compute the total video duration needed to telepromt `text` at a fixed
    reading pace of SCROLL_CHARS_PER_SECOND, plus a fixed author-display tail.

    Args:
        text: Full quote body text (no truncation for scroll style).

    Returns:
        Total duration in seconds.
    """
    reading_time = len(text) / self.SCROLL_CHARS_PER_SECOND
    return reading_time + self.SCROLL_AUTHOR_DISPLAY_SECONDS
```

- [ ] **Step 2.5: Update timing inside `create_scroll_clips`**

In `src/video_processor.py`, inside `create_scroll_clips`, find the `# ---- Timing ----` block (line ~525–529):

```python
# Before
        # ---- Timing ----
        # Reserve the last ~2.5 s (or 15% of duration) for the author name.
        author_display_start = duration - min(2.5, duration * 0.15)
        # Each word gets equal time; floor at 0.3 s to avoid imperceptibly fast flashes.
        word_dt = max(0.3, author_display_start / n_words)
```

Replace with:

```python
        # ---- Timing ----
        # Duration is derived from text length at a fixed chars/sec rate.
        # Ignore the passed-in duration; compute from text instead so speed never changes.
        computed_duration = self.calculate_scroll_duration(text)
        author_display_start = computed_duration - self.SCROLL_AUTHOR_DISPLAY_SECONDS
        # Each word gets equal time; floor at 0.3 s to avoid imperceptibly fast flashes.
        word_dt = max(0.3, author_display_start / n_words)
```

Also update the two places that use `duration` to build the VideoClip and the scrim (at the bottom of `create_scroll_clips`, ~line 617–624):

```python
# Before
        scroll_clip = VideoClip(make_frame, duration=duration)
        ...
        return [self._make_scrim_clip(w, h, duration), scroll_clip]

# After
        scroll_clip = VideoClip(make_frame, duration=computed_duration)
        scroll_clip = (scroll_clip.with_fps(30) if hasattr(scroll_clip, 'with_fps')
                       else scroll_clip.set_fps(30))
        scroll_clip = (scroll_clip.with_position((0, 0)) if hasattr(scroll_clip, 'with_position')
                       else scroll_clip.set_position((0, 0)))

        return [self._make_scrim_clip(w, h, computed_duration), scroll_clip]
```

- [ ] **Step 2.6: Override duration in `create_image_quote_video` for scroll style**

In `src/video_processor.py`, inside `create_image_quote_video`, find line 1245:

```python
        use_flyer = flyer_lines and len(flyer_lines) > 0
        total_duration = (duration + flyer_duration) if use_flyer else duration
```

The scroll override must happen **before** `total_duration` is computed (line 1246), so `total_duration` is also correct. Replace those two lines with:

```python
        use_flyer = flyer_lines and len(flyer_lines) > 0
        # For scroll style, duration is derived from text length at a fixed reading pace
        # so all photos together fill exactly the time needed to read the full quote.
        # --duration from the CLI is ignored for scroll.
        if quote_style == 'scroll':
            duration = self.calculate_scroll_duration(text)
        total_duration = (duration + flyer_duration) if use_flyer else duration
```

Then ensure the image-clip block a few lines later (line ~1249) also sees the updated `duration`:

```python
        # ---- Segment 1: image(s) + quote ----
        n = len(image_paths)
        segment_duration = duration / n   # duration already overridden above for scroll
        if n == 1:
            image_clip = self.image_to_clip(image_paths[0], duration=duration)
        else:
            clips = [self.image_to_clip(p, duration=segment_duration) for p in image_paths]
            image_clip = concatenate_videoclips(clips, method='compose')
```

No changes are needed to the image-clip block itself — it already uses `duration`; only the override insertion above matters.

Also update the `duration` parameter docstring in `create_image_quote_video` (around line 1223):

```python
# Before
            duration: Total quote segment duration in seconds (default 15); split across images.

# After
            duration: Quote segment duration in seconds (default 15); split across images.
                Ignored when quote_style='scroll' — duration is then computed automatically
                from text length at SCROLL_CHARS_PER_SECOND characters per second.
```

- [ ] **Step 2.7: Update stale comment in `TestScrollAuthorPosition`**

The existing test `TestScrollAuthorPosition` (in `tests/test_video_processor.py`) has a comment that references the old timing formula. Find:

```python
        # author_display_start = duration - min(2.5, duration * 0.15) = 5.0 - 0.75 = 4.25
        author_t = 4.5  # safely past author_display_start
```

Replace with:

```python
        # After fixed-speed timing: author_display_start = calculate_scroll_duration(text) - 2.5
        # text = "Yoga is the mirror to look at ourselves from within." (52 chars)
        # → 52/13 + 2.5 = 6.5 s total, author_display_start = 4.0 s
        author_t = 4.5  # safely past author_display_start (4.0 s)
```

- [ ] **Step 2.8: Run the tests to verify they pass**

```bash
python3 -m pytest tests/test_video_processor.py::TestScrollFixedSpeed -v
```

Expected: all `PASSED`.

- [ ] **Step 2.9: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 2.10: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: fixed chars/sec scroll speed — duration computed from text length (13 chars/s default)"
```

---

## Final Check

- [ ] **Run the complete test suite one last time**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests pass.

---

## Manual Smoke Test

```bash
# Single image — duration derived entirely from text
python3 main.py generate-quote-cards \
  -i assets/01-ajuda/Yoga_Funchal21.jpg \
  --quote-style scroll

# Play back: verify scroll advances at a comfortable pace independent of --duration

# Three images — total time = text length / 13 + 2.5 s, split across 3 photos
python3 main.py generate-quote-cards \
  -i assets/01-ajuda/Yoga_Funchal21.jpg \
  -i assets/01-ajuda/Yoga_Funchal22.jpg \
  -i assets/01-ajuda/Yoga_Funchal23.jpg \
  --quote-style scroll

# Play back and verify:
# 1. Top (past) line is bright cream, not faded
# 2. Active word is gold
# 3. Bottom (future) line is dimmed
# 4. Author appears for 2.5 s at end
# 5. Total duration ≈ len(quote) / 13 + 2.5 — same regardless of image count
```
