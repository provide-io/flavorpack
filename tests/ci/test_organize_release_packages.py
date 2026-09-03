#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for ci/organize-release-packages.sh.

v0.5.0 shipped without its two Windows flavor packages. They were built,
uploaded as artifacts, downloaded by the release job, and then dropped by a
loop that globbed ``*.psp`` while a Windows flavor build is written ``.exe``.
The loop body never ran, and the script reported success.

Nothing tested this script, and nothing still would: no PR check matches
``ci/**``. These tests are what stands between that shape and another release
that is quietly short a platform.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

pytestmark = [pytest.mark.ci, pytest.mark.packaging]

SCRIPT = Path(__file__).resolve().parents[2] / "ci" / "organize-release-packages.sh"
VERSION = "9.9.9"


def _artifact(root: Path, subdir: str, filename: str) -> Path:
    """Write one downloaded artifact, in the layout the release job produces."""
    path = root / subdir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not a real package")
    return path


def _run(tmp_path: Path, *input_dirs: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "out", VERSION, *input_dirs],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_collects_windows_exe_packages(tmp_path: Path) -> None:
    """A Windows flavor package is named .exe and still belongs in the release.

    This is the v0.5.0 failure exactly: with the old ``*.psp`` glob both files
    are skipped and the script still exits 0.
    """
    _artifact(tmp_path / "flavor-psp", f"flavor-{VERSION}-linux_amd64", f"flavor-{VERSION}-linux_amd64.psp")
    _artifact(
        tmp_path / "flavor-psp", f"flavor-{VERSION}-windows_amd64", f"flavor-{VERSION}-windows_amd64.exe"
    )
    _artifact(
        tmp_path / "flavor-psp", f"flavor-{VERSION}-windows_arm64", f"flavor-{VERSION}-windows_arm64.exe"
    )

    result = _run(tmp_path, "flavor-psp")

    assert result.returncode == 0, result.stderr
    collected = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert collected == [
        f"flavor-{VERSION}-linux_amd64.psp",
        f"flavor-{VERSION}-windows_amd64.exe",
        f"flavor-{VERSION}-windows_arm64.exe",
    ], f"a platform was dropped: {collected}"


def test_collects_from_several_input_directories(tmp_path: Path) -> None:
    """flavor and taster arrive as separate downloads and merge into one set."""
    _artifact(tmp_path / "flavor-psp", f"flavor-{VERSION}-linux_amd64", f"flavor-{VERSION}-linux_amd64.psp")
    _artifact(
        tmp_path / "taster-psp", f"taster-{VERSION}-windows_amd64", f"taster-{VERSION}-windows_amd64.exe"
    )

    result = _run(tmp_path, "flavor-psp", "taster-psp")

    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        f"flavor-{VERSION}-linux_amd64.psp",
        f"taster-{VERSION}-windows_amd64.exe",
    ]


def test_uncollected_files_are_named(tmp_path: Path) -> None:
    """Anything left behind is reported, so a shortfall is visible in the log.

    The v0.5.0 run printed only what it copied, so two missing platforms looked
    exactly like a complete release.
    """
    _artifact(tmp_path / "flavor-psp", f"flavor-{VERSION}-linux_amd64", f"flavor-{VERSION}-linux_amd64.psp")
    _artifact(tmp_path / "flavor-psp", f"flavor-{VERSION}-linux_amd64", "build.log")

    result = _run(tmp_path, "flavor-psp")

    assert result.returncode == 0, result.stderr
    assert "build.log" in result.stdout, f"an uncollected file was not named: {result.stdout}"


def test_collecting_nothing_fails(tmp_path: Path) -> None:
    """A release that would ship no binaries must not be cut.

    The previous version printed "⚠️ No PSP packages collected" and returned
    success, so this case would have produced an empty release.
    """
    (tmp_path / "flavor-psp" / "empty").mkdir(parents=True)

    result = _run(tmp_path, "flavor-psp")

    assert result.returncode != 0, f"collecting nothing reported success: {result.stdout}"
    assert "No packages collected" in result.stdout


def test_version_in_filename_is_rewritten(tmp_path: Path) -> None:
    """Artifacts built at the pipeline's version are renamed to the release's."""
    _artifact(tmp_path / "flavor-psp", "flavor-0.0.1-linux_amd64", "flavor-0.0.1-linux_amd64.psp")

    result = _run(tmp_path, "flavor-psp")

    assert result.returncode == 0, result.stderr
    assert [p.name for p in (tmp_path / "out").iterdir()] == [f"flavor-{VERSION}-linux_amd64.psp"]


def test_missing_input_directory_is_skipped_not_fatal(tmp_path: Path) -> None:
    """A pipeline that produced no taster packages should not stop the release."""
    _artifact(tmp_path / "flavor-psp", f"flavor-{VERSION}-linux_amd64", f"flavor-{VERSION}-linux_amd64.psp")

    result = _run(tmp_path, "flavor-psp", "taster-psp")

    assert result.returncode == 0, result.stderr
    assert "taster-psp" in result.stdout


# 🌶️📦🔚
