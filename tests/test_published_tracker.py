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


# ── process_published_folder ──────────────────────────────────────────────────

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
