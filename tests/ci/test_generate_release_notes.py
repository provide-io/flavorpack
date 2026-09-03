#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for ci/generate-release-notes.sh.

These notes are the release body: they are the list a user reads to know what
the release contains, and the `curl` line they copy. When the list is written
by hand it becomes a second place naming files the pipeline names elsewhere,
and the two drift -- v0.5.0's notes advertised Windows packages the release
job was dropping.

So the notes are checked against the same rule the build scripts apply: a
Windows package is `.exe`, everything else is `.psp`.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

pytestmark = [pytest.mark.ci, pytest.mark.packaging]

SCRIPT = Path(__file__).resolve().parents[2] / "ci" / "generate-release-notes.sh"
VERSION = "9.9.9"
REPOSITORY = "provide-io/flavorpack"


def _run(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], str]:
    result = subprocess.run(
        ["bash", str(SCRIPT), VERSION, REPOSITORY, "notes.md"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    notes = (tmp_path / "notes.md").read_text() if (tmp_path / "notes.md").exists() else ""
    return result, notes


@pytest.mark.parametrize("platform", ["windows_amd64", "windows_arm64"])
def test_windows_packages_are_listed_as_exe(tmp_path: Path, platform: str) -> None:
    """The regression: Windows packages are named the way they are built."""
    result, notes = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert f"flavor-{VERSION}-{platform}.exe" in notes
    assert f"flavor-{VERSION}-{platform}.psp" not in notes


@pytest.mark.parametrize("platform", ["linux_amd64", "linux_arm64", "darwin_amd64", "darwin_arm64"])
def test_other_platforms_are_listed_as_psp(tmp_path: Path, platform: str) -> None:
    """Everything that is not Windows keeps the .psp name."""
    result, notes = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert f"flavor-{VERSION}-{platform}.psp" in notes


def test_every_platform_wheel_is_listed(tmp_path: Path) -> None:
    """A wheel that is published but unlisted is a wheel nobody knows to install."""
    _, notes = _run(tmp_path)

    for tag in [
        "manylinux2014_x86_64",
        "manylinux2014_aarch64",
        "macosx_10_9_x86_64",
        "macosx_11_0_arm64",
        "win_amd64",
        "win_arm64",
    ]:
        assert f"flavorpack-{VERSION}-py3-none-{tag}.whl" in notes


def test_the_quick_install_command_names_a_real_asset(tmp_path: Path) -> None:
    """The curl line is copied verbatim by users, so it must name an attached file.

    It previously curled a versioned name and then ran a `flavor-*.psp` glob,
    which matches whatever else is in the directory.
    """
    _, notes = _run(tmp_path)

    asset = f"flavor-{VERSION}-linux_amd64.psp"
    assert f"https://github.com/{REPOSITORY}/releases/download/v{VERSION}/{asset}" in notes
    assert f"./{asset} --help" in notes
    assert "flavor-*.psp" not in notes


def test_version_and_repository_are_substituted(tmp_path: Path) -> None:
    """No unexpanded placeholder reaches the published release body."""
    _, notes = _run(tmp_path)

    assert "${{" not in notes
    assert "${VERSION}" not in notes
    assert notes.startswith(f"# Flavor Pack {VERSION}")


def test_missing_arguments_fail(tmp_path: Path) -> None:
    """Called without a version, it must not write a release body naming nothing."""
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert not (tmp_path / "release").exists()
