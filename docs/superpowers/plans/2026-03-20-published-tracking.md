# Published Media Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a generated video is moved to `output/published/`, running `python3 main.py mark-published` marks the quote as `published` (excluded from future generation) and records which images were used (warns if they're specified again).

**Architecture:** Add an `images_used` field to `generated_cards` metadata at generation time so we know which photos went into each video. A new `PublishedTracker` module scans the `output/published/` folder, matches filenames back to quotes via `generated_cards`, marks matched quotes as `published`, and maintains a log file. Quote loading already uses a `get_quote_status()` gate — we add `published` as an excluded status there. A new CLI command `mark-published` orchestrates the scan. The `generate-quote-cards` command gains an image-already-published warning.

**Tech Stack:** Python 3, Click (CLI), JSON (quotes.json + published log), pytest

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/published_tracker.py` | **Create** | Scan published folder, look up quotes by filename, mark as published, load/save log |
| `tests/test_published_tracker.py` | **Create** | Tests for all PublishedTracker functions |
| `src/quote_card_generator.py` | **Modify** | Record `images_used` in generated_cards; exclude `published` quotes from `load_accepted_quotes` |
| `tests/test_quote_card_generator.py` | **Modify** | Tests for `published` status exclusion and `images_used` recording |
| `main.py` | **Modify** | Add `mark-published` CLI command; add published-image warning in `generate-quote-cards` |
| `output/published/` | **Create (folder)** | Destination folder the user drags published videos into |

---

## Published Log Format

The log lives at `output/published/.published_log.json` and is keyed by filename (not full path, since the file moves):

```json
{
  "quote_image_video_20260320_161015.mp4": {
    "quote_id": "chunk001_quote002",
    "quote_group": "Iyengar-LightOnLife",
    "images_used": [
      "assets/01-ajuda/Yoga_Funchal21.jpg",
      "assets/01-ajuda/Yoga_Funchal10.jpg"
    ],
    "marked_at": "2026-03-20T16:30:00.000000"
  }
}
```

---

## Task 1: Record `images_used` in generated card metadata

**Files:**
- Modify: `src/quote_card_generator.py` (methods `_append_generated_cards_to_quote` and `generate_quote_cards`)
- Modify: `tests/test_quote_card_generator.py`

- [ ] **Step 1.1: Write the failing test**

Add this test to `tests/test_quote_card_generator.py`:

```python
def test_append_generated_cards_records_images_used(tmp_path):
    """images_used list is stored in generated_cards entry when provided."""
    # Set up a minimal quotes.json
    knowledge_dir = tmp_path / "assets" / "10_knowledge"
    group_dir = knowledge_dir / "TestGroup"
    group_dir.mkdir(parents=True)
    quotes_file = group_dir / "quotes.json"
    quotes_file.write_text(json.dumps({
        "source": "Test",
        "author": "Tester",
        "quotes": [{"id": "q001", "text": "Test quote", "status": "accepted"}]
    }))

    generator = QuoteCardGenerator.__new__(QuoteCardGenerator)
    generator.knowledge_dir = knowledge_dir
    generator.assets_base_path = tmp_path / "assets"

    quote = {"id": "q001", "group": "TestGroup"}
    results = {"image_videos": [tmp_path / "out.mp4"]}
    images_used = ["assets/01-ajuda/Yoga_Funchal21.jpg", "assets/01-ajuda/Yoga_Funchal10.jpg"]

    generator._append_generated_cards_to_quote(quote, results, images_used=images_used)

    data = json.loads(quotes_file.read_text())
    card = data["quotes"][0]["generated_cards"][0]
    assert card["images_used"] == images_used
```

- [ ] **Step 1.2: Run the test to verify it fails**

```bash
cd /Users/roel.heremans/Documents/PersonalRepos/Yoga
python -m pytest tests/test_quote_card_generator.py::test_append_generated_cards_records_images_used -v
```

Expected: `FAILED` — `TypeError: _append_generated_cards_to_quote() got an unexpected keyword argument 'images_used'`

- [ ] **Step 1.3: Implement — add `images_used` parameter to `_append_generated_cards_to_quote`**

In `src/quote_card_generator.py`, modify the method signature and the `new_entries` loop:

```python
def _append_generated_cards_to_quote(
    self,
    quote: Dict,
    results: Dict[str, List[Path]],
    created_at: Optional[str] = None,
    images_used: Optional[List[str]] = None,
) -> None:
    ...
    for card_type, paths in results.items():
        if not paths:
            continue
        for p in paths:
            path_obj = Path(p)
            try:
                rel = path_obj.relative_to(repo_root)
            except ValueError:
                rel = path_obj
            entry = {
                'type': card_type,
                'path': str(rel).replace('\\', '/'),
                'created_at': created_at,
            }
            if images_used:
                entry['images_used'] = images_used
            new_entries.append(entry)
