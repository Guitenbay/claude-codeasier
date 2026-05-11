from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import session_hook
from index_store import index_path


@pytest.fixture(autouse=True)
def isolate_state(tmp_path: Path):
    fake_state = tmp_path / "state"
    fake_state.mkdir()
    with (
        patch("config.state_dir", return_value=fake_state),
        patch("index_store.state_dir", return_value=fake_state),
    ):
        yield fake_state


class TestHandleStart:
    def test_records_session(self):
        payload = {
            "session_id": "s1",
            "transcript_path": "/tmp/s1.jsonl",
            "cwd": "/home/user/project",
            "source": "cli",
            "model": "opus",
        }
        result = session_hook.handle_start(payload)
        assert result == 0

    def test_returns_0_when_missing_fields(self):
        assert session_hook.handle_start({}) == 0
        assert session_hook.handle_start({"session_id": "s1"}) == 0

    def test_sets_status_active(self):
        session_hook.handle_start({"session_id": "s1", "transcript_path": "/tmp/x", "cwd": "/proj"})
        from index_store import load_index

        index = load_index()
        assert index["sessions"]["s1"]["status"] == "active"


class TestHandleEnd:
    def test_updates_status(self):
        # First start a session
        session_hook.handle_start({"session_id": "s1", "transcript_path": "/tmp/x", "cwd": "/proj"})
        result = session_hook.handle_end({"session_id": "s1", "cwd": "/proj"})
        assert result == 0

        from index_store import load_index

        index = load_index()
        assert index["sessions"]["s1"]["status"] == "ended"

    def test_returns_0_when_no_session_id(self):
        assert session_hook.handle_end({}) == 0

    def test_handles_missing_cwd(self):
        session_hook.handle_start({"session_id": "s1", "transcript_path": "/tmp/x", "cwd": "/proj"})
        result = session_hook.handle_end({"session_id": "s1"})
        assert result == 0

    def test_deletes_pending_delete_session_on_end(self, tmp_path: Path):
        """Session in pending-delete status should be deleted when SessionEnd fires."""
        transcript = tmp_path / "t.jsonl"
        transcript.write_text("data\n")

        index = {
            "version": 1,
            "sessions": {
                "s1": {
                    "session_id": "s1",
                    "cwd": str(tmp_path),
                    "project_slug": "test",
                    "transcript_path": str(transcript),
                    "status": "pending-delete",
                    "delete_mode": "trash",
                    "started_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-15T10:00:00Z",
                },
            },
        }
        index_path().write_text(json.dumps(index))

        cfg = {
            "archiveDir": str(tmp_path / "archive"),
            "trashDir": str(tmp_path / "trash" / "${project_slug}"),
            "defaultDeleteMode": "trash",
            "archiveCurrentSessionMode": "copy",
        }
        with patch("cc_session.load_config", return_value=cfg):
            result = session_hook.handle_end({"session_id": "s1", "cwd": str(tmp_path)})
        assert result == 0

        from index_store import load_index

        idx = load_index()
        assert idx["sessions"]["s1"]["status"] == "deleted"
        assert not transcript.exists()


class TestReadHookInput:
    def _fake_stdin(self, text: str):
        return type("FakeStdin", (), {"read": lambda _self: text})()

    def test_parses_json(self):
        with patch("sys.stdin", self._fake_stdin('{"a": 1}')):
            result = session_hook.read_hook_input()
        assert result == {"a": 1}

    def test_handles_empty_input(self):
        with patch("sys.stdin", self._fake_stdin("")):
            result = session_hook.read_hook_input()
        assert result == {}

    def test_handles_whitespace(self):
        with patch("sys.stdin", self._fake_stdin("  \n  ")):
            result = session_hook.read_hook_input()
        assert result == {}


class TestMain:
    def test_on_start(self):
        payload = json.dumps({"session_id": "s1", "transcript_path": "/tmp/x", "cwd": "/proj"})
        with patch("sys.stdin", type("S", (), {"read": lambda _self: payload})()):
            result = session_hook.main(["on-start"])
        assert result == 0

    def test_on_end(self):
        # First create a session
        start_payload = json.dumps({"session_id": "s1", "transcript_path": "/tmp/x", "cwd": "/proj"})
        with patch("sys.stdin", type("S", (), {"read": lambda _self: start_payload})()):
            session_hook.main(["on-start"])

        end_payload = json.dumps({"session_id": "s1", "cwd": "/proj"})
        with patch("sys.stdin", type("S", (), {"read": lambda _self: end_payload})()):
            result = session_hook.main(["on-end"])
        assert result == 0

    def test_invalid_event(self):
        with pytest.raises(SystemExit):
            session_hook.main(["invalid"])
