---
title: Flyer-Ajuda Scroll Video — Ajuda10–14
date: 2026-04-09
---

## Goal

Generate a single Instagram Reel: a scroll-style quote card using 5 background photos from the Ajuda series, a random accepted quote from *Light on Life* by B.K.S. Iyengar, auto-picked background music, and the Ajuda Public Garden class-info slide appended at the end.

## Command

```bash
python3 main.py generate-quote-cards \
  -i assets/01-ajuda/Ajuda10.png \
  -i assets/01-ajuda/Ajuda11.png \
  -i assets/01-ajuda/Ajuda12.png \
  -i assets/01-ajuda/Ajuda13.png \
  -i assets/01-ajuda/Ajuda14.png \
  --quote-style scroll \
  --group Iyengar-LightOnLife \
  --flyer-ajuda
```

## Parameters

| Parameter | Value |
|-----------|-------|
| Images | Ajuda10.png – Ajuda14.png (5 photos, cycling equally) |
| Quote style | `scroll` (teleprompter, 3-line word-by-word) |
| Quote group | `Iyengar-LightOnLife` (random accepted quote) |
| Duration | Auto-calculated from quote length at 8 chars/second |
| Music | Auto-picked from `assets/00_music/` |
| Flyer | `--flyer-ajuda` (Ajuda Public Garden class info, 5s) |

## Output

Written to `output/quote_cards/` as an `.mp4` Reel.
