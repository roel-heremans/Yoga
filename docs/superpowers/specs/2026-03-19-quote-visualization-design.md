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

The current implementation uses `quote_overlay_style=True` in `create_text_clip()`, which renders the full quote text inside a semi-transparent dark rectangular band near the bottom of the frame. While functional, it looks visually heavy and dated compared to modern Instagram content.

---

## Design

### Visual Style (both modes)

| Element | Value |
|---|---|
| Quote text color | Cream `#f0ece4` |
| Quote font | Serif (try: Liberation Serif, DejaVu Serif, Georgia, Arial fallback) |
| Quote font style | Italic |
| Quote letter spacing | 0.03em |
| Divider | Thin 1px gold `#c9a96e` line, 30px wide, centered |
| Author text color | Gold `#c9a96e` |
| Author font | Same serif, non-italic |
| Author letter spacing | 0.15em, uppercase |
| Backdrop | Subtle radial vignette (dark at edges, transparent at center) — **not** an opaque bar |

### Mode 1 — `cinematic`

- Full quote displayed at once, vertically and horizontally centered in the frame.
- Quote → divider line → author, stacked with breathing room.
- The dark radial vignette behind the centered text is subtle — it darkens the image edges, not a solid box.
- This is the **new default** — `--quote-style cinematic` (or omitting `--quote-style`).

### Mode 2 — `reveal`

- Same aesthetic as cinematic (same colors, fonts, centering).
- Quote is split into wrapped lines (same wrapping logic as cinematic).
- Lines fade in one by one, evenly spaced across the video duration.
- Previous lines remain visible as new ones appear (accumulate).
- Author line (with gold divider) fades in last, after all quote lines.
- Each line uses a short crossfade-in (~0.5s).
- Timing: total video duration divided equally across (N lines + 1 author block).

---

## Implementation Plan

### Files changed

| File | Change |
|---|---|
| `src/video_processor.py` | Add `create_cinematic_text_clip()`, `create_line_reveal_clips()`. Modify `create_image_quote_video()` to accept `quote_style` param. |
| `src/quote_card_generator.py` | Pass `quote_style` through `generate_image_video_quote_card()` to `VideoProcessor`. |
| `main.py` | Add `--quote-style` option (choices: `cinematic`, `reveal`; default: `cinematic`) to `generate-quote-cards` command. |

### New methods in `VideoProcessor`

#### `create_cinematic_text_clip(text, author, duration, font_size)`
- Renders the full quote + divider + author as a single centered composite.
- Returns a `CompositeVideoClip` (vignette + text layers) with the given duration.
- Uses the warm gold/cream color constants defined as class attributes.

#### `create_line_reveal_clips(text, author, duration, font_size)`
- Splits `text` into wrapped lines.
- Returns a list of clips: one per line + one for the divider+author block.
- Each clip has `with_start()` set to its reveal time (evenly distributed across `duration`).
- Each clip uses `crossfadein(0.5)`.
- Caller composes these on top of the background clip.

#### Modified `create_image_quote_video()`
- New param: `quote_style: str = 'cinematic'` (accepts `'cinematic'` or `'reveal'`).
- Branches at the text overlay step: calls `create_cinematic_text_clip()` or `create_line_reveal_clips()` based on the value.
- All other logic (flyer segment, audio, fades, multi-image) unchanged.

### New CLI option in `main.py`

```
--quote-style [cinematic|reveal]   Quote overlay style (default: cinematic)
```

Added to the `generate-quote-cards` command. Passed through to `QuoteCardGenerator.generate_image_video_quote_card()`.

### New class-level color constants in `VideoProcessor`

```python
CINEMATIC_QUOTE_COLOR = '#f0ece4'   # cream
CINEMATIC_AUTHOR_COLOR = '#c9a96e'  # warm gold
CINEMATIC_DIVIDER_COLOR = '#c9a96e' # warm gold
CINEMATIC_VIGNETTE_ALPHA = 120      # 0–255, subtle radial dark overlay
```

---

## Scope

### In scope
- `create_image_quote_video()` path only (the `--image` flag on `generate-quote-cards`).
- Both new modes fully implemented and usable from CLI.
- `cinematic` becomes the new default (replaces current `quote_overlay_style=True` behavior for this path).

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
# Cinematic (new default)
python3 main.py generate-quote-cards --image assets/01_images/Ajuda/photo.png --duration 15

# Cinematic (explicit)
python3 main.py generate-quote-cards --image assets/01_images/Ajuda/photo.png --duration 15 --quote-style cinematic

# Line reveal
python3 main.py generate-quote-cards --image assets/01_images/Ajuda/photo.png --duration 15 --quote-style reveal

# Reveal with flyer (flyer segment unaffected)
python3 main.py generate-quote-cards --image assets/01_images/Ajuda/photo.png --duration 15 --quote-style reveal --flyer-ajuda
```
