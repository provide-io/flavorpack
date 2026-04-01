#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for `flavor policy init/show/check` subcommands."""

from __future__ import annotations

import os
from pathlib import Path
import time
from unittest import mock

from click.testing import CliRunner

from flavor.cli import cli
from flavor.commands.policy import _get_current_platform, _is_root
from flavor.config.policy import OperatorPolicy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_reader(metadata: dict[str, object] | None = None, build_timestamp: int = 0) -> mock.MagicMock:
    """Return a mock PSPFReader context manager."""
    mock_index = mock.MagicMock()
    mock_index.build_timestamp = build_timestamp

    reader = mock.MagicMock()
    reader.__enter__ = mock.MagicMock(return_value=reader)
    reader.__exit__ = mock.MagicMock(return_value=False)
    reader.read_metadata.return_value = metadata if metadata is not None else {}
    reader.read_index.return_value = mock_index
    return reader


# ---------------------------------------------------------------------------
# policy init
# ---------------------------------------------------------------------------


def test_policy_init_creates_file(tmp_path: Path) -> None:
    """flavor policy init creates policy.toml when it does not exist."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        result = runner.invoke(cli, ["policy", "init"])

    assert result.exit_code == 0, result.output
    policy_file = tmp_path / "policy.toml"
    assert policy_file.exists()
    content = policy_file.read_text()
    assert "FlavorPack operator policy" in content
    assert "scaffolded" in result.output
    assert "user policy file ready" in result.output


def test_policy_init_idempotent(tmp_path: Path) -> None:
    """flavor policy init does not overwrite an existing policy.toml."""
    policy_file = tmp_path / "policy.toml"
    original_content = "# my custom policy\n"
    policy_file.write_text(original_content)

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        result = runner.invoke(cli, ["policy", "init"])

    assert result.exit_code == 0, result.output
    assert policy_file.read_text() == original_content
    assert "already exists" in result.output
    assert "user policy file ready" in result.output


def test_policy_init_global_flag(tmp_path: Path) -> None:
    """flavor policy init --global scaffolds at the system policy path."""
    system_policy_file = tmp_path / "policy.toml"

    runner = CliRunner()
    with mock.patch("flavor.commands.policy.get_policy_file", return_value=system_policy_file):
        result = runner.invoke(cli, ["policy", "init", "--global"])

    assert result.exit_code == 0, result.output
    assert system_policy_file.exists()
    assert "scaffolded" in result.output
    assert "system policy file ready" in result.output


def test_policy_init_creates_parent_dirs(tmp_path: Path) -> None:
    """flavor policy init creates parent directories if they don't exist."""
    nested_dir = tmp_path / "a" / "b" / "c"
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(nested_dir)}):
        result = runner.invoke(cli, ["policy", "init"])

    assert result.exit_code == 0, result.output
    assert (nested_dir / "policy.toml").exists()


# ---------------------------------------------------------------------------
# policy show
# ---------------------------------------------------------------------------


def test_policy_show_defaults(tmp_path: Path) -> None:
    """flavor policy show prints all default policy fields."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        result = runner.invoke(cli, ["policy", "show"])

    assert result.exit_code == 0, result.output
    assert "[trust]" in result.output
    assert "require_trusted_key = false" in result.output
    assert "use_os_keychain     = false" in result.output
    assert "[execution]" in result.output
    assert "refuse_root     = false" in result.output
    assert "(no limit)" in result.output
    assert "(all platforms)" in result.output
    assert "[attestation]" in result.output
    assert "require_sbom = false" in result.output


def test_policy_show_with_max_age_days(tmp_path: Path) -> None:
    """flavor policy show prints max_age_days when operator sets it."""
    op = OperatorPolicy(max_age_days=90)
    runner = CliRunner()
    with mock.patch("flavor.commands.policy.load_operator_policy", return_value=op):
        result = runner.invoke(cli, ["policy", "show"])

    assert result.exit_code == 0, result.output
    assert "max_age_days    = 90" in result.output


def test_policy_show_with_allow_platforms(tmp_path: Path) -> None:
    """flavor policy show prints allow_platforms when operator sets them."""
    op = OperatorPolicy(allow_platforms=["linux_amd64", "linux_arm64"])
    runner = CliRunner()
    with mock.patch("flavor.commands.policy.load_operator_policy", return_value=op):
        result = runner.invoke(cli, ["policy", "show"])

    assert result.exit_code == 0, result.output
    assert "linux_amd64" in result.output


def test_policy_show_all_flags_true(tmp_path: Path) -> None:
    """flavor policy show prints 'true' for boolean flags that are enabled."""
    op = OperatorPolicy(
        require_trusted_key=True,
        use_os_keychain=True,
        refuse_root=True,
        require_sbom=True,
    )
    runner = CliRunner()
    with mock.patch("flavor.commands.policy.load_operator_policy", return_value=op):
        result = runner.invoke(cli, ["policy", "show"])

    assert result.exit_code == 0, result.output
    assert "require_trusted_key = true" in result.output
    assert "use_os_keychain     = true" in result.output
    assert "refuse_root     = true" in result.output
    assert "require_sbom = true" in result.output


# ---------------------------------------------------------------------------
# policy check — allowed packages
# ---------------------------------------------------------------------------


def test_policy_check_allowed(tmp_path: Path) -> None:
    """policy check prints allowed message for a permissive policy."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader()

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=OperatorPolicy()),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 0, result.output
    assert "✓ Package would be allowed on this host." in result.output
    assert "Platform:" in result.output
    assert "refuse_root:" in result.output
    assert "max_age_days:" in result.output


