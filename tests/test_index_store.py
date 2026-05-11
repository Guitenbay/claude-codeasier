from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import index_store
import pytest


@pytest.fixture(autouse=True)
def isolate_state(tmp_path: Path):
    fake_state = tmp_path / "state"
    fake_state.mkdir()
    with (
        patch("config.state_dir", return_value=fake_state),
        patch("index_store.state_dir", return_value=fake_state),
    ):
        yield fake_state


class TestNowIso:
    def test_format(self):
        result = index_store.now_iso()
        assert result.endswith("Z")
        assert "T" in result
        # Should not have microseconds
        assert "." not in result

    def test_parseable(self):
        result = index_store.now_iso()
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert dt.tzinfo is not None


class TestLoadIndex:
    def test_empty_index(self):
        result = index_store.load_index()
        assert result["version"] == index_store.INDEX_VERSION
        assert result["sessions"] == {}

    def test_loads_existing(self, isolate_state: Path):
        data = {"version": 1, "sessions": {"s1": {"status": "active"}}}
        (isolate_state / "session-index.json").write_text(json.dumps(data))
        result = index_store.load_index()
        assert result["sessions"]["s1"]["status"] == "active"

    def test_handles_missing_sessions_key(self, isolate_state: Path):
        (isolate_state / "session-index.json").write_text('{"version": 1}')
        result = index_store.load_index()
        assert result["sessions"] == {}

    def test_handles_missing_version(self, isolate_state: Path):
        (isolate_state / "session-index.json").write_text('{"sessions": {}}')
        result = index_store.load_index()
        assert result["version"] == index_store.INDEX_VERSION


class TestSaveIndex:
    def test_saves_to_disk(self, isolate_state: Path):
        index = {"version": 1, "sessions": {}}
        index_store.save_index(index)
        saved = json.loads((isolate_state / "session-index.json").read_text())
        assert saved == index


class TestGetSession:
    def test_found(self):
        index = {"sessions": {"s1": {"status": "active"}}}
        result = index_store.get_session(index, "s1")
        assert result is not None
        assert result["status"] == "active"

    def test_not_found(self):
        index = {"sessions": {}}
        assert index_store.get_session(index, "s1") is None


class TestUpsertSession:
    def test_insert_new(self):
        index = {"sessions": {}}
        result = index_store.upsert_session(index, "s1", {"status": "active"})
        assert result["session_id"] == "s1"
        assert result["status"] == "active"
        assert index["sessions"]["s1"] is result

    def test_update_existing(self):
        index = {"sessions": {"s1": {"session_id": "s1", "status": "active"}}}
        result = index_store.upsert_session(index, "s1", {"status": "ended"})
        assert result["status"] == "ended"
        assert result["session_id"] == "s1"

    def test_preserves_existing_fields(self):
        index = {"sessions": {"s1": {"session_id": "s1", "cwd": "/home"}}}
        index_store.upsert_session(index, "s1", {"status": "active"})
        assert index["sessions"]["s1"]["cwd"] == "/home"


class TestMarkSessionMissing:
    def test_marks_existing(self):
        index = {"sessions": {"s1": {"session_id": "s1", "status": "active"}}}
        result = index_store.mark_session_missing(index, "s1")
        assert result is not None
        assert result["status"] == "missing"
        assert "updated_at" in result

    def test_returns_none_for_missing(self):
        index = {"sessions": {}}
        assert index_store.mark_session_missing(index, "s1") is None


class TestLatestActiveSession:
    def test_returns_most_recent(self):
        index = {
            "sessions": {
                "s1": {"status": "active", "updated_at": "2024-01-01T00:00:00Z"},
                "s2": {"status": "active", "updated_at": "2024-06-01T00:00:00Z"},
            }
        }
        result = index_store.latest_active_session(index)
        assert result is not None
        assert result["updated_at"] == "2024-06-01T00:00:00Z"

    def test_returns_none_when_empty(self):
        assert index_store.latest_active_session({"sessions": {}}) is None

    def test_filters_by_cwd(self):
        index = {
            "sessions": {
                "s1": {"status": "active", "cwd": "/a", "updated_at": "2024-06-01T00:00:00Z"},
                "s2": {"status": "active", "cwd": "/b", "updated_at": "2024-01-01T00:00:00Z"},
            }
        }
        result = index_store.latest_active_session(index, cwd="/b")
        assert result is not None
        assert result["cwd"] == "/b"

    def test_falls_back_when_cwd_no_match(self):
        index = {
            "sessions": {
                "s1": {"status": "active", "cwd": "/a", "updated_at": "2024-01-01T00:00:00Z"},
            }
        }
        result = index_store.latest_active_session(index, cwd="/nonexistent")
        assert result is not None

    def test_ignores_non_active(self):
        index = {
            "sessions": {
                "s1": {"status": "ended", "updated_at": "2024-06-01T00:00:00Z"},
            }
        }
        assert index_store.latest_active_session(index) is None

    def test_uses_started_at_fallback(self):
        index = {
            "sessions": {
                "s1": {"status": "active", "started_at": "2024-01-01T00:00:00Z"},
            }
        }
        result = index_store.latest_active_session(index)
        assert result is not None
