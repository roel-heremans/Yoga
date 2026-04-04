# Visual Enhancements: Flyer Size, Scroll Style, Green Fade

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three visual improvements to the quote card video generator: (1) double the flyer text size, (2) add a `scroll` (teleprompter) quote style with a 3-line word-by-word display, (3) fade all videos to brand green at the end instead of white.

**Architecture:** All changes are in `VideoProcessor` (rendering logic), wired through `QuoteCardGenerator` (unchanged — already passes `quote_style` through), and exposed via the Click CLI. The scroll style uses a PIL `VideoClip(make_frame)` to render an RGBA transparent overlay frame-by-frame, giving full word-level color control. PIL imports are lazy (inside the methods) to avoid hard-requiring Pillow at module load time.

**Tech Stack:** Python 3, moviepy 2.x, Pillow (PIL), Click, pytest

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `src/video_processor.py` | **Modify** | Task 1: flyer font defaults + title formula; Task 2: `_load_pil_font`, `create_scroll_clips`, wire `scroll` into `create_image_quote_video`; Task 3: brand-green fade for all final segments |
| `main.py` | **Modify** | Task 1: `--flyer-font-size` default + help text; Task 2: add `'scroll'` to `--quote-style` choices |
| `tests/test_video_processor.py` | **Modify** | New tests for each task |

`src/quote_card_generator.py` — no changes needed; it already passes `quote_style` through to `VideoProcessor` unchanged.

---

## Task 1: Double flyer-ajuda default font size

**Files:**
- Modify: `src/video_processor.py` — `create_cinematic_flyer_clip` (line ~749, ~832), `create_image_quote_video` (line ~1044)
- Modify: `main.py` — `--flyer-font-size` option (line ~347)
- Modify: `tests/test_video_processor.py`

### Background

`create_cinematic_flyer_clip` takes `font_size: int = 40`. Body text uses that directly; title uses:

```python
title_font_size = min(72, font_size + 28)   # current
```

At `font_size=40`: title=68, body=40 — title larger. ✓
At `font_size=80` (doubled): title=min(72,108)=**72 < body=80** — title smaller than body. ✗

Fix: remove the `min(72, ...)` cap:

```python
title_font_size = font_size + 28   # fixed: always larger than body
```

---

- [ ] **Step 1.1: Write the failing test**

Add to `tests/test_video_processor.py`:

```python
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
```

- [ ] **Step 1.2: Run the test to verify it fails**

```bash
cd /Users/roel.heremans/Documents/PersonalRepos/Yoga
python3 -m pytest tests/test_video_processor.py::TestFlyerFontDefaults -v
```

Expected: `FAILED` — default is 40, not 80.

- [ ] **Step 1.3: Update `create_cinematic_flyer_clip` defaults and title formula**

In `src/video_processor.py`, change the method signature (line ~749):

```python
# Before
def create_cinematic_flyer_clip(self, flyer_lines: list, duration: float, font_size: int = 40, logo_path=None):

# After
def create_cinematic_flyer_clip(self, flyer_lines: list, duration: float, font_size: int = 80, logo_path=None):
```

Change the title formula (line ~832):

```python
# Before
title_font_size = min(72, font_size + 28)

# After
title_font_size = font_size + 28
```

- [ ] **Step 1.4: Update `create_image_quote_video` default**

In `src/video_processor.py`, change the parameter (line ~1044):

```python
# Before
flyer_font_size: int = 40,

# After
flyer_font_size: int = 80,
```

- [ ] **Step 1.5: Update CLI default and help text**

In `main.py`, find the `--flyer-font-size` option (line ~347):

```python
# Before
@click.option('--flyer-font-size', default=40, type=int, help='Flyer body text font size (default: 40); title is larger')

# After
@click.option('--flyer-font-size', default=80, type=int, help='Flyer body text font size (default: 80); title is larger')
```

- [ ] **Step 1.6: Run the test to verify it passes**

```bash
python3 -m pytest tests/test_video_processor.py::TestFlyerFontDefaults -v
```

Expected: `PASSED`

- [ ] **Step 1.7: Run full test suite to check no regressions**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 1.8: Commit**

