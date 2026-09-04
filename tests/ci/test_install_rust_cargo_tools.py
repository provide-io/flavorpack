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

# A cargo stub that answers `cargo install --list` with the tools the test says
# are present, which is the record the script reads to decide whether to install.
CARGO_STUB = """#!/bin/bash
echo "$@" >> "$CALLS"
if [ "$1" = "install" ] && [ "$2" = "--list" ]; then
    cat "$INSTALLED" 2>/dev/null
fi
exit 0
"""

# A tool that refuses --version and answers --help, which is what cargo-license
# 0.7.0 does. Asking it for a version is what broke the first attempt at this
# script: the install succeeded and the check then called it broken.
TOOL_STUB = """#!/bin/bash
if [ "$1" = "--help" ]; then
    exit 0
fi
exit 2
"""


def _stub_env(tmp_path: Path, tools: tuple[str, ...], version: str) -> tuple[Path, Path]:
    """A PATH holding a cargo stub and a stub for each tool cargo reports installed."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    installed = tmp_path / "installed.txt"

    cargo = bin_dir / "cargo"
    cargo.write_text(CARGO_STUB)
    cargo.chmod(0o755)

    installed.write_text("".join(f"{tool} v{version}:\n    {tool}\n" for tool in tools))

    for tool in tools:
        binary = bin_dir / tool
        binary.write_text(TOOL_STUB)
        binary.chmod(0o755)

    return bin_dir, installed


def _run(tmp_path: Path, *tools: str, version: str = "9.9.9") -> subprocess.CompletedProcess[str]:
    known = tuple(tool for tool in tools if tool.startswith("cargo-") and "nonexistent" not in tool)
    bin_dir, installed = _stub_env(tmp_path, known, version)
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "CALLS": str(tmp_path / "calls.txt"),
        "INSTALLED": str(installed),
        # Pin every tool to what the stub reports installed, so the script takes
        # its already-installed path and never shells out to a real install.
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
    """Every named tool is checked, and the script reports each one.

    The stubs refuse `--version` the way cargo-license does, so this also pins
    that a tool without that flag is not mistaken for a broken install.
    """
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
        # `cargo install --list` reads what is installed; it installs nothing.
        if "cargo install" in line and "--list" not in line and not line.strip().startswith("#")
    ]

    assert installs, "no cargo install lines found"
    for line in installs:
        assert "--locked" in line, f"install is not locked: {line}"