```

- [ ] **Step 1.4: Pass `images_used` from `generate_quote_cards`**

In `src/quote_card_generator.py`, find the call to `_append_generated_cards_to_quote` near line 595 (end of `generate_quote_cards`). At that point in the method, `image_paths` is the parameter received by `generate_quote_cards` — it may be `None` or a list of `Path` objects (the caller in `main.py` already wraps them as `[Path(p) for p in image]`). Replace the existing call:

```python
if quote.get('group') and quote.get('id'):
    self._append_generated_cards_to_quote(
        quote,
        results,
        created_at=datetime.now().isoformat(),
    )
```

with:

```python
if quote.get('group') and quote.get('id'):
    images_used_rel = None
    if image_paths:
        repo_root = self.assets_base_path.parent
        images_used_rel = []
        for p in image_paths:
            try:
                images_used_rel.append(str(Path(p).relative_to(repo_root)).replace('\\', '/'))
            except ValueError:
                images_used_rel.append(str(p))
    self._append_generated_cards_to_quote(
        quote,
        results,
        created_at=datetime.now().isoformat(),
        images_used=images_used_rel,
    )
```

- [ ] **Step 1.5: Run the test to verify it passes**

```bash
python -m pytest tests/test_quote_card_generator.py::test_append_generated_cards_records_images_used -v
```

Expected: `PASSED`

- [ ] **Step 1.6: Commit**

```bash
git add src/quote_card_generator.py tests/test_quote_card_generator.py
git commit -m "feat: record images_used in generated_cards metadata"
```

---

## Task 2: Exclude `published` quotes from `load_accepted_quotes`

**Files:**
- Modify: `src/quote_card_generator.py` (methods `get_quote_status` and `load_accepted_quotes`)
- Modify: `tests/test_quote_card_generator.py`

- [ ] **Step 2.1: Write the failing test**

Add to `tests/test_quote_card_generator.py`:

```python
def test_published_quote_excluded_from_accepted(tmp_path):
    """Quotes with status 'published' are not returned by load_accepted_quotes."""
    knowledge_dir = tmp_path / "assets" / "10_knowledge"
    group_dir = knowledge_dir / "TestGroup"
    group_dir.mkdir(parents=True)
    (group_dir / "quotes.json").write_text(json.dumps({
        "source": "Test", "author": "Tester",
        "quotes": [
            {"id": "q001", "text": "Accepted quote", "status": "accepted"},
            {"id": "q002", "text": "Published quote", "status": "published"},
            {"id": "q003", "text": "Pending quote", "status": "pending"},
        ]
    }))

    generator = QuoteCardGenerator.__new__(QuoteCardGenerator)
    generator.knowledge_dir = knowledge_dir

    quotes = generator.load_accepted_quotes()
    ids = [q["id"] for q in quotes]
    assert "q001" in ids
    assert "q002" not in ids   # published must be excluded
    assert "q003" not in ids


def test_get_quote_status_published():
    """get_quote_status returns 'published' for quotes with status='published'."""
    generator = QuoteCardGenerator.__new__(QuoteCardGenerator)
    assert generator.get_quote_status({"status": "published"}) == "published"
```

- [ ] **Step 2.2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_quote_card_generator.py::test_published_quote_excluded_from_accepted tests/test_quote_card_generator.py::test_get_quote_status_published -v
```

Expected: `FAILED` — `get_quote_status` doesn't handle `published`, and `load_accepted_quotes` doesn't know to exclude it.

- [ ] **Step 2.3: Implement — update `get_quote_status`**

In `src/quote_card_generator.py`, change the valid status list in `get_quote_status`:

```python
def get_quote_status(self, quote: Dict) -> str:
    """Get quote status: pending, accepted, rejected, or published."""
    if 'status' in quote:
        status = quote['status'].lower()
        if status in ['pending', 'accepted', 'rejected', 'published']:
            return status
    # Legacy support: convert approved boolean to status
    if quote.get('approved', False):
        return 'accepted'
    return 'pending'
```

- [ ] **Step 2.4: Implement — update `load_accepted_quotes`**

`load_accepted_quotes` already filters with `if self.get_quote_status(quote) == 'accepted'` — since `published` now returns a different string, published quotes are automatically excluded. No code change needed in the filter itself, only in `get_quote_status`. Verify by running tests.

- [ ] **Step 2.5: Run the tests to verify they pass**

