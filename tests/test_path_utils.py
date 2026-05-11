from __future__ import annotations

from pathlib import Path

from path_utils import (
    dedupe_destination,
    expand_template,
    project_slug,
    resolve_directory,
    safe_session_filename,
)


class TestProjectSlug:
    def test_simple_path(self, tmp_path: Path):
        p = tmp_path / "user" / "project"
        p.mkdir(parents=True)
        resolved = p.resolve()
        expected = str(resolved).strip("/").replace("/", "-")
        assert project_slug(str(p)) == expected

    def test_trailing_slash(self, tmp_path: Path):
        p = tmp_path / "user" / "project"
        p.mkdir(parents=True)
        resolved = p.resolve()
        expected = str(resolved).strip("/").replace("/", "-")
        assert project_slug(str(p) + "/") == expected

    def test_root(self):
        assert project_slug("/") == "root"


class TestExpandTemplate:
    def test_single_variable(self):
        result = expand_template("hello ${name}", {"name": "world"})
        assert result == "hello world"

    def test_multiple_variables(self):
        result = expand_template("${a}/${b}", {"a": "foo", "b": "bar"})
        assert result == "foo/bar"

    def test_missing_variable_kept(self):
        result = expand_template("${missing}", {})
        assert result == "${missing}"

    def test_no_variables(self):
        assert expand_template("plain text", {}) == "plain text"

    def test_alphanumeric_underscore_keys(self):
        result = expand_template("${key_1}", {"key_1": "val"})
        assert result == "val"


class TestResolveDirectory:
    def test_resolves_to_absolute(self, tmp_path: Path):
        template = str(tmp_path / "${slug}")
        result = resolve_directory(template, {"slug": "myproject"})
        assert result == (tmp_path / "myproject").resolve()

    def test_expanduser(self):
        result = resolve_directory("~/${slug}", {"slug": "test"})
        assert result == (Path.home() / "test").resolve()


class TestSafeSessionFilename:
    def test_format(self):
        session = {"session_id": "abc123", "started_at": "2024-01-15T10:30:00Z"}
        result = safe_session_filename(session)
        assert result == "2024-01-15T10-30-00Z__abc123.jsonl"

    def test_missing_started_at(self):
        session = {"session_id": "abc123"}
        result = safe_session_filename(session)
        assert result == "unknown__abc123.jsonl"

    def test_colons_replaced(self):
        session = {"session_id": "x", "started_at": "12:34:56"}
        result = safe_session_filename(session)
        assert ":" not in result


class TestDedupeDestination:
    def test_no_conflict(self, tmp_path: Path):
        target = tmp_path / "test.jsonl"
        assert dedupe_destination(target) == target

    def test_single_conflict(self, tmp_path: Path):
        target = tmp_path / "test.jsonl"
        target.touch()
        result = dedupe_destination(target)
        assert result == tmp_path / "test__1.jsonl"

    def test_multiple_conflicts(self, tmp_path: Path):
        target = tmp_path / "test.jsonl"
        target.touch()
        (tmp_path / "test__1.jsonl").touch()
        result = dedupe_destination(target)
        assert result == tmp_path / "test__2.jsonl"
