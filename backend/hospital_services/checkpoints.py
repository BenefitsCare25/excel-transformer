"""Persist finished pages so an interrupted document resumes instead of restarting at page 1."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil


def _write(path: Path, payload: bytes) -> None:
    pending = path.with_name(f"{path.name}.pending")
    with pending.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(pending, path)


def _paths(work_dir: Path, page_number: int) -> tuple[Path, Path]:
    stem = work_dir / f"page_{page_number:05d}"
    return stem.with_suffix(".png"), stem.with_suffix(".json")


def save_page(work_dir: Path, page_number: int, png: bytes, redactions: int, data: dict | None) -> None:
    """Write the redacted image first; the JSON record marks the page as complete."""
    work_dir.mkdir(parents=True, exist_ok=True)
    image_path, record_path = _paths(work_dir, page_number)
    _write(image_path, png)
    _write(record_path, json.dumps({"redactions": redactions, "data": data}).encode("utf-8"))


def load_page(work_dir: Path, page_number: int) -> tuple[bytes, int, dict | None] | None:
    image_path, record_path = _paths(work_dir, page_number)
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        png = image_path.read_bytes()
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    data = record["data"]
    if data is not None:
        # JSON has no tuples; page grouping compares pagination as (part, total) tuples.
        data["_pagination"] = tuple(data["_pagination"]) if data["_pagination"] else None
        for observation in data["_pagination_evidence"]:
            observation["value"] = tuple(observation["value"]) if observation["value"] else None
    return png, record["redactions"], data


def page_image(work_dir: Path, page_number: int) -> bytes:
    return _paths(work_dir, page_number)[0].read_bytes()


def remove(work_dir: Path) -> None:
    shutil.rmtree(work_dir, ignore_errors=True)
