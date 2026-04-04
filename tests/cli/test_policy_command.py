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
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from flavor.cli import cli
from flavor.config.policy import OperatorPolicy, get_current_platform, is_privileged_user

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


def _raw_public_key_bytes() -> bytes:
    key = Ed25519PrivateKey.generate().public_key()
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw)


# ---------------------------------------------------------------------------
# policy init
# ---------------------------------------------------------------------------


def test_policy_init_creates_file(tmp_path: Path) -> None:
    """flavor policy init creates policy.json when it does not exist."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        result = runner.invoke(cli, ["policy", "init"])

    assert result.exit_code == 0, result.output
    policy_file = tmp_path / "policy.json"
    assert policy_file.exists()
    content = policy_file.read_text()
    assert '"version": 1' in content
    assert "scaffolded" in result.output


def test_policy_init_idempotent(tmp_path: Path) -> None:
    """flavor policy init does not overwrite an existing policy.json."""
    policy_file = tmp_path / "policy.json"
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
    system_policy_file = tmp_path / "policy.json"

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
    assert (nested_dir / "policy.json").exists()


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
        mock.patch("flavor.config.policy.get_current_platform", return_value="darwin_arm64"),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "platform not permitted" in result.output.lower()


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
        mock.patch("flavor.config.policy.is_privileged_user", return_value=True),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "refused to run as root" in result.output


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
        mock.patch("flavor.config.policy.is_privileged_user", return_value=False),
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
    # enforce_policy reports the first missing var; either one may appear first due to set ordering
    assert "VAR_ONE" in result.output or "VAR_TWO" in result.output


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


def test_policy_check_rejects_missing_sbom_when_required(tmp_path: Path) -> None:
    """policy check must reflect require_sbom, not just platform/root/env."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={"slots": []})
    runner = CliRunner()

    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch(
            "flavor.commands.policy.load_operator_policy", return_value=OperatorPolicy(require_sbom=True)
        ),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "SBOM" in result.output


def test_policy_check_rejects_unsigned_package_when_trusted_key_required(tmp_path: Path) -> None:
    """Unsigned bundles must fail policy check when require_trusted_key is enabled."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={})
    mock_reader.read_index.return_value.public_key = b"\x00" * 32
    mock_reader.read_index.return_value.attestation_key_fp = b"\x00" * 64

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch(
            "flavor.commands.policy.load_operator_policy",
            return_value=OperatorPolicy(require_trusted_key=True),
        ),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "trusted" in result.output or "signed" in result.output


def test_policy_check_rejects_missing_trust_store_when_trusted_key_required(tmp_path: Path) -> None:
    """A missing trust store must not be treated as implicitly trusted."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={})
    mock_reader.read_index.return_value.public_key = _raw_public_key_bytes()
    mock_reader.read_index.return_value.attestation_key_fp = b"\x00" * 64

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch(
            "flavor.commands.policy.load_operator_policy",
            return_value=OperatorPolicy(require_trusted_key=True),
        ),
        mock.patch("flavor.commands.policy.is_key_trusted", return_value=None),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "trusted" in result.output or "store" in result.output


def test_policy_check_rejects_attestation_fingerprint_mismatch_without_trusted_key_requirement(
    tmp_path: Path,
) -> None:
    """policy check must reject malformed signer metadata even when trust-store policy is permissive."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={})
    mock_reader.read_index.return_value.public_key = _raw_public_key_bytes()
    mock_reader.read_index.return_value.attestation_key_fp = b"sha256:wrong-fingerprint"

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=OperatorPolicy()),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "fingerprint" in result.output
    assert "embedded public key" in result.output


def test_policy_check_rejects_unsupported_os_keychain(tmp_path: Path) -> None:
    """use_os_keychain must fail closed in policy check until implemented."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={})
    runner = CliRunner()

    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch(
            "flavor.commands.policy.load_operator_policy",
            return_value=OperatorPolicy(use_os_keychain=True),
        ),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "use_os_keychain" in result.output or "unsupported" in result.output


# ---------------------------------------------------------------------------
# get_current_platform
# ---------------------------------------------------------------------------


def testget_current_platform_returns_string() -> None:
    """get_current_platform returns a non-empty platform string."""
    platform = get_current_platform()
    assert isinstance(platform, str)
    assert "_" in platform
    parts = platform.split("_")
    assert parts[0] in ("linux", "darwin", "windows")
    assert parts[1] in ("amd64", "arm64")