```bash
git add src/video_processor.py main.py tests/test_video_processor.py
git commit -m "feat: double default flyer font size (40→80), fix title size formula"
```

---

## Task 2: Add `scroll` (teleprompter) quote style

This is the complex task. The `scroll` style shows a 3-line window that advances word by word:
- **Top row:** previous line — all words at low opacity (past)
- **Middle row:** current line — read words cream/bright, active word gold/bright, unread words cream/dim
- **Bottom row:** next line — all words at low opacity (future)
- Lines outside the 3-line window are hidden (not yet reached, or already scrolled past)
- After the text is done, the author name appears centered in gold for the last ~2.5 s

Implementation uses `VideoClip(make_frame)` (a PIL-rendered per-frame RGBA transparent overlay).

**Files:**
- Modify: `src/video_processor.py` — add `_load_pil_font`, `create_scroll_clips`; wire `scroll` into `create_image_quote_video`
- Modify: `main.py` — add `'scroll'` to `click.Choice`
- Modify: `tests/test_video_processor.py`

---

- [ ] **Step 2.1: Write failing tests for `create_scroll_clips`**

Add to `tests/test_video_processor.py`:

```python
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
        """create_image_quote_video must accept quote_style='scroll' without raising."""
        import inspect
        from src.video_processor import VideoProcessor
        sig = inspect.signature(VideoProcessor.create_image_quote_video)
        # quote_style param exists (already exists for cinematic/reveal)
        assert 'quote_style' in sig.parameters
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_video_processor.py::TestCreateScrollClips -v
```

Expected: `FAILED` — `AttributeError: type object 'VideoProcessor' has no attribute 'create_scroll_clips'`

- [ ] **Step 2.3: Add `VideoClip` to the existing try/except import block in `video_processor.py`**

`video_processor.py` uses a try/except block to support both moviepy 2.x and 1.x. Add `VideoClip` to **both** lines:

```python
# Before (top of file)
try:
    from moviepy import VideoFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, ImageClip, AudioFileClip, concatenate_audioclips, ColorClip
except ImportError:
    try:
        from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, ImageClip, AudioFileClip, concatenate_audioclips, ColorClip
    except ImportError:
        raise ImportError(...)

# After — add VideoClip to both import lines
try:
    from moviepy import VideoFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, ImageClip, AudioFileClip, concatenate_audioclips, ColorClip, VideoClip
except ImportError:
    try:
        from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, ImageClip, AudioFileClip, concatenate_audioclips, ColorClip, VideoClip
    except ImportError:
        raise ImportError(...)
```

- [ ] **Step 2.4: Add `_load_pil_font` helper to `VideoProcessor`**

Add this method just before `create_scroll_clips` (after `_make_scrim_clip`):

```python
def _load_pil_font(self, size: int):
    """Load a PIL TrueType font at the given pixel size.

    Tries common system paths; falls back to PIL's built-in bitmap font
    (which ignores size but always works).
    """
    from PIL import ImageFont
    candidates = [
        # macOS
        '/Library/Fonts/Georgia.ttf',
        '/System/Library/Fonts/Supplemental/Georgia.ttf',
        '/System/Library/Fonts/Times.ttc',
        # Linux
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
        '/usr/share/fonts/truetype/fonts-dejavu/DejaVuSerif.ttf',
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()
```

- [ ] **Step 2.5: Add `create_scroll_clips` to `VideoProcessor`**

Add this method immediately after `_load_pil_font`:

