from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PLUGIN_NAME = "session"
DEFAULT_ARCHIVE_DIR = "~/.claude/projects/${project_slug}/.archive/sessions"
DEFAULT_TRASH_DIR = "~/.claude/projects/${project_slug}/.trash/sessions"
DEFAULT_DELETE_MODE = "trash"
DEFAULT_ARCHIVE_CURRENT_SESSION_MODE = "copy"

DEFAULT_CONFIG: dict[str, Any] = {
    "archiveDir": DEFAULT_ARCHIVE_DIR,
    "trashDir": DEFAULT_TRASH_DIR,
    "defaultDeleteMode": DEFAULT_DELETE_MODE,
    "archiveCurrentSessionMode": DEFAULT_ARCHIVE_CURRENT_SESSION_MODE,
}


def state_dir() -> Path:
    return Path.home() / ".claude" / "plugins" / PLUGIN_NAME / "state"


def ensure_state_dir() -> Path:
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def config_path() -> Path:
    return state_dir() / "config.json"


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return dict(DEFAULT_CONFIG)

    data = json.loads(path.read_text())
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    return merged


def save_config(config: dict[str, Any]) -> dict[str, Any]:
    ensure_state_dir()
    merged = dict(DEFAULT_CONFIG)
    merged.update(config)
    config_path().write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n")
    return merged