def testget_current_platform_linux() -> None:
    """get_current_platform returns linux_* on a linux platform."""
    with mock.patch("sys.platform", "linux"):
        platform = get_current_platform()
    assert platform.startswith("linux_")


def testget_current_platform_darwin() -> None:
    """get_current_platform returns darwin_* on macOS."""
    with mock.patch("sys.platform", "darwin"):
        platform = get_current_platform()
    assert platform.startswith("darwin_")


def testget_current_platform_windows() -> None:
    """get_current_platform returns windows_* on Windows."""
    with mock.patch("sys.platform", "win32"):
        platform = get_current_platform()
    assert platform.startswith("windows_")


def testget_current_platform_aarch64() -> None:
    """get_current_platform maps aarch64 to arm64."""
    with mock.patch("platform.machine", return_value="aarch64"):
        platform = get_current_platform()
    assert platform.endswith("_arm64")


def testget_current_platform_x86_64() -> None:
    """get_current_platform maps x86_64 to amd64."""
    with mock.patch("platform.machine", return_value="x86_64"):
        platform = get_current_platform()
    assert platform.endswith("_amd64")


# ---------------------------------------------------------------------------
# is_privileged_user
# ---------------------------------------------------------------------------


def testis_privileged_user_returns_bool() -> None:
    """is_privileged_user returns a bool."""
    result = is_privileged_user()
    assert isinstance(result, bool)


def testis_privileged_user_true_when_euid_zero() -> None:
    """is_privileged_user returns True when os.geteuid() returns 0."""
    # create=True so the patch works on Windows where os.geteuid doesn't exist
    with mock.patch("os.geteuid", return_value=0, create=True):
        assert is_privileged_user() is True


def testis_privileged_user_false_when_euid_nonzero() -> None:
    """is_privileged_user returns False when os.geteuid() returns nonzero."""
    # create=True so the patch works on Windows where os.geteuid doesn't exist
    with mock.patch("os.geteuid", return_value=1000, create=True):
        assert is_privileged_user() is False


def testis_privileged_user_false_on_windows_attribute_error() -> None:
    """is_privileged_user returns False when os.geteuid raises AttributeError (Windows)."""
    # create=True so the patch works on Windows where os.geteuid doesn't exist
    with mock.patch("os.geteuid", side_effect=AttributeError("no geteuid"), create=True):
        assert is_privileged_user() is False


# ---------------------------------------------------------------------------
# policy check — refuse_root via is_privileged_user in commands/policy.py
# ---------------------------------------------------------------------------


def test_policy_check_refuse_root_privileged_user_command_path(tmp_path: Path) -> None:
    """policy check exits 1 when refuse_root + is_privileged_user via the command's own check (L148-150)."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={"policy": {"refuse_root": True}})
    op = OperatorPolicy(refuse_root=True)

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=op),
        mock.patch("flavor.config.policy.is_privileged_user", return_value=True),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "refused to run as root" in result.output


# ---------------------------------------------------------------------------
# _validate_package_key_metadata — fingerprint present but no public key
# ---------------------------------------------------------------------------


def test_policy_check_fingerprint_present_no_public_key(tmp_path: Path) -> None:
    """Fingerprint present but embedded public key is zeroed/missing (L199)."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={})
    mock_reader.read_index.return_value.public_key = b"\x00" * 32
    mock_reader.read_index.return_value.attestation_key_fp = b"sha256:abc123"

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=OperatorPolicy()),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "fingerprint is present but embedded public key is missing" in result.output


# ---------------------------------------------------------------------------
# _validate_package_key_metadata — invalid Ed25519 key (L206-207)
# ---------------------------------------------------------------------------


def test_policy_check_invalid_ed25519_key(tmp_path: Path) -> None:
    """Embedded public key that is not a valid Ed25519 key (L206-207)."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={})
    mock_reader.read_index.return_value.public_key = _raw_public_key_bytes()
    mock_reader.read_index.return_value.attestation_key_fp = b""

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=OperatorPolicy()),
        mock.patch(
            "flavor.commands.policy.Ed25519PublicKey.from_public_bytes",
            side_effect=ValueError("invalid key"),
        ),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "not a valid Ed25519 key" in result.output


# ---------------------------------------------------------------------------
# _validate_package_key_metadata — non-ASCII fingerprint (L213-214)
# ---------------------------------------------------------------------------


def test_policy_check_non_ascii_fingerprint(tmp_path: Path) -> None:
    """Fingerprint containing non-ASCII bytes must be rejected (L213-214)."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={})
    mock_reader.read_index.return_value.public_key = _raw_public_key_bytes()
    mock_reader.read_index.return_value.attestation_key_fp = b"\xc0\xc1\xfe\xff" + b"\x00" * 60

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=OperatorPolicy()),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "not valid ASCII" in result.output


