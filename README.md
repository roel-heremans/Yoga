# Yoga Quote Card Generator

Automated quote card generator for yoga content, extracting meaningful quotes, statements, and wisdom from yoga literature and creating beautiful quote cards for social media.

## Features

- **AI-Powered Quote Extraction**: Intelligently extract quotes, statements, slogans, and interesting facts from yoga literature using AI/LLM
- **Intelligent Agent-Based Extraction**: Advanced multi-stage agent system that:
  - Analyzes document structure and chunks documents intelligently
  - Summarizes main ideas from each chunk
  - Extracts context-aware quotes with thematic tags
  - Ranks and deduplicates quotes by quality
  - Processes entire documents (not just first 8000 characters)
- **Simple Extraction Mode**: Fast extraction for quick quote gathering
- **Literature Group Organization**: Organize quotes by source (Bhagavad Gita, Iyengar books, Upanishads, Osho, etc.)
- **Human-in-the-Loop Approval**: Review and approve extracted quotes before generating cards
- **Web-Based Quote Reviewer**: Beautiful web UI for reviewing, approving, editing, and managing quotes with filters and statistics
- **Automatic Duplicate Prevention**: Track posted quotes via metadata to avoid reusing content
- **Beautiful Quote Cards**: Generate Instagram-ready quote card images with proper attribution
- **Source Attribution**: Automatically include author/source information on quote cards

## Installation

1. Install Python 3.9 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (create `.env` file in project root):
```bash
OPENAI_API_KEY=your_api_key_here
```
   Get your OpenAI API key from: https://platform.openai.com/api-keys

## Project Structure

```
Yoga-Content-Generator/
├── assets/                      # Your content assets
│   ├── 00_music/                # Background music files (optional)
│   ├── 01_images/               # Images for content
│   ├── 02_videos/               # Videos for content
│   └── 10_knowledge/            # Yoga literature text files
│       ├── BhagavadGita/
│       │   └── *.txt            # Text files from literature
│       ├── Iyengar-LightOnYoga/
│       ├── Iyengar-LightOnLife/
│       ├── Iyengar-LightOnPranayama/
│       ├── Iyengar-LightOnYogaSutrasOfPatanjali/
│       ├── Upanishads/
│       └── Osho-LoveLettersToLife/
├── output/                      # Generated content
│   ├── feed_posts/              # Quote cards from generate_quote_card.py
│   ├── quote_cards/             # Quote cards from main.py generate-quote-cards
│   ├── reels/                   # Generated reels (if using theme-based generate)
│   └── posted-on-social-media/  # Quote cards that have been posted
│       ├── quote_[timestamp].jpg
│       └── quote_[timestamp]_metadata.json
├── config/                      # Configuration files
│   └── settings.yaml            # Brand colors, fonts, literature groups, AI settings
└── src/                         # Source code
```

## Usage

The main entry point is **`main.py`**, which provides all CLI commands:

| Command | Description |
|--------|-------------|
| `config` | Show current configuration (brand, AI, literature groups) |
| `extract-quotes` | Extract quotes from literature text files (simple or intelligent) |
| `generate-quote-cards` | Generate quote cards (white background, photo overlay, or video overlay) |
| `themes` | List available theme directories (for feed/reel content) |
| `stats` | Show statistics about themes and assets |
| `generate` | Generate a single feed post or reel (theme-based) |
| `batch-generate` | Generate multiple feed posts and reels in one run |
| `preprocess-pdfs` | Preprocess PDFs and save structured content to JSON |
| `extract-brand` | Extract brand colors and fonts from a website |

For the **yoga quote card workflow**, use: `extract-quotes` → review in Web UI or JSON → `generate-quote-cards` or `generate_quote_card.py`.

### 1. Prepare Literature Text Files

Place text files (.txt) in the appropriate literature group directories:
- `assets/10_knowledge/BhagavadGita/`
- `assets/10_knowledge/Iyengar-LightOnYoga/`
- `assets/10_knowledge/Iyengar-LightOnLife/`
- `assets/10_knowledge/Iyengar-LightOnPranayama/`
- `assets/10_knowledge/Iyengar-LightOnYogaSutrasOfPatanjali/`
- `assets/10_knowledge/Upanishads/`
- `assets/10_knowledge/Osho-LoveLettersToLife/`

**Note**: You can convert PDFs to text files using online tools like https://cloudconvert.com/pdf-to-txt

### 2. Extract Quotes from Literature

Extract quotes from your literature text files using AI. The system supports two extraction methods:

#### Simple Extraction (Default)
Fast extraction from the beginning of documents:

```bash
# Extract quotes from all literature groups (simple method)
python3 main.py extract-quotes --all --simple

# Extract quotes from a specific group
python3 main.py extract-quotes --group BhagavadGita --simple
```

#### Intelligent Agent-Based Extraction (Recommended)
Advanced extraction that processes entire documents in chunks, summarizes main ideas, and extracts context-aware quotes:

```bash
# Extract quotes using intelligent agent-based method
python3 main.py extract-quotes --all --intelligent

# Extract from specific group with intelligent method
python3 main.py extract-quotes --group BhagavadGita --intelligent

# Customize chunk size and max quotes
python3 main.py extract-quotes --group BhagavadGita --intelligent --chunk-size 6000 --max-quotes 75

# Re-extract even if JSON already exists
python3 main.py extract-quotes --all --intelligent --force
```

**Intelligent Extraction Features:**
- **Document Analysis**: Analyzes document structure (chapters, sections)
- **Smart Chunking**: Splits documents into semantic chunks with overlap
- **Main Idea Extraction**: Summarizes main ideas/themes from each chunk
- **Context-Aware Quotes**: Extracts quotes with chapter/section context
- **Quality Scoring**: Ranks quotes by importance and relevance
- **Thematic Tagging**: Automatically tags quotes with themes
- **Deduplication**: Removes similar/duplicate quotes
- **Full Document Coverage**: Processes entire documents, not just first 8000 characters

**Example Output (Intelligent Method):**
```
Using intelligent agent-based extraction method
============================================================
Processing group: BhagavadGita
============================================================
Extracting quotes from 1 file(s) in BhagavadGita...
  Using intelligent agent-based extraction...
  Processing The Bhagavad Gita.txt...
    Processing 15 chunks...
    Processed 15 chunks, extracted 87 quote candidates
  Refining quotes...
  Final quotes after refinement: 45
✓ Extracted 45 quotes total. Saved to assets/10_knowledge/BhagavadGita/quotes.json
  Method: intelligent
  Chunks processed: 15
  Main themes: yoga, practice, self, spiritual, path
```

**Simple vs Intelligent:**
- **Simple**: Fast, processes first ~8000 characters, good for quick extraction
- **Intelligent**: Slower but more thorough, processes entire document, includes context and themes

### 3. Review and Approve Quotes

After extraction, review and approve quotes. You have two options:

#### Option A: Web UI (Recommended)

Use the built-in web interface for easy quote review:

```bash
# Start the quote reviewer web UI
python3 quote_reviewer.py
```

Then open your browser to: **http://localhost:5000**

**Features:**
- Browse all literature groups with statistics
- View quotes with importance scores and themes
- Filter by status (accepted/pending/rejected), type, score, or search text
- Approve/reject quotes with one click (saved as status: accepted/rejected/pending)
- Edit quote text inline
- Add notes to quotes
- See real-time statistics

**How to use:**
1. Click on a literature group card
2. Review quotes (sorted by importance score)
3. Click "Approve" or "Reject" for each quote (status is saved as accepted/pending/rejected)
4. Click "Edit Text" to modify quote wording
5. Add notes in the notes field
6. Changes are saved automatically

#### Option B: Manual JSON Editing

Edit JSON files directly:

**File Structure (Simple Method):**
```json
{
  "source": "Bhagavad Gita",
  "author": "Eknath Easwaran",
  "extracted_at": "2024-01-15T10:00:00",
  "extraction_method": "simple",
  "quotes": [
    {
      "id": "bhagavadgita_001",
      "text": "On this path effort never goes to waste...",
      "type": "quote",
      "context": "Chapter 2, Verse 40",
      "approved": false,
      "notes": ""
    }
  ]
}
```

**File Structure (Intelligent Method):**
```json
{
  "source": "Bhagavad Gita",
  "author": "Eknath Easwaran",
  "extracted_at": "2024-01-15T10:00:00",
  "extraction_method": "intelligent",
  "document_summary": {
    "total_chunks": 15,
    "main_themes": ["yoga", "practice", "self", "spiritual", "path"],
    "chapters_detected": 18,
    "total_quotes_extracted": 87,
    "final_quotes_count": 45
  },
  "chunks": [
    {
      "chunk_id": "chunk_001",
      "position": 1,
      "main_ideas": ["Introduction to yoga practice", "Importance of discipline"],
      "context": "Chapter 1",
      "quote_count": 5
    }
  ],
  "quotes": [
    {
      "id": "chunk001_quote001",
      "text": "On this path effort never goes to waste...",
      "type": "quote",
      "context": "Chapter 1",
      "chunk_id": "chunk_001",
      "themes": ["yoga", "practice", "path"],
      "importance_score": 0.85,
      "approved": false,
      "notes": ""
    }
  ]
}
```

