#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for ci/create-release-tag.sh.

The only release script that writes. It stamps VERSION, commits, and creates
the annotated tag a published release and every downloaded artifact points at.

`gh` is stubbed and records what it was asked to do, so the tests can assert on
the calls without creating anything.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

pytestmark = [pytest.mark.ci, pytest.mark.packaging]

SCRIPT = Path(__file__).resolve().parents[2] / "ci" / "create-release-tag.sh"


def _stub_gh(tmp_path: Path, *, existing_tag_sha: str | None) -> tuple[Path, Path]:
    """A `gh` that reports whether the tag exists and logs every call."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    calls = tmp_path / "gh-calls.log"

    if existing_tag_sha is None:
        lookup = "exit 1"  # no such tag
    else:
        lookup = f'printf \'{{"object":{{"sha":"{existing_tag_sha}"}}}}\\n\'; exit 0'

    (bindir / "gh").write_text(
        "#!/bin/bash\n"
        f'echo "$*" >> "{calls}"\n'
        'case "$*" in\n'
        f"  *git/refs/tags/*) {lookup} ;;\n"
        '  *git/tags*) printf \'{"sha":"newtagobj"}\\n\' ;;\n'
        "  *git/refs*) printf '{}\\n' ;;\n"
        "esac\n"
        "exit 0\n"
    )
    (bindir / "gh").chmod(0o755)
    return bindir, calls


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@example.com"],
        ["git", "config", "user.name", "t"],
        ["git", "commit", "-q", "--allow-empty", "-m", "first"],
    ):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    (repo / "VERSION").write_text("0.0.1\n")
    return repo


def _run(repo: Path, bindir: Path, version: str = "9.9.9") -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "GITHUB_REPOSITORY": "provide-io/flavorpack",
    }
    return subprocess.run(
        ["bash", str(SCRIPT), version, f"v{version}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_stamps_version_and_creates_the_tag(tmp_path: Path) -> None:
    """VERSION is written and committed, then the tag is created at that commit."""
    repo = _repo(tmp_path)
    bindir, calls = _stub_gh(tmp_path, existing_tag_sha=None)

    result = _run(repo, bindir)

    assert result.returncode == 0, result.stderr
    assert (repo / "VERSION").read_text().strip() == "9.9.9"

    log = calls.read_text()
    assert "git/tags" in log, "no annotated tag object was created"
    assert "refs/tags/v9.9.9" in log


def test_existing_tag_at_the_same_commit_is_accepted(tmp_path: Path) -> None:
    """Re-running a release must not fail once the tag already points at HEAD."""
    repo = _repo(tmp_path)

    # Stamp and commit first so HEAD is the commit the tag would point at.
    (repo / "VERSION").write_text("9.9.9\n")
    subprocess.run(["git", "add", "VERSION"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "🚀 Release v9.9.9"], cwd=repo, check=True, capture_output=True
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    bindir, _ = _stub_gh(tmp_path, existing_tag_sha=head)

    result = _run(repo, bindir)

    assert result.returncode == 0, f"a re-run over an identical tag failed: {result.stdout}{result.stderr}"
    assert "already exists" in result.stdout


def test_existing_tag_at_a_different_commit_is_refused(tmp_path: Path) -> None:
    """Moving a released tag would orphan every artifact already published."""
    repo = _repo(tmp_path)
    bindir, _ = _stub_gh(tmp_path, existing_tag_sha="0" * 40)

    result = _run(repo, bindir)

    assert result.returncode != 0, f"the tag was allowed to move: {result.stdout}"
    assert "different commit" in result.stdout


def test_arguments_are_required(tmp_path: Path) -> None:
    """Both the version and the tag name have to be supplied."""
    repo = _repo(tmp_path)
    bindir, _ = _stub_gh(tmp_path, existing_tag_sha=None)
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "GITHUB_REPOSITORY": "provide-io/flavorpack",
    }

    result = subprocess.run(
        ["bash", str(SCRIPT)], cwd=repo, capture_output=True, text=True, check=False, env=env
    )

    assert result.returncode != 0


# 🌶️📦🔚