```python
def create_scroll_clips(
    self,
    text: str,
    author: str,
    duration: float,
    font_size: int = 72,
) -> list:
    """
    Teleprompter-style 3-line scroll overlay.

    At any moment the display shows:
      - Top row:    previous line, all words dim (past)
      - Middle row: current line, read words bright/cream, active word gold, unread words dim
      - Bottom row: next line, all words dim (future)

    Lines outside the 3-line window are hidden. After all words are shown, the
    author name appears centered in gold for the last ~2.5 s of the clip.

    Returns a list of transparent overlay clips to composite over the background.
    """
    import numpy as np

    w, h = self.reel_width, self.reel_height

    # ---- Text wrapping ----
    char_width_ratio = 0.55
    usable_width = w - 120
    max_chars = max(20, int(usable_width / (font_size * char_width_ratio) * 1.2))
    wrapped_lines = self._smart_wrap(text, max_chars)
    words_per_line = [line.split() for line in wrapped_lines if line.strip()]

    # Flat word list: each entry is (line_idx, word_idx_within_line)
    flat_words = [
        (li, wi)
        for li, words in enumerate(words_per_line)
        for wi in range(len(words))
    ]
    n_words = max(1, len(flat_words))

    # ---- Timing ----
    # Reserve the last ~2.5 s (or 15% of duration) for the author name.
    author_display_start = duration - min(2.5, duration * 0.15)
    # Each word gets equal time; floor at 0.3 s to avoid imperceptibly fast flashes.
    word_dt = max(0.3, author_display_start / n_words)

    # ---- Layout ----
    line_height = int(font_size * self.LINE_HEIGHT_MULT)
    block_top = max(80, h // 6)
    # Row offsets: past=-1 (top), current=0 (middle), future=+1 (bottom)
    # Visible rows are at block_top, block_top+line_height, block_top+2*line_height

    # ---- Colours ----
    cream_rgb = self.hex_to_rgb(self.CINEMATIC_QUOTE_COLOR)    # (#f0ece4)
    gold_rgb  = self.hex_to_rgb(self.CINEMATIC_AUTHOR_COLOR)   # (#c9a96e)
    BRIGHT = 255
    DIM    = 80

    # ---- Pre-load fonts ----
    pil_font   = self._load_pil_font(font_size)
    author_font = self._load_pil_font(max(28, font_size // 2))

    # ---- Measure helper (handles Pillow API differences) ----
    def _measure(fnt, txt: str) -> int:
        from PIL import ImageDraw, Image
        d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        try:
            return int(d.textlength(txt, font=fnt))
        except AttributeError:
            try:
                return int(fnt.getlength(txt))
            except AttributeError:
                return int(fnt.getsize(txt)[0])

    # ---- Per-frame renderer ----
    def make_frame(t):
        from PIL import Image, ImageDraw
        img  = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if t >= author_display_start:
            # Show author centred in gold
            if author:
                author_text = author.upper()
                tw = _measure(author_font, author_text)
                x  = (w - tw) // 2
                y  = h // 2
                draw.text((x, y), author_text, font=author_font,
                          fill=(*gold_rgb, BRIGHT))
            return np.array(img)

        # Which word is active at time t?
        word_idx = min(int(t / word_dt), n_words - 1)
        cur_line, cur_word = flat_words[word_idx]

        # Render past / current / future rows
        for offset in (-1, 0, 1):
            li = cur_line + offset
            if li < 0 or li >= len(words_per_line):
                continue
            words = words_per_line[li]
            y = block_top + (offset + 1) * line_height  # offset -1→top, 0→mid, 1→bottom

            if offset == 0:
                # Current line: word-by-word colouring
                total_w = sum(_measure(pil_font, wd + ' ') for wd in words)
                x = (w - total_w) // 2
                for wi, wd in enumerate(words):
                    if wi < cur_word:
                        rgba = (*cream_rgb, BRIGHT)   # already read
                    elif wi == cur_word:
                        rgba = (*gold_rgb,  BRIGHT)   # active word
                    else:
                        rgba = (*cream_rgb, DIM)      # not yet read
                    draw.text((x, y), wd, font=pil_font, fill=rgba)
                    x += _measure(pil_font, wd + ' ')
            else:
                # Past or future: render the full line dimmed
                line_text = ' '.join(words)
                tw = _measure(pil_font, line_text)
                x  = (w - tw) // 2
                draw.text((x, y), line_text, font=pil_font,
                          fill=(*cream_rgb, DIM))

        return np.array(img)

    # ---- Build the VideoClip overlay ----
    scroll_clip = VideoClip(make_frame, duration=duration)
    scroll_clip = (scroll_clip.with_fps(30) if hasattr(scroll_clip, 'with_fps')
                   else scroll_clip.set_fps(30))
    scroll_clip = (scroll_clip.with_position((0, 0)) if hasattr(scroll_clip, 'with_position')
                   else scroll_clip.set_position((0, 0)))

    return [self._make_scrim_clip(w, h, duration), scroll_clip]
```