**Manual Editing:**
- Set `"approved": true` or `"status": "accepted"` for quotes you want to use (both are supported)
- Edit `"text"` if you want to refine the quote wording
- Add `"notes"` for your own reference
- Remove quotes you don't want to use

**Tip**: This is a one-time effort per year. Once accepted, quotes can be reused for quote card generation.

### 4. Generate Quote Cards

You can generate quote cards in two ways.

#### Option A: Main CLI (`main.py generate-quote-cards`) — recommended

Flexible generation with white background, photo overlays, or video overlays:

```bash
# White background quote card only
python3 main.py generate-quote-cards --white-background

# Quote cards overlaid on photos (from a directory)
python3 main.py generate-quote-cards --photo-dir assets/01_images/Roel --num-photos 3

# Quote cards overlaid on videos
python3 main.py generate-quote-cards --video-dir assets/02_videos --num-videos 2

# Combine options: white + photos + videos
python3 main.py generate-quote-cards --white-background --photo-dir assets/01_images/Nina --video-dir assets/02_videos --num-photos 2 --num-videos 1

# Use a specific quote by ID or literature group
python3 main.py generate-quote-cards --white-background --group BhagavadGita
python3 main.py generate-quote-cards --white-background --quote-id chunk001_quote001

# Add background music to video overlay cards (.mp3, .wav, etc.)
python3 main.py generate-quote-cards --video-dir assets/02_videos --music assets/00_music/your_track.wav

# Image-as-video quote card: single background image, 15s, quote overlay, music fades to silence, video fades to white
python3 main.py generate-quote-cards --image assets/01_images/Ajuda/photo-collage-01.png --duration 15 -m assets/00_music/your_track.wav
# Optional: --audio-fade 3 (seconds for music to fade to silence), --video-fade 2 (seconds for fade to white)

# Custom output directory
python3 main.py generate-quote-cards --white-background --output-dir output/my_cards
```

**Output:** Cards are written to `output/quote_cards/` (or `--output-dir`). The system uses **accepted** quotes (status `accepted` or legacy `approved: true`). Use `--music` / `-m` to add background music to **video** quote cards (music is mixed at 30% volume with fade-out). With **`--image`**, you get a video: one static background image for the chosen duration (default 15s), quote overlay, optional music (fading to silence over the last 3s), and the image fading to white over the last 2s.

#### How to use the generator: music, quotes, duration, and media

**Music**

| Context | Where to put music | Formats | How to choose |
|--------|---------------------|---------|----------------|
| Quote cards (video or image-video) | `assets/00_music/` | `.mp3`, `.wav`, `.m4a` | Pass a file with `--music` / `-m` (e.g. `-m assets/00_music/your_track.mp3`). For **image-video** only: if you omit `--music`, a random track from `assets/00_music/` is used. |
| Theme reels (`generate` / `batch-generate`) | Same | Same | Use `-m path/to/track.mp3` for a specific track; otherwise a random file from `assets/00_music/` is used. |

- Music is mixed at **30% volume** so it stays in the background.
- **Video overlay cards**: music fades out over the last **1.5 seconds**.
- **Image-video quote cards**: fade length is configurable with `--audio-fade` (default **3** seconds).

**Quotes**

- **Random (default):** One random **accepted** quote is used for all cards in that run (from any literature group).
- **By group:** `--group BhagavadGita` (or another group name) — only accepted quotes from that group.
- **By ID:** `--quote-id chunk001_quote001` — use that exact quote (group is optional; if given, the quote is looked up in that group).

Only quotes with `status: "accepted"` or legacy `approved: true` in the group’s `quotes.json` are used.

**Duration**

| Output type | Duration |
|-------------|----------|
| **White background / photo overlay** | N/A (single image). |
| **Video overlay** (from `--video-dir`) | Uses the **full length** of each selected source video. Music is looped if shorter than the video and faded out at the end. |
| **Image-video** (`--image`) | Set with `--duration` in **seconds** (default **15**). Optional `--flyer-ajuda` or `--flyer-palheiro` adds a second segment; its length is `--flyer-duration` (default 15s). |

**Which video and photo material to choose**

