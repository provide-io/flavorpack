"""Regression tests for PackagingOrchestrator._detect_launcher_type.

The detector picks which launcher a package is built around. Getting it wrong is
not a crash -- it silently packages a Go launcher as a Rust one -- so the cases
that matter most here are the ones where the function is *able* to return a
plausible answer from input it did not actually understand.

The regression these cover: `run` is called with text=False, so stdout is bytes,
but the function used to coerce anything that was not bytes to b"". A decoded
string therefore lost the version banner before it was ever matched and fell
through to the "rust" default. Tests that asserted "rust" passed by accident,
because "rust" is what the broken path returned.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flavor.packaging.orchestrator import PackagingOrchestrator


def _make_orchestrator(tmp_path: Path) -> PackagingOrchestrator:
    return PackagingOrchestrator(
        package_integrity_key_path=None,
        public_key_path=None,
        output_flavor_path=str(tmp_path / "out.psp"),
        build_config={},
        manifest_dir=tmp_path,
        package_name="testpkg",
        version="1.0.0",
        entry_point="main:cli",
    )


# --------------------------------------------------------------------------
# Filename fast path: our own helpers are named, so no subprocess should run.
# --------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("flavor-go-launcher-windows_amd64.exe", "go"),
        ("flavor-go-launcher-darwin_arm64", "go"),
        ("flavor-rs-launcher-linux_amd64", "rust"),
        ("flavor-rust-launcher-linux_arm64", "rust"),
        ("FLAVOR-GO-LAUNCHER-DARWIN_ARM64", "go"),
    ],
)
@patch("flavor.packaging.orchestrator.run")
def test_filename_is_authoritative_and_skips_the_subprocess(
    mock_run: MagicMock,
    tmp_path: Path,
    filename: str,
    expected: str,
) -> None:
    orch = _make_orchestrator(tmp_path)
    assert orch._detect_launcher_type(tmp_path / filename) == expected
    mock_run.assert_not_called()


# --------------------------------------------------------------------------
# Version banner, as bytes. This is the production contract: run(text=False).
# --------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        (b"flavor-go-launcher version 1.2.3", "go"),
        (b"flavor-rs-launcher 0.5.0", "rust"),
        (b"go version go1.22.0 darwin/arm64", "go"),
        (b"rustc 1.79.0", "rust"),
    ],
)
@patch("flavor.packaging.orchestrator.run")
def test_detects_from_bytes_version_output(
    mock_run: MagicMock,
    tmp_path: Path,
    stdout: bytes,
    expected: str,
) -> None:
    orch = _make_orchestrator(tmp_path)
    mock_run.return_value.stdout = stdout
    assert orch._detect_launcher_type(tmp_path / "launcher") == expected


# --------------------------------------------------------------------------
# Version banner, already decoded. This is the case that regressed: the banner
# was discarded and every call landed on the "rust" default.
# --------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("flavor-go-launcher version 1.2.3", "go"),
        ("flavor-rs-launcher 0.5.0", "rust"),
        ("go version go1.22.0 darwin/arm64", "go"),
        ("rustc 1.79.0", "rust"),
    ],
)
@patch("flavor.packaging.orchestrator.run")
def test_detects_from_str_version_output(
    mock_run: MagicMock,
    tmp_path: Path,
    stdout: str,
    expected: str,
) -> None:
    orch = _make_orchestrator(tmp_path)
    mock_run.return_value.stdout = stdout
    assert orch._detect_launcher_type(tmp_path / "launcher") == expected


# --------------------------------------------------------------------------
# Precedence. A Go banner that happens to mention rust is still a Go launcher;
# the exact helper name has to beat the loose substring.
# --------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "stdout",
    [
        b"flavor-go-launcher 1.2.3 (rust-free build)",
        "flavor-go-launcher 1.2.3 (rust-free build)",
    ],
    ids=["bytes", "str"],
)
@patch("flavor.packaging.orchestrator.run")
def test_exact_helper_name_beats_the_loose_rust_substring(
    mock_run: MagicMock,
    tmp_path: Path,
    stdout: bytes | str,
) -> None:
    orch = _make_orchestrator(tmp_path)
    mock_run.return_value.stdout = stdout
    assert orch._detect_launcher_type(tmp_path / "launcher") == "go"


# --------------------------------------------------------------------------
# Genuinely unrecognised output. "rust" is the documented default; what matters
# is that it is reached only when nothing matched, and that a warning is logged
# rather than the guess passing silently.
# --------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "stdout",
    [b"some other launcher", "some other launcher", b"", "", None],
    ids=["bytes", "str", "empty-bytes", "empty-str", "none"],
)
@patch("flavor.packaging.orchestrator.logger")
@patch("flavor.packaging.orchestrator.run")
def test_unrecognised_output_warns_before_falling_back_to_rust(
    mock_run: MagicMock,
    mock_logger: MagicMock,
    tmp_path: Path,
    stdout: bytes | str | None,
) -> None:
    orch = _make_orchestrator(tmp_path)
    mock_run.return_value.stdout = stdout
    assert orch._detect_launcher_type(tmp_path / "launcher") == "rust"
    assert mock_logger.warning.called


@pytest.mark.unit
@patch("flavor.packaging.orchestrator.logger")
@patch("flavor.packaging.orchestrator.run")
def test_a_recognised_banner_does_not_warn(
    mock_run: MagicMock,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> None:
    orch = _make_orchestrator(tmp_path)
    mock_run.return_value.stdout = "flavor-go-launcher version 1.2.3"
    assert orch._detect_launcher_type(tmp_path / "launcher") == "go"
    assert not mock_logger.warning.called


# --------------------------------------------------------------------------
# Undecodable bytes must not raise; errors="replace" keeps the match working.
# --------------------------------------------------------------------------


@pytest.mark.unit
@patch("flavor.packaging.orchestrator.run")
def test_handles_non_utf8_subprocess_output(mock_run: MagicMock, tmp_path: Path) -> None:
    orch = _make_orchestrator(tmp_path)
    mock_run.return_value.stdout = b"\x90\x91flavor-go-launcher 1.2.3\n"
    assert orch._detect_launcher_type(tmp_path / "launcher.exe") == "go"
