from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import config
import pytest


@pytest.fixture(autouse=True)
def isolate_state_dir(tmp_path: Path):
    """Redirect all config file I/O to a temp directory."""
    fake_state = tmp_path / "state"
    fake_state.mkdir()
    with patch.object(config, "state_dir", return_value=fake_state):
        yield fake_state


class TestStateDir:
    def test_returns_path(self):
        result = config.state_dir()
        assert isinstance(result, Path)


class TestEnsureStateDir:
    def test_creates_directory(self, tmp_path: Path):
        target = tmp_path / "new" / "state"
        with patch.object(config, "state_dir", return_value=target):
            result = config.ensure_state_dir()
        assert result == target
        assert target.is_dir()


class TestLoadConfig:
    def test_returns_defaults_when_no_file(self):
        result = config.load_config()
        assert result == dict(config.DEFAULT_CONFIG)

    def test_merges_with_defaults(self, isolate_state_dir: Path):
        overrides = {"archiveDir": "/custom/path"}
        (isolate_state_dir / "config.json").write_text(json.dumps(overrides))
        result = config.load_config()
        assert result["archiveDir"] == "/custom/path"
        assert result["trashDir"] == config.DEFAULT_CONFIG["trashDir"]

    def test_custom_value_overrides_default(self, isolate_state_dir: Path):
        overrides = {"defaultDeleteMode": "purge"}
        (isolate_state_dir / "config.json").write_text(json.dumps(overrides))
        result = config.load_config()
        assert result["defaultDeleteMode"] == "purge"


class TestSaveConfig:
    def test_creates_file(self, isolate_state_dir: Path):
        data = {"archiveDir": "/a"}
        result = config.save_config(data)
        assert result["archiveDir"] == "/a"
        saved = json.loads((isolate_state_dir / "config.json").read_text())
        assert saved["archiveDir"] == "/a"

    def test_merges_with_defaults_on_save(self, isolate_state_dir: Path):
        result = config.save_config({"archiveDir": "/x"})
        assert "trashDir" in result
        assert result["trashDir"] == config.DEFAULT_CONFIG["trashDir"]
