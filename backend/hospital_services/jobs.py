"""Run every accepted document independently of browser connections."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import threading
from typing import BinaryIO
from uuid import uuid4

from . import queue_store


_lock = threading.Lock()
_workers: dict[str, threading.Thread] = {}
_wake = threading.Event()


def start(output_dir: str, logger: logging.Logger) -> None:
    """Start in the serving process, including after a preloaded worker forks."""
    key = str(Path(output_dir).resolve())
    with _lock:
        existing = _workers.get(key)
        if existing and existing.is_alive():
            _wake.set()
            return
        worker = threading.Thread(target=_work, args=(key, logger), name="hospital-queue", daemon=True)
        _workers[key] = worker
        worker.start()


def submit_batch(batch_id: str, files: list[tuple[str, BinaryIO]], output_dir: str,
                 logger: logging.Logger) -> dict:
    result = queue_store.enqueue(batch_id, files, output_dir)
    start(output_dir, logger)
    return result


def submit(source: BinaryIO, output_dir: str, logger: logging.Logger) -> str:
    result = submit_batch(uuid4().hex, [("hospital_bill.pdf", source)], output_dir, logger)
    return result["runs"][0]["run_id"]


def status(run_id: str, output_dir: str) -> dict | None:
    return queue_store.read(queue_store.result_path(run_id, output_dir))


def delete(run_id: str, output_dir: str) -> bool:
    return queue_store.delete(run_id, output_dir)


def _work(output_dir: str, logger: logging.Logger) -> None:
    try:
        with queue_store.locked(queue_store.root(output_dir) / "worker.lock", blocking=False):
            queue_store.clean_inputs(output_dir)
            while True:
                try:
                    runs = queue_store.pending_runs(output_dir)
                    if runs:
                        _process(runs[0], output_dir, logger)
                        continue
                except Exception:
                    logger.exception("Hospital queue iteration failed; retrying")
                _wake.wait(2)
                _wake.clear()
    except OSError:
        logger.exception("Hospital queue worker stopped or its lock is held by another worker")
    except Exception:
        logger.exception("Hospital queue worker stopped unexpectedly")


def _process(run: dict, output_dir: str, logger: logging.Logger) -> None:
    run_id = run["run_id"]
    target = Path(output_dir) / f"{run_id}_redacted.pdf"
    pending = target.with_suffix(".pending")
    source = queue_store.root(output_dir) / f"{run_id}.source.pdf"

    def on_page(completed: int, total: int) -> None:
        queue_store.save(queue_store.result_path(run_id, output_dir), {
            "state": "processing", **run, "completed_pages": completed, "total_pages": total,
        })

    try:
        from .processor import process_pdf

        on_page(0, 0)
        rows, redactions, warnings = process_pdf(source, pending, on_page=on_page)
        with pending.open("rb+") as handle:
            os.fsync(handle.fileno())
        os.replace(pending, target)
        # Row issues travel with each row's review_notes so superseded rows never leave stale notes.
        result = {"state": "completed", **run, "rows": rows,
                  "redactions": redactions, "document_warnings": warnings}
    except ValueError as exc:
        result = {"state": "failed", **run, "error": str(exc)}
    except Exception:
        logger.exception("Hospital bill processing failed for %s", run_id)
        result = {"state": "failed", **run, "error": "Could not process the hospital bill."}
    finally:
        try:
            pending.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove temporary hospital output for %s", run_id)
    queue_store.save(queue_store.result_path(run_id, output_dir), result)
    try:
        source.unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not remove hospital queue input for %s", run_id)
