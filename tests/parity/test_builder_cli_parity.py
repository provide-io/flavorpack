#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Parity test: Python orchestrator passes flag names that match Go and Rust builder CLIs."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
pytestmark = [pytest.mark.cross_language, pytest.mark.ci, pytest.mark.integration]

# Flags Python passes to external builders (from orchestrator.py build_cmd_args).
# If a flag is renamed in Go or Rust the corresponding test below will fail immediately.
BUILDER_FLAGS = [
    "--manifest",
    "--output",
    "--launcher-bin",
    "--private-key",
    "--public-key",
    "--key-seed",
]


def _in_file(path: Path, text: str) -> bool:
    try:
        return text in path.read_text(errors="ignore")
    except OSError:
        return False


@pytest.mark.parity
@pytest.mark.parity_category("Builder CLI")
@pytest.mark.parametrize("flag", BUILDER_FLAGS)
def test_flag_in_python_orchestrator(flag: str) -> None:
    """Python orchestrator must pass this flag to external builders."""
    orchestrator = REPO_ROOT / "src/flavor/packaging/orchestrator.py"
    assert _in_file(orchestrator, flag), f'Flag "{flag}" not found in orchestrator.py'


@pytest.mark.parity
@pytest.mark.parity_category("Builder CLI")
@pytest.mark.parametrize("flag", BUILDER_FLAGS)
def test_flag_in_go_builder(flag: str) -> None:
    """Go builder must accept this flag (cobra/pflag registers it by name without --)."""
    go_main = REPO_ROOT / "src/flavor-go/cmd/flavor-go-builder/main.go"
    flag_name = flag.lstrip("-")
    assert _in_file(go_main, flag_name), f'Flag "{flag}" ({flag_name}) not found in Go builder main.go'


@pytest.mark.parity
@pytest.mark.parity_category("Builder CLI")
@pytest.mark.parametrize("flag", BUILDER_FLAGS)
def test_flag_in_rust_builder(flag: str) -> None:
    """Rust builder must accept this flag (clap converts snake_case struct fields to kebab-case)."""
    rs_builder = REPO_ROOT / "src/flavor-rs/src/bin/flavor-rs-builder.rs"
    flag_name = flag.lstrip("-")
    snake_name = flag_name.replace("-", "_")
    content = rs_builder.read_text(errors="ignore")
    assert flag_name in content or snake_name in content, (
        f'Flag "{flag}" (kebab: {flag_name}, snake: {snake_name}) not found in Rust builder'
    )


# 🌶️📦🔚
