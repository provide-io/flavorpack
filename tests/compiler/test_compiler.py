"""Tests for the compiler.py module."""

from pathlib import Path
import subprocess
from typing import Never

import pytest

from flavor.compiler import _find_go_source_path, ensure_go_binary
from flavor.exceptions import BuildError


def test_ensure_go_binary_go_not_found(monkeypatch) -> None:
    """Tests that BuildError is raised if 'go' command is not in PATH."""
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(BuildError, match="Go compiler not found"):
        ensure_go_binary("any")


def test_ensure_go_binary_build_fails(tmp_path: Path, monkeypatch) -> None:
    """Tests that BuildError is raised if 'go build' fails."""
    monkeypatch.setattr("flavor.compiler._get_cache_dir", lambda: tmp_path)

    fake_src_path = tmp_path / "src"
    # THE FIX: Create the parent directory before trying to touch a file in it.
    fake_src_path.mkdir()
    (fake_src_path / "go.mod").touch()
    monkeypatch.setattr("flavor.compiler._find_go_source_path", lambda: fake_src_path)

    def mock_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=[], returncode=1, stderr="build failed")

    monkeypatch.setattr("subprocess.run", mock_run)

    with pytest.raises(BuildError, match="Failed to compile Go binary"):
        ensure_go_binary("flavor-go")


def test_ensure_go_binary_gomod_not_found(tmp_path: Path, monkeypatch) -> None:
    """Tests that BuildError is raised if go.mod is missing."""
    monkeypatch.setattr("flavor.compiler._get_cache_dir", lambda: tmp_path)
    fake_src_path = tmp_path / "src"
    fake_src_path.mkdir()
    monkeypatch.setattr("flavor.compiler._find_go_source_path", lambda: fake_src_path)

    with pytest.raises(BuildError, match="go.mod not found"):
        ensure_go_binary("flavor-go")


def test_find_go_source_path_not_found(monkeypatch) -> None:
    """Tests that BuildError is raised if the Go source directory cannot be found."""

    def mock_files(*args) -> Never:
        raise FileNotFoundError

    monkeypatch.setattr("importlib.resources.files", mock_files)
    with pytest.raises(BuildError, match="Could not find bundled Go source directory"):
        _find_go_source_path()


def test_ensure_go_binary_already_exists(tmp_path: Path, monkeypatch) -> None:
    """Tests the fast path where the binary is already compiled."""
    cache_dir = tmp_path / "cache"
    bin_dir = cache_dir / "bin"
    bin_dir.mkdir(parents=True)
    binary_path = bin_dir / "flavor-go"
    binary_path.touch()

    monkeypatch.setattr("flavor.compiler._get_cache_dir", lambda: cache_dir)
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/go")

    result = ensure_go_binary("flavor-go")
    assert result == binary_path


# 📦🍜🧪🪄
