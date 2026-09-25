"""Background OCR jobs with persistent completed results."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import threading
from uuid import uuid4


_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_active_job: str | None = None


def _result_path(run_id: str, output_dir: str) -> Path:
    return Path(output_dir) / f"{run_id}.json"


def _save_result(run_id: str, output_dir: str, result: dict) -> None:
    path = _result_path(run_id, output_dir)
    pending = path.with_suffix(".pending")
    try:
        pending.write_text(json.dumps(result), encoding="utf-8")
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def submit(source: bytes, output_dir: str, logger: logging.Logger) -> str | None:
    """Accept one active OCR job per worker to bound model memory use."""
    global _active_job
    with _lock:
        if _active_job is not None:
            return None
        run_id = uuid4().hex
        _jobs[run_id] = {
            "state": "processing", "completed_pages": 0, "total_pages": 0,
        }
        _active_job = run_id

    worker = threading.Thread(
        target=_process, args=(run_id, source, output_dir, logger),
        name=f"hospital-ocr-{run_id[:8]}", daemon=True,
    )
    try:
        worker.start()
    except Exception:
        with _lock:
            _jobs.pop(run_id, None)
            _active_job = None
        raise
    return run_id


def status(run_id: str, output_dir: str) -> dict | None:
    with _lock:
        job = _jobs.get(run_id)
        if job:
            return dict(job)
    try:
        return json.loads(_result_path(run_id, output_dir).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def _process(run_id: str, source: bytes, output_dir: str, logger: logging.Logger) -> None:
    global _active_job
    target = Path(output_dir) / f"{run_id}_redacted.pdf"
    pending = target.with_suffix(".pending")

    def on_page(completed: int, total: int) -> None:
        with _lock:
            _jobs[run_id]["completed_pages"] = completed
            _jobs[run_id]["total_pages"] = total

    try:
        from .processor import process_pdf

        pdf_bytes, rows, redactions, warnings = process_pdf(source, on_page=on_page)
        pending.write_bytes(pdf_bytes)
        os.replace(pending, target)
        result = {
            "state": "completed", "run_id": run_id, "rows": rows,
            "redactions": redactions, "warnings": warnings,
        }
    except ValueError as exc:
        result = {"state": "failed", "error": str(exc)}
    except Exception:
        logger.exception("Hospital bill processing failed")
        result = {"state": "failed", "error": "Could not process the hospital bill."}
    finally:
        try:
            pending.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove temporary hospital output for %s", run_id)
        with _lock:
            _jobs[run_id].update(result)
            _active_job = None
        try:
            _save_result(run_id, output_dir, result)
        except OSError:
            logger.exception("Could not save hospital result %s", run_id)
        else:
            with _lock:
                _jobs.pop(run_id, None)
