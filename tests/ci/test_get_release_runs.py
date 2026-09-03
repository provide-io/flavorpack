#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for ci/get-release-runs.sh.

This script decides which pipeline runs a release takes its artifacts from.
Everything the release publishes comes from the two run IDs it returns, so a
wrong answer here ships the wrong binaries under the right version number.

`gh` is stubbed: the script's logic is the subject, not GitHub.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import textwrap

import pytest

pytestmark = [pytest.mark.ci, pytest.mark.packaging]

SCRIPT = Path(__file__).resolve().parents[2] / "ci" / "get-release-runs.sh"
VERSION = "9.9.9"


def _stub_gh(tmp_path: Path, runs: dict[str, list[str]], artifacts: dict[str, list[str]]) -> Path:
    """A `gh` that answers from fixtures.

    `gh run list` yields run IDs per workflow; `gh api .../artifacts` yields
    artifact names per run.
    """
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "gh"

    newline = "\\n"

    def _emit(values: list[str]) -> str:
        return " ".join(values) if values else "''"

    run_cases = "\n".join(
        f'      *{workflow}*) printf "%s{newline}" {_emit(ids)} ;;' for workflow, ids in runs.items()
    )
    art_cases = "\n".join(
        f'      *runs/{run_id}/artifacts*) printf "%s{newline}" {_emit(names)} ;;'
        for run_id, names in artifacts.items()
    )

    stub.write_text(
        textwrap.dedent(f"""\
        #!/bin/bash
        case "$1" in
          run)
            case "$*" in
        {run_cases}
              *) : ;;
            esac
            ;;
          api)
            case "$*" in
        {art_cases}
              *) exit 1 ;;
            esac
            ;;
        esac
        """)
    )
    stub.chmod(0o755)
    return bindir


def _run(tmp_path: Path, bindir: Path, version: str = VERSION) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "GITHUB_REPOSITORY": "provide-io/flavorpack",
    }
    return subprocess.run(
        ["bash", str(SCRIPT), version], cwd=tmp_path, capture_output=True, text=True, check=False, env=env
    )


def test_finds_the_run_carrying_this_version(tmp_path: Path) -> None:
    """The newest run whose artifacts carry the release version wins."""
    bindir = _stub_gh(
        tmp_path,
        runs={"helper-prep.yml": ["300", "200"], "flavor-pipeline.yml": ["301", "201"]},
        artifacts={
            "300": [f"flavor-helpers-{VERSION}-all"],
            "200": ["flavor-helpers-0.0.1-all"],
            "301": [f"flavor-wheel-{VERSION}-linux_amd64"],
            "201": ["flavor-wheel-0.0.1-linux_amd64"],
        },
    )

    result = _run(tmp_path, bindir)

    assert result.returncode == 0, result.stderr
    assert "300" in result.stdout
    assert "301" in result.stdout


def test_skips_runs_built_at_another_version(tmp_path: Path) -> None:
    """A newer run for a different version must not be taken.

    Artifacts are matched by the version in their name, so a release cut while
    main has moved on has to reach past the newer runs.
    """
    bindir = _stub_gh(
        tmp_path,
        runs={"helper-prep.yml": ["400", "300"], "flavor-pipeline.yml": ["401", "301"]},
        artifacts={
            "400": ["flavor-helpers-1.2.3-all"],
            "300": [f"flavor-helpers-{VERSION}-all"],
            "401": ["flavor-wheel-1.2.3-linux_amd64"],
            "301": [f"flavor-wheel-{VERSION}-linux_amd64"],
        },
    )

    result = _run(tmp_path, bindir)

    assert result.returncode == 0, result.stderr
    assert "300" in result.stdout, "took a run built at the wrong version"
    assert "301" in result.stdout


def test_no_matching_run_fails(tmp_path: Path) -> None:
    """A release with no artifacts for its version must stop here.

    Continuing would assemble a release out of whatever ran most recently.
    """
    bindir = _stub_gh(
        tmp_path,
        runs={"helper-prep.yml": ["300"], "flavor-pipeline.yml": ["301"]},
        artifacts={"300": ["flavor-helpers-0.0.1-all"], "301": ["flavor-wheel-0.0.1-linux_amd64"]},
    )

    result = _run(tmp_path, bindir)

    assert result.returncode != 0, f"a release with no matching artifacts was allowed: {result.stdout}"


def test_version_is_required(tmp_path: Path) -> None:
    """Without a version there is nothing to match against."""
    bindir = _stub_gh(tmp_path, runs={}, artifacts={})

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "RELEASE_VERSION": ""},
    )

    assert result.returncode != 0


# 🌶️📦🔚
