#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

from config import DEFAULT_CONFIG, load_config, save_config
from index_store import (
    get_session,
    latest_active_session,
    latest_pending_session,
    load_index,
    mark_session_missing,
    now_iso,
    save_index,
)
from path_utils import dedupe_destination, project_slug, resolve_directory, safe_session_filename


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cc_session.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    archive = subparsers.add_parser("archive")
    archive.add_argument("session_id", nargs="?")

    delete = subparsers.add_parser("delete")
    delete.add_argument("session_id", nargs="?")
    delete.add_argument("--mode", choices=("trash", "purge"), default=None)

    setup = subparsers.add_parser("setup")
    setup_subparsers = setup.add_subparsers(dest="setup_command", required=True)

    archive_dir = setup_subparsers.add_parser("archive-dir")
    archive_dir.add_argument("path")

    trash_dir = setup_subparsers.add_parser("trash-dir")
    trash_dir.add_argument("path")

    setup_subparsers.add_parser("show")

    reset = setup_subparsers.add_parser("reset")
    reset.add_argument("key", nargs="?", choices=("archive-dir", "trash-dir"))

    return parser


def session_variables(session: dict[str, Any]) -> dict[str, str]:
    cwd = session.get("cwd") or str(Path.cwd())
    return {
        "project_dir": cwd,
        "project_slug": session.get("project_slug") or project_slug(cwd),
        "session_id": session["session_id"],
    }


def resolve_session(index: dict[str, Any], session_id: str | None, allow_pending: bool = False) -> dict[str, Any]:
    if session_id:
        session = get_session(index, session_id)
        if session is None:
            raise SystemExit(f"Session not found: {session_id}")
        return session

    cwd = str(Path.cwd().resolve())
    session = latest_active_session(index, cwd=cwd)
    if session is None:
        session = latest_active_session(index)
    for pending_status in ("pending-delete", "failed-delete", "pending-archive", "failed-archive"):
        if allow_pending and session is None:
            session = latest_pending_session(index, pending_status, cwd=cwd)
        if allow_pending and session is None:
            session = latest_pending_session(index, pending_status)
    if session is None:
        raise SystemExit("No active session found. Pass an explicit session id.")
    return session


def set_failure(index: dict[str, Any], session: dict[str, Any], status: str, error: str) -> None:
    session["status"] = status
    session["last_error"] = error
    session["updated_at"] = now_iso()
    save_index(index)


def clear_failure(session: dict[str, Any]) -> None:
    session.pop("last_error", None)


def ensure_transcript(session: dict[str, Any], index: dict[str, Any]) -> Path:
    transcript_path = session.get("transcript_path")
    if not transcript_path:
        raise SystemExit(f"Session {session['session_id']} has no transcript path recorded.")

    transcript = Path(transcript_path).expanduser()
    if transcript.is_file():
        return transcript

    if transcript.exists():
        raise SystemExit(f"Transcript path is not a file: {transcript}")

    mark_session_missing(index, session["session_id"])
    save_index(index)
    raise SystemExit(f"Transcript file not found: {transcript}")


