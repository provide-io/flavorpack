#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for ci/install-rust-cargo-tools.sh.

Four workflows installed their cargo subcommands with bare `cargo install`, so
each run resolved every tool's dependency tree afresh. When tinyvec 1.13.0 was
published broken, `cargo install cargo-deny` could not build for four hours and
License Compliance failed on a pull request whose own dependencies were fine.

What these pin is that the install is reproducible -- a pinned version and
`--locked` every time -- and that a tool which does not end up runnable fails
here, naming the tool, rather than inside the check that needs it.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

pytestmark = [pytest.mark.ci, pytest.mark.packaging]

SCRIPT = Path(__file__).resolve().parents[2] / "ci" / "install-rust-cargo-tools.sh"

# A cargo stub that records its arguments and reports the pinned version back,
# so the script's "already installed" path is what runs.
CARGO_STUB = """#!/bin/bash
echo "$@" >> "$CALLS"
if [ "$2" = "--version" ]; then
    echo "$1 {version}"
fi
exit 0
"""


def _stub_cargo(tmp_path: Path, version: str = "9.9.9") -> tuple[Path, Path]:
    """A PATH containing only a cargo stub, plus the file it logs calls to."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    calls = tmp_path / "calls.txt"

    cargo = bin_dir / "cargo"
    cargo.write_text(CARGO_STUB.format(version=version))
    cargo.chmod(0o755)

    return bin_dir, calls


def _run(tmp_path: Path, *tools: str, version: str = "9.9.9") -> subprocess.CompletedProcess[str]:
    bin_dir, calls = _stub_cargo(tmp_path, version)
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "CALLS": str(calls),
        # Pin every tool to what the stub reports, so the script takes its
        # already-installed path and never shells out to a real install.
        "CARGO_LICENSE_VERSION": version,
        "CARGO_DENY_VERSION": version,
        "CARGO_AUDIT_VERSION": version,
    }
    return subprocess.run(
        ["bash", str(SCRIPT), *tools],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_installs_each_tool_it_is_given(tmp_path: Path) -> None:
    """Every named tool is checked, and the script reports each one."""
    result = _run(tmp_path, "cargo-license", "cargo-deny")

    assert result.returncode == 0, result.stderr
    assert "cargo-license" in result.stdout
    assert "cargo-deny" in result.stdout


def test_an_unknown_tool_fails_rather_than_installing_unpinned(tmp_path: Path) -> None:
    """A typo in a workflow must not become an unpinned install.

    Installing whatever that name resolves to on crates.io is the wrong
    recovery: it is how an unreviewed dependency enters CI.
    """
    result = _run(tmp_path, "cargo-nonexistent")

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "cargo-nonexistent" in output
    assert "unpinned" in output


def test_calling_it_with_no_tools_fails(tmp_path: Path) -> None:
    """An install step that installs nothing must not report success."""
    result = _run(tmp_path)

    assert result.returncode != 0
    assert "Usage" in result.stdout + result.stderr


def test_every_pinned_version_is_exact(tmp_path: Path) -> None:
    """No pin is a range: `cargo install` must resolve one version, not the newest.

    A caret or wildcard would put the tool's own release schedule back in the
    build, which is the failure this script exists to prevent.
    """
    body = SCRIPT.read_text()
    pins = [line.split(":-")[1].split("}")[0] for line in body.splitlines() if "_VERSION:-" in line]

    assert pins, "no version pins found"
    for pin in pins:
        assert pin[0].isdigit(), f"pin is not an exact version: {pin}"
        assert not any(char in pin for char in "^~*<>= "), f"pin is a range: {pin}"


def test_the_source_fallback_is_locked(tmp_path: Path) -> None:
    """Every `cargo install` in the script carries --locked.

    Without it the tool's own lockfile is ignored and its dependencies resolve
    afresh, which is exactly what let a broken upstream release fail CI.
    """
    body = SCRIPT.read_text()
    installs = [
        line.strip()
        for line in body.splitlines()
        if "cargo install" in line and not line.strip().startswith("#")
    ]

    assert installs, "no cargo install lines found"
    for line in installs:
        assert "--locked" in line, f"install is not locked: {line}"
