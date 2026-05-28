from __future__ import annotations

import fcntl
import json
import os
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ensure_state_dir, state_dir

INDEX_VERSION = 1


def index_path() -> Path:
    return state_dir() / "session-index.json"


@contextmanager
def locked_index() -> Generator[None]:
    ensure_state_dir()
    lock_path = state_dir() / "session-index.lock"
    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")  # noqa: UP017


def load_index() -> dict[str, Any]:
    path = index_path()
    if not path.exists():
        return {"version": INDEX_VERSION, "sessions": {}}

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        quarantine_path = path.with_name(f"{path.name}.corrupt-{now_iso().replace(':', '-')}")
        path.replace(quarantine_path)
        return {"version": INDEX_VERSION, "sessions": {}}

    if not isinstance(data, dict):
        return {"version": INDEX_VERSION, "sessions": {}}
    if "sessions" not in data or not isinstance(data["sessions"], dict):
        data["sessions"] = {}
    if "version" not in data:
        data["version"] = INDEX_VERSION
    return data


def save_index(index: dict[str, Any]) -> dict[str, Any]:
    ensure_state_dir()
    path = index_path()
    payload = json.dumps(index, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as tmp:
        tmp.write(payload)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return index


def get_session(index: dict[str, Any], session_id: str) -> dict[str, Any] | None:
    return index["sessions"].get(session_id)


def upsert_session(index: dict[str, Any], session_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    existing = dict(index["sessions"].get(session_id, {}))
    existing.update(fields)
    existing.setdefault("session_id", session_id)
    index["sessions"][session_id] = existing
    return existing


def mark_session_missing(index: dict[str, Any], session_id: str) -> dict[str, Any] | None:
    session = get_session(index, session_id)
    if session is None:
        return None
    session["status"] = "missing"
    session["updated_at"] = now_iso()
    return session


def reconcile_stale_sessions(index: dict[str, Any], current_session_id: str | None = None) -> list[dict[str, Any]]:
    reconciled = []
    timestamp = now_iso()
    for session in index["sessions"].values():
        if session.get("session_id") == current_session_id:
            continue
        if session.get("status") == "active":
            session["status"] = "ended"
            session["ended_at"] = session.get("ended_at") or timestamp
            session["updated_at"] = timestamp
            reconciled.append(session)
    return reconciled


def latest_session_by_status(index: dict[str, Any], status: str, cwd: str | None = None) -> dict[str, Any] | None:
    candidates = [session for session in index["sessions"].values() if session.get("status") == status]
    if cwd is not None:
        cwd_candidates = [session for session in candidates if session.get("cwd") == cwd]
        if cwd_candidates:
            candidates = cwd_candidates
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.get("updated_at", item.get("started_at", "")))


def latest_active_session(index: dict[str, Any], cwd: str | None = None) -> dict[str, Any] | None:
    return latest_session_by_status(index, "active", cwd=cwd)


def latest_pending_session(index: dict[str, Any], status: str, cwd: str | None = None) -> dict[str, Any] | None:
    return latest_session_by_status(index, status, cwd=cwd)