```bash
python -m pytest tests/test_quote_card_generator.py::test_published_quote_excluded_from_accepted tests/test_quote_card_generator.py::test_get_quote_status_published -v
```

Expected: `PASSED`

- [ ] **Step 2.6: Commit**

```bash
git add src/quote_card_generator.py tests/test_quote_card_generator.py
git commit -m "feat: exclude published quotes from accepted quote selection"
```

---

## Task 3: Create `src/published_tracker.py`

This module handles everything related to the published folder: loading/saving the log, finding which quotes correspond to published video filenames, and marking quotes as published.

**Files:**
- Create: `src/published_tracker.py`
- Create: `tests/test_published_tracker.py`

- [ ] **Step 3.1: Write failing tests**

Create `tests/test_published_tracker.py`:

```python
import json
import pytest
from pathlib import Path
from src.published_tracker import (
    load_published_log,
    save_published_log,
    scan_for_new_files,
    find_quote_for_file,
    mark_quote_as_published,
    get_all_published_images,
)


# ── load / save log ───────────────────────────────────────────────────────────

def test_load_published_log_missing_file(tmp_path):
    """Returns empty dict when log file does not exist."""
    result = load_published_log(tmp_path / ".published_log.json")
    assert result == {}


def test_save_and_load_published_log(tmp_path):
    """Round-trips the log dict through JSON."""
    log_path = tmp_path / ".published_log.json"
    log = {"video.mp4": {"quote_id": "q001", "quote_group": "G", "images_used": [], "marked_at": "2026-01-01"}}
    save_published_log(log_path, log)
    assert load_published_log(log_path) == log


# ── scan_for_new_files ────────────────────────────────────────────────────────

def test_scan_for_new_files_finds_mp4(tmp_path):
    """Returns filenames of .mp4 files not already in the log."""
    published_dir = tmp_path / "published"
    published_dir.mkdir()
    (published_dir / "new_video.mp4").touch()
    (published_dir / "old_video.mp4").touch()

    log = {"old_video.mp4": {"quote_id": "q001", "quote_group": "G", "images_used": [], "marked_at": "x"}}
    result = scan_for_new_files(published_dir, log)
    assert result == ["new_video.mp4"]


def test_scan_for_new_files_empty_folder(tmp_path):
    published_dir = tmp_path / "published"
    published_dir.mkdir()
    assert scan_for_new_files(published_dir, {}) == []


def test_scan_for_new_files_skips_non_video(tmp_path):
    """Ignores .json, .txt, hidden files etc."""
    published_dir = tmp_path / "published"
    published_dir.mkdir()
    (published_dir / ".published_log.json").touch()
    (published_dir / "readme.txt").touch()
    (published_dir / "video.mp4").touch()
    result = scan_for_new_files(published_dir, {})
    assert result == ["video.mp4"]


# ── find_quote_for_file ───────────────────────────────────────────────────────

def test_find_quote_for_file_match(tmp_path):
    """Finds quote whose generated_cards path matches the given filename."""
    knowledge_dir = tmp_path / "knowledge"
    group_dir = knowledge_dir / "TestGroup"
    group_dir.mkdir(parents=True)
    (group_dir / "quotes.json").write_text(json.dumps({
        "source": "S", "author": "A",
        "quotes": [{
            "id": "q001",
            "text": "x",
            "status": "accepted",
            "generated_cards": [{
                "type": "image_videos",
                "path": "output/quote_cards/my_video.mp4",
                "created_at": "2026-01-01",
                "images_used": ["assets/01-ajuda/Yoga1.jpg"]
            }]
        }]
    }))

    result = find_quote_for_file("my_video.mp4", knowledge_dir)
    assert result is not None
    quote_id, group_name, images_used = result
    assert quote_id == "q001"
    assert group_name == "TestGroup"
    assert images_used == ["assets/01-ajuda/Yoga1.jpg"]


def test_find_quote_for_file_no_match(tmp_path):
    """Returns None when no quote references the given filename."""
    knowledge_dir = tmp_path / "knowledge"
    group_dir = knowledge_dir / "TestGroup"
    group_dir.mkdir(parents=True)
    (group_dir / "quotes.json").write_text(json.dumps({
        "source": "S", "author": "A", "quotes": []
    }))
    assert find_quote_for_file("nonexistent.mp4", knowledge_dir) is None


# ── mark_quote_as_published ───────────────────────────────────────────────────

def test_mark_quote_as_published_updates_status(tmp_path):
    """Sets quote status to 'published' in quotes.json."""
    knowledge_dir = tmp_path / "knowledge"
    group_dir = knowledge_dir / "TestGroup"
    group_dir.mkdir(parents=True)
    quotes_file = group_dir / "quotes.json"
    quotes_file.write_text(json.dumps({
        "source": "S", "author": "A",
        "quotes": [{"id": "q001", "text": "x", "status": "accepted"}]
    }))

    result = mark_quote_as_published("q001", "TestGroup", knowledge_dir)
    assert result is True

    data = json.loads(quotes_file.read_text())
    assert data["quotes"][0]["status"] == "published"


def test_mark_quote_as_published_missing_id(tmp_path):
    """Returns False when the quote id is not found."""
    knowledge_dir = tmp_path / "knowledge"
    group_dir = knowledge_dir / "TestGroup"
    group_dir.mkdir(parents=True)
    (group_dir / "quotes.json").write_text(json.dumps({
        "source": "S", "author": "A", "quotes": []
    }))
    assert mark_quote_as_published("q_unknown", "TestGroup", knowledge_dir) is False


# ── get_all_published_images ──────────────────────────────────────────────────

def test_get_all_published_images(tmp_path):
    """Aggregates all images_used from the log into a flat set."""
    log = {
        "v1.mp4": {"quote_id": "q1", "quote_group": "G", "marked_at": "x",
                   "images_used": ["assets/img1.jpg", "assets/img2.jpg"]},
        "v2.mp4": {"quote_id": "q2", "quote_group": "G", "marked_at": "x",
                   "images_used": ["assets/img2.jpg", "assets/img3.jpg"]},
    }
    result = get_all_published_images(log)
    assert result == {"assets/img1.jpg", "assets/img2.jpg", "assets/img3.jpg"}
```

