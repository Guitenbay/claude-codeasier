from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import cc_session
import config
import pytest


@pytest.fixture(autouse=True)
def isolate_state(tmp_path: Path):
    fake_state = tmp_path / "state"
    fake_state.mkdir()
    with (
        patch("config.state_dir", return_value=fake_state),
        patch("index_store.state_dir", return_value=fake_state),
    ):
        yield {"state_dir": fake_state, "tmp": tmp_path}


@pytest.fixture
def sample_session(tmp_path: Path):
    """Create a transcript file and index entry for testing."""
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text('{"role": "user", "text": "hello"}\n')

    session = {
        "session_id": "test-s1",
        "cwd": str(tmp_path),
        "project_slug": "test-project",
        "transcript_path": str(transcript),
        "status": "active",
        "started_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z",
    }
    return session, transcript


class TestBuildParser:
    def test_archive_command(self):
        parser = cc_session.build_parser()
        args = parser.parse_args(["archive", "s1"])
        assert args.command == "archive"
        assert args.session_id == "s1"

    def test_archive_no_session(self):
        parser = cc_session.build_parser()
        args = parser.parse_args(["archive"])
        assert args.session_id is None

    def test_delete_trash_mode(self):
        parser = cc_session.build_parser()
        args = parser.parse_args(["delete", "s1", "--mode", "trash"])
        assert args.command == "delete"
        assert args.mode == "trash"

    def test_delete_purge_mode(self):
        parser = cc_session.build_parser()
        args = parser.parse_args(["delete", "s1", "--mode", "purge"])
        assert args.mode == "purge"

    def test_setup_show(self):
        parser = cc_session.build_parser()
        args = parser.parse_args(["setup", "show"])
        assert args.command == "setup"
        assert args.setup_command == "show"

    def test_setup_archive_dir(self):
        parser = cc_session.build_parser()
        args = parser.parse_args(["setup", "archive-dir", "/path"])
        assert args.path == "/path"


class TestSessionVariables:
    def test_from_session(self):
        session = {"cwd": "/home/proj", "project_slug": "proj", "session_id": "s1"}
        result = cc_session.session_variables(session)
        assert result["project_dir"] == "/home/proj"
        assert result["project_slug"] == "proj"
        assert result["session_id"] == "s1"

    def test_defaults_cwd(self):
        session = {"session_id": "s1"}
        result = cc_session.session_variables(session)
        assert "project_dir" in result


class TestCopyOrMove:
    def test_copy(self, tmp_path: Path):
        src = tmp_path / "src.jsonl"
        src.write_text("data")
        dest = tmp_path / "sub" / "dest.jsonl"
        cc_session.copy_or_move(src, dest, move=False)
        assert dest.exists()
        assert src.exists()

    def test_move(self, tmp_path: Path):
        src = tmp_path / "src.jsonl"
        src.write_text("data")
        dest = tmp_path / "sub" / "dest.jsonl"
        cc_session.copy_or_move(src, dest, move=True)
        assert dest.exists()
        assert not src.exists()


class TestSetupShow:
    def test_output(self, capsys):
        cc_session.setup_show(config.DEFAULT_CONFIG)
        captured = capsys.readouterr()
        assert "archiveDir=" in captured.out
        assert "trashDir=" in captured.out


class TestSetupReset:
    def test_reset_all(self, isolate_state):
        result = cc_session.setup_reset(None)
        assert result == 0

    def test_reset_archive_dir(self, isolate_state):
        result = cc_session.setup_reset("archive-dir")
        assert result == 0


