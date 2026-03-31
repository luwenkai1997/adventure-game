"""Thread-safe atomic JSON/text writes."""
import json
import os
import tempfile
import threading
from typing import Any, Dict

_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(path: str) -> threading.Lock:
    ap = os.path.abspath(path)
    with _locks_guard:
        if ap not in _locks:
            _locks[ap] = threading.Lock()
        return _locks[ap]


def atomic_write_json(path: str, data: Any, *, indent: int = 2) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with _lock_for(path):
        fd, tmp_path = tempfile.mkstemp(
            dir=directory or ".", prefix=".atomic_", suffix=".json"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


def atomic_write_text(path: str, text: str, encoding: str = "utf-8") -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with _lock_for(path):
        fd, tmp_path = tempfile.mkstemp(
            dir=directory or ".", prefix=".atomic_", suffix=".txt"
        )
        try:
            with os.fdopen(fd, "w", encoding=encoding) as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
