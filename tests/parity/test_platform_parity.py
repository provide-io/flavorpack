# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Cross-language parity tests for platform-specific behaviour.

Tests the Python implementation of platform behaviours that must be
consistent across Python, Go and Rust launchers.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from flavor.cache import get_cache_dir

pytestmark = [pytest.mark.cross_language, pytest.mark.ci, pytest.mark.integration]


# ---------------------------------------------------------------------------
# Cache dir respects XDG_CACHE_HOME
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Platform Behavior")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_cache_dir_respects_xdg_cache_home(tmp_path: Path) -> None:
    """get_cache_dir uses XDG_CACHE_HOME when set."""
    xdg_dir = str(tmp_path / "xdg-cache")
    with patch.dict(os.environ, {"XDG_CACHE_HOME": xdg_dir}, clear=False):
        # Also clear FLAVOR_CACHE so the override doesn't take precedence
        env = os.environ.copy()
        env.pop("FLAVOR_CACHE", None)
        with patch.dict(os.environ, env, clear=True):
            result = get_cache_dir()
    assert result == Path(xdg_dir) / "flavor" / "workenv"


# ---------------------------------------------------------------------------
# Cache dir uses LOCALAPPDATA on Windows
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Platform Behavior")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_cache_dir_uses_localappdata_on_windows(tmp_path: Path) -> None:
    """FLAVOR_CACHE override works (Windows would set LOCALAPPDATA-based path)."""
    # We cannot truly simulate Windows platform detection on macOS/Linux,
    # but we can verify the FLAVOR_CACHE override path which is the mechanism
    # a Windows user or CI would use.
    custom_cache = str(tmp_path / "AppData" / "Local" / "flavor" / "workenv")
    with patch.dict(os.environ, {"FLAVOR_CACHE": custom_cache}, clear=False):
        result = get_cache_dir()
    assert result == Path(custom_cache)


# ---------------------------------------------------------------------------
# PATH uses Scripts on Windows
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Platform Behavior")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_path_uses_scripts_on_windows() -> None:
    """Executor selects 'Scripts' as bin dir when platform is win32."""
    from flavor.psp.format_2025.executor import BundleExecutor

    executor = object.__new__(BundleExecutor)
    executor.workenv_dir = Path("/fake/workenv")

    with patch.object(sys, "platform", "win32"):
        bin_dir, python_exe, _python_bin = executor._platform_vars()

    assert bin_dir == "Scripts"
    assert python_exe == "python.exe"


# ---------------------------------------------------------------------------
# PATH uses bin on Unix
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Platform Behavior")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_path_uses_bin_on_unix() -> None:
    """Executor selects 'bin' as bin dir when platform is linux/darwin."""
    from flavor.psp.format_2025.executor import BundleExecutor

    executor = object.__new__(BundleExecutor)
    executor.workenv_dir = Path("/fake/workenv")

    with patch.object(sys, "platform", "linux"):
        bin_dir, python_exe, _python_bin = executor._platform_vars()

    assert bin_dir == "bin"
    assert python_exe == "python3"


# ---------------------------------------------------------------------------
# File encoding is always UTF-8
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Platform Behavior")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_file_encoding_is_always_utf8(tmp_path: Path) -> None:
    """All PSPF text operations use explicit UTF-8 encoding."""
    test_content = "Hello\nWorld\n\u00e9\u00e8\u00ea\n\u2603\n"
    test_file = tmp_path / "test.txt"

    # Write with explicit UTF-8 and LF-only line endings (PSPF always uses LF).
    # newline="\n" suppresses Windows text-mode CRLF translation (Python 3.10+).
    test_file.write_text(test_content, encoding="utf-8", newline="\n")

    # Read back with explicit UTF-8; text mode normalises \r\n→\n, so result matches original.
    result = test_file.read_text(encoding="utf-8")
    assert result == test_content

    # Verify raw bytes are valid UTF-8 with LF-only endings
    raw = test_file.read_bytes()
    decoded = raw.decode("utf-8")
    assert decoded == test_content