class TestArchiveSession:
    def test_copies_active_session_by_default(self, sample_session, tmp_path: Path):
        session, transcript = sample_session
        cfg = dict(config.DEFAULT_CONFIG)
        cfg["archiveDir"] = str(tmp_path / "archive" / "${project_slug}")
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        result = cc_session.archive_session(index, cfg, session)
        assert result == 0
        assert session["status"] == "active"
        assert transcript.exists()
        archived_path = Path(session["archived_path"])
        assert archived_path.exists()
        assert archived_path.read_text() == transcript.read_text()
        assert archived_path.parent == tmp_path / "archive" / session["project_slug"]

    def test_marks_active_session_pending_archive_when_not_copy_mode(self, sample_session, tmp_path: Path):
        session, transcript = sample_session
        cfg = dict(config.DEFAULT_CONFIG)
        cfg["archiveDir"] = str(tmp_path / "archive" / "${project_slug}")
        cfg["archiveCurrentSessionMode"] = "defer"
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        result = cc_session.archive_session(index, cfg, session)
        assert result == 0
        assert session["status"] == "pending-archive"
        assert transcript.exists()

    def test_errors_on_already_pending_archive(self, sample_session, tmp_path: Path):
        session, _ = sample_session
        session["status"] = "pending-archive"
        cfg = dict(config.DEFAULT_CONFIG)
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        with pytest.raises(SystemExit, match="already pending archive"):
            cc_session.archive_session(index, cfg, session)

    def test_archives_ended_session_move(self, sample_session, tmp_path: Path):
        session, transcript = sample_session
        session["status"] = "ended"
        cfg = dict(config.DEFAULT_CONFIG)
        cfg["archiveDir"] = str(tmp_path / "archive" / "${project_slug}")
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        result = cc_session.archive_session(index, cfg, session)
        assert result == 0
        assert not transcript.exists()


class TestArchiveCancel:
    def test_cancels_pending_archive(self, sample_session):
        session, _ = sample_session
        session["status"] = "pending-archive"
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        result = cc_session.archive_cancel(index, session)
        assert result == 0
        assert session["status"] == "active"

    def test_errors_when_not_pending(self, sample_session):
        session, _ = sample_session
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        with pytest.raises(SystemExit, match="not pending archive"):
            cc_session.archive_cancel(index, session)


class TestArchiveAfterEnd:
    def test_archives_pending_archive_session(self, sample_session, tmp_path: Path):
        session, _ = sample_session
        session["status"] = "pending-archive"
        cfg = dict(config.DEFAULT_CONFIG)
        cfg["archiveDir"] = str(tmp_path / "archive" / "${project_slug}")
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        with patch("cc_session.load_index", return_value=index), patch("cc_session.load_config", return_value=cfg):
            result = cc_session.archive_after_end(session["session_id"])
        assert result == 0
        assert session["status"] == "archived"

    def test_returns_0_when_session_not_pending(self, sample_session):
        session, _ = sample_session
        session["status"] = "active"
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        with patch("cc_session.load_index", return_value=index):
            result = cc_session.archive_after_end(session["session_id"])
        assert result == 0

    def test_returns_0_when_session_missing(self):
        index = {"version": 1, "sessions": {}}

        with patch("cc_session.load_index", return_value=index):
            result = cc_session.archive_after_end("nonexistent")
        assert result == 0


class TestDeleteSession:
    def test_marks_active_session_pending_delete(self, sample_session, tmp_path: Path):
        session, _ = sample_session
        cfg = dict(config.DEFAULT_CONFIG)
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        result = cc_session.delete_session(index, cfg, session, "trash")
        assert result == 0
        assert session["status"] == "pending-delete"
        assert session["delete_mode"] == "trash"

    def test_refuses_to_delete_pending_archive(self, sample_session, tmp_path: Path):
        session, _ = sample_session
        session["status"] = "pending-archive"
        cfg = dict(config.DEFAULT_CONFIG)
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        with pytest.raises(SystemExit, match="pending archive"):
            cc_session.delete_session(index, cfg, session, "trash")

    def test_trash_mode(self, sample_session, tmp_path: Path):
        session, transcript = sample_session
        session["status"] = "ended"
        cfg = dict(config.DEFAULT_CONFIG)
        cfg["trashDir"] = str(tmp_path / "trash" / "${project_slug}")
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        result = cc_session.delete_session(index, cfg, session, "trash")
        assert result == 0
        assert not transcript.exists()
        assert session["status"] == "deleted"
        assert session["delete_mode"] == "trash"

    def test_purge_mode(self, sample_session, tmp_path: Path):
        session, transcript = sample_session
        session["status"] = "ended"
        cfg = dict(config.DEFAULT_CONFIG)
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        result = cc_session.delete_session(index, cfg, session, "purge")
        assert result == 0
        assert not transcript.exists()
        assert session["delete_mode"] == "purge"


