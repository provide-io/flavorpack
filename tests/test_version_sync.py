#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Regression tests for scripts/check_version_sync.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from types import ModuleType

# ---------------------------------------------------------------------------
# Import the script as a module via importlib
# ---------------------------------------------------------------------------
_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "check_version_sync.py"


@pytest.fixture(scope="session")
def version_sync() -> ModuleType:
    """Import check_version_sync.py as a module."""
    spec = importlib.util.spec_from_file_location("check_version_sync", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_version_sync"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_REPO_ROOT = _SCRIPT_PATH.resolve().parent.parent
_CANONICAL_VERSION = (_REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# 1. Full script returns 0 (success) when all versions match
# ---------------------------------------------------------------------------
class TestMainSuccess:
    """Verify the main() entry-point returns 0 with the current repo state."""

    def test_main_returns_zero(self, version_sync: ModuleType) -> None:
        result: int = version_sync.main()
        assert result == 0, "main() should return 0 when all versions are in sync"


# ---------------------------------------------------------------------------
# 2. VERSION file reader
# ---------------------------------------------------------------------------
class TestReadVersionFile:
    """Verify _read_version_file returns the expected canonical version."""

    def test_reads_version_file(self, version_sync: ModuleType) -> None:
        version: str = version_sync._read_version_file()
        assert version == _CANONICAL_VERSION

    def test_version_is_semver(self, version_sync: ModuleType) -> None:
        version: str = version_sync._read_version_file()
        parts = version.split(".")
        assert len(parts) == 3, f"Expected MAJOR.MINOR.PATCH, got {version}"
        for part in parts:
            assert part.isdigit(), f"Non-numeric segment in version: {version}"


# ---------------------------------------------------------------------------
# 3. Go builder version reader
# ---------------------------------------------------------------------------
class TestGoBuilderVersion:
    """Verify _go_builder_version reads the Go main.go constant."""

    def test_reads_go_version(self, version_sync: ModuleType) -> None:
        version = version_sync._go_builder_version()
        assert version is not None, "Go builder main.go should be found"
        assert version == _CANONICAL_VERSION


# ---------------------------------------------------------------------------
# 4. Rust Cargo.toml version reader
# ---------------------------------------------------------------------------
class TestRustCargoVersion:
    """Verify _rust_cargo_version reads the Cargo.toml version."""

    def test_reads_cargo_version(self, version_sync: ModuleType) -> None:
        version = version_sync._rust_cargo_version()
        assert version is not None, "Cargo.toml should be found"
        assert version == _CANONICAL_VERSION


# ---------------------------------------------------------------------------
# 5. Rust version.rs reader
# ---------------------------------------------------------------------------
class TestRustVersionRs:
    """Verify _rust_version_rs reads the Rust version constant."""

    def test_reads_version_rs(self, version_sync: ModuleType) -> None:
        version = version_sync._rust_version_rs()
        assert version is not None, "version.rs should be found"
        assert version == _CANONICAL_VERSION


# ---------------------------------------------------------------------------
# 6. Python version (dynamic from VERSION file)
# ---------------------------------------------------------------------------
class TestPythonVersion:
    """Verify _python_version returns the dynamic version from pyproject.toml."""

    def test_reads_python_version(self, version_sync: ModuleType) -> None:
        version = version_sync._python_version()
        assert version is not None, "pyproject.toml should be found"
        assert version == _CANONICAL_VERSION


# ---------------------------------------------------------------------------
# 7. Mismatch detection
# ---------------------------------------------------------------------------
class TestMismatchDetection:
    """Verify that main() returns 1 when a reader reports a wrong version.

    The script's main() iterates _LANG_READERS dict, so we must patch the dict
    values rather than the module-level functions.
    """

    @staticmethod
    def _patched_readers(
        version_sync: ModuleType,
        overrides: dict[str, str | None],
    ) -> dict[str, object]:
        """Build a patched copy of _LANG_READERS with specific return values."""
        original: dict[str, object] = dict(version_sync._LANG_READERS)
        for key, value in overrides.items():
            original[key] = lambda v=value: v
        return original

    def test_detects_go_mismatch(self, version_sync: ModuleType) -> None:
        readers = self._patched_readers(version_sync, {"go (builder main.go)": "0.0.0"})
        with patch.object(version_sync, "_LANG_READERS", readers):
            result: int = version_sync.main()
        assert result == 1, "main() should return 1 when Go version mismatches"

    def test_detects_rust_cargo_mismatch(self, version_sync: ModuleType) -> None:
        readers = self._patched_readers(version_sync, {"rust (Cargo.toml)": "99.99.99"})
        with patch.object(version_sync, "_LANG_READERS", readers):
            result: int = version_sync.main()
        assert result == 1, "main() should return 1 when Cargo.toml version mismatches"

    def test_detects_rust_version_rs_mismatch(self, version_sync: ModuleType) -> None:
        readers = self._patched_readers(version_sync, {"rust (version.rs)": "1.2.3"})
        with patch.object(version_sync, "_LANG_READERS", readers):
            result: int = version_sync.main()
        assert result == 1, "main() should return 1 when version.rs version mismatches"

    def test_detects_python_mismatch(self, version_sync: ModuleType) -> None:
        readers = self._patched_readers(version_sync, {"python (pyproject.toml)": "0.0.1"})
        with patch.object(version_sync, "_LANG_READERS", readers):
            result: int = version_sync.main()
        assert result == 1, "main() should return 1 when Python version mismatches"

    def test_skips_missing_reader(self, version_sync: ModuleType) -> None:
        """When a reader returns None the language is skipped, not treated as mismatch."""
        readers = self._patched_readers(version_sync, {"go (builder main.go)": None})
        with patch.object(version_sync, "_LANG_READERS", readers):
            result: int = version_sync.main()
        assert result == 0, "main() should skip (not fail) when a reader returns None"
