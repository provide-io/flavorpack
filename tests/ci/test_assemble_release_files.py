#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for ci/assemble-release-files.sh.

This is the last hop before assets are attached to the GitHub release. It ran
as an inline `run:` block of `cp ... 2>/dev/null || true` lines that globbed
`*.psp` only, so both Windows `.exe` packages -- built, collected, and
uploaded -- were dropped here, and the `|| true` guaranteed the job stayed
green while it happened.

The v0.5.0 Windows binaries were attached by hand. These tests exist so that
never has to happen again.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

pytestmark = [pytest.mark.ci, pytest.mark.packaging]

SCRIPT = Path(__file__).resolve().parents[2] / "ci" / "assemble-release-files.sh"
VERSION = "9.9.9"


def _artifact(root: Path, artifact: str, name: str) -> Path:
    """Write one file inside a downloaded artifact directory."""
    path = root / artifact / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"contents of {name}")
    return path


def _run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "artifacts", "release"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def _baseline(root: Path) -> None:
    """The two assets every release carries, produced by the generate-assets job."""
    _artifact(root, "release-assets", "release-notes.md")
    _artifact(root, "release-assets", "checksums.txt")


def _assembled(tmp_path: Path) -> set[str]:
    """Assembled filenames, minus the baseline assets each test would repeat."""
    return {p.name for p in (tmp_path / "release").iterdir()} - {
        "release-notes.md",
        "checksums.txt",
    }


def test_windows_exe_packages_reach_the_release(tmp_path: Path) -> None:
    """The regression: a Windows package is assembled like any other platform."""
    artifacts = tmp_path / "artifacts"
    _artifact(artifacts, "release-psp", f"flavor-{VERSION}-linux_amd64.psp")
    _artifact(artifacts, "release-psp", f"flavor-{VERSION}-windows_amd64.exe")
    _artifact(artifacts, "release-psp", f"flavor-{VERSION}-windows_arm64.exe")
    _baseline(artifacts)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert _assembled(tmp_path) == {
        f"flavor-{VERSION}-linux_amd64.psp",
        f"flavor-{VERSION}-windows_amd64.exe",
        f"flavor-{VERSION}-windows_arm64.exe",
    }


def test_assembles_wheels_packages_and_notes(tmp_path: Path) -> None:
    """Every artifact the release job downloads contributes what it should."""
    artifacts = tmp_path / "artifacts"
    _artifact(artifacts, "release-wheels", f"flavorpack-{VERSION}-py3-none-win_amd64.whl")
    _artifact(artifacts, "release-psp", f"flavor-{VERSION}-darwin_arm64.psp")
    _artifact(artifacts, "release-psp", f"taster-{VERSION}-windows_amd64.exe")
    _artifact(artifacts, "release-assets", "checksums.txt")
    _artifact(artifacts, "release-assets", "release-notes.md")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert _assembled(tmp_path) == {
        f"flavorpack-{VERSION}-py3-none-win_amd64.whl",
        f"flavor-{VERSION}-darwin_arm64.psp",
        f"taster-{VERSION}-windows_amd64.exe",
    }
    assert (tmp_path / "release" / "checksums.txt").is_file()
    assert (tmp_path / "release" / "release-notes.md").is_file()


def test_assembled_packages_stay_executable(tmp_path: Path) -> None:
    """A package that arrives without its execute bit is not runnable.

    The whole point of a PSP is that a user downloads it and runs it.
    """
    artifacts = tmp_path / "artifacts"
    psp = _artifact(artifacts, "release-psp", f"flavor-{VERSION}-linux_amd64.psp")
    psp.chmod(0o755)
    _baseline(artifacts)

    assert _run(tmp_path).returncode == 0

    import os

    assert os.access(tmp_path / "release" / psp.name, os.X_OK)


def test_release_notes_are_required(tmp_path: Path) -> None:
    """Without release-notes.md the release body is empty and the job fails later.

    Failing here names the missing file; failing later names a path.
    """
    artifacts = tmp_path / "artifacts"
    _artifact(artifacts, "release-psp", f"flavor-{VERSION}-linux_amd64.psp")

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "release-notes.md" in result.stdout + result.stderr


def test_assembling_no_packages_fails(tmp_path: Path) -> None:
    """A release with no wheels and no packages must not be published."""
    artifacts = tmp_path / "artifacts"
    _baseline(artifacts)

    result = _run(tmp_path)

    assert result.returncode != 0


def test_a_missing_artifacts_directory_fails(tmp_path: Path) -> None:
    """Nothing downloaded is a failed release, not an empty one."""
    result = _run(tmp_path)

    assert result.returncode != 0


def test_reports_what_it_assembled(tmp_path: Path) -> None:
    """The log names counts per type, so a short release is visible in the job output."""
    artifacts = tmp_path / "artifacts"
    _artifact(artifacts, "release-wheels", f"flavorpack-{VERSION}-py3-none-win_amd64.whl")
    _artifact(artifacts, "release-psp", f"flavor-{VERSION}-windows_amd64.exe")
    _baseline(artifacts)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert f"flavor-{VERSION}-windows_amd64.exe" in result.stdout