- [ ] **Step 3.2: Run the tests to verify they all fail**

```bash
python -m pytest tests/test_published_tracker.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'src.published_tracker'`

- [ ] **Step 3.3a: Implement the pure functions in `src/published_tracker.py`**

Create `/Users/roel.heremans/Documents/PersonalRepos/Yoga/src/published_tracker.py` with everything up to (but not including) `process_published_folder`):

```python
"""
published_tracker.py — Track which videos have been published to social media.

Workflow:
1. User drags a generated .mp4 from output/quote_cards/ into output/published/
2. User runs: python3 main.py mark-published
3. This module scans output/published/, finds unprocessed videos,
   looks up their quotes, marks quotes as 'published', and logs everything.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Extensions treated as publishable media files
_MEDIA_EXTENSIONS = {'.mp4', '.mov', '.jpg', '.jpeg', '.png'}


def load_published_log(log_path: Path) -> Dict:
    """Load the published log. Returns empty dict if the file doesn't exist."""
    if not log_path.exists():
        return {}
    with open(log_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_published_log(log_path: Path, log: Dict) -> None:
    """Save the published log to disk."""
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def scan_for_new_files(published_dir: Path, log: Dict) -> List[str]:
    """
    Return filenames of media files in published_dir not already in the log.
    Ignores hidden files (e.g. .published_log.json) and non-media files.
    """
    if not published_dir.exists():
        return []
    new_files = []
    for f in sorted(published_dir.iterdir()):
        if f.is_file() and not f.name.startswith('.') and f.suffix.lower() in _MEDIA_EXTENSIONS:
            if f.name not in log:
                new_files.append(f.name)
    return new_files


def find_quote_for_file(
    filename: str, knowledge_dir: Path
) -> Optional[Tuple[str, str, List[str]]]:
    """
    Search all quotes.json files for a generated_cards entry whose path
    ends with the given filename.

    Returns (quote_id, group_name, images_used) or None if not found.
    images_used is an empty list if the entry has no images_used field.
    """
    if not knowledge_dir.exists():
        return None
    for group_dir in sorted(knowledge_dir.iterdir()):
        if not group_dir.is_dir():
            continue
        quotes_file = group_dir / 'quotes.json'
        if not quotes_file.exists():
            continue
        with open(quotes_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for quote in data.get('quotes', []):
            for card in quote.get('generated_cards', []):
                card_path = card.get('path', '')
                if Path(card_path).name == filename:
                    return (
                        quote['id'],
                        group_dir.name,
                        card.get('images_used') or [],
                    )
    return None


def mark_quote_as_published(
    quote_id: str, group_name: str, knowledge_dir: Path
) -> bool:
    """
    Set the status of the given quote to 'published' in its quotes.json.
    Returns True if the quote was found and updated, False otherwise.
    """
    quotes_file = knowledge_dir / group_name / 'quotes.json'
    if not quotes_file.exists():
        return False
    with open(quotes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for quote in data.get('quotes', []):
        if quote.get('id') == quote_id:
            quote['status'] = 'published'
            with open(quotes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
    return False


def get_all_published_images(log: Dict) -> Set[str]:
    """
    Return a flat set of all image paths recorded across all log entries.
    """
    images: Set[str] = set()
    for entry in log.values():
        for img in entry.get('images_used') or []:
            images.add(img)
    return images
```