- [ ] **Step 2.6: Wire `scroll` into `create_image_quote_video`**

In `src/video_processor.py`, find the section in `create_image_quote_video` that dispatches on `quote_style` (around line 1106):

```python
# Before (two branches)
if quote_style == 'reveal':
    reveal_clips = self.create_line_reveal_clips(...)
    segment_1 = CompositeVideoClip([image_clip] + reveal_clips)
else:
    # 'cinematic' (default)
    text_clip = self.create_cinematic_text_clip(...)
    segment_1 = CompositeVideoClip([image_clip, text_clip])

# After (three branches)
if quote_style == 'reveal':
    reveal_clips = self.create_line_reveal_clips(
        text=text,
        author=author,
        duration=duration,
        font_size=quote_font_size,
    )
    segment_1 = CompositeVideoClip([image_clip] + reveal_clips)
elif quote_style == 'scroll':
    scroll_clips = self.create_scroll_clips(
        text=text,
        author=author,
        duration=duration,
        font_size=quote_font_size,
    )
    segment_1 = CompositeVideoClip([image_clip] + scroll_clips)
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

- [ ] **Step 2.7: Add `'scroll'` to CLI choices**

In `main.py`, find the `--quote-style` option (line ~348):

```python
# Before
@click.option('--quote-style', type=click.Choice(['cinematic', 'reveal'], case_sensitive=False), ...)

# After
@click.option('--quote-style', type=click.Choice(['cinematic', 'reveal', 'scroll'], case_sensitive=False), ...)
```

Also update the help text to mention `scroll`:

```python
help='Quote overlay style: cinematic (centered gold/cream), reveal (line-by-line fade-in), or scroll (teleprompter 3-line word-by-word) [default: cinematic]'
```

- [ ] **Step 2.8: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_video_processor.py::TestCreateScrollClips -v
```

Expected: all `PASSED`

- [ ] **Step 2.9: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 2.10: Commit**

```bash
git add src/video_processor.py main.py tests/test_video_processor.py
git commit -m "feat: add scroll (teleprompter) quote style with 3-line word-by-word display"
```

---

## Task 3: Fade to brand green at end of every video

Currently `_add_white_fade_overlay` defaults to white. The brand primary green (`#2c5530`) should be the fade target for all final segments — whether or not a flyer is present.

**Files:**
- Modify: `src/video_processor.py` — `create_image_quote_video` (lines ~1127–1147)
- Modify: `tests/test_video_processor.py`

### How the code currently works

```python
# Line ~1128 — inside `if use_flyer:` block only
_gr, _gg, _gb = self.hex_to_rgb(
    self.config.get('brand', {}).get('colors', {}).get('primary', '#2c5530'))
segment_1 = self._add_white_fade_overlay(segment_1, video_fade_duration, fps,
                                          color=(_gr, _gg, _gb))   # ← green ✓
...
segment_2 = self._add_white_fade_overlay(segment_2, video_fade_duration, fps)  # ← white ✗

# Line ~1133 — inside `else:` (no flyer)
segment_1 = self._add_white_fade_overlay(segment_1, video_fade_duration, fps)  # ← white ✗
```

### Fix

Extract the brand green colour before the `if use_flyer` block so both branches can use it:

```python
# Extract once, before the if use_flyer block
_fade_r, _fade_g, _fade_b = self.hex_to_rgb(
    self.config.get('brand', {}).get('colors', {}).get('primary', '#2c5530'))
_fade_color = (_fade_r, _fade_g, _fade_b)

if use_flyer:
    segment_1 = self._add_white_fade_overlay(segment_1, video_fade_duration, fps,
                                              color=_fade_color)   # green transition to flyer
    ...
    segment_2 = self._add_white_fade_overlay(segment_2, video_fade_duration, fps,
                                              color=_fade_color)   # green at very end ← changed
else:
    segment_1 = self._add_white_fade_overlay(segment_1, video_fade_duration, fps,
                                              color=_fade_color)   # green at very end ← changed
```

---

- [ ] **Step 3.1: Write the failing test**

Add to `tests/test_video_processor.py`:

```python
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

        processor = make_processor()  # make_processor() is a plain function at module scope in test_video_processor.py
        # Patch heavy operations so the test runs fast
        fake_clip = MagicMock()
        fake_clip.size = (1080, 1920)
        fake_clip.duration = 5

        with patch.object(processor, '_add_white_fade_overlay', return_value=fake_clip) as mock_fade, \
             patch('src.video_processor.ImageClip', return_value=fake_clip), \
             patch('src.video_processor.CompositeVideoClip', return_value=fake_clip), \
             patch('src.video_processor.concatenate_videoclips', return_value=fake_clip), \
             patch.object(processor, 'create_cinematic_text_clip', return_value=fake_clip), \
             patch.object(processor, '_append_generated_cards_to_quote', return_value=None):
            try:
                processor.create_image_quote_video(
                    text="Yoga is peace.",
                    author="Iyengar",
                    image_paths=[Path('/tmp/fake.jpg')],
                    output_path=Path('/tmp/out.mp4'),
                    duration=5.0,
                    use_flyer=False,
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
```

- [ ] **Step 3.2: Run the test to verify it fails**

```bash
python3 -m pytest tests/test_video_processor.py::TestGreenFadeAtEnd -v
```

Expected: `FAILED` — no-flyer path calls `_add_white_fade_overlay` without a color kwarg.

- [ ] **Step 3.3: Implement the fix in `create_image_quote_video`**

In `src/video_processor.py`, inside `create_image_quote_video`, locate the segment around line 1127. Extract the brand color **before** the `if use_flyer:` block and pass it to every `_add_white_fade_overlay` call for the final segment:

```python
# ---- Extract brand fade colour (used for all end-of-video fades) ----
_fade_color = self.hex_to_rgb(
    self.config.get('brand', {}).get('colors', {}).get('primary', '#2c5530'))

if use_flyer:
    segment_1 = self._add_white_fade_overlay(
        segment_1, video_fade_duration, fps, color=_fade_color)
else:
    segment_1 = self._add_white_fade_overlay(
        segment_1, video_fade_duration, fps, color=_fade_color)

if not use_flyer:
    final_clip = segment_1
else:
    segment_2 = self.create_cinematic_flyer_clip(
        flyer_lines=flyer_lines,
        duration=flyer_duration,
        font_size=flyer_font_size,
        logo_path=flyer_logo_path,
    )
    if hasattr(segment_2, 'with_fps'):
        segment_2 = segment_2.with_fps(fps)
    segment_2 = self._add_white_fade_overlay(
        segment_2, video_fade_duration, fps, color=_fade_color)   # ← was white
    final_clip = concatenate_videoclips([segment_1, segment_2], method='chain')
    ...
```

> Note: Remove the now-duplicate `_gr, _gg, _gb = self.hex_to_rgb(...)` line that was inside `if use_flyer:`.

- [ ] **Step 3.4: Run the test to verify it passes**

```bash
python3 -m pytest tests/test_video_processor.py::TestGreenFadeAtEnd -v
```

Expected: `PASSED`

- [ ] **Step 3.5: Run full test suite**

```bash
python3 -m pytest tests/ -q
```

Expected: all passing.

- [ ] **Step 3.6: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: fade to brand green at end of all videos (no-flyer and flyer paths)"
```

---

## Final Full Test Run

- [ ] **Run the complete test suite**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests pass, no regressions.

---

## End-to-End Smoke Test (manual)

After all tasks complete, test each feature manually:

```bash
# Task 1: Flyer text doubled
python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg --duration 15 --flyer-ajuda -m assets/00_music/track.mp3
# → Inspect output: flyer text should be noticeably larger

# Task 2: Scroll style
python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg --duration 20 --quote-style scroll
# → Play output: 3-line teleprompter window should advance word by word, author appears at end

# Task 3: Green fade
python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg --duration 15
# → Play output: last ~0.8 s should fade to deep green (#2c5530), not white

# Combined: scroll + flyer + green fade
python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg --duration 20 --quote-style scroll --flyer-ajuda -m assets/00_music/track.mp3
# → Quote scrolls word by word → fades to green → large flyer text → fades to green
```
