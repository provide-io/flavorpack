#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Parity test: FLAVOR_* environment variable names are consistent across Go, Rust, and Python.

Reads the actual source files and asserts that shared env var names appear in both
codebases, and that the old `FLAVOR_CACHE` name (renamed to `FLAVOR_CACHE_DIR`) no
longer appears in the Rust source.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
GO_SRC = REPO_ROOT / "src/flavor-go"
RUST_SRC = REPO_ROOT / "src/flavor-rs"
PYTHON_SRC = REPO_ROOT / "src/flavor"
pytestmark = [pytest.mark.cross_language, pytest.mark.ci, pytest.mark.integration]

# Env vars that must appear in Python source.
# Note: Python uses FLAVOR_CACHE (not FLAVOR_CACHE_DIR) for its own cache directory;
# FLAVOR_CACHE_DIR is a Go/Rust concept.  The list below covers vars that Python
# reads or exposes as configuration knobs.
PYTHON_SHARED_ENV_VARS = [
    "FLAVOR_CONFIG_DIR",
    "FLAVOR_TRUSTED_KEYS_DIR",
    "FLAVOR_LAUNCHER_BIN",
    "FLAVOR_WORKENV_BASE",
    "FLAVOR_VALIDATION",
]

# Env vars that must appear in BOTH Go and Rust source
SHARED_ENV_VARS = [
    "FLAVOR_LOG_LEVEL",
    "FLAVOR_LAUNCHER_LOG_LEVEL",
    "FLAVOR_LOG_PATH",
    "FLAVOR_CACHE_DIR",
    "FLAVOR_CONFIG_DIR",
    "FLAVOR_TRUSTED_KEYS_DIR",
    "FLAVOR_WORKENV",
    "FLAVOR_WORKENV_CACHE",
    "FLAVOR_WORKENV_BASE",
    "FLAVOR_EXEC_MODE",
    "FLAVOR_LAUNCHER_BIN",
    "FLAVOR_VALIDATION",
]


def _grep_src(root: Path, string: str) -> bool:
    """Return True if the exact string appears anywhere under root (.go or .rs files)."""
    suffix = ".go" if "flavor-go" in str(root) else ".rs"
    for f in root.rglob(f"*{suffix}"):
        try:
            if string in f.read_text(errors="ignore"):
                return True
        except OSError:
            pass
    return False


def _grep_py(string: str) -> bool:
    """Return True if the exact string appears anywhere under PYTHON_SRC (.py files)."""
    for f in PYTHON_SRC.rglob("*.py"):
        try:
            if string in f.read_text(errors="ignore"):
                return True
        except OSError:
            pass
    return False


@pytest.mark.parity
@pytest.mark.parity_category("Env Vars")
@pytest.mark.parametrize("var", PYTHON_SHARED_ENV_VARS)
def test_shared_env_var_in_python(var: str) -> None:
    """Each shared env var must appear in Python source."""
    assert _grep_py(var), f'"{var}" not found in Python source (src/flavor/)'


@pytest.mark.parity
@pytest.mark.parity_category("Env Vars")
@pytest.mark.parametrize("var", SHARED_ENV_VARS)
def test_shared_env_var_in_go(var: str) -> None:
    """Each shared env var must appear (as a string constant) in Go source."""
    assert _grep_src(GO_SRC, f'"{var}"'), f'"{var}" not found in Go source'


@pytest.mark.parity
@pytest.mark.parity_category("Env Vars")
@pytest.mark.parametrize("var", SHARED_ENV_VARS)
def test_shared_env_var_in_rust(var: str) -> None:
    """Each shared env var must appear (as a string constant) in Rust source."""
    assert _grep_src(RUST_SRC, f'"{var}"'), f'"{var}" not found in Rust source'


@pytest.mark.parity
@pytest.mark.parity_category("Env Vars")
def test_old_flavor_cache_absent_from_rust() -> None:
    """FLAVOR_CACHE (old name) must not appear in Rust source; it was renamed to FLAVOR_CACHE_DIR."""
    assert not _grep_src(RUST_SRC, '"FLAVOR_CACHE"'), (
        'Old name "FLAVOR_CACHE" still present in Rust source; should be "FLAVOR_CACHE_DIR"'
    )


# 🌶️📦🔚
