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
│   ├── feed_posts/              # Generated quote cards (before posting)
│   ├── reels/                   # Generated reels (if needed)
│   └── posted-on-social-media/ # Quote cards that have been posted
│       ├── quote_[timestamp].jpg
│       └── quote_[timestamp]_metadata.json
├── config/                      # Configuration files
│   └── settings.yaml            # Brand colors, fonts, literature groups, AI settings
└── src/                         # Source code
```

## Usage

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
- Filter by status (approved/pending), type, score, or search text
- Approve/reject quotes with one click
- Edit quote text inline
- Add notes to quotes
- See real-time statistics

**How to use:**
1. Click on a literature group card
2. Review quotes (sorted by importance score)
3. Click "Approve" or "Reject" for each quote
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
- Set `"approved": true` for quotes you want to use
- Edit `"text"` if you want to refine the quote wording
- Add `"notes"` for your own reference
- Remove quotes you don't want to use

**Tip**: This is a one-time effort per year. Once approved, quotes can be reused for quote card generation.

### 4. Generate Quote Cards

Generate quote cards from approved quotes:

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

Check available quotes and groups:

```bash
# View configuration
python3 main.py config

# Test quote generator
python3 -m src.quote_generator
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
   - Edit JSON files in `assets/10_knowledge/[group]/quotes.json`
   - Set `approved: true` for quotes to use

3. **Generate** (As needed):
   ```bash
   python3 generate_quote_card.py
   ```

4. **Post & Track** (After each post):
   - Post quote card to social media
   - Move files to `output/posted-on-social-media/`
   - System automatically prevents duplicate usage

## Configuration

Edit `config/settings.yaml` to customize:

- **Brand colors and fonts**: Update colors and fonts for quote cards
- **Literature groups**: Add or modify literature groups
- **AI settings**: Configure AI provider, model, and language
- **Quote extraction settings**: Configure intelligent extraction parameters

**Example Configuration:**
```yaml
brand:
  name: Yoga Content Generator
  colors:
    primary: '#2c5530'
    secondary: '#4a7c59'
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

literature_groups:
- name: BhagavadGita
  display_name: Bhagavad Gita
  author: Eknath Easwaran
  source_path: assets/10_knowledge/BhagavadGita

ai:
  provider: openai
  model: gpt-4
  language: en
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
