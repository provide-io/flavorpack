#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for ci/validate-release-version.sh.

The first gate the release workflow runs. Everything after it — tagging,
asset collection, the PyPI upload — assumes this said yes for a good reason.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

pytestmark = [pytest.mark.ci, pytest.mark.packaging]

SCRIPT = Path(__file__).resolve().parents[2] / "ci" / "validate-release-version.sh"


def _run(
    version: str | None, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    args = ["bash", str(SCRIPT)] + ([version] if version is not None else [])
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False, env=env)


def _git_repo(tmp_path: Path) -> Path:
    """A repository with one commit, so tag checks have something to compare."""
    repo = tmp_path / "repo"
    repo.mkdir()
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@example.com"],
        ["git", "config", "user.name", "t"],
        ["git", "commit", "-q", "--allow-empty", "-m", "first"],
    ):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    return repo


@pytest.mark.parametrize("version", ["1.0.0", "0.5.0", "10.20.30", "1.0.0-beta.1", "2.0.0-rc1"])
def test_accepts_valid_versions(version: str, tmp_path: Path) -> None:
    """Semantic versions, with or without a prerelease suffix."""
    result = _run(version, _git_repo(tmp_path))
    assert result.returncode == 0, f"{version} rejected: {result.stdout}"


@pytest.mark.parametrize(
    "version",
    ["1.0", "v1.0.0", "1.0.0.0", "1.0.0-", "abc", "1.0.0 ", "", "01.0.0-!"],
)
def test_rejects_invalid_versions(version: str, tmp_path: Path) -> None:
    """Anything that is not a semantic version stops the release.

    A malformed version reaches artifact names and the tag, so accepting one
    produces a release nothing can refer to.
    """
    result = _run(version, _git_repo(tmp_path))
    assert result.returncode != 0, f"{version!r} was accepted: {result.stdout}"


def test_missing_version_is_rejected(tmp_path: Path) -> None:
    """No argument at all."""
    result = _run(None, _git_repo(tmp_path))
    assert result.returncode != 0


def test_existing_tag_on_a_different_commit_is_refused(tmp_path: Path) -> None:
    """Re-tagging a released version somewhere else would rewrite history.

    The tag is what a published release, and every downloaded artifact, points
    at.
    """
    repo = _git_repo(tmp_path)
    subprocess.run(["git", "tag", "v1.2.3"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "second"], cwd=repo, check=True, capture_output=True
    )

    result = _run("1.2.3", repo)

    assert result.returncode != 0, f"re-tagging a different commit was allowed: {result.stdout}"
    assert "different commit" in result.stdout


def test_existing_tag_on_head_is_allowed(tmp_path: Path) -> None:
    """Re-running a release to publish only is a legitimate case."""
    repo = _git_repo(tmp_path)
    subprocess.run(["git", "tag", "v1.2.3"], cwd=repo, check=True, capture_output=True)

    result = _run("1.2.3", repo)

    assert result.returncode == 0, f"a publish-only re-run was refused: {result.stdout}"


def test_writes_github_output(tmp_path: Path) -> None:
    """The workflow reads version and version_tag from here."""
    import os

    repo = _git_repo(tmp_path)
    out = tmp_path / "gh_output"
    env = {**os.environ, "GITHUB_OUTPUT": str(out)}

    result = _run("3.4.5", repo, env=env)

    assert result.returncode == 0, result.stdout
    written = out.read_text()
    assert "version=3.4.5" in written
    assert "version_tag=v3.4.5" in written


# 🌶️📦🔚