- [ ] **Step 3.3b: Add `process_published_folder` to `src/published_tracker.py`**

Append this function to the module:

```python
def process_published_folder(
    published_dir: Path,
    knowledge_dir: Path,
) -> Dict:
    """
    High-level orchestration used by the CLI command.

    Scans published_dir, processes new files, updates quotes.json,
    and saves the log. Returns a summary dict with keys:
      - processed: list of filenames successfully matched and marked
      - unmatched: list of filenames with no matching quote found
      - already_done: list of filenames already in the log (from previous runs)
    """
    log_path = published_dir / '.published_log.json'
    log = load_published_log(log_path)

    already_done = list(log.keys())
    new_files = scan_for_new_files(published_dir, log)
    processed = []
    unmatched = []

    for filename in new_files:
        match = find_quote_for_file(filename, knowledge_dir)
        if match is None:
            unmatched.append(filename)
            continue
        quote_id, group_name, images_used = match
        mark_quote_as_published(quote_id, group_name, knowledge_dir)
        log[filename] = {
            'quote_id': quote_id,
            'quote_group': group_name,
            'images_used': images_used,
            'marked_at': datetime.now().isoformat(),
        }
        processed.append(filename)

    if processed:
        save_published_log(log_path, log)

    return {
        'processed': processed,
        'unmatched': unmatched,
        'already_done': already_done,
    }
```

- [ ] **Step 3.3c: Add integration test for `process_published_folder`**

Add to `tests/test_published_tracker.py`:

```python
from src.published_tracker import process_published_folder

def test_process_published_folder_happy_path(tmp_path):
    """Full flow: video in published folder gets matched, quote marked, log saved."""
    published_dir = tmp_path / "published"
    published_dir.mkdir()
    (published_dir / "my_video.mp4").touch()

    knowledge_dir = tmp_path / "knowledge"
    group_dir = knowledge_dir / "TestGroup"
    group_dir.mkdir(parents=True)
    quotes_file = group_dir / "quotes.json"
    quotes_file.write_text(json.dumps({
        "source": "S", "author": "A",
        "quotes": [{
            "id": "q001", "text": "x", "status": "accepted",
            "generated_cards": [{
                "type": "image_videos",
                "path": "output/quote_cards/my_video.mp4",
                "created_at": "2026-01-01",
                "images_used": ["assets/01-ajuda/Yoga1.jpg"]
            }]
        }]
    }))

    summary = process_published_folder(published_dir, knowledge_dir)

    assert summary["processed"] == ["my_video.mp4"]
    assert summary["unmatched"] == []

    # Quote should now be published
    data = json.loads(quotes_file.read_text())
    assert data["quotes"][0]["status"] == "published"

    # Log should exist and contain the entry
    log = load_published_log(published_dir / ".published_log.json")
    assert "my_video.mp4" in log
    assert log["my_video.mp4"]["quote_id"] == "q001"
    assert log["my_video.mp4"]["images_used"] == ["assets/01-ajuda/Yoga1.jpg"]


def test_process_published_folder_unmatched(tmp_path):
    """Videos with no matching quote are reported as unmatched, not errors."""
    published_dir = tmp_path / "published"
    published_dir.mkdir()
    (published_dir / "foreign_video.mp4").touch()

    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    summary = process_published_folder(published_dir, knowledge_dir)
    assert summary["unmatched"] == ["foreign_video.mp4"]
    assert summary["processed"] == []


def test_process_published_folder_skips_already_processed(tmp_path):
    """Files already in the log are not re-processed."""
    published_dir = tmp_path / "published"
    published_dir.mkdir()
    (published_dir / "old_video.mp4").touch()
    existing_log = {"old_video.mp4": {"quote_id": "q001", "quote_group": "G",
                                       "images_used": [], "marked_at": "2026-01-01"}}
    save_published_log(published_dir / ".published_log.json", existing_log)

    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    summary = process_published_folder(published_dir, knowledge_dir)
    assert summary["processed"] == []
    assert summary["already_done"] == ["old_video.mp4"]
```

