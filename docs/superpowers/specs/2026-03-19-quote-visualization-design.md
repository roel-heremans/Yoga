# Quote Visualization Improvement — Design Spec

**Date:** 2026-03-19
**Status:** Approved

## Summary

Replace the current quote overlay (dark opaque band at the bottom) with two distinct, high-quality styles selectable via a `--quote-style` CLI flag:

- **`cinematic`** (new default): full quote centered in the frame, warm gold/cream palette, elegant serif typography, subtle vignette — no opaque band.
- **`reveal`** (new): same aesthetic, but lines of the quote fade in one by one as the video plays (accumulating), with the author line appearing last.

Both modes apply only to the `generate-quote-cards` command's image-video output (i.e. `create_image_quote_video`). Photo overlays, white background cards, and video overlays are out of scope.

---

## Background

The current implementation uses `create_text_clip()` with `quote_overlay_style=True`, which renders the full quote text inside a semi-transparent dark rectangular band near the bottom of the frame. While functional, it looks visually heavy and dated compared to modern Instagram content.

---

## Design

### Visual Style (both modes)

| Element | Value |
|---|---|
| Quote text color | Cream `#f0ece4` |
| Quote font | Serif (try: Liberation Serif, DejaVu Serif, Georgia, Arial fallback) |
| Quote font style | Italic |
| Author text color | Gold `#c9a96e` |
| Author text style | Non-italic, uppercase |
| Divider | Thin line, 30px wide, 1px tall, centered, color `#c9a96e` |
| Backdrop | Subtle radial vignette (dark at edges, transparent at center) — **not** an opaque bar |

**Note on letter spacing:** PIL/moviepy do not support native letter-spacing. Author uppercase is the primary requirement; any letter-spacing approximation is best-effort and may be omitted in the initial implementation.

### Mode 1 — `cinematic`

- Full quote displayed at once, vertically and horizontally centered in the frame.
- Layout (stacked, centered): quote text → divider → author.
- The radial vignette darkens the image edges to improve text readability.
- This is the **new default**: `--quote-style cinematic` (or omitting `--quote-style`).

### Mode 2 — `reveal`

- Same aesthetic as cinematic (same colors, fonts, centering).
- Quote is split into wrapped lines using the same wrapping logic as cinematic.
- Lines fade in one by one, evenly spaced across the video duration.
- Previous lines remain visible as new ones appear (accumulate).
- Author line (preceded by the gold divider) fades in last.
- Each line/author uses a short crossfade-in (~0.5s), with moviepy 2.x compatibility guards (see below).
- **Timing formula:** `interval = duration / (N_lines + 1)` where N_lines is the number of wrapped quote lines. Each line `i` starts at `i * interval`. Author block starts at `N_lines * interval`.
- **Minimum interval clamp:** If `interval < 1.0s`, clamp it to `1.0s` (the reveal will extend beyond the clip duration, but later lines will simply not be visible — graceful degradation).

---

## Implementation Plan

### Files changed

| File | Change |
|---|---|
| `src/video_processor.py` | Add `create_cinematic_text_clip()`, `create_line_reveal_clips()`. Modify `create_image_quote_video()` to accept `quote_style` param. |
| `src/quote_card_generator.py` | Pass `quote_style` through `generate_image_video_quote_card()` **and** `generate_quote_cards()` to `VideoProcessor`. |
| `main.py` | Add `--quote-style` option (choices: `cinematic`, `reveal`; default: `cinematic`) to `generate-quote-cards` command. |

### Internal data flow change

Currently, `generate_image_video_quote_card()` combines quote and author into a single string before calling the video processor:

```python
overlay_text = f"{quote_text}\n\n— {author}"
```

This pre-formatting must be removed for both new modes. Instead, `text` (quote body) and `author` are passed as **separate arguments** to `create_cinematic_text_clip()` and `create_line_reveal_clips()`. The combined string path is fully replaced.

### New class-level color constants in `VideoProcessor`

```python
CINEMATIC_QUOTE_COLOR = '#f0ece4'    # cream
CINEMATIC_AUTHOR_COLOR = '#c9a96e'   # warm gold
CINEMATIC_DIVIDER_COLOR = '#c9a96e'  # warm gold
CINEMATIC_VIGNETTE_ALPHA = 120       # 0–255, max darkness at frame edges
```

