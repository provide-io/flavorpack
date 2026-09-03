#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the naming contract in ci/build-flavor-self.sh and
ci/build-taster-with-psp.sh.

These scripts run a real `flavor pack`, which needs the whole toolchain and
minutes to complete. What is worth testing without that is the part that
actually broke: what the output is called, and whether the script reports the
same name it created.

A Windows build is written .exe so the binary is directly runnable. The two
scripts disagreed about that until v0.5.0 — flavor used .exe, taster used .psp
— and the release organizer globbed *.psp, so both Windows flavor packages
were built, downloaded and silently dropped. taster meanwhile shipped under a
name Windows will not execute.

`flavor pack` is stubbed: it creates the file it was told to and nothing else.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

pytestmark = [pytest.mark.ci, pytest.mark.packaging]

CI = Path(__file__).resolve().parents[2] / "ci"
FLAVOR_SELF = CI / "build-flavor-self.sh"
TASTER = CI / "build-taster-with-psp.sh"
VERSION = "9.9.9"

# The stub honours --output and creates a runnable file, so the scripts'
# own smoke tests (--version, --help) succeed.
PACKER_STUB = """#!/bin/bash
out=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if [ -n "$out" ]; then
  mkdir -p "$(dirname "$out")"
  printf '#!/bin/sh\\necho stub\\n' > "$out"
  chmod +x "$out"
fi
exit 0
"""


def _stub_packer(tmp_path: Path, name: str) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    p = bindir / name
    p.write_text(PACKER_STUB)
    p.chmod(0o755)
    return bindir


def _env(bindir: Path) -> dict[str, str]:
    return {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}


class TestFlavorSelfBuildNaming:
    """ci/build-flavor-self.sh"""

    def _workspace(self, tmp_path: Path) -> tuple[Path, Path]:
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "pyproject.toml").write_text("[project]\nname='x'\n")
        (ws / "wheel.whl").write_text("wheel")
        (ws / "launcher").write_text("launcher")
        return ws, _stub_packer(tmp_path, "flavor")

    @pytest.mark.parametrize(
        ("platform", "expected"),
        [
            ("linux_amd64", f"flavor-{VERSION}-linux_amd64.psp"),
            ("darwin_arm64", f"flavor-{VERSION}-darwin_arm64.psp"),
            ("windows_amd64", f"flavor-{VERSION}-windows_amd64.exe"),
            ("windows_arm64", f"flavor-{VERSION}-windows_arm64.exe"),
        ],
    )
    def test_output_extension(self, platform: str, expected: str, tmp_path: Path) -> None:
        """Windows gets .exe so the binary is directly runnable; others get .psp."""
        ws, bindir = self._workspace(tmp_path)

        result = subprocess.run(
            ["bash", str(FLAVOR_SELF), platform, VERSION, "wheel.whl", "launcher"],
            cwd=ws,
            capture_output=True,
            text=True,
            check=False,
            env=_env(bindir),
        )

        assert result.returncode == 0, result.stderr
        produced = sorted(p.name for p in (ws / "artifacts").iterdir())
        assert produced == [expected], f"named {produced}, expected [{expected!r}]"

    def test_output_is_executable(self, tmp_path: Path) -> None:
        """A package nobody can execute is not a deliverable."""
        ws, bindir = self._workspace(tmp_path)

        subprocess.run(
            ["bash", str(FLAVOR_SELF), "linux_amd64", VERSION, "wheel.whl", "launcher"],
            cwd=ws,
            capture_output=True,
            text=True,
            check=True,
            env=_env(bindir),
        )

        built = ws / "artifacts" / f"flavor-{VERSION}-linux_amd64.psp"
        assert os.access(built, os.X_OK), "built package is not executable"


class TestTasterBuildNaming:
    """ci/build-taster-with-psp.sh"""

    def _workspace(self, tmp_path: Path) -> tuple[Path, Path]:
        ws = tmp_path / "ws"
        (ws / "tests" / "taster").mkdir(parents=True)
        (ws / "tests" / "taster" / "pyproject.toml").write_text("[project]\nname='t'\n")

        packer = ws / "flavor.psp"
        packer.write_text(PACKER_STUB)
        packer.chmod(0o755)

        (ws / "launcher").write_text("launcher")
        return ws, packer

    @pytest.mark.parametrize(
        ("platform", "expected"),
        [
            ("linux_amd64", f"taster-{VERSION}-linux_amd64.psp"),
            ("windows_amd64", f"taster-{VERSION}-windows_amd64.exe"),
            ("windows_arm64", f"taster-{VERSION}-windows_arm64.exe"),
        ],
    )
    def test_output_extension_matches_flavor(self, platform: str, expected: str, tmp_path: Path) -> None:
        """taster follows the same rule as flavor.

        It did not until v0.5.0, and that disagreement is what let the release
        organizer drop the Windows flavor packages while taster kept appearing.
        """
        ws, packer = self._workspace(tmp_path)

        result = subprocess.run(
            ["bash", str(TASTER), f"./{packer.name}", "launcher", platform, VERSION],
            cwd=ws,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        built = ws / "tests" / "taster" / expected
        assert built.is_file(), (
            f"expected {expected}, found {[p.name for p in (ws / 'tests' / 'taster').iterdir()]}"
        )

    def test_reported_path_is_the_file_it_created(self, tmp_path: Path) -> None:
        """The script reports the name it chose, rather than the caller rebuilding it.

        taster-pipeline.yml used to spell the filename a second time, so the two
        could drift. Two places naming one file is what shipped a release short
        two platforms.
        """
        ws, packer = self._workspace(tmp_path)
        gh_output = tmp_path / "gh_out"

        result = subprocess.run(
            ["bash", str(TASTER), f"./{packer.name}", "launcher", "windows_amd64", VERSION],
            cwd=ws,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "GITHUB_OUTPUT": str(gh_output)},
        )

        reported = [
            line.split("=", 1)[1] for line in result.stdout.splitlines() if line.startswith("taster_path=")
        ]
        assert reported, f"no taster_path reported: {result.stdout}"
        assert Path(reported[0]).is_file(), f"reported a path that does not exist: {reported[0]}"
        assert reported[0].endswith(".exe"), f"reported the wrong extension: {reported[0]}"
        assert f"taster_path={reported[0]}" in gh_output.read_text()


# 🌶️📦🔚
