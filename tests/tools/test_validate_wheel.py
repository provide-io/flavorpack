"""Tests for validate_wheel.py helper validation logic."""

from pathlib import Path
import sys
import tempfile
import zipfile

# Import from tools/ directory
sys.path.insert(0, str(Path(__file__).parents[2] / "tools"))
from validate_wheel import _parse_wheel_platform, validate_helpers  # type: ignore[import-not-found]

from flavor.psp.format_2025.metadata.assembly import _semver_key


def make_wheel(stem: str, helpers: list[str]) -> Path:
    """Create a minimal in-memory wheel zip at a temp path."""
    tmp = Path(tempfile.mktemp(suffix=".whl"))
    with zipfile.ZipFile(tmp, "w") as zf:
        for helper in helpers:
            zf.writestr(f"flavor/helpers/bin/{helper}", b"fake-binary")
    # Rename to give it the right stem
    dest = tmp.parent / f"{stem}.whl"
    tmp.rename(dest)
    return dest


def test_parse_universal_wheel() -> None:
    p = Path("flavorpack-0.3.21-py3-none-any.whl")
    assert _parse_wheel_platform(p) == "any"


def test_parse_linux_amd64() -> None:
    p = Path("flavorpack-0.3.21-py3-none-linux_x86_64.whl")
    assert _parse_wheel_platform(p) == "linux_amd64"


def test_parse_darwin_arm64() -> None:
    p = Path("flavorpack-0.3.21-py3-none-macosx_14_0_arm64.whl")
    assert _parse_wheel_platform(p) == "darwin_arm64"


def test_parse_windows_amd64() -> None:
    p = Path("flavorpack-0.3.21-py3-none-win_amd64.whl")
    assert _parse_wheel_platform(p) == "windows_amd64"


def test_universal_wheel_no_helpers_passes() -> None:
    whl = make_wheel("flavorpack-0.3.21-py3-none-any", [])
    try:
        success, msgs = validate_helpers(whl)
        assert success
        assert any("Universal" in m for m in msgs)
    finally:
        whl.unlink(missing_ok=True)


def test_platform_wheel_correct_helpers_passes() -> None:
    whl = make_wheel(
        "flavorpack-0.3.21-py3-none-linux_x86_64",
        [
            "flavor-go-builder-0.3.21-linux_amd64",
            "flavor-go-launcher-0.3.21-linux_amd64",
            "flavor-rs-builder-0.3.21-linux_amd64",
            "flavor-rs-launcher-0.3.21-linux_amd64",
        ],
    )
    try:
        success, msgs = validate_helpers(whl)
        assert success, msgs
    finally:
        whl.unlink(missing_ok=True)


def test_platform_wheel_wrong_platform_fails() -> None:
    whl = make_wheel(
        "flavorpack-0.3.21-py3-none-linux_x86_64",
        [
            "flavor-go-builder-0.3.21-darwin_arm64",  # wrong platform
            "flavor-go-launcher-0.3.21-linux_amd64",
            "flavor-rs-builder-0.3.21-linux_amd64",
            "flavor-rs-launcher-0.3.21-linux_amd64",
        ],
    )
    try:
        success, msgs = validate_helpers(whl)
        assert not success
        assert any("flavor-go-builder" in m and "❌" in m for m in msgs)
    finally:
        whl.unlink(missing_ok=True)


def test_platform_wheel_duplicate_helpers_fails() -> None:
    whl = make_wheel(
        "flavorpack-0.3.21-py3-none-linux_x86_64",
        [
            "flavor-rs-launcher-0.3.20-linux_amd64",
            "flavor-rs-launcher-0.3.21-linux_amd64",  # duplicate
            "flavor-go-builder-0.3.21-linux_amd64",
            "flavor-go-launcher-0.3.21-linux_amd64",
            "flavor-rs-builder-0.3.21-linux_amd64",
        ],
    )
    try:
        success, msgs = validate_helpers(whl)
        assert not success
        assert any("Multiple" in m for m in msgs)
    finally:
        whl.unlink(missing_ok=True)


def test_platform_wheel_missing_helper_fails() -> None:
    whl = make_wheel(
        "flavorpack-0.3.21-py3-none-linux_x86_64",
        [
            "flavor-go-builder-0.3.21-linux_amd64",
            # missing go-launcher, rs-builder, rs-launcher
        ],
    )
    try:
        success, _ = validate_helpers(whl)
        assert not success
    finally:
        whl.unlink(missing_ok=True)


def test_universal_wheel_with_helpers_fails() -> None:
    """Universal wheel containing native helpers is a packaging defect — must fail."""
    whl = make_wheel(
        "flavorpack-0.3.21-py3-none-any",
        ["flavor-rs-launcher-0.3.21-linux_amd64"],
    )
    try:
        success, msgs = validate_helpers(whl)
        assert not success
        assert any("❌" in m for m in msgs)
    finally:
        whl.unlink(missing_ok=True)


def test_semver_key_orders_correctly() -> None:
    """_semver_key must select 0.3.21 over 0.3.9 (lexicographic sort gets this wrong)."""
    p9 = Path("flavor-rs-launcher-0.3.9-darwin_arm64")
    p21 = Path("flavor-rs-launcher-0.3.21-darwin_arm64")
    assert _semver_key(p21) > _semver_key(p9)
    assert sorted([p9, p21], key=_semver_key, reverse=True)[0] == p21
