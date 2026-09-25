"""Short-lived OCR jobs for uploads that exceed the HTTP request window."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import threading
import time
from uuid import uuid4


RETENTION_SECONDS = 15 * 60
_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_active_job: str | None = None


def _prune(now: float) -> None:
    expired = [run_id for run_id, job in _jobs.items()
               if job["state"] in ("completed", "failed")
               and now - job["finished_at"] > RETENTION_SECONDS]
    for run_id in expired:
        del _jobs[run_id]


def submit(source: bytes, output_dir: str, logger: logging.Logger) -> str | None:
    """Accept one active OCR job per worker to bound model memory use."""
    global _active_job
    with _lock:
        _prune(time.monotonic())
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


def status(run_id: str) -> dict | None:
    with _lock:
        _prune(time.monotonic())
        job = _jobs.get(run_id)
        return dict(job) if job else None


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
            "retention_minutes": 15,
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
            _jobs[run_id]["finished_at"] = time.monotonic()
            _active_job = None