### New methods in `VideoProcessor`

#### `create_cinematic_text_clip(text, author, duration, font_size=64)`

**Returns:** A `CompositeVideoClip` of size `(reel_width, reel_height)` containing the vignette and text layers. It does **not** include the background image itself — the caller composites it on top. The explicit `size=` argument ensures correct dimensions when nested inside another `CompositeVideoClip`.

**Layout constants (shared with `create_line_reveal_clips`):**
```python
LINE_HEIGHT_MULT = 1.6   # line_height = font_size * LINE_HEIGHT_MULT
DIVIDER_GAP = 20         # pixels between last quote line and divider
AUTHOR_GAP = 12          # pixels between divider and author text
DIVIDER_WIDTH = 30       # pixels wide
DIVIDER_HEIGHT = 2       # pixels tall
```

**Assembly steps:**
1. **Vignette layer**: Full-frame RGBA NumPy array (`shape = (reel_height, reel_width, 4)`). Alpha computed as a radial gradient — zero at center, rising to `CINEMATIC_VIGNETTE_ALPHA` at edges:
   ```python
   cx, cy = w / 2, h / 2
   Y, X = np.mgrid[0:h, 0:w]
   dist = np.hypot((X - cx) / cx, (Y - cy) / cy)  # normalised 0..~1.4
   alpha = np.clip(dist * CINEMATIC_VIGNETTE_ALPHA, 0, CINEMATIC_VIGNETTE_ALPHA).astype(np.uint8)
   ```
   Wrap in `ImageClip(arr)` (with `transparent=True` if supported), set duration, position at `(0, 0)`.

2. **Quote TextClip**: cream `#f0ece4`, italic serif, `size=(reel_width - 120, None)`, `margin=(20, 20)`. Use font fallback chain (`QUOTE_OVERLAY_FONT_CANDIDATES`). Wrap text using the same char-width formula as `create_text_clip()`.

3. **Divider**: RGBA NumPy array of shape `(DIVIDER_HEIGHT, DIVIDER_WIDTH, 4)`, filled gold `#c9a96e`, full alpha. Wrapped in `ImageClip`.

4. **Author TextClip**: gold `#c9a96e`, non-italic, uppercase, same serif fallback chain, `size=(reel_width - 120, None)`.

5. **Vertical centering**: estimate total block height as `(N_lines * font_size * LINE_HEIGHT_MULT) + DIVIDER_GAP + DIVIDER_HEIGHT + AUTHOR_GAP + author_height`. Set `block_top = max(80, (reel_height - total_block_height) // 2)`. Position each element sequentially from `block_top`. All clips horizontally centered at `('center', y)`.

6. **Duration and size**: set `duration` on all clips. Return `CompositeVideoClip([vignette, quote_clip, divider_clip, author_clip], size=(reel_width, reel_height))`.

**Font size:** Default `64`. No dynamic derivation from letterbox geometry.

---

#### `create_line_reveal_clips(text, author, duration, font_size=64)`

**Returns:** A list of moviepy clips. Each clip is a transparent-background overlay, pre-positioned at its final absolute `(x, y)` coordinate in the reel frame before being returned. The caller simply adds them all to `CompositeVideoClip`.

**Layout pre-computation:** Uses the same constants as `create_cinematic_text_clip()` (`LINE_HEIGHT_MULT`, `DIVIDER_GAP`, `AUTHOR_GAP`). Before creating any clips, compute all final positions:
1. Wrap `text` into lines using the same char-width formula as `create_text_clip`.
2. `line_height = font_size * LINE_HEIGHT_MULT`
3. Estimate total block height: `(N_lines * line_height) + DIVIDER_GAP + DIVIDER_HEIGHT + AUTHOR_GAP + author_height`.
4. `block_top = max(80, (reel_height - total_block_height) // 2)`.
5. Each line `i` is positioned at `y = block_top + i * line_height`.
6. Divider is positioned at `y = block_top + N_lines * line_height + DIVIDER_GAP`.
7. Author is positioned at `y = divider_y + DIVIDER_HEIGHT + AUTHOR_GAP`.

