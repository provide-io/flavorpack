#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Regression tests for conftest's launcher-binary discovery.

The probe used to name ``dist/bin/flavor-rs-launcher-darwin_arm64`` literally
and glob only ``helpers/bin``. ``./build.sh`` writes platform-suffixed binaries
into ``dist/bin``, so on Linux — where the suffix is ``linux_amd64`` — a
checkout with helpers freshly built matched nothing, and every
``requires_helpers`` test skipped itself while the suite still reported green.

The failure was invisible on the one platform the literal path happened to
name, which is exactly why it needs a test rather than a careful reading.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.conftest import _check_binaries_available

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.fixture
def fake_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Run the probe against a throwaway checkout, not the real repository.

    Without this the real ``dist/bin`` answers every question and the tests
    pass whatever the probe does.
    """
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)
    # The probe also looks relative to conftest's own location, which would
    # otherwise resolve to the real repository and answer every question.
    monkeypatch.setattr("tests.conftest.__file__", str(tmp_path / "tests" / "conftest.py"))
    monkeypatch.delenv("FLAVOR_LAUNCHER_BIN", raising=False)
    yield tmp_path


def _place(root: Path, relative: str) -> Path:
    """Create a stand-in binary at the given path inside the fake checkout."""
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\x00")
    return target


@pytest.mark.parametrize(
    "relative",
    [
        "dist/bin/flavor-rs-launcher-linux_amd64",
        "dist/bin/flavor-rs-launcher-linux_arm64",
        "dist/bin/flavor-rs-launcher-darwin_arm64",
        "dist/bin/flavor-rs-launcher-darwin_amd64",
        "dist/bin/flavor-rs-launcher-windows_amd64.exe",
        "dist/bin/flavor-rs-launcher",
        "helpers/bin/flavor-rs-launcher",
        "helpers/bin/flavor-rs-launcher-linux_amd64",
    ],
)
def test_finds_the_launcher_on_every_platform(fake_checkout: Path, relative: str) -> None:
    """Discovery does not depend on which platform built the binaries."""
    _place(fake_checkout, relative)
    assert _check_binaries_available(), f"{relative} was not discovered"


def test_reports_nothing_when_the_bin_dir_is_empty(fake_checkout: Path) -> None:
    """An existing but empty bin directory is not mistaken for built helpers."""
    (fake_checkout / "dist" / "bin").mkdir(parents=True)
    (fake_checkout / "helpers" / "bin").mkdir(parents=True)

    assert not _check_binaries_available()


def test_reports_nothing_when_only_other_binaries_are_present(fake_checkout: Path) -> None:
    """A builder alone is not a launcher; the probe is specifically for launchers."""
    _place(fake_checkout, "dist/bin/flavor-rs-builder-linux_amd64")
    _place(fake_checkout, "dist/bin/flavor-go-builder-linux_amd64")

    assert not _check_binaries_available()


def test_env_override_is_honoured(fake_checkout: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FLAVOR_LAUNCHER_BIN points at a launcher outside either bin directory."""
    elsewhere = _place(fake_checkout, "somewhere/else/my-launcher")
    monkeypatch.setenv("FLAVOR_LAUNCHER_BIN", str(elsewhere))

    assert _check_binaries_available()


def test_env_override_pointing_at_nothing_is_not_enough(
    fake_checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale FLAVOR_LAUNCHER_BIN must not stand in for a real binary.

    The previous implementation appended the path unconditionally and then
    tested every candidate with ``exists()``, so this happened to work. Keep it
    asserted: reporting helpers as available when the named file is gone turns
    a clear setup error into a confusing test failure.
    """
    monkeypatch.setenv("FLAVOR_LAUNCHER_BIN", str(fake_checkout / "no" / "such" / "launcher"))

    assert not _check_binaries_available()


# 🌶️📦🔚
