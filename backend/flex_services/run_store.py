"""Ephemeral run storage for Flex Report generations.

Each generation writes into ``<PROCESSED_FOLDER>/flex_runs/<run_id>/`` with two
sub-folders (``in`` for uploads, ``out`` for generated files) and a manifest that
records the ordered output filenames. Downloads resolve through the manifest, so
they do not depend on in-process state and survive a worker restart.

Payroll data is sensitive: run folders are deleted RETENTION_MINUTES after the run
by a background reaper, and orphaned folders are purged at startup.
"""
import io
import json
import logging
import os
import re
import shutil
import threading
import time
import uuid
import zipfile

logger = logging.getLogger(__name__)

RUNS_DIRNAME = 'flex_runs'
RETENTION_MINUTES = 30
REAPER_INTERVAL_SECONDS = 300
MANIFEST_NAME = 'manifest.json'

_RUN_ID_PATTERN = re.compile(r'^[0-9a-f]{12}$')
_reaper_thread = None


def is_valid_run_id(run_id):
    """Guard against path traversal via the run_id URL segment."""
    return bool(run_id and _RUN_ID_PATTERN.match(str(run_id)))


def runs_root(processed_folder):
    return os.path.join(processed_folder, RUNS_DIRNAME)


def run_dir(processed_folder, run_id):
    if not is_valid_run_id(run_id):
        return None
    return os.path.join(runs_root(processed_folder), run_id)


def create_run(processed_folder):
    """Create a fresh run folder. Returns (run_id, input_dir, output_dir)."""
    run_id = uuid.uuid4().hex[:12]
    base = os.path.join(runs_root(processed_folder), run_id)
    indir = os.path.join(base, 'in')
    outdir = os.path.join(base, 'out')
    os.makedirs(indir, exist_ok=True)
    os.makedirs(outdir, exist_ok=True)
    return run_id, indir, outdir


def discard_run(processed_folder, run_id):
    """Remove a run folder (used when generation fails)."""
    base = run_dir(processed_folder, run_id)
    if base and os.path.isdir(base):
        shutil.rmtree(base, ignore_errors=True)


def finalize_run(processed_folder, run_id, output_paths, meta=None):
    """Write the manifest and drop the uploaded inputs.

    Returns the ordered output descriptors ``[{"i": 0, "name": "..."}, ...]``.
    """
    base = run_dir(processed_folder, run_id)
    if not base:
        raise ValueError('Invalid run id')

    outputs = []
    for index, path in enumerate(output_paths):
        if not os.path.exists(path):
            logger.warning(f"Flex run {run_id}: declared output missing on disk: {path}")
            continue
        outputs.append({'i': len(outputs), 'name': os.path.basename(path)})

    manifest = {
        'run_id': run_id,
        'created': time.time(),
        'outputs': [o['name'] for o in outputs],
    }
    if meta:
        manifest.update(meta)

    with open(os.path.join(base, MANIFEST_NAME), 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle)

    # Uploaded source files are no longer needed once outputs exist.
    shutil.rmtree(os.path.join(base, 'in'), ignore_errors=True)
    return outputs


def read_manifest(processed_folder, run_id):
    base = run_dir(processed_folder, run_id)
    if not base:
        return None
    path = os.path.join(base, MANIFEST_NAME)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        logger.error(f"Flex run {run_id}: unreadable manifest: {exc}")
        return None


def output_path(processed_folder, run_id, index):
    """Resolve one output file of a run, or None when absent/expired."""
    manifest = read_manifest(processed_folder, run_id)
    if not manifest:
        return None
    names = manifest.get('outputs', [])
    if index < 0 or index >= len(names):
        return None
    path = os.path.join(run_dir(processed_folder, run_id), 'out', names[index])
    return path if os.path.exists(path) else None


def zip_run(processed_folder, run_id):
    """Bundle every output of a run into an in-memory zip, or None when absent."""
    manifest = read_manifest(processed_folder, run_id)
    if not manifest:
        return None
    outdir = os.path.join(run_dir(processed_folder, run_id), 'out')
    buffer = io.BytesIO()
    written = 0
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in manifest.get('outputs', []):
            path = os.path.join(outdir, name)
            if os.path.exists(path):
                archive.write(path, name)
                written += 1
    if not written:
        return None
    buffer.seek(0)
    return buffer


def purge_expired(processed_folder, retention_minutes=RETENTION_MINUTES):
    """Delete run folders older than the retention window. Returns count removed."""
    root = runs_root(processed_folder)
    if not os.path.isdir(root):
        return 0

    cutoff = time.time() - retention_minutes * 60
    removed = 0
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        try:
            manifest = read_manifest(processed_folder, name)
            created = manifest.get('created') if manifest else os.path.getmtime(path)
            if created is None or created < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        except OSError as exc:
            logger.warning(f"Flex run cleanup failed for {name}: {exc}")

    if removed:
        logger.info(f"Flex run cleanup: removed {removed} expired run folder(s)")
    return removed


def start_reaper(processed_folder, retention_minutes=RETENTION_MINUTES):
    """Start the background retention thread (idempotent)."""
    global _reaper_thread
    if _reaper_thread is not None and _reaper_thread.is_alive():
        return

    os.makedirs(runs_root(processed_folder), exist_ok=True)
    purge_expired(processed_folder, retention_minutes)

    def _loop():
        while True:
            time.sleep(REAPER_INTERVAL_SECONDS)
            try:
                purge_expired(processed_folder, retention_minutes)
            except Exception as exc:  # keep the thread alive on any failure
                logger.error(f"Flex run reaper error: {exc}")

    _reaper_thread = threading.Thread(target=_loop, daemon=True, name='FlexRunReaper')
    _reaper_thread.start()
    logger.info(
        f"Flex run retention started: {retention_minutes} min TTL, "
        f"sweep every {REAPER_INTERVAL_SECONDS // 60} min"
    )
