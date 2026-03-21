# Scroll Style Fixes: Full Quote Display and Author Position

**Date:** 2026-03-21
**Status:** Approved

## Problem

Two bugs in the `scroll` (teleprompter) quote style:

1. **Quote truncation** — `max_display_length: 120` in `config/settings.yaml` silently cuts long quotes before they reach the video. The scroll style was designed to handle long quotes, so this limit should not apply to it.
2. **Author position** — the author name appears at `y = h // 2` (screen center) when it fades in at the end of the video. It should appear at "line 4" — directly below the 3-line scroll window in the top-third area.

## Design

### Change 1: Bypass truncation for scroll style

**File:** `src/quote_card_generator.py` — method `generate_image_video_quote_card`

This method receives `quote_style` as a parameter and currently calls:

```python
quote_text = self._shorten_quote_for_display(quote.get('text', ''))
```

Replace with a conditional guard:

```python
raw_text = quote.get('text', '')
quote_text = raw_text if quote_style == 'scroll' else self._shorten_quote_for_display(raw_text)
```

`generate_image_video_quote_card` is the single place where truncation occurs; the guard here is sufficient — `generate_quote_cards` delegates to this method and does not call `_shorten_quote_for_display` separately.

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

`block_top` and `line_height` are computed earlier in the method body and are free variables closed over by `make_frame` — no signature or structural changes to the method are needed. This places the author at the natural "line 4" slot — directly below the 3-line scroll window — within the top-third area of the frame, consistent with how other styles position attribution text.

## Files Touched

| File | Change |
|------|--------|
| `src/quote_card_generator.py` | Bypass `max_display_length` when `quote_style == 'scroll'` |
| `src/video_processor.py` | Move author y-position from `h // 2` to `block_top + 3 * line_height` |
| `tests/test_quote_card_generator.py` | New test: scroll style receives full quote text (see test spec below) |
| `tests/test_video_processor.py` | New test: author y-position is `block_top + 3 * line_height` |

## Test Spec

**`tests/test_quote_card_generator.py` — Change 1 test:**

Use a quote whose text exceeds 120 characters (e.g., the Iyengar quote in the problem statement: ~170 chars). Patch `VideoProcessor.create_image_quote_video` and follow the existing mock-and-inspect-call-args pattern in the file. Assert on the `text` keyword argument specifically (`call_kwargs.kwargs['text']`):

```
- quote_style='scroll', text length > 120 chars
- assert: mock_create_image_quote_video.call_args.kwargs['text'] == full original text

- quote_style='cinematic', same long text (regression guard)
- from src.utils import shorten_quote_for_display
- assert: mock_create_image_quote_video.call_args.kwargs['text'] == shorten_quote_for_display(long_text, 120)
  (call with explicit 120, not config-loaded value; use the actual utility, not text[:120])
```

**`tests/test_video_processor.py` — Change 2 test:**

Verify the author y-position formula directly using computed values. `font_size = 36` is used as a test-convenience value (not the production default of 72); the formula is font-size-agnostic.

The three scroll rows are rendered at `block_top + (offset+1)*line_height` for offset in (-1, 0, 1), giving rows at offsets 0, 1, 2 from `block_top`. "Line 4" = `block_top + 3*line_height` — one slot below the bottom row.

Call `create_scroll_clips` with a patched `VideoClip`. To verify the `make_frame` closure actually uses the new y-value, patch `PIL.ImageDraw.Draw.text` and capture the `xy` argument on calls that occur at `t >= author_display_start`:

```python
font_size = 36  # test-convenience value; production default is 72
line_height = int(font_size * VideoProcessor.LINE_HEIGHT_MULT)
block_top = max(80, processor.reel_height // 6)
expected_y = block_top + 3 * line_height

# Invoke make_frame at author display time and capture draw.text xy arg
# assert: xy[1] == expected_y  (y-coordinate of the author text draw call)
assert expected_y < processor.reel_height // 2  # sanity: in top half, not center
```

## Out of Scope

- No changes to cinematic or reveal styles.
- No config changes.
- No changes to timing of author appearance (still last ~2.5 s).
- No test covering the `generate_quote_cards` → `generate_image_video_quote_card` delegation path for truncation; the fix is in the single method where truncation occurs and that is sufficient.