- [ ] **Step 3.4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_published_tracker.py -v
```

Expected: all `PASSED`

- [ ] **Step 3.5: Commit**

```bash
git add src/published_tracker.py tests/test_published_tracker.py
git commit -m "feat: add PublishedTracker module for tracking published media"
```

---

## Task 4: Add `mark-published` CLI command

**Files:**
- Modify: `main.py`
- Create: `output/published/` folder

- [ ] **Step 4.1: Create the published folder**

```bash
mkdir -p output/published
touch output/published/.gitkeep
```

- [ ] **Step 4.2: Write a failing CLI test**

Add to `tests/test_cli.py`:

```python
def test_mark_published_no_folder(runner):
    """mark-published prints a clear message when published folder doesn't exist."""
    # Pass a path that is guaranteed not to exist — no mocking needed
    result = runner.invoke(cli, ['mark-published', '--published-dir', '/tmp/yoga_test_nonexistent_published_dir'])
    assert result.exit_code == 0
    assert 'does not exist' in result.output.lower()
```

- [ ] **Step 4.3: Run the test to verify it fails**

```bash
python -m pytest tests/test_cli.py::test_mark_published_no_folder -v
```

Expected: `FAILED` — `No such command 'mark-published'`

- [ ] **Step 4.4: Implement the `mark-published` command in `main.py`**

Add this import near the top of `main.py` (after existing imports):

```python
from src.published_tracker import process_published_folder, get_all_published_images, load_published_log
```

Add this command before the `if __name__ == '__main__':` block:

```python
@cli.command()
@click.option(
    '--published-dir',
    type=click.Path(file_okay=False, dir_okay=True),
    default='output/published',
    show_default=True,
    help='Folder containing published videos to process',
)
def mark_published(published_dir):
    """Mark videos in the published folder as used.

    Scan the published folder for new video files, look up which quote and
    images each video used, mark those quotes as 'published' (excluded from
    future generation), and record the images used.

    Example:
    \\b
    # After dragging videos into output/published/:
    python3 main.py mark-published
    """
    published_path = Path(published_dir)
    if not published_path.exists():
        click.echo(f"{Fore.YELLOW}Published folder does not exist: {published_path}{Style.RESET_ALL}")
        click.echo("Create it and drag your published videos there, then run this command.")
        return

    knowledge_dir = Path(__file__).parent / 'assets' / '10_knowledge'
    summary = process_published_folder(published_path, knowledge_dir)

    if not summary['processed'] and not summary['unmatched']:
        click.echo(f"{Fore.CYAN}No new files found in {published_path}{Style.RESET_ALL}")
        if summary['already_done']:
            click.echo(f"  ({len(summary['already_done'])} previously processed files already in log)")
        return

    if summary['processed']:
        click.echo(f"\n{Fore.GREEN}✓ Marked {len(summary['processed'])} video(s) as published:{Style.RESET_ALL}")
        for filename in summary['processed']:
            click.echo(f"  - {filename}")

    if summary['unmatched']:
        click.echo(f"\n{Fore.YELLOW}⚠ {len(summary['unmatched'])} file(s) had no matching quote (not generated by this system?):{Style.RESET_ALL}")
        for filename in summary['unmatched']:
            click.echo(f"  - {filename}")

    # Print image summary
    log = load_published_log(published_path / '.published_log.json')
    all_images = get_all_published_images(log)
    if all_images:
        click.echo(f"\n{Fore.CYAN}Total unique images used across all published posts: {len(all_images)}{Style.RESET_ALL}")
```

- [ ] **Step 4.5: Run the test to verify it passes**

```bash
python -m pytest tests/test_cli.py::test_mark_published_no_folder -v
```

Expected: `PASSED`

- [ ] **Step 4.6: Smoke-test the command manually**

```bash
python3 main.py mark-published --help
python3 main.py mark-published
```

Expected: help text shown; command runs without error, prints "No new files found" (since published folder is empty).

- [ ] **Step 4.7: Commit**

```bash
git add main.py output/published/.gitkeep tests/test_cli.py
git commit -m "feat: add mark-published CLI command to mark videos as published"
```

---

## Task 5: Warn when generating with already-published images

When the user runs `generate-quote-cards -i some_image.jpg` and that image was previously used in a published post, print a warning (but don't block generation).

**Files:**
- Modify: `main.py` (inside `generate_quote_cards` command)

- [ ] **Step 5.1: Write a failing CLI test**

Add to `tests/test_cli.py`. Note: existing tests use `CliRunner()` inline (no `runner` fixture); follow the same pattern.

```python
def test_generate_warns_for_published_image(tmp_path):
    """generate-quote-cards warns when a specified image was already used in a published post."""
    import json
    from click.testing import CliRunner
    from unittest.mock import patch, MagicMock
    import main as main_module

    # Create a real image file so Click's exists=True check passes
    img = tmp_path / "Yoga_Funchal21.jpg"
    img.write_bytes(b"fake")

    # Build a fake log that marks this exact image path as used
    log_data = {
        "some_video.mp4": {
            "quote_id": "q001",
            "quote_group": "TestGroup",
            "images_used": [str(img)],
            "marked_at": "2026-01-01",
        }
    }

    mock_gen = MagicMock()
    mock_gen.generate_quote_cards.return_value = {
        'white_background': [], 'photos': [], 'videos': [], 'image_videos': []
    }

    with patch('main.QuoteCardGenerator', return_value=mock_gen), \
         patch('src.published_tracker.load_published_log', return_value=log_data):
        runner = CliRunner()
        result = runner.invoke(main_module.cli, ['generate-quote-cards', '-i', str(img)])

    assert 'already used in a published post' in result.output
