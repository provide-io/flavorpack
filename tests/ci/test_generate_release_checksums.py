#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for ci/generate-release-checksums.sh.

The release notes tell every user to run `sha256sum -c checksums.txt`. A
package missing from that file cannot be verified, and nothing in the release
job noticed: the generator globbed `*.whl` and `*.psp`, so the two Windows
`.exe` packages were attached to v0.5.0 with no checksum line at all.

Both facts these tests pin -- that `.exe` is covered, and that an empty
release directory is a failure -- are the difference between a release that
is verifiable and one that only looks it.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

pytestmark = [pytest.mark.ci, pytest.mark.packaging]

SCRIPT = Path(__file__).resolve().parents[2] / "ci" / "generate-release-checksums.sh"
VERSION = "9.9.9"


def _asset(release: Path, name: str) -> Path:
    """Write one release asset with content unique to its name."""
    release.mkdir(parents=True, exist_ok=True)
    path = release / name
    path.write_text(f"contents of {name}")
    return path


def _run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "release"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def _checksummed_names(release: Path) -> set[str]:
    """The filenames named in checksums.txt."""
    lines = (release / "checksums.txt").read_text().splitlines()
    return {line.split()[-1] for line in lines if line.strip()}


def test_windows_exe_packages_are_checksummed(tmp_path: Path) -> None:
    """A Windows package is verifiable like every other platform.

    This is the regression: `.exe` is how a Windows flavor package is named,
    and a checksum file that skips it silently ships two unverifiable assets.
    """
    release = tmp_path / "release"
    _asset(release, f"flavor-{VERSION}-linux_amd64.psp")
    _asset(release, f"flavor-{VERSION}-windows_amd64.exe")
    _asset(release, f"flavor-{VERSION}-windows_arm64.exe")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert _checksummed_names(release) == {
        f"flavor-{VERSION}-linux_amd64.psp",
        f"flavor-{VERSION}-windows_amd64.exe",
        f"flavor-{VERSION}-windows_arm64.exe",
    }


def test_wheels_and_packages_are_all_covered(tmp_path: Path) -> None:
    """Every asset type the release attaches appears in checksums.txt."""
    release = tmp_path / "release"
    _asset(release, f"flavorpack-{VERSION}-py3-none-win_amd64.whl")
    _asset(release, f"flavor-{VERSION}-darwin_arm64.psp")
    _asset(release, f"taster-{VERSION}-windows_amd64.exe")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert _checksummed_names(release) == {
        f"flavorpack-{VERSION}-py3-none-win_amd64.whl",
        f"flavor-{VERSION}-darwin_arm64.psp",
        f"taster-{VERSION}-windows_amd64.exe",
    }


def test_checksums_verify_against_the_files(tmp_path: Path) -> None:
    """The file the notes tell users to run actually verifies.

    Generating checksums in a format `sha256sum -c` cannot read would fail the
    same way as generating none: the user finds out, not the release job.
    """
    checker = shutil.which("sha256sum") or shutil.which("shasum")
    if checker is None:
        pytest.skip("no sha256 checker available")

    release = tmp_path / "release"
    _asset(release, f"flavor-{VERSION}-linux_amd64.psp")
    _asset(release, f"flavor-{VERSION}-windows_amd64.exe")

    assert _run(tmp_path).returncode == 0

    cmd = [checker, "-c", "checksums.txt"]
    if checker.endswith("shasum"):
        cmd = [checker, "-a", "256", "-c", "checksums.txt"]
    verify = subprocess.run(cmd, cwd=release, capture_output=True, text=True, check=False)

    assert verify.returncode == 0, verify.stdout + verify.stderr
    # A warning on a correct file is how a verification step teaches users to
    # ignore it. macOS shasum does not skip `#` comment lines the way GNU
    # sha256sum does, so the file carries none.
    assert "improperly formatted" not in verify.stderr, verify.stderr
    assert "WARNING" not in verify.stderr, verify.stderr


def test_checksums_txt_is_not_checksummed(tmp_path: Path) -> None:
    """The output must not list itself: it cannot hash its own final contents."""
    release = tmp_path / "release"
    _asset(release, f"flavor-{VERSION}-linux_amd64.psp")
    _asset(release, "release-notes.md")

    assert _run(tmp_path).returncode == 0

    assert "checksums.txt" not in _checksummed_names(release)


def test_an_empty_release_directory_fails(tmp_path: Path) -> None:
    """A release with nothing to verify is not a release.

    Writing a checksums.txt with a header and no entries is the exact shape of
    a check that reports without checking.
    """
    (tmp_path / "release").mkdir()

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "no" in (result.stdout + result.stderr).lower()


def test_a_missing_release_directory_fails(tmp_path: Path) -> None:
    """Pointing at a directory that was never produced is an error, not a no-op."""
    result = _run(tmp_path)

    assert result.returncode != 0