- **Photos (for overlay cards):**  
  - `--photo-dir PATH` — directory containing images (e.g. `assets/01_images/Nina`).  
  - Supported formats: **`.jpg`, `.jpeg`, `.png`** (case-insensitive).  
  - `--num-photos N` — how many cards to generate (default **1**). Files are chosen **randomly** from the directory.

- **Videos (for video overlay cards):**  
  - `--video-dir PATH` — directory containing videos (e.g. `assets/02_videos`).  
  - Supported formats: **`.mp4`, `.mov`, `.avi`** (case-insensitive).  
  - `--num-videos N` — how many cards to generate (default **1**). Files are chosen **randomly** from the directory.

- **Image(s) (for image-video quote card):**  
  - `--image PATH` (or `-i`) — one or more image files; repeat for multiple (e.g. `-i img1.png -i img2.png -i img3.png`). Creates a video of total length `--duration` with the **duration split equally across all images**, same quote overlay on the whole segment, optional music, and fade to white (and optional flyer with `--flyer-ajuda` or `--flyer-palheiro`).

**Optional: yoga flyer (image-video only)**

- `--flyer-ajuda` — after the quote segment, add a **white slide** with Ajuda Public Garden class info (Sundays 11h15–12h45, contact).
- `--flyer-palheiro` — same, but with Casa Velha do Palheiro class info (Wednesdays 18h00–19h00, contact). Use only one of `--flyer-ajuda` or `--flyer-palheiro`.
- `--flyer-line1`, `--flyer-line2` — custom text (override when using a flyer preset).
- `--flyer-duration` — length of the flyer segment in seconds (default **15**).
- `--flyer-font-size` — font size for flyer text (default **46**).

#### Option B: Standalone script (`generate_quote_card.py`)

Quick single white-background card from a random approved quote:

```bash
# Generate a random quote card from approved, unused quotes
python3 generate_quote_card.py

# Generate a quote card with a custom quote
python3 generate_quote_card.py "Your custom quote text here"
```

**Output:**
- Quote card image: `output/feed_posts/quote_[timestamp].jpg`
- Ready for posting on social media

**Example:**
```
Available literature groups:
  1. BhagavadGita: 25 approved quotes
  2. Iyengar-LightOnYoga: 18 approved quotes

Selected quote:
  Text: On this path effort never goes to waste...
  Source: Bhagavad Gita
  Author: Eknath Easwaran
  ID: bhagavadgita_001

Generating quote card...
✓ Quote card created: output/feed_posts/quote_20240115_120000.jpg

Ready to post on social media!
```

### 5. Track Posted Quotes

After posting a quote card to social media:

1. Move the generated files to `output/posted-on-social-media/`:
   ```bash
   mv output/feed_posts/quote_20240115_120000.jpg output/posted-on-social-media/
   mv output/feed_posts/quote_20240115_120000_metadata.json output/posted-on-social-media/
   ```

2. The system automatically checks this folder to avoid reusing posted quotes

**Metadata File Structure:**
```json
{
  "quote_id": "bhagavadgita_001",
  "quote": "On this path effort never goes to waste...",
  "quote_source": "Bhagavad Gita",
  "quote_author": "Eknath Easwaran",
  "generated_at": "2024-01-15T12:00:00"
}
```

### 6. View Statistics

Check configuration and available content:

```bash
# View configuration (brand, AI, literature groups)
python3 main.py config

# List theme directories (for feed/reel content)
python3 main.py themes

# Show stats for themes and assets
python3 main.py stats
```

## Workflow Summary

1. **Extract** (One-time per year):
   ```bash
   # Intelligent extraction (recommended)
   python3 main.py extract-quotes --all --intelligent
   
   # Or simple extraction for faster results
   python3 main.py extract-quotes --all --simple
   ```

2. **Review & Approve** (One-time per year):
   - Use the web UI: `PORT=5001 python3 quote_reviewer.py` → http://localhost:5000  
   - Or edit JSON in `assets/10_knowledge/[group]/quotes.json`: set `"approved": true` or `"status": "accepted"` for quotes to use

3. **Generate** (As needed):
   ```bash
   # Full options: white background, photo overlay, video overlay
   python3 main.py generate-quote-cards --white-background
   
   # Or quick single card
   python3 generate_quote_card.py
   ```

4. **Post & Track** (After each post):
   - Post quote card to social media
   - Move files to `output/posted-on-social-media/` (or keep metadata in `output/quote_cards/` for main CLI)
   - System automatically prevents duplicate usage