def test_policy_check_shows_no_limit_when_max_age_none(tmp_path: Path) -> None:
    """policy check shows (no limit) when max_age_days is None."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader()

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=OperatorPolicy()),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 0, result.output
    assert "(no limit)" in result.output


# ---------------------------------------------------------------------------
# policy check — platform not permitted
# ---------------------------------------------------------------------------


def test_policy_check_platform_not_permitted(tmp_path: Path) -> None:
    """policy check exits 1 when current platform is not in allowed platforms."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={"policy": {"platforms": ["linux_amd64"]}})

    op = OperatorPolicy()

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
        mock.patch("flavor.commands.policy._get_current_platform", return_value="darwin_arm64"),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "Platform not permitted" in result.output


# ---------------------------------------------------------------------------
# policy check — root check
# ---------------------------------------------------------------------------


def test_policy_check_refuses_root(tmp_path: Path) -> None:
    """policy check exits 1 when package refuses root and process is root."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={"policy": {"refuse_root": True}})
    op = OperatorPolicy()

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
        mock.patch("flavor.commands.policy._is_root", return_value=True),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "refuses to run as root" in result.output


def test_policy_check_refuse_root_not_root(tmp_path: Path) -> None:
    """policy check allows when refuse_root=True but process is not root."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={"policy": {"refuse_root": True}})
    op = OperatorPolicy()

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
        mock.patch("flavor.commands.policy._is_root", return_value=False),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 0, result.output
    assert "✓ Package would be allowed on this host." in result.output


# ---------------------------------------------------------------------------
# policy check — age check
# ---------------------------------------------------------------------------


def test_policy_check_package_too_old(tmp_path: Path) -> None:
    """policy check exits 1 when package exceeds max_age_days."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    # Build timestamp 400 days ago
    old_ts = int(time.time()) - (400 * 86400)
    mock_reader = _make_mock_reader(build_timestamp=old_ts)
    op = OperatorPolicy(max_age_days=365)

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "days old" in result.output


def test_policy_check_package_fresh_enough(tmp_path: Path) -> None:
    """policy check allows package within max_age_days."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    # Build timestamp 10 days ago
    recent_ts = int(time.time()) - (10 * 86400)
    mock_reader = _make_mock_reader(build_timestamp=recent_ts)
    op = OperatorPolicy(max_age_days=365)

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 0, result.output
    assert "✓ Package would be allowed on this host." in result.output


def test_policy_check_zero_build_timestamp_skips_age(tmp_path: Path) -> None:
    """policy check skips age check when build_timestamp is 0."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(build_timestamp=0)
    op = OperatorPolicy(max_age_days=1)  # very strict but timestamp=0 means skip

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 0, result.output


def test_policy_check_no_max_age_skips_age_check(tmp_path: Path) -> None:
    """policy check skips age check when max_age_days is None."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    old_ts = int(time.time()) - (1000 * 86400)
    mock_reader = _make_mock_reader(build_timestamp=old_ts)
    op = OperatorPolicy(max_age_days=None)

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# policy check — missing env vars
# ---------------------------------------------------------------------------


