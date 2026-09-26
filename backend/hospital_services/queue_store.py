"""Persist accepted batches and serialize queue access across worker processes."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
from uuid import uuid4


MAX_PENDING = 20


def root(output_dir: str) -> Path:
    path = Path(output_dir) / "queue"
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def locked(path: Path, blocking: bool = True):
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            if not handle.read(1):
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def save(path: Path, result: dict) -> None:
    pending = path.with_name(f"{path.name}.{uuid4().hex}.pending")
    try:
        with pending.open("w", encoding="utf-8") as handle:
            json.dump(result, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def result_path(run_id: str, output_dir: str) -> Path:
    return Path(output_dir) / f"{run_id}.json"


def batch(batch_id: str, output_dir: str) -> dict | None:
    return read(root(output_dir) / f"{batch_id}.batch.json")


def _pending_runs(output_dir: str) -> list[dict]:
    runs = []
    manifests = sorted(root(output_dir).glob("*.batch.json"), key=lambda path: path.stat().st_mtime_ns)
    for path in manifests:
        manifest = read(path)
        if manifest is None:
            continue
        for run in manifest["runs"]:
            state = read(result_path(run["run_id"], output_dir))
            if state and state["state"] in ("queued", "processing"):
                runs.append(run)
    return runs


def pending_runs(output_dir: str) -> list[dict]:
    with locked(root(output_dir) / "submission.lock"):
        return _pending_runs(output_dir)


def enqueue(batch_id: str, files: list[tuple[str, bytes]], output_dir: str) -> dict:
    directory = root(output_dir)
    with locked(directory / "submission.lock"):
        existing = batch(batch_id, output_dir)
        if existing is not None:
            return existing
        if len(_pending_runs(output_dir)) + len(files) > MAX_PENDING:
            raise ValueError("The hospital queue is full. Please retry after some documents finish.")
        runs = [{"run_id": uuid4().hex, "filename": filename} for filename, _ in files]
        created = []
        try:
            for run, (_, source) in zip(runs, files):
                source_path = directory / f"{run['run_id']}.source.pdf"
                created.append(source_path)
                with source_path.open("xb") as handle:
                    handle.write(source)
                    handle.flush()
                    os.fsync(handle.fileno())
                path = result_path(run["run_id"], output_dir)
                created.append(path)
                save(path, {"state": "queued", **run, "completed_pages": 0, "total_pages": 0})
            manifest = {"batch_id": batch_id, "runs": runs}
            save(directory / f"{batch_id}.batch.json", manifest)
            return manifest
        except Exception:
            for path in created:
                path.unlink(missing_ok=True)
            raise


def delete(run_id: str, output_dir: str) -> bool:
    directory = root(output_dir)
    with locked(directory / "submission.lock"):
        state = read(result_path(run_id, output_dir))
        if state and state["state"] in ("queued", "processing"):
            return False
        for path in (result_path(run_id, output_dir), Path(output_dir) / f"{run_id}_redacted.pdf",
                     directory / f"{run_id}.source.pdf"):
            path.unlink(missing_ok=True)
        for path in directory.glob("*.batch.json"):
            manifest = read(path)
            if manifest and any(run["run_id"] == run_id for run in manifest["runs"]):
                manifest["runs"] = [run for run in manifest["runs"] if run["run_id"] != run_id]
                if manifest["runs"]:
                    save(path, manifest)
                else:
                    path.unlink(missing_ok=True)
        return True


def clean_inputs(output_dir: str) -> None:
    directory = root(output_dir)
    with locked(directory / "submission.lock"):
        pending = {run["run_id"] for run in _pending_runs(output_dir)}
        for path in directory.glob("*.source.pdf"):
            if path.name.removesuffix(".source.pdf") not in pending:
                path.unlink(missing_ok=True)
