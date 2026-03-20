# Yoga Quote Card Generator

Automated quote card generator for yoga content, extracting meaningful quotes, statements, and wisdom from yoga literature and creating beautiful quote cards for social media.

## Features

- **AI-Powered Quote Extraction**: Intelligently extract quotes, statements, slogans, and interesting facts from yoga literature using Anthropic Claude
- **Intelligent Agent-Based Extraction**: Advanced multi-stage system that:
  - Analyzes document structure and chunks documents intelligently
  - Summarizes main ideas from each chunk
  - Extracts context-aware quotes with thematic tags
  - Ranks and deduplicates quotes by quality
  - Filters dangling-pronoun quotes (e.g. "It is..." without context) to ensure self-contained quotes
  - Processes entire documents (not just first 8000 characters)
- **Simple Extraction Mode**: Fast extraction for quick quote gathering
- **Literature Group Organization**: Organize quotes by source (Bhagavad Gita, Iyengar books, Upanishads, Osho, etc.)
- **Human-in-the-Loop Approval**: Review and approve extracted quotes before generating cards
- **Web-Based Quote Reviewer**: Beautiful web UI for reviewing, approving, editing, and managing quotes with filters and statistics
- **Published Quote Tracking**: Mark quotes as published after posting — they are automatically excluded from future generation
- **Published Image Tracking**: Track which images were used in published posts — warns on reuse and silently excludes them from random `--photo-dir` selection
- **Beautiful Quote Cards**: Generate Instagram-ready quote card images and videos with proper attribution
- **Multiple Visual Styles**: `cinematic` (centered, cream/gold on dark scrim) and `reveal` (line-by-line fade-in) styles

## Installation

1. Install Python 3.9 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (create `.env` file in project root):
```bash
ANTHROPIC_API_KEY=your_api_key_here
```
   Get your Anthropic API key from: https://console.anthropic.com/

## Project Structure

```
Yoga-Content-Generator/
├── assets/                      # Your content assets
│   ├── 00_music/                # Background music files (.mp3, .wav, .m4a)
│   ├── 01-ajuda/                # Photos for Ajuda quote cards
│   ├── 10_knowledge/            # Yoga literature text files
│   │   ├── BhagavadGita/
│   │   │   ├── *.txt            # Text files from literature
│   │   │   └── quotes.json      # Extracted + reviewed quotes
│   │   ├── Iyengar-LightOnYoga/
│   │   ├── Iyengar-LightOnLife/
│   │   ├── Iyengar-LightOnPranayama/
│   │   ├── Iyengar-LightOnYogaSutrasOfPatanjali/
│   │   ├── Upanishads/
│   │   └── Osho-LoveLettersToLife/
├── output/                      # Generated content
│   ├── quote_cards/             # Generated quote cards and videos
│   └── published/               # Videos you have posted to Instagram
│       └── .published_log.json  # Auto-generated tracking log
├── config/
│   └── settings.yaml            # Brand colors, fonts, literature groups, AI settings
└── src/                         # Source code
```

## Usage

The main entry point is **`main.py`**, which provides all CLI commands:

| Command | Description |
|---------|-------------|
| `extract-quotes` | Extract quotes from literature text files (simple or intelligent) |
| `generate-quote-cards` | Generate quote cards (white background, photo overlay, video overlay, or image-video) |
| `mark-published` | Scan `output/published/`, mark matched quotes as published, log images used |
| `config` | Show current configuration (brand, AI, literature groups) |
| `themes` | List available theme directories (for feed/reel content) |
| `stats` | Show statistics about themes and assets |
| `generate` | Generate a single feed post or reel (theme-based) |
| `batch-generate` | Generate multiple feed posts and reels in one run |
| `preprocess-pdfs` | Preprocess PDFs and save structured content to JSON |
| `extract-brand` | Extract brand colors and fonts from a website |

---

## Core Workflow

```
1. Extract quotes from literature  →  extract-quotes
2. Review & approve quotes         →  quote_reviewer.py  (web UI)
3. Generate a video/card           →  generate-quote-cards
4. Post to Instagram
5. Drag video into output/published/
6. Register it                     →  mark-published
   └─ quote marked published (excluded from future generation)
   └─ images logged (excluded from future --photo-dir picks)
```

---

### Step 1. Prepare Literature Text Files

Place text files (`.txt`) in the appropriate literature group directories:
- `assets/10_knowledge/BhagavadGita/`
- `assets/10_knowledge/Iyengar-LightOnYoga/`
- `assets/10_knowledge/Iyengar-LightOnLife/`
- `assets/10_knowledge/Iyengar-LightOnPranayama/`
- `assets/10_knowledge/Iyengar-LightOnYogaSutrasOfPatanjali/`
- `assets/10_knowledge/Upanishads/`
- `assets/10_knowledge/Osho-LoveLettersToLife/`

**Tip:** Convert PDFs to text with tools like https://cloudconvert.com/pdf-to-txt

---

### Step 2. Extract Quotes from Literature

#### Simple Extraction (Fast)
Processes the first ~8000 characters of each document:

```bash
python3 main.py extract-quotes --all --simple
python3 main.py extract-quotes --group BhagavadGita --simple
```

#### Intelligent Extraction (Recommended)
Processes the entire document in chunks, resolves dangling pronouns, and scores by quality:

```bash
python3 main.py extract-quotes --all --intelligent
python3 main.py extract-quotes --group BhagavadGita --intelligent

# Re-extract even if quotes.json already exists
python3 main.py extract-quotes --group Iyengar-LightOnLife --intelligent --force

# Tune chunk size and quote limit
python3 main.py extract-quotes --group BhagavadGita --intelligent --chunk-size 6000 --max-quotes 75
```

**Intelligent extraction features:**
- Full document coverage (not just first 8000 chars)
- Smart chunking with overlap to preserve context
- Resolves dangling-pronoun references ("It is…", "They are…") — only self-contained quotes are kept
- Quality scoring and deduplication
- Thematic tagging

---

### Step 3. Review and Approve Quotes

#### Option A: Web UI (Recommended)

```bash
python3 quote_reviewer.py
```

Open: **http://localhost:5000**

- Browse groups with statistics
- Filter by status, type, importance score, or text search
- Approve / reject / edit quotes with one click
- Changes are saved automatically to `quotes.json`

#### Option B: Edit JSON directly

Set `"status": "accepted"` (or legacy `"approved": true`) on quotes you want to use:

```json
{
  "id": "chunk001_quote002",
  "text": "Yoga is the art, science and philosophy of life.",
  "status": "accepted"
}
```

Only quotes with `status: "accepted"` are used during generation.

---

### Step 4. Generate Quote Cards

#### Image-video quote card (most common for Instagram Reels)

A static background image rendered as a video with quote overlay, optional music, and fade to white:

```bash
# Single image, 15s, auto-picks music from assets/00_music/
python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg --duration 15

# Multiple images: 30s split equally across 3 images (10s each)
python3 main.py generate-quote-cards -i img1.jpg -i img2.jpg -i img3.jpg --duration 30

# Explicit music track
python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg --duration 15 -m assets/00_music/track.mp3

# With Ajuda flyer: quote 15s → fade → flyer slide 15s → fade
python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg --duration 15 -m assets/00_music/track.mp3 --flyer-ajuda

# With Palheiro flyer
python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg --duration 15 -m assets/00_music/track.mp3 --flyer-palheiro
```

#### White background quote card

```bash
python3 main.py generate-quote-cards --white-background
```

#### Photo overlay cards

```bash
python3 main.py generate-quote-cards --photo-dir assets/01-ajuda --num-photos 3
```

Photos in `output/published/.published_log.json` are **silently excluded** from random selection — you will never accidentally reuse a photo that appeared in a published post.

#### Video overlay cards

```bash
python3 main.py generate-quote-cards --video-dir assets/02_videos --num-videos 2
```

#### Combine output types

```bash
python3 main.py generate-quote-cards --white-background --photo-dir assets/01-ajuda --num-photos 2
```

#### Select a specific quote or group

```bash
# All accepted quotes from one literature group
python3 main.py generate-quote-cards -i photo.jpg --group BhagavadGita

# One specific quote by ID
python3 main.py generate-quote-cards -i photo.jpg --quote-id chunk001_quote002
```

#### Visual styles (`--quote-style`)

| Style | Description |
|-------|-------------|
| `cinematic` (default) | Centered cream italic quote, gold author line, gold divider, radial vignette |
| `reveal` | Lines fade in one by one |

```bash
python3 main.py generate-quote-cards -i photo.jpg --quote-style reveal
```

#### All `generate-quote-cards` options

| Option | Default | Description |
|--------|---------|-------------|
| `-i / --image PATH` | — | Image(s) for image-video card; repeat for multiple |
| `--duration N` | 15 | Video duration in seconds (split equally across images) |
| `-m / --music PATH` | auto | Music file; omit to auto-pick from `assets/00_music/` |
| `--audio-fade N` | 3 | Seconds for music to fade out at end |
| `--video-fade N` | 0.8 | Seconds for image to fade to white at end |
| `--photo-dir DIR` | — | Directory of photos for overlay cards |
| `--num-photos N` | 1 | How many photo overlay cards to generate |
| `--video-dir DIR` | — | Directory of videos for video overlay cards |
| `--num-videos N` | 1 | How many video overlay cards to generate |
| `--white-background` | off | Also generate a white-background card |
| `-g / --group NAME` | random | Use only quotes from this literature group |
| `--quote-id ID` | random | Use this specific quote |
| `--output-dir DIR` | `output/quote_cards/` | Where to write output files |
| `--quote-style` | `cinematic` | Visual style: `cinematic` or `reveal` |
| `--flyer-ajuda` | off | Append Ajuda Public Garden class info slide |
| `--flyer-palheiro` | off | Append Casa Velha do Palheiro class info slide |
| `--flyer-line1 TEXT` | preset | Override first line of flyer |
| `--flyer-line2 TEXT` | preset | Override second line of flyer |
| `--flyer-duration N` | 15 | Flyer segment duration in seconds |
| `--flyer-font-size N` | 40 | Font size for flyer body text |

