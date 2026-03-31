"""Tests for provenance record assembly."""

from __future__ import annotations

from datetime import datetime
import json
import os
from unittest import mock

from flavor.psp.format_2025.provenance import build_provenance


def _build_base() -> dict[str, object]:
    """Call build_provenance with standard test inputs."""
    return build_provenance(
        builder_name="flavor-python",
        builder_version="0.3.21",
        build_timestamp=1743379200,
        platform_os="linux",
        platform_arch="amd64",
        python_version="3.11.12",
        launcher_language="go",
        launcher_version="1.24.1",
        launcher_hash="sha256:" + "ab" * 32,
        signing_key_fingerprint="cd" * 32,
    )


def test_provenance_has_required_fields() -> None:
    """Provenance record contains all spec-required top-level fields."""
    prov = _build_base()
    assert prov["builder"] == "flavor-python"
    assert prov["builder_version"] == "0.3.21"
    assert prov["build_timestamp"] == "2025-03-31T00:00:00+00:00"
    platform = prov["platform"]
    assert isinstance(platform, dict)
    assert platform["os"] == "linux"
    assert platform["arch"] == "amd64"
    python = prov["python"]
    assert isinstance(python, dict)
    assert python["version"] == "3.11.12"
    launcher = prov["launcher"]
    assert isinstance(launcher, dict)
    assert launcher["language"] == "go"
    assert prov["signing_key_fingerprint"] == "cd" * 32


def test_provenance_source_date_epoch_stored() -> None:
    """source_date_epoch field is the raw integer timestamp."""
    prov = _build_base()
    assert prov["source_date_epoch"] == 1743379200


def test_provenance_python_implementation() -> None:
    """Python sub-record contains implementation=cpython."""
    prov = _build_base()
    python = prov["python"]
    assert isinstance(python, dict)
    assert python["implementation"] == "cpython"


def test_provenance_launcher_subrecord() -> None:
    """Launcher sub-record contains language, version, and hash."""
    prov = _build_base()
    launcher = prov["launcher"]
    assert isinstance(launcher, dict)
    assert launcher["language"] == "go"
    assert launcher["version"] == "1.24.1"
    assert launcher["hash"] == "sha256:" + "ab" * 32


def test_provenance_is_json_serialisable() -> None:
    """Provenance record is JSON-serialisable."""
    prov = _build_base()
    serialised = json.dumps(prov, sort_keys=True)
    assert len(serialised) > 50


def test_provenance_reproducible_false_by_default() -> None:
    """reproducible is False when SOURCE_DATE_EPOCH is not set."""
    with mock.patch.dict(os.environ, {}, clear=False):
        env = os.environ.copy()
        env.pop("SOURCE_DATE_EPOCH", None)
        with mock.patch.dict(os.environ, env, clear=True):
            prov = _build_base()
    assert prov["reproducible"] is False


def test_provenance_reproducible_flag() -> None:
    """reproducible is True when SOURCE_DATE_EPOCH is set."""
    with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1743379200"}):
        prov = _build_base()
    assert prov["reproducible"] is True


def test_provenance_reproducible_whitespace_only_epoch() -> None:
    """reproducible is False when SOURCE_DATE_EPOCH is whitespace only."""
    with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "   "}):
        prov = _build_base()
    assert prov["reproducible"] is False


def test_provenance_timestamp_is_iso8601_utc() -> None:
    """build_timestamp is formatted as ISO 8601 UTC."""
    prov = _build_base()
    ts = prov["build_timestamp"]
    assert isinstance(ts, str)
    assert ts.endswith("+00:00")
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None


def test_provenance_empty_signing_key_fingerprint() -> None:
    """Empty signing_key_fingerprint is preserved as-is."""
    prov = build_provenance(
        builder_name="flavor-python",
        builder_version="0.3.21",
        build_timestamp=1743379200,
        platform_os="linux",
        platform_arch="amd64",
        python_version="3.11.12",
        launcher_language="go",
        launcher_version="1.24.1",
        launcher_hash="sha256:" + "ab" * 32,
        signing_key_fingerprint="",
    )
    assert prov["signing_key_fingerprint"] == ""


def test_provenance_empty_launcher_hash() -> None:
    """Empty launcher_hash is preserved as-is."""
    prov = build_provenance(
        builder_name="flavor-python",
        builder_version="0.3.21",
        build_timestamp=1743379200,
        platform_os="linux",
        platform_arch="amd64",
        python_version="3.11.12",
        launcher_language="go",
        launcher_version="1.24.1",
        launcher_hash="",
        signing_key_fingerprint="cd" * 32,
    )
    launcher = prov["launcher"]
    assert isinstance(launcher, dict)
    assert launcher["hash"] == ""


def test_provenance_rust_launcher() -> None:
    """Provenance works correctly with rust launcher_language."""
    prov = build_provenance(
        builder_name="flavor-python",
        builder_version="0.3.21",
        build_timestamp=1743379200,
        platform_os="linux",
        platform_arch="amd64",
        python_version="3.11.12",
        launcher_language="rust",
        launcher_version="1.24.1",
        launcher_hash="sha256:" + "ab" * 32,
        signing_key_fingerprint="cd" * 32,
    )
    launcher = prov["launcher"]
    assert isinstance(launcher, dict)
    assert launcher["language"] == "rust"


def test_provenance_darwin_platform() -> None:
    """Provenance stores darwin/arm64 platform correctly."""
    prov = build_provenance(
        builder_name="flavor-python",
        builder_version="0.3.21",
        build_timestamp=1743379200,
        platform_os="darwin",
        platform_arch="arm64",
        python_version="3.11.12",
        launcher_language="go",
        launcher_version="1.24.1",
        launcher_hash="sha256:" + "ab" * 32,
        signing_key_fingerprint="cd" * 32,
    )
    platform = prov["platform"]
    assert isinstance(platform, dict)
    assert platform["os"] == "darwin"
    assert platform["arch"] == "arm64"


def test_provenance_zero_timestamp() -> None:
    """Unix epoch 0 is handled correctly (1970-01-01T00:00:00+00:00)."""
    prov = build_provenance(
        builder_name="flavor-python",
        builder_version="0.3.21",
        build_timestamp=0,
        platform_os="linux",
        platform_arch="amd64",
        python_version="3.11.12",
        launcher_language="go",
        launcher_version="1.24.1",
        launcher_hash="sha256:" + "ab" * 32,
        signing_key_fingerprint="cd" * 32,
    )
    assert prov["build_timestamp"] == "1970-01-01T00:00:00+00:00"
    assert prov["source_date_epoch"] == 0
