from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config import ensure_state_dir, state_dir


INDEX_VERSION = 1


def index_path() -> Path:
    return state_dir() / "session-index.json"


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_index() -> dict[str, Any]:
    path = index_path()
    if not path.exists():
        return {"version": INDEX_VERSION, "sessions": {}}

    data = json.loads(path.read_text())
    if "sessions" not in data or not isinstance(data["sessions"], dict):
        data["sessions"] = {}
    if "version" not in data:
        data["version"] = INDEX_VERSION
    return data


def save_index(index: dict[str, Any]) -> dict[str, Any]:
    ensure_state_dir()
    index_path().write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
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


def latest_active_session(index: dict[str, Any], cwd: str | None = None) -> dict[str, Any] | None:
    candidates = [session for session in index["sessions"].values() if session.get("status") == "active"]
    if cwd is not None:
        cwd_candidates = [session for session in candidates if session.get("cwd") == cwd]
        if cwd_candidates:
            candidates = cwd_candidates
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.get("updated_at", item.get("started_at", "")))