All clips are pre-positioned using `with_position(('center', y))` (or `set_position` for moviepy 1.x) before being returned.

**Timing:**
- `interval = max(1.0, duration / (N_lines + 1))`
- Line `i` has `start_time = i * interval`.
- Author block has `start_time = N_lines * interval`.

**Fade-in:** Each clip uses `crossfadein(0.5)`. Apply with `hasattr` guard for moviepy 2.x compatibility:
```python
if hasattr(clip, 'crossfadein'):
    clip = clip.crossfadein(0.5)
```
If `crossfadein` is unavailable, proceed without the fade (graceful degradation).

---

### Modified `create_image_quote_video()`

**New signature** (replacing `text_overlay: str` with separate `text` and `author`, and adding `quote_style`):
```python
def create_image_quote_video(
    self,
    image_paths: List[Path],
    text: str,           # quote body only (was: text_overlay)
    author: str,         # attribution line (was: embedded in text_overlay)
    output_path: Path,
    duration: float = 15.0,
    music_path: Optional[Path] = None,
    audio_fade_duration: float = 3.0,
    video_fade_duration: float = 0.8,
    text_position: str = 'bottom',   # kept for backwards compat, ignored by cinematic/reveal
    font_size: int = 64,
    flyer_lines: Optional[List[str]] = None,
    flyer_duration: float = 15.0,
    flyer_font_size: int = 40,
    flyer_logo_path: Optional[Path] = None,
    quote_style: str = 'cinematic',  # 'cinematic' or 'reveal'
) -> Path:
```

The old `text_overlay` parameter is **removed** (not aliased). All callers must be updated.

- Branches at the text overlay step:
  - `'cinematic'`: calls `create_cinematic_text_clip(text, author, duration, font_size)`, composites result on top of image clip.
  - `'reveal'`: calls `create_line_reveal_clips(text, author, duration, font_size)`, composites all returned clips on top of image clip.
- All other logic (flyer segment, audio fade, white fade-out, multi-image splitting) is unchanged.

### Modified `generate_image_video_quote_card()` in `QuoteCardGenerator`

- New param: `quote_style: str = 'cinematic'`.
- Stops constructing `overlay_text = f"{quote_text}\n\n— {author}"`.
- Passes `text=quote_text`, `author=author`, `font_size=64`, `quote_style=quote_style` to `VideoProcessor.create_image_quote_video()`.

### Modified `generate_quote_cards()` in `QuoteCardGenerator`

- New param: `quote_style: str = 'cinematic'`.
- Passes `quote_style` through to `generate_image_video_quote_card()`.

### New CLI option in `main.py`

```
--quote-style [cinematic|reveal]   Quote overlay style (default: cinematic)
```

Added to the `generate-quote-cards` command. Passed through the full call chain to `VideoProcessor`.

**Behavior when `--quote-style` is used without `--image`:** The flag is silently ignored. The existing CLI already gates image-video generation on whether `image_paths` is set — no additional error or warning is needed.

---

## Scope

### In scope
- `create_image_quote_video()` path only (the `--image` flag on `generate-quote-cards`).
- Both new modes fully implemented and usable from CLI.
- `cinematic` becomes the new default, replacing `quote_overlay_style=True` for this path.

### Out of scope
- Photo overlay cards (`generate_photo_overlay_card`)
- Video overlay cards (`generate_video_overlay_card`)
- White background cards
- Flyer segment styling
- `create_reel()` / `create_combined_reel()` paths
- Animated transitions between image segments

---

## Usage Examples

```bash
# Cinematic (new default — omitting --quote-style)
python3 main.py generate-quote-cards --image assets/01_images/Ajuda/photo.png --duration 15

# Cinematic (explicit)
python3 main.py generate-quote-cards --image assets/01_images/Ajuda/photo.png --duration 15 --quote-style cinematic

# Line reveal
python3 main.py generate-quote-cards --image assets/01_images/Ajuda/photo.png --duration 15 --quote-style reveal

# Reveal with flyer (flyer segment unaffected by quote-style)
python3 main.py generate-quote-cards --image assets/01_images/Ajuda/photo.png --duration 15 --quote-style reveal --flyer-ajuda
```