class TestDeleteCancel:
    def test_cancels_pending_delete(self, sample_session):
        session, _ = sample_session
        session["status"] = "pending-delete"
        session["delete_mode"] = "trash"
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        result = cc_session.delete_cancel(index, session)
        assert result == 0
        assert session["status"] == "active"
        assert "delete_mode" not in session

    def test_raises_when_not_pending_delete(self, sample_session):
        session, _ = sample_session
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        with pytest.raises(SystemExit, match="not pending deletion"):
            cc_session.delete_cancel(index, session)


class TestDeleteAfterEnd:
    def test_deletes_pending_delete_session(self, sample_session, tmp_path: Path):
        session, _ = sample_session
        session["status"] = "pending-delete"
        session["delete_mode"] = "trash"
        cfg = dict(config.DEFAULT_CONFIG)
        cfg["trashDir"] = str(tmp_path / "trash" / "${project_slug}")
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        with patch("cc_session.load_index", return_value=index), patch("cc_session.load_config", return_value=cfg):
            result = cc_session.delete_after_end(session["session_id"])
        assert result == 0
        assert session["status"] == "deleted"

    def test_returns_0_when_session_not_pending(self, sample_session):
        session, _ = sample_session
        session["status"] = "active"
        index = {"version": 1, "sessions": {session["session_id"]: session}}

        with patch("cc_session.load_index", return_value=index):
            result = cc_session.delete_after_end(session["session_id"])
        assert result == 0

    def test_returns_0_when_session_missing(self):
        index = {"version": 1, "sessions": {}}

        with patch("cc_session.load_index", return_value=index):
            result = cc_session.delete_after_end("nonexistent")
        assert result == 0


class TestResolveSession:
    def test_finds_by_id(self):
        index = {"sessions": {"s1": {"session_id": "s1"}}}
        result = cc_session.resolve_session(index, "s1")
        assert result["session_id"] == "s1"

    def test_raises_when_not_found(self):
        index = {"sessions": {}}
        with pytest.raises(SystemExit, match="Session not found"):
            cc_session.resolve_session(index, "s1")


class TestEnsureTranscript:
    def test_raises_when_no_path(self):
        session = {"session_id": "s1"}
        index = {"sessions": {"s1": session}}
        with pytest.raises(SystemExit, match="no transcript path"):
            cc_session.ensure_transcript(session, index)

    def test_raises_when_file_missing(self, tmp_path: Path):
        session = {"session_id": "s1", "transcript_path": "/nonexistent/file.jsonl"}
        index = {"version": 1, "sessions": {"s1": session}}
        with pytest.raises(SystemExit, match="Transcript file not found"):
            cc_session.ensure_transcript(session, index)

    def test_returns_path_when_exists(self, tmp_path: Path):
        transcript = tmp_path / "t.jsonl"
        transcript.write_text("data")
        session = {"session_id": "s1", "transcript_path": str(transcript)}
        index = {"version": 1, "sessions": {"s1": session}}
        result = cc_session.ensure_transcript(session, index)
        assert result == transcript


