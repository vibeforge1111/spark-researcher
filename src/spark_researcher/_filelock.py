"""Standalone file-locking utilities — kept separate to avoid circular imports."""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def locked_file(path: Path, *, timeout_seconds: float = 30.0):
    ensure_parent(path)
    lock_path = path.with_name(path.name + ".lock")
    deadline = time.monotonic() + timeout_seconds
    handle: int | None = None
    while handle is None:
        try:
            handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                owner = None
                try:
                    owner = lock_path.read_text(encoding="utf-8", errors="ignore").strip()[:64] or None
                except OSError:
                    owner = None
                suffix = f" (owner={owner})" if owner else ""
                raise TimeoutError(f"Timed out waiting for ledger lock: {lock_path}{suffix}")
            time.sleep(0.05)
    try:
        os.write(handle, str(os.getpid()).encode("ascii", errors="ignore"))
        yield
    finally:
        os.close(handle)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