def test_policy_check_missing_env_var(tmp_path: Path) -> None:
    """policy check exits 1 when a required env var is not set."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={"policy": {"require_env": ["MY_REQUIRED_VAR"]}})
    op = OperatorPolicy()

    runner = CliRunner()
    env = {k: v for k, v in os.environ.items() if k != "MY_REQUIRED_VAR"}
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
        mock.patch.dict(os.environ, env, clear=True),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "MY_REQUIRED_VAR" in result.output


def test_policy_check_multiple_missing_env_vars(tmp_path: Path) -> None:
    """policy check reports all missing env vars and exits 1."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={"policy": {"require_env": ["VAR_ONE", "VAR_TWO"]}})
    op = OperatorPolicy()

    runner = CliRunner()
    env = {k: v for k, v in os.environ.items() if k not in ("VAR_ONE", "VAR_TWO")}
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
        mock.patch.dict(os.environ, env, clear=True),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "VAR_ONE" in result.output
    assert "VAR_TWO" in result.output


def test_policy_check_env_var_present(tmp_path: Path) -> None:
    """policy check succeeds when required env var is present."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={"policy": {"require_env": ["MY_PRESENT_VAR"]}})
    op = OperatorPolicy()

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
        mock.patch.dict(os.environ, {"MY_PRESENT_VAR": "set_value"}),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 0, result.output
    assert "✓ Package would be allowed on this host." in result.output


# ---------------------------------------------------------------------------
# _get_current_platform
# ---------------------------------------------------------------------------


def test_get_current_platform_returns_string() -> None:
    """_get_current_platform returns a non-empty platform string."""
    platform = _get_current_platform()
    assert isinstance(platform, str)
    assert "_" in platform
    parts = platform.split("_")
    assert parts[0] in ("linux", "darwin", "windows")
    assert parts[1] in ("amd64", "arm64")


def test_get_current_platform_linux() -> None:
    """_get_current_platform returns linux_* on a linux platform."""
    with mock.patch("sys.platform", "linux"):
        platform = _get_current_platform()
    assert platform.startswith("linux_")


def test_get_current_platform_darwin() -> None:
    """_get_current_platform returns darwin_* on macOS."""
    with mock.patch("sys.platform", "darwin"):
        platform = _get_current_platform()
    assert platform.startswith("darwin_")


def test_get_current_platform_windows() -> None:
    """_get_current_platform returns windows_* on Windows."""
    with mock.patch("sys.platform", "win32"):
        platform = _get_current_platform()
    assert platform.startswith("windows_")


def test_get_current_platform_aarch64() -> None:
    """_get_current_platform maps aarch64 to arm64."""
    with mock.patch("platform.machine", return_value="aarch64"):
        platform = _get_current_platform()
    assert platform.endswith("_arm64")


def test_get_current_platform_x86_64() -> None:
    """_get_current_platform maps x86_64 to amd64."""
    with mock.patch("platform.machine", return_value="x86_64"):
        platform = _get_current_platform()
    assert platform.endswith("_amd64")


# ---------------------------------------------------------------------------
# _is_root
# ---------------------------------------------------------------------------


def test_is_root_returns_bool() -> None:
    """_is_root returns a bool."""
    result = _is_root()
    assert isinstance(result, bool)


def test_is_root_true_when_euid_zero() -> None:
    """_is_root returns True when os.geteuid() returns 0."""
    # create=True so the patch works on Windows where os.geteuid doesn't exist
    with mock.patch("os.geteuid", return_value=0, create=True):
        assert _is_root() is True


def test_is_root_false_when_euid_nonzero() -> None:
    """_is_root returns False when os.geteuid() returns nonzero."""
    # create=True so the patch works on Windows where os.geteuid doesn't exist
    with mock.patch("os.geteuid", return_value=1000, create=True):
        assert _is_root() is False


def test_is_root_false_on_windows_attribute_error() -> None:
    """_is_root returns False when os.geteuid raises AttributeError (Windows)."""
    # create=True so the patch works on Windows where os.geteuid doesn't exist
    with mock.patch("os.geteuid", side_effect=AttributeError("no geteuid"), create=True):
        assert _is_root() is False


# 🌶️📦🔚