class TestMain:
    def test_setup_show(self, capsys):
        result = cc_session.main(["setup", "show"])
        assert result == 0
        captured = capsys.readouterr()
        assert "archiveDir=" in captured.out

    def test_setup_reset_all(self, capsys):
        result = cc_session.main(["setup", "reset"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Reset all settings" in captured.out

    def test_setup_reset_archive_dir(self, capsys):
        result = cc_session.main(["setup", "reset", "archive-dir"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Reset archiveDir" in captured.out


class TestValidateDirectoryTemplate:
    def test_rejects_file_path(self):
        with pytest.raises(SystemExit, match="must be a directory path"):
            cc_session.validate_directory_template(
                "archiveDir",
                "/tmp/${project_slug}/file.jsonl",
                dict(config.DEFAULT_CONFIG),
            )

    def test_rejects_same_as_other(self):
        with pytest.raises(SystemExit, match="must be different"):
            cc_session.validate_directory_template(
                "archiveDir",
                config.DEFAULT_CONFIG["trashDir"],
                dict(config.DEFAULT_CONFIG),
            )

    def test_accepts_valid_directory(self):
        cc_session.validate_directory_template(
            "archiveDir",
            "/tmp/my-archive/${project_slug}",
            dict(config.DEFAULT_CONFIG),
        )


class TestSetupUpdate:
    def test_updates_config(self, isolate_state):
        result = cc_session.setup_update("archiveDir", "/tmp/${project_slug}/archive")
        assert result == 0


class TestResolveSessionFallback:
    def test_falls_back_to_any_active(self, tmp_path: Path):
        index = {
            "sessions": {
                "s1": {
                    "session_id": "s1",
                    "status": "active",
                    "cwd": "/other/path",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
            }
        }
        with patch("cc_session.Path") as mock_path_cls:
            mock_cwd = MagicMock()
            mock_cwd.resolve.return_value = Path("/no/match/here")
            mock_path_cls.cwd.return_value = mock_cwd
            result = cc_session.resolve_session(index, None)
        assert result["session_id"] == "s1"

    def test_raises_when_no_active(self):
        index = {"sessions": {"s1": {"session_id": "s1", "status": "ended"}}}
        with pytest.raises(SystemExit, match="No active session"):
            cc_session.resolve_session(index, None)

    def test_falls_back_to_pending_delete_when_allowed(self):
        index = {
            "sessions": {
                "s1": {
                    "session_id": "s1",
                    "status": "pending-delete",
                    "delete_mode": "trash",
                    "cwd": "/proj",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
            }
        }
        with patch("cc_session.Path") as mock_path_cls:
            mock_cwd = MagicMock()
            mock_cwd.resolve.return_value = Path("/no/match/here")
            mock_path_cls.cwd.return_value = mock_cwd
            result = cc_session.resolve_session(index, None, allow_pending=True)
        assert result["session_id"] == "s1"

    def test_does_not_fall_back_to_pending_delete_by_default(self):
        index = {
            "sessions": {
                "s1": {
                    "session_id": "s1",
                    "status": "pending-delete",
                    "delete_mode": "trash",
                    "cwd": "/proj",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
            }
        }
        with (
            patch("cc_session.Path") as mock_path_cls,
            pytest.raises(SystemExit, match="No active session"),
        ):
            mock_cwd = MagicMock()
            mock_cwd.resolve.return_value = Path("/no/match/here")
            mock_path_cls.cwd.return_value = mock_cwd
            cc_session.resolve_session(index, None)

    def test_falls_back_to_pending_archive_when_allowed(self):
        index = {
            "sessions": {
                "s1": {
                    "session_id": "s1",
                    "status": "pending-archive",
                    "cwd": "/proj",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
            }
        }
        with patch("cc_session.Path") as mock_path_cls:
            mock_cwd = MagicMock()
            mock_cwd.resolve.return_value = Path("/no/match/here")
            mock_path_cls.cwd.return_value = mock_cwd
            result = cc_session.resolve_session(index, None, allow_pending=True)
        assert result["session_id"] == "s1"