```

- [ ] **Step 5.2: Run the test to verify it fails**

```bash
python -m pytest tests/test_cli.py::test_generate_warns_for_published_image -v
```

Expected: `FAILED` — no warning text in output (the warning code doesn't exist yet).

- [ ] **Step 5.3: Add the warning to `generate_quote_cards` in `main.py`**

In `main.py`, inside the `generate_quote_cards` function, after the block that resolves `image_paths` (around line 392). Remove the `if log_path.exists()` guard — `load_published_log` already handles a missing file by returning `{}`, so the guard is redundant and makes the function hard to test.

```python
# Warn if any specified image was already used in a published post
if image_paths:
    from src.published_tracker import load_published_log, get_all_published_images
    _pub_log_path = Path(__file__).parent / 'output' / 'published' / '.published_log.json'
    pub_log = load_published_log(_pub_log_path)
    published_images = get_all_published_images(pub_log)
    for img_path in image_paths:
        if str(img_path) in published_images:
            click.echo(
                f"{Fore.YELLOW}⚠ Warning: '{img_path}' was already used in a published post.{Style.RESET_ALL}"
            )
```

> Note: we compare `str(img_path)` (absolute path) against the log entries. The log stores absolute paths for images specified via `-i`. This matches how `images_used_rel` is built in Task 1 Step 1.4 — if the image is inside the repo root it stores the relative path, otherwise the absolute path. Add a `try/except` to match both forms:

```python
if image_paths:
    from src.published_tracker import load_published_log, get_all_published_images
    _pub_log_path = Path(__file__).parent / 'output' / 'published' / '.published_log.json'
    pub_log = load_published_log(_pub_log_path)
    published_images = get_all_published_images(pub_log)
    repo_root = Path(__file__).parent
    for img_path in image_paths:
        try:
            rel = str(img_path.relative_to(repo_root)).replace('\\', '/')
        except ValueError:
            rel = str(img_path)
        if rel in published_images or str(img_path) in published_images:
            click.echo(
                f"{Fore.YELLOW}⚠ Warning: '{rel}' was already used in a published post.{Style.RESET_ALL}"
            )
```

- [ ] **Step 5.4: Smoke-test the warning manually**

First generate a card and move it to the published folder, then mark it:
```bash
# 1. Generate a video (use actual paths from your project)
python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg --duration 5

# 2. Move the output video to output/published/
mv output/quote_cards/quote_image_video_*.mp4 output/published/

# 3. Mark it as published
python3 main.py mark-published

# 4. Try generating with the same image — should see warning
python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg --duration 5
```

Expected: `⚠ Warning: 'assets/01-ajuda/Yoga_Funchal21.jpg' was already used in a published post.`

- [ ] **Step 5.5: Commit**

```bash
git add main.py tests/test_cli.py
git commit -m "feat: warn when generate-quote-cards uses already-published images"
```

---

## Task 6: Exclude published images from `--photo-dir` random selection

When the user uses `--photo-dir assets/01-ajuda/` the system picks photos at random. Published images must be excluded from that pool automatically (no warning — just silently skip them).

**Files:**
- Modify: `src/quote_card_generator.py` (method `generate_quote_cards`, where `selected_photos` is built)
- Modify: `main.py` (pass `published_images` set into `generate_quote_cards`, or load it inside the generator)
- Modify: `tests/test_quote_card_generator.py`

**Design note:** The simplest approach keeps `QuoteCardGenerator` unaware of the published log path. Instead, pass an optional `exclude_images: set` parameter into `generate_quote_cards` and filter before random selection. The caller (`main.py`) loads the set from the log before invoking.

- [ ] **Step 6.1: Write the failing test**

Add to `tests/test_quote_card_generator.py`:

```python
def test_generate_quote_cards_has_exclude_images_parameter():
    """generate_quote_cards must accept an exclude_images parameter."""
    import inspect
    sig = inspect.signature(QuoteCardGenerator.generate_quote_cards)
    assert 'exclude_images' in sig.parameters  # fails until Step 6.3
