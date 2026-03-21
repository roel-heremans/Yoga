# Visual Enhancements Design Spec
**Date:** 2026-03-21

## Overview

Five visual improvements to the Yoga quote card video generator:

1. Semi-transparent pill background behind each line of text (all 3 quote styles)
2. Bigger default font size for quote text
3. Flyer-ajuda card duration reduced to 5 seconds
4. Teleprompter (scroll) end-of-quote: freeze last 3 lines, show author below
5. Teleprompter text block position: `h // 8` from top

---

## 1. Semi-transparent pill background per line

A semi-transparent dark rounded rectangle is drawn behind each line of text to improve readability against bright or busy background photos.

**Spec:**
- Shape: rounded rectangle, border radius ~20px
- Colour: `rgba(0, 0, 0, 0.50)` — dark but background photo shows through
- Padding: 6px vertical, 14px horizontal inside the pill
- Applied per-line (not one block for all text)

**Implementation per style:**

### Cinematic (`create_cinematic_text_clip`)
- After computing wrapped lines and their y-positions, call a new helper `_make_pill_overlay(lines, font_size, line_y_positions, w, h, duration)`.
- `_make_pill_overlay` uses PIL to draw one rounded rectangle per line, sized to the text width + padding, and returns a static `ImageClip` (RGBA transparent except for the pills).
- This clip is composited between the scrim and the text clips in the returned `CompositeVideoClip`.

### Reveal (`create_line_reveal_clips`)
- Same approach: call `_make_pill_overlay` with the wrapped lines and computed y-positions.
- The pill overlay is static (always visible); the text clips fade in over it as before.
- Pill overlay is composited below the text clips and above the scrim.

### Scroll (`create_scroll_clips`)
- No separate helper needed — scroll already renders per-frame with PIL.
- Inside `make_frame`, before drawing text for each row (past, current, future), call `draw.rounded_rectangle()` with `rgba(0,0,0,0.50)` fill to draw the pill behind that line.
- During the author phase (`t >= author_display_start`), pills are drawn behind the frozen quote lines and behind the author/book lines.

---

## 2. Bigger default font size

The previous default font size of `72px` for scroll and `64px` for cinematic/reveal, plus the restrictive cap formula `min(font_size, max(40, (top_black - 20) // 3))`, kept text too small. With pill backgrounds providing contrast regardless of the image content, text can safely overlay the photo area.

**Changes:**
- `create_scroll_clips`: default `font_size` parameter `72` → `96`
- `create_image_quote_video`: default `font_size` parameter `64` → `96`
- `create_image_quote_video`: remove the cap formula `quote_font_size = min(font_size, max(40, (top_black - 20) // 3))` — replace with `quote_font_size = font_size` (pass through directly)
- CLI `main.py`: update `--font-size` / `font_size` default to `96` if exposed, or rely on the updated Python defaults

**Note:** The existing scroll duration calculation (`len(text) / SCROLL_CHARS_PER_SECOND + SCROLL_AUTHOR_DISPLAY_SECONDS`) and the per-photo duration split are **not changed**. Total video duration continues to be derived from text length at the fixed reading speed, split equally across all supplied photos.

---

## 3. Flyer-ajuda duration → 5 seconds

The flyer-ajuda card (white background + studio text) currently defaults to 15 seconds. Users only need ~5 seconds to read it.

**Changes:**
- `create_image_quote_video` in `video_processor.py`: `flyer_duration: float = 15.0` → `flyer_duration: float = 5.0`
- `main.py`: `--flyer-duration` option default `15` → `5`, update help text accordingly

---

## 4. Scroll: freeze last 3 lines when author appears

**Current behaviour:** At `t >= author_display_start`, `make_frame` clears the screen and renders only the author name centred in gold.

**New behaviour:** At `t >= author_display_start`:

1. Determine the last 3 lines of `words_per_line` (or all lines if fewer than 3). Call these `frozen_lines`.
2. Render `frozen_lines` as static pill rows starting at `block_top` (`h // 8`), all words at full brightness / cream colour — no word-by-word highlighting, they are finished.
3. Below the last frozen line: a thin horizontal divider, colour `rgba(201, 169, 110, 0.4)`, width 55% of frame, centred.
4. Below the divider: author name (gold, `CINEMATIC_AUTHOR_COLOR`, uppercase) in its own pill.
5. Below the author: book/source name if present (cream, `CINEMATIC_QUOTE_COLOR`, dimmed alpha ~160) in its own pill.

The vertical spacing between frozen lines, divider, and author uses the same `line_height` as the rest of the scroll rendering.

---

## 5. Scroll text block position: `h // 8` from top

**Current:** `block_top = max(80, h // 6)` — places text ~320px from top on a 1920px frame.

**New:** `block_top = h // 8` — places text ~240px from top on a 1920px frame. Higher on screen, more image visible below the text block.

---

## Files changed

| File | What changes |
|------|-------------|
| `src/video_processor.py` | `_make_pill_overlay` helper (new); `create_cinematic_text_clip` (pill overlay); `create_line_reveal_clips` (pill overlay); `create_scroll_clips` (inline pills, frozen-lines author phase, `block_top`, `font_size` default); `create_image_quote_video` (`font_size` default, remove cap formula, `flyer_duration` default) |
| `main.py` | `--flyer-duration` default 15→5 |
| `tests/test_video_processor.py` | New test classes for each change |

---

## What is NOT changed

- `calculate_scroll_duration` and `SCROLL_CHARS_PER_SECOND` — scroll video length continues to be derived from text length at a fixed reading speed.
- The per-photo duration split in `create_image_quote_video` for scroll style — multiple photos each get an equal share of the computed duration.
- Green fade at end of all videos.
- `create_cinematic_flyer_clip` — flyer content and styling unchanged, only its default duration is reduced.
