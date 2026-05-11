from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_TEMPLATE_PATTERN = re.compile(r"\$\{([a-zA-Z0-9_]+)\}")


def project_slug(project_dir: str) -> str:
    path = Path(project_dir).expanduser().resolve()
    return str(path).strip("/").replace("/", "-") or "root"


def expand_template(template: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))

    return _TEMPLATE_PATTERN.sub(replace, template)


def resolve_directory(template: str, variables: dict[str, str]) -> Path:
    expanded = expand_template(template, variables)
    return Path(expanded).expanduser().resolve()


def safe_session_filename(session: dict[str, Any]) -> str:
    started_at = session.get("started_at", "unknown")
    safe_started_at = started_at.replace(":", "-")
    session_id = session["session_id"]
    return f"{safe_started_at}__{session_id}.jsonl"


def dedupe_destination(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}__{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