```

- [ ] **Step 6.2: Run the test to verify it fails**

```bash
python -m pytest tests/test_quote_card_generator.py::test_generate_quote_cards_has_exclude_images_parameter -v
```

Expected: `FAILED` — `AssertionError: 'exclude_images' not in signature parameters`

- [ ] **Step 6.3: Add `exclude_images` parameter to `generate_quote_cards` in `src/quote_card_generator.py`**

Find the method signature of `generate_quote_cards` (around line 449). Add an optional parameter:

```python
def generate_quote_cards(
    self,
    ...
    exclude_images: Optional[set] = None,
) -> Dict[str, List[Path]]:
```

Then, in the section that builds `selected_photos` from `photo_dir` (around line 560), add exclusion filtering:

```python
if photo_dir:
    available_photos = self.get_available_media_files(photo_dir, ['.jpg', '.jpeg', '.png'])
    if exclude_images:
        available_photos = [p for p in available_photos
                            if str(p) not in exclude_images
                            and str(p.resolve()) not in exclude_images]
    if not available_photos:
        print("Warning: no photos available after excluding published images")
    else:
        selected_photos = random.sample(available_photos, min(num_photos, len(available_photos)))
```

- [ ] **Step 6.4: Wire `exclude_images` from `main.py`**

In the `generate_quote_cards` CLI command in `main.py`, after the image-reuse warning block (Step 5.3), add:

```python
# Build set of published images to exclude from photo-dir selection
exclude_images = set()
published_log_path = Path(__file__).parent / 'output' / 'published' / '.published_log.json'
if published_log_path.exists():
    from src.published_tracker import load_published_log, get_all_published_images
    pub_log = load_published_log(published_log_path)
    exclude_images = get_all_published_images(pub_log)
```

Then pass `exclude_images` into the `generate_quote_cards` call:

```python
results = generator.generate_quote_cards(
    ...
    exclude_images=exclude_images or None,
)
```

- [ ] **Step 6.4b: Add a filtering integration test**

Add to `tests/test_quote_card_generator.py` (after Step 6.3 implementation):

```python
def test_generate_quote_cards_excludes_published_photo(tmp_path):
    """Photos in exclude_images are not passed to generate_photo_overlay_card."""
    from unittest.mock import MagicMock, patch

    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    img1 = photo_dir / "photo1.jpg"
    img2 = photo_dir / "photo2.jpg"
    img1.write_bytes(b"fake")
    img2.write_bytes(b"fake")

    generator = QuoteCardGenerator.__new__(QuoteCardGenerator)
    generator.knowledge_dir = tmp_path / "knowledge"
    generator.knowledge_dir.mkdir()
    generator.max_quote_display_length = 200

    fake_quote = {'id': 'q1', 'text': 'Test', 'group': 'G',
                  '_file_author': 'A', '_file_source': 'S'}

    with patch.object(generator, 'get_random_accepted_quote', return_value=fake_quote), \
         patch.object(generator, 'generate_photo_overlay_card', return_value=[tmp_path / 'out.jpg']) as mock_gen, \
         patch.object(generator, '_append_generated_cards_to_quote'):
        generator.generate_quote_cards(
            photo_dir=photo_dir,
            num_photos=1,
            exclude_images={str(img1)},
        )

    assert mock_gen.called
    used_photos = mock_gen.call_args[0][1]  # second positional arg is photos list
    assert all(str(p) != str(img1) for p in used_photos), "Published image should be excluded"
```

Run:
```bash
python -m pytest tests/test_quote_card_generator.py::test_generate_quote_cards_excludes_published_photo -v
```
Expected: `PASSED`

- [ ] **Step 6.5: Run the full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all `PASSED`

- [ ] **Step 6.6: Commit**

```bash
git add src/quote_card_generator.py main.py tests/test_quote_card_generator.py
git commit -m "feat: exclude published images from photo-dir random selection"
```

---

## Full Test Run

- [ ] **Run the complete test suite**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass, no regressions.

---

## End-to-End Workflow Summary

After this is built, the user's workflow becomes:

```
1. Generate video:
   python3 main.py generate-quote-cards -i assets/01-ajuda/Yoga_Funchal21.jpg ...

2. Review the video, post it to Instagram.

3. Drag the .mp4 from output/quote_cards/ into output/published/

4. Register it:
   python3 main.py mark-published
   → Quote marked as 'published' (won't be selected again)
   → Images logged (warning shown if reused)

5. Next time you generate:
   - That quote is excluded from random selection (status = published)
   - If you use -i with a published image: warning printed
   - If you use --photo-dir: published images silently skipped from the pool
```
