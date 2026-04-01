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

# Env vars that must appear in ALL THREE: Go, Rust, and Python source
SHARED_ENV_VARS = [
    "FLAVOR_LOG_LEVEL",
    "FLAVOR_CACHE_DIR",
    "FLAVOR_CONFIG_DIR",
    "FLAVOR_TRUSTED_KEYS_DIR",
    "FLAVOR_VALIDATION",
    "FLAVOR_LAUNCHER_BIN",
    "FLAVOR_WORKENV_BASE",
]

# Env vars that must appear in BOTH Go and Rust source (but not necessarily Python)
GO_RUST_ONLY_ENV_VARS = [
    "FLAVOR_LAUNCHER_LOG_LEVEL",
    "FLAVOR_LOG_PATH",
    "FLAVOR_WORKENV",
    "FLAVOR_WORKENV_CACHE",
    "FLAVOR_EXEC_MODE",
]

# Env vars that must appear in Python source only
PYTHON_ONLY_ENV_VARS = [
    "FLAVOR_BUILDER_BIN",
    "FLAVOR_SETUP_LOG_LEVEL",
    "FLAVOR_INCLUDE_BUILD_HOST",
    "FLAVOR_WHEEL_CACHE",
    "FLAVOR_METADATA_PACKAGE_NAME",
    "FLAVOR_PACKAGE_NAME",
    "FLAVOR_VERSION",
    "FLAVOR_ENTRY_POINT",
    "FLAVOR_OUTPUT_FORMAT",
    "FLAVOR_OUTPUT_FILE",
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
@pytest.mark.parametrize("var", SHARED_ENV_VARS)
def test_shared_env_var_in_python(var: str) -> None:
    """Each shared env var must appear in Python source."""
    assert _grep_py(var), f'"{var}" not found in Python source (src/flavor/)'


@pytest.mark.parity
@pytest.mark.parity_category("Env Vars")
@pytest.mark.parametrize("var", PYTHON_ONLY_ENV_VARS)
def test_python_only_env_var_in_python(var: str) -> None:
    """Each Python-only env var must appear in Python source."""
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
@pytest.mark.parametrize("var", GO_RUST_ONLY_ENV_VARS)
def test_go_rust_env_var_in_go(var: str) -> None:
    """Each Go/Rust-only env var must appear (as a string constant) in Go source."""
    assert _grep_src(GO_SRC, f'"{var}"'), f'"{var}" not found in Go source'


@pytest.mark.parity
@pytest.mark.parity_category("Env Vars")
@pytest.mark.parametrize("var", GO_RUST_ONLY_ENV_VARS)
def test_go_rust_env_var_in_rust(var: str) -> None:
    """Each Go/Rust-only env var must appear (as a string constant) in Rust source."""
    assert _grep_src(RUST_SRC, f'"{var}"'), f'"{var}" not found in Rust source'


@pytest.mark.parity
@pytest.mark.parity_category("Env Vars")
def test_old_flavor_cache_absent_from_rust() -> None:
    """FLAVOR_CACHE (old name) must not appear in Rust source; it was renamed to FLAVOR_CACHE_DIR."""
    assert not _grep_src(RUST_SRC, '"FLAVOR_CACHE"'), (
        'Old name "FLAVOR_CACHE" still present in Rust source; should be "FLAVOR_CACHE_DIR"'
    )


# 🌶️📦🔚
