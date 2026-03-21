# Scroll Style Fixes: Full Quote Display and Author Position

**Date:** 2026-03-21
**Status:** Approved

## Problem

Two bugs in the `scroll` (teleprompter) quote style:

1. **Quote truncation** — `max_display_length: 120` in `config/settings.yaml` silently cuts long quotes before they reach the video. The scroll style was designed to handle long quotes, so this limit should not apply to it.
2. **Author position** — the author name appears at `y = h // 2` (screen center) when it fades in at the end of the video. It should appear at "line 4" — directly below the 3-line scroll window in the top-third area.

## Design

### Change 1: Bypass truncation for scroll style

**File:** `src/quote_card_generator.py`

Where the quote text is prepared before being passed to `VideoProcessor`, conditionally apply the display-length cap:

```python
display_text = quote['text']
if quote_style != 'scroll':
    display_text = display_text[:self.max_quote_display_length]
```

- Cinematic and reveal styles keep the 120-char cap (they are not designed for long text).
- Scroll always receives the full quote text.
- No changes to `config/settings.yaml` or any other style.

### Change 2: Author position in scroll style

**File:** `src/video_processor.py` — `create_scroll_clips` method

Change the author y-position from:

```python
y = h // 2
```

to:

```python
y = block_top + 3 * line_height
```

`block_top` and `line_height` are already computed earlier in the method. This places the author at the natural "line 4" slot — directly below the 3-line scroll window — within the top-third area of the frame, consistent with how other styles position attribution text.

## Files Touched

| File | Change |
|------|--------|
| `src/quote_card_generator.py` | Bypass `max_display_length` when `quote_style == 'scroll'` |
| `src/video_processor.py` | Move author y-position from `h // 2` to `block_top + 3 * line_height` |
| `tests/test_quote_card_generator.py` | New test: scroll style receives full quote text |
| `tests/test_video_processor.py` | New test: author y-position is `block_top + 3 * line_height` |

## Out of Scope

- No changes to cinematic or reveal styles.
- No config changes.
- No changes to timing of author appearance (still last ~2.5 s).
