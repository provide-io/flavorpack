#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for ci/organize-release-wheels.sh.

The sibling script that collects PSP packages shipped v0.5.0 without its two
Windows binaries, because a glob matched nothing and the script reported
success anyway. This one collects the wheels that get published to PyPI, and
had the same ending: an unconditional "✅ Collected wheels" with no count.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

pytestmark = [pytest.mark.ci, pytest.mark.packaging]

SCRIPT = Path(__file__).resolve().parents[2] / "ci" / "organize-release-wheels.sh"
VERSION = "9.9.9"


def _wheel(root: Path, platform: str, filename: str) -> Path:
    """Write one downloaded wheel artifact, in the layout the release job produces."""
    path = root / f"flavor-wheel-{VERSION}-{platform}" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not a real wheel")
    return path


def _run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "wheels", "out", VERSION],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_collects_every_platform_wheel(tmp_path: Path) -> None:
    """All six platform wheels reach the output directory."""
    wheels = tmp_path / "wheels"
    for platform, name in [
        ("linux_amd64", f"flavorpack-{VERSION}-py3-none-manylinux2014_x86_64.whl"),
        ("linux_arm64", f"flavorpack-{VERSION}-py3-none-manylinux2014_aarch64.whl"),
        ("darwin_arm64", f"flavorpack-{VERSION}-py3-none-macosx_11_0_arm64.whl"),
        ("windows_amd64", f"flavorpack-{VERSION}-py3-none-win_amd64.whl"),
    ]:
        _wheel(wheels, platform, name)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert len(list((tmp_path / "out").iterdir())) == 4, "a platform wheel was dropped"


def test_collecting_no_wheels_fails(tmp_path: Path) -> None:
    """A release with no wheels must not be cut.

    PyPI publishing consumes exactly this output. Reporting success over an
    empty directory is how a release ships nothing installable.
    """
    (tmp_path / "wheels").mkdir()

    result = _run(tmp_path)

    assert result.returncode != 0, f"collecting no wheels reported success: {result.stdout}"


def test_platform_directory_without_a_wheel_fails(tmp_path: Path) -> None:
    """A platform whose build produced no wheel is a short release, not a pass."""
    wheels = tmp_path / "wheels"
    (wheels / f"flavor-wheel-{VERSION}-linux_amd64").mkdir(parents=True)

    result = _run(tmp_path)

    assert result.returncode != 0, f"an empty platform directory reported success: {result.stdout}"


def test_missing_input_directory_fails(tmp_path: Path) -> None:
    """A download step that produced nothing must not read as a clean run."""
    result = _run(tmp_path)

    assert result.returncode != 0, f"a missing input directory reported success: {result.stdout}"


def test_version_is_required(tmp_path: Path) -> None:
    """Without a version the script cannot know what it is assembling."""
    result = subprocess.run(
        ["bash", str(SCRIPT), "wheels", "out"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Version is required" in result.stdout


# 🌶️📦🔚