def copy_or_move(src: Path, dest: Path, move: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise FileExistsError(f"Destination already exists: {dest}")
    if move:
        shutil.move(str(src), str(dest))
    else:
        shutil.copy2(src, dest)


def archive_session(index: dict[str, Any], config: dict[str, Any], session: dict[str, Any]) -> int:
    status = session.get("status")

    if status == "pending-archive":
        print(f"Session {session['session_id']} is already pending archive.")
        return 0

    if status == "failed-archive":
        clear_failure(session)

    if status == "active":
        session["status"] = "pending-archive"
        session["updated_at"] = now_iso()
        save_index(index)
        print(f"Session {session['session_id']} marked as pending-archive. It will be archived when the session ends.")
        return 0

    transcript = ensure_transcript(session, index)
    destination_dir = resolve_directory(config["archiveDir"], session_variables(session))
    destination = dedupe_destination(destination_dir / safe_session_filename(session))

    try:
        copy_or_move(transcript, destination, move=True)
    except OSError as exc:
        set_failure(index, session, "failed-archive", str(exc))
        raise SystemExit(f"Failed to archive session {session['session_id']}: {exc}") from exc

    clear_failure(session)
    session["archived_at"] = now_iso()
    session["archived_path"] = str(destination)
    session["updated_at"] = now_iso()
    session["status"] = "archived"
    save_index(index)
    print(f"Archived session {session['session_id']} to {destination}")
    return 0


def archive_cancel(index: dict[str, Any], session: dict[str, Any]) -> int:
    if session.get("status") not in ("pending-archive", "failed-archive"):
        raise SystemExit(f"Session {session['session_id']} is not pending archive.")

    session["status"] = "active"
    clear_failure(session)
    session["updated_at"] = now_iso()
    save_index(index)
    print(f"Session {session['session_id']} pending archive cancelled")
    return 0


def archive_after_end(session_id: str, index: dict[str, Any] | None = None) -> int:
    if index is None:
        index = load_index()
    session = get_session(index, session_id)
    if session is None:
        return 0

    if session.get("status") != "pending-archive":
        return 0

    config = load_config()
    transcript = ensure_transcript(session, index)
    destination_dir = resolve_directory(config["archiveDir"], session_variables(session))
    destination = dedupe_destination(destination_dir / safe_session_filename(session))

    try:
        copy_or_move(transcript, destination, move=True)
    except OSError as exc:
        set_failure(index, session, "failed-archive", str(exc))
        raise SystemExit(f"Failed to archive session {session['session_id']}: {exc}") from exc

    clear_failure(session)
    session["archived_at"] = now_iso()
    session["archived_path"] = str(destination)
    session["updated_at"] = now_iso()
    session["status"] = "archived"
    save_index(index)
    print(f"Archived session {session['session_id']} to {destination}")
    return 0


def delete_session(
    index: dict[str, Any], config: dict[str, Any], session: dict[str, Any], mode: str, execute_pending: bool = False
) -> int:
    status = session.get("status")
    if status == "active":
        session["status"] = "pending-delete"
        session["delete_mode"] = mode
        session["updated_at"] = now_iso()
        save_index(index)
        print(f"Session {session['session_id']} marked for deletion. It will be deleted when the session ends.")
        return 0

    if status == "pending-delete" and not execute_pending:
        existing_mode = session.get("delete_mode", mode)
        if existing_mode != mode:
            raise SystemExit(f"Session {session['session_id']} is already pending deletion with mode {existing_mode}.")
        print(f"Session {session['session_id']} is already pending deletion with mode {existing_mode}.")
        return 0

    if status == "pending-archive":
        raise SystemExit("Refusing to delete a session that is pending archive. Use 'archive cancel' first.")

    if status == "failed-delete":
        existing_mode = session.get("delete_mode", mode)
        if existing_mode != mode:
            raise SystemExit(f"Session {session['session_id']} previously failed deletion with mode {existing_mode}.")
        clear_failure(session)

    transcript = ensure_transcript(session, index)
    try:
        if mode == "purge":
            transcript.unlink()
            destination = None
        else:
            trash_dir = resolve_directory(config["trashDir"], session_variables(session))
            destination = dedupe_destination(trash_dir / safe_session_filename(session))
            copy_or_move(transcript, destination, move=True)
    except OSError as exc:
        set_failure(index, session, "failed-delete", str(exc))
        raise SystemExit(f"Failed to delete session {session['session_id']} with mode {mode}: {exc}") from exc

    clear_failure(session)
    session["deleted_at"] = now_iso()
    session["delete_mode"] = mode
    session["updated_at"] = now_iso()
    session["status"] = "deleted"
    save_index(index)

    if destination is None:
        print(f"Purged session {session['session_id']}")
    else:
        print(f"Moved session {session['session_id']} to trash at {destination}")
    return 0


def delete_cancel(index: dict[str, Any], session: dict[str, Any]) -> int:
    if session.get("status") not in ("pending-delete", "failed-delete"):
        raise SystemExit(f"Session {session['session_id']} is not pending deletion.")

    session["status"] = "active"
    session.pop("delete_mode", None)
    clear_failure(session)
    session["updated_at"] = now_iso()
    save_index(index)
    print(f"Session {session['session_id']} pending deletion cancelled")
    return 0


def delete_after_end(session_id: str, index: dict[str, Any] | None = None) -> int:
    if index is None:
        index = load_index()
    session = get_session(index, session_id)
    if session is None:
        return 0

    if session.get("status") != "pending-delete":
        return 0

    config = load_config()
    return delete_session(index, config, session, session.get("delete_mode", "trash"), execute_pending=True)


def validate_directory_template(label: str, value: str, current: dict[str, Any]) -> None:
    _vars = {"project_slug": "example-project", "project_dir": str(Path.cwd()), "session_id": "example-session"}
    candidate = resolve_directory(value, _vars)
    if candidate.name.endswith(".jsonl"):
        raise SystemExit(f"{label} must be a directory path, not a transcript file path.")

    other_key = "trashDir" if label == "archiveDir" else "archiveDir"
    other_value = current.get(other_key, DEFAULT_CONFIG[other_key])
    other_candidate = resolve_directory(other_value, _vars)
    if candidate == other_candidate:
        raise SystemExit("archiveDir and trashDir must be different.")


def setup_show(config: dict[str, Any]) -> int:
    print(f"archiveDir={config['archiveDir']}")
    print(f"trashDir={config['trashDir']}")
    print(f"defaultDeleteMode={config['defaultDeleteMode']}")
    print(f"archiveCurrentSessionMode={config['archiveCurrentSessionMode']}")
    return 0


def setup_update(key: str, value: str) -> int:
    config = load_config()
    validate_directory_template(key, value, config)
    config[key] = value
    save_config(config)
    print(f"Set {key}={value}")
    return 0


def setup_reset(target: str | None) -> int:
    config = load_config()
    if target is None:
        config = save_config(dict(DEFAULT_CONFIG))
        print("Reset all settings to defaults")
        return 0

    key = "archiveDir" if target == "archive-dir" else "trashDir"
    config[key] = DEFAULT_CONFIG[key]
    save_config(config)
    print(f"Reset {key} to default")
    return 0


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()

    if args.command == "setup":
        if args.setup_command == "show":
            return setup_show(config)
        if args.setup_command == "archive-dir":
            return setup_update("archiveDir", args.path)
        if args.setup_command == "trash-dir":
            return setup_update("trashDir", args.path)
        return setup_reset(args.key)

    index = load_index()

    if args.command == "delete" and args.session_id == "cancel":
        session = resolve_session(index, None, allow_pending=True)
        return delete_cancel(index, session)

    if args.command == "archive" and args.session_id == "cancel":
        session = resolve_session(index, None, allow_pending=True)
        return archive_cancel(index, session)

    allow_pending = args.command in ("delete", "archive")
    session = resolve_session(index, args.session_id, allow_pending=allow_pending)

    if args.command == "archive":
        return archive_session(index, config, session)

    mode = args.mode or config.get("defaultDeleteMode", "trash")
    return delete_session(index, config, session, mode)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
