#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from index_store import now_iso, load_index, save_index, upsert_session
from path_utils import project_slug


def read_hook_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def handle_start(payload: dict) -> int:
    session_id = payload.get("session_id")
    transcript_path = payload.get("transcript_path")
    cwd = payload.get("cwd")
    if not session_id or not transcript_path or not cwd:
        return 0

    index = load_index()
    upsert_session(
        index,
        session_id,
        {
            "session_id": session_id,
            "cwd": cwd,
            "project_slug": project_slug(cwd),
            "transcript_path": transcript_path,
            "source": payload.get("source"),
            "model": payload.get("model"),
            "status": "active",
            "started_at": payload.get("started_at", now_iso()),
            "updated_at": now_iso(),
            "ended_at": None,
        },
    )
    save_index(index)
    return 0


def handle_end(payload: dict) -> int:
    session_id = payload.get("session_id")
    transcript_path = payload.get("transcript_path")
    cwd = payload.get("cwd")
    if not session_id:
        return 0

    index = load_index()
    upsert_session(
        index,
        session_id,
        {
            "session_id": session_id,
            "cwd": cwd,
            "project_slug": project_slug(cwd) if cwd else None,
            "transcript_path": transcript_path,
            "status": "ended",
            "ended_at": now_iso(),
            "updated_at": now_iso(),
        },
    )
    save_index(index)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session_hook.py")
    parser.add_argument("event", choices=("on-start", "on-end"))
    args = parser.parse_args(argv)

    payload = read_hook_input()
    if args.event == "on-start":
        return handle_start(payload)
    return handle_end(payload)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
