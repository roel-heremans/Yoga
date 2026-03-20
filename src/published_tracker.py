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
                if Path(card_path).name == filename and quote.get('id'):
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