### Theme-based feed posts and reels (optional)

If you use theme directories (e.g. `04_theme_name`, `05_theme_name` in `assets/`) with images, videos, and PDFs:

```bash
# List themes
python3 main.py themes

# Generate a single feed post or reel
python3 main.py generate -t 05_kombucha_benefits -T feed
python3 main.py generate -t 05_kombucha_benefits -T reel --combined --use-quote

# Batch generate feed posts and reels
python3 main.py batch-generate --feeds 3 --reels 3

# Preprocess PDFs in theme folders to JSON
python3 main.py preprocess-pdfs --all
```

**Choosing media and music for theme-based generation:**

- **Feed post:** use `-i path/to/image.jpg` to force a specific image; otherwise one is picked from the theme folder.
- **Reel:** use `-v video1.mp4 -v video2.mp4` to set specific videos; use `-m path/to/track.mp3` to set background music. Without `-m`, a random track from `assets/00_music/` is used. Reel duration is constrained by `config/settings.yaml` under `instagram.reel_duration` (default min 15s, max 90s).

## Configuration

Edit `config/settings.yaml` to customize:

- **Brand colors and fonts**: Update colors and fonts for quote cards
- **Literature groups**: Add or modify literature groups
- **AI settings**: Configure AI provider, model, and language
- **Quote extraction settings**: Configure intelligent extraction parameters (chunk size, max quotes, priority concepts)
- **Instagram dimensions**: Feed and reel dimensions, reel duration

**Example Configuration:**
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
  method: intelligent  # 'simple' or 'intelligent'
  chunk_size: 5000  # Characters per chunk
  chunk_overlap: 500  # Overlap between chunks
  max_quotes_per_chunk: 10
  max_total_quotes: 100
  min_quote_length: 20
  max_quote_length: 500
  enable_summarization: true
  enable_thematic_tagging: true
  priority_concepts: [sattva, rajas, tamas, asana, pranayama, ...]  # Optional yoga concepts to prioritize

literature_groups:
- name: BhagavadGita
  display_name: Bhagavad Gita
  author: Eknath Easwaran
  source_path: assets/10_knowledge/BhagavadGita

ai:
  provider: openai
  model: gpt-4
  language: en

instagram:
  feed_dimensions: { width: 1080, height: 1080 }
  reel_dimensions: { width: 1080, height: 1920 }
  reel_duration: { min: 15, max: 90 }
```

## Quote Extraction Details

The AI extraction process identifies:
- **Inspirational quotes**: Motivating and uplifting statements
- **Philosophical statements**: Deep wisdom and insights
- **Practical wisdom**: Actionable guidance
- **Interesting facts**: Educational content about yoga
- **Slogans**: Memorable phrases

Each extracted quote includes:
- Unique ID for tracking
- Quote text
- Type (quote, statement, slogan, fact)
- Context (chapter, verse, page, etc.)
- Approval status (for human review)

## Troubleshooting

**Q: No quotes extracted**
- A: Check that text files exist in the literature group directories
- A: Verify OPENAI_API_KEY is set correctly
- A: Check that text files contain sufficient content (>100 characters)

**Q: All quotes have been posted**
- A: Extract more quotes: `python3 main.py extract-quotes --all --force`
- A: Approve more quotes in the JSON files
- A: Add new literature sources

**Q: Quote cards don't show attribution**
- A: Ensure quotes have `author` or `source` in the JSON metadata
- A: Check that literature groups are configured in `config/settings.yaml`

**Q: Quotes are being reused**
- A: Make sure you move files to `output/posted-on-social-media/` after posting
- A: Verify metadata files include `quote_id` field

**Q: Intelligent extraction is slow**
- A: This is expected - it processes entire documents in chunks. Use `--simple` flag for faster extraction
- A: Reduce `chunk_size` in config to process smaller chunks faster
- A: Reduce `max_total_quotes` to limit processing time

**Q: How do I choose between simple and intelligent extraction?**
- A: Use **simple** for quick extraction from short documents or when you need quotes fast
- A: Use **intelligent** for thorough extraction from long documents, when you need context and themes, or for better quality quotes

## Best Practices

- **Extract Once**: Run extraction annually or when adding new literature
- **Review Carefully**: Take time to approve high-quality quotes
- **Track Posts**: Always move posted content to `posted-on-social-media/` folder
- **Backup JSON**: Keep backups of your approved quotes JSON files
- **Version Control**: Consider tracking JSON files in git for quote history

## License

Private project for yoga content generation.