**Published-image warning:** If you pass `-i` with an image that was previously used in a published post, the system prints a warning before generating (generation still proceeds).

---

### Step 5. Post to Instagram, then Register as Published

After posting a video to Instagram:

1. **Drag the `.mp4`** from `output/quote_cards/` into `output/published/`

2. **Run `mark-published`:**

```bash
python3 main.py mark-published
```

This will:
- Scan `output/published/` for new video files
- Look up which quote and images each video used (from the metadata recorded at generation time)
- Set the quote's status to `"published"` in `quotes.json` — it will **never be selected again**
- Record the images used in `output/published/.published_log.json`
- Print a summary of what was processed

**Example output:**
```
✓ Marked 1 video(s) as published:
  - quote_image_video_20260320_161015.mp4

Total unique images used across all published posts: 4
```

**What happens automatically after this:**
- The published quote is excluded from all future `generate-quote-cards` runs
- Any image from the log is silently excluded when using `--photo-dir` random selection
- Using `-i` with a published image prints a warning (but does not block generation)

**Custom published folder:**
```bash
python3 main.py mark-published --published-dir /path/to/other/folder
```

---

### Step 6. Utility Commands

```bash
# Show current configuration (brand, AI provider, literature groups)
python3 main.py config

# List theme directories
python3 main.py themes

# Show asset and theme statistics
python3 main.py stats
```

---

## Theme-Based Feed Posts and Reels (Optional)

If you use theme directories (e.g. `04_theme_name`, `05_theme_name` in `assets/`) with images, videos, and PDFs:

```bash
# List available themes
python3 main.py themes

# Generate a single feed post
python3 main.py generate -t 05_kombucha_benefits -T feed

# Generate a reel
python3 main.py generate -t 05_kombucha_benefits -T reel --combined --use-quote

# Batch generate
python3 main.py batch-generate --feeds 3 --reels 3

# Preprocess PDFs to JSON for use in themes
python3 main.py preprocess-pdfs --all
```

- Feed posts: use `-i path/to/image.jpg` to force a specific image; otherwise one is picked from the theme folder.
- Reels: use `-v video.mp4` for specific videos; `-m track.mp3` for music. Without `-m`, a random track from `assets/00_music/` is used.

---

## Configuration

Edit `config/settings.yaml` to customize:

```yaml
brand:
  name: Yoga Content Generator
  colors:
    primary: '#2c5530'
    secondary: '#4a7c59'
    accent: '#8fbc8f'
    text: '#2c2c2c'
    background: '#ffffff'
  fonts:
    heading: Arial
    body: Arial

quote_extraction:
  method: intelligent        # 'simple' or 'intelligent'
  chunk_size: 5000           # Characters per chunk
  chunk_overlap: 500
  max_quotes_per_chunk: 10
  max_total_quotes: 100
  min_quote_length: 20
  max_quote_length: 500
  enable_summarization: true
  enable_thematic_tagging: true

literature_groups:
  - name: BhagavadGita
    display_name: Bhagavad Gita
    author: Eknath Easwaran
    source_path: assets/10_knowledge/BhagavadGita

ai:
  provider: anthropic
  model: claude-sonnet-4-6
  language: en

instagram:
  feed_dimensions: { width: 1080, height: 1080 }
  reel_dimensions: { width: 1080, height: 1920 }
  reel_duration: { min: 15, max: 90 }
```

---

## Troubleshooting

**Q: No quotes extracted**
- Check that `.txt` files exist in the literature group directories
- Verify `ANTHROPIC_API_KEY` is set correctly in `.env`
- Check that text files contain sufficient content (>100 characters)

**Q: All accepted quotes have been used up**
- Re-extract: `python3 main.py extract-quotes --all --intelligent --force`
- Approve more quotes in the web UI or JSON files
- Add new literature source directories

**Q: `mark-published` says "no new files found"**
- Make sure you dragged `.mp4` files (not other formats) into `output/published/`
- Files already in the log are skipped on subsequent runs (that's expected)

**Q: `mark-published` reports a video as "unmatched"**
- The video was not generated by this system, or was generated before `images_used` tracking was added (commit `fd1879b`). The quote will not be marked — you can set it manually in `quotes.json`.

**Q: Intelligent extraction is slow**
- Expected — it processes entire documents. Use `--simple` for faster results
- Reduce `chunk_size` or `max_total_quotes` in `config/settings.yaml`

**Q: Quote cards don't show attribution**
- Ensure quotes have `author` or `source` in the JSON metadata
- Check that literature groups are configured in `config/settings.yaml`

---

## Best Practices

- **Extract once per literature source** — re-run with `--force` only when you add new text files or want fresher results
- **Review carefully** — the web UI makes this fast; quality quotes make better cards
- **Always run `mark-published` after posting** — this keeps your quote and image pools fresh and prevents repetition
- **Keep `output/published/` in sync** — the log is the source of truth for what has been published

---

## License

Private project for yoga content generation.