# ---------------------------------------------------------------------------
# _check_package_key_trust — metadata error (L224)
# ---------------------------------------------------------------------------


def test_policy_check_key_trust_metadata_error(tmp_path: Path) -> None:
    """_check_package_key_trust metadata error causes key_trusted=False, enforcement denies."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={})
    mock_reader.read_index.return_value.public_key = _raw_public_key_bytes()
    mock_reader.read_index.return_value.attestation_key_fp = b"\x00" * 64

    runner = CliRunner()
    # First _validate call (standalone) returns None (ok), second (inside
    # _check_package_key_trust) returns an error → key_trusted=False →
    # enforce_policy denies with "trusted signing key" message.
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch(
            "flavor.commands.policy.load_operator_policy",
            return_value=OperatorPolicy(require_trusted_key=True),
        ),
        mock.patch(
            "flavor.commands.policy._validate_package_key_metadata",
            side_effect=[None, "simulated metadata error"],
        ),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "trusted signing key" in result.output


# ---------------------------------------------------------------------------
# _check_package_key_trust — key trusted returns True (L233)
# ---------------------------------------------------------------------------


def test_policy_check_key_trusted(tmp_path: Path) -> None:
    """_check_package_key_trust returns True when key is in trust store (L233)."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={})
    mock_reader.read_index.return_value.public_key = _raw_public_key_bytes()
    mock_reader.read_index.return_value.attestation_key_fp = b"\x00" * 64

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch(
            "flavor.commands.policy.load_operator_policy",
            return_value=OperatorPolicy(require_trusted_key=True),
        ),
        mock.patch("flavor.commands.policy.is_key_trusted", return_value=True),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 0, result.output
    assert "Package would be allowed" in result.output


# ---------------------------------------------------------------------------
# _check_package_key_trust — key not in trusted store (L239)
# ---------------------------------------------------------------------------


def test_policy_check_key_not_trusted(tmp_path: Path) -> None:
    """_check_package_key_trust returns False when key is not in trust store (L239)."""
    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    mock_reader = _make_mock_reader(metadata={})
    mock_reader.read_index.return_value.public_key = _raw_public_key_bytes()
    mock_reader.read_index.return_value.attestation_key_fp = b"\x00" * 64

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch(
            "flavor.commands.policy.load_operator_policy",
            return_value=OperatorPolicy(require_trusted_key=True),
        ),
        mock.patch("flavor.commands.policy.is_key_trusted", return_value=False),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 1
    assert "not in the trusted store" in result.output


# ---------------------------------------------------------------------------
# _validate_package_key_metadata — fingerprint matches embedded key (L215→218)
# ---------------------------------------------------------------------------


def test_policy_check_fingerprint_matches_public_key(tmp_path: Path) -> None:
    """When attestation fingerprint matches the embedded public key, validation passes (L215→218)."""
    from flavor.config.trust import compute_key_fingerprint

    pkg = tmp_path / "test.psp"
    pkg.write_bytes(b"fake")

    # Generate a real key pair and compute the correct fingerprint
    private_key = Ed25519PrivateKey.generate()
    public_key_obj = private_key.public_key()
    raw_pub = public_key_obj.public_bytes(Encoding.Raw, PublicFormat.Raw)
    fingerprint = compute_key_fingerprint(public_key_obj)

    mock_reader = _make_mock_reader(metadata={})
    mock_reader.read_index.return_value.public_key = raw_pub
    # Store the correct fingerprint (padded to 64 bytes with null)
    fp_bytes = fingerprint.encode("ascii")
    mock_reader.read_index.return_value.attestation_key_fp = fp_bytes + b"\x00" * (64 - len(fp_bytes))

    runner = CliRunner()
    with (
        mock.patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
        mock.patch("flavor.commands.policy.load_operator_policy", return_value=OperatorPolicy()),
    ):
        result = runner.invoke(cli, ["policy", "check", str(pkg)])

    assert result.exit_code == 0, result.output
    assert "Package would be allowed" in result.output


# 🌶️📦🔚
