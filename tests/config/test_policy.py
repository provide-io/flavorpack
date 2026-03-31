#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for FlavorPack launch-time policy schema, parsing, and merge logic."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from flavor.config.policy import (
    EffectivePolicy,
    OperatorPolicy,
    PackagePolicy,
    load_operator_policy,
    merge_policy,
    parse_package_policy,
)

# ---------------------------------------------------------------------------
# parse_package_policy
# ---------------------------------------------------------------------------


def test_parse_package_policy_empty() -> None:
    policy = parse_package_policy({})
    assert policy.refuse_root is False
    assert policy.max_age_days is None
    assert policy.platforms == []
    assert policy.require_env == []


def test_parse_package_policy_full() -> None:
    raw = {
        "platforms": ["linux_amd64", "darwin_arm64"],
        "refuse_root": True,
        "max_age_days": 30,
        "require_env": ["MY_ENV", "OTHER_ENV"],
    }
    policy = parse_package_policy(raw)
    assert policy.platforms == ["linux_amd64", "darwin_arm64"]
    assert policy.refuse_root is True
    assert policy.max_age_days == 30
    assert policy.require_env == ["MY_ENV", "OTHER_ENV"]


def test_parse_package_policy_refuse_root_truthy() -> None:
    # Test that truthy non-bool values are coerced to bool
    policy = parse_package_policy({"refuse_root": 1})
    assert policy.refuse_root is True


# ---------------------------------------------------------------------------
# merge_policy
# ---------------------------------------------------------------------------


def test_merge_refuse_root_stricter_wins_pkg() -> None:
    pkg = PackagePolicy(refuse_root=True)
    op = OperatorPolicy(refuse_root=False)
    result = merge_policy(pkg, op)
    assert result.refuse_root is True


def test_merge_refuse_root_stricter_wins_op() -> None:
    pkg = PackagePolicy(refuse_root=False)
    op = OperatorPolicy(refuse_root=True)
    result = merge_policy(pkg, op)
    assert result.refuse_root is True


def test_merge_refuse_root_both_false() -> None:
    pkg = PackagePolicy(refuse_root=False)
    op = OperatorPolicy(refuse_root=False)
    result = merge_policy(pkg, op)
    assert result.refuse_root is False


def test_merge_max_age_lower_wins() -> None:
    pkg = PackagePolicy(max_age_days=30)
    op = OperatorPolicy(max_age_days=10)
    result = merge_policy(pkg, op)
    assert result.max_age_days == 10


def test_merge_max_age_lower_wins_pkg_smaller() -> None:
    pkg = PackagePolicy(max_age_days=5)
    op = OperatorPolicy(max_age_days=90)
    result = merge_policy(pkg, op)
    assert result.max_age_days == 5


def test_merge_max_age_none_operator_uses_package() -> None:
    pkg = PackagePolicy(max_age_days=14)
    op = OperatorPolicy(max_age_days=None)
    result = merge_policy(pkg, op)
    assert result.max_age_days == 14


def test_merge_max_age_none_package_uses_operator() -> None:
    pkg = PackagePolicy(max_age_days=None)
    op = OperatorPolicy(max_age_days=7)
    result = merge_policy(pkg, op)
    assert result.max_age_days == 7


def test_merge_max_age_both_none() -> None:
    pkg = PackagePolicy(max_age_days=None)
    op = OperatorPolicy(max_age_days=None)
    result = merge_policy(pkg, op)
    assert result.max_age_days is None


def test_merge_platforms_intersection() -> None:
    pkg = PackagePolicy(platforms=["linux_amd64", "darwin_arm64", "windows_amd64"])
    op = OperatorPolicy(allow_platforms=["linux_amd64", "darwin_arm64"])
    result = merge_policy(pkg, op)
    assert result.platforms == ["linux_amd64", "darwin_arm64"]


def test_merge_platforms_intersection_empty_result() -> None:
    pkg = PackagePolicy(platforms=["linux_amd64"])
    op = OperatorPolicy(allow_platforms=["darwin_arm64"])
    result = merge_policy(pkg, op)
    assert result.platforms == []


def test_merge_platforms_only_operator() -> None:
    pkg = PackagePolicy(platforms=[])
    op = OperatorPolicy(allow_platforms=["linux_amd64", "darwin_arm64"])
    result = merge_policy(pkg, op)
    assert result.platforms == ["linux_amd64", "darwin_arm64"]


def test_merge_platforms_only_package() -> None:
    pkg = PackagePolicy(platforms=["linux_amd64"])
    op = OperatorPolicy(allow_platforms=[])
    result = merge_policy(pkg, op)
    assert result.platforms == ["linux_amd64"]


def test_merge_platforms_both_empty() -> None:
    pkg = PackagePolicy(platforms=[])
    op = OperatorPolicy(allow_platforms=[])
    result = merge_policy(pkg, op)
    assert result.platforms == []


def test_merge_require_env_union() -> None:
    pkg = PackagePolicy(require_env=["FOO", "BAR"])
    op = OperatorPolicy()
    result = merge_policy(pkg, op)
    assert set(result.require_env) == {"FOO", "BAR"}


def test_merge_require_env_deduplicates() -> None:
    pkg = PackagePolicy(require_env=["FOO", "FOO", "BAR"])
    op = OperatorPolicy()
    result = merge_policy(pkg, op)
    assert set(result.require_env) == {"FOO", "BAR"}
    assert len(result.require_env) == 2


def test_merge_operator_flags_propagated() -> None:
    pkg = PackagePolicy()
    op = OperatorPolicy(require_trusted_key=True, use_os_keychain=True, require_sbom=True)
    result = merge_policy(pkg, op)
    assert result.require_trusted_key is True
    assert result.use_os_keychain is True
    assert result.require_sbom is True


def test_merge_returns_effective_policy_type() -> None:
    pkg = PackagePolicy()
    op = OperatorPolicy()
    result = merge_policy(pkg, op)
    assert isinstance(result, EffectivePolicy)


# ---------------------------------------------------------------------------
# load_operator_policy
# ---------------------------------------------------------------------------


def test_load_operator_policy_missing_file_returns_defaults(tmp_path: Path) -> None:
    """When no policy files exist, all fields should be at their permissive defaults."""
    with (
        mock.patch("flavor.config.policy.get_system_config_dir", return_value=tmp_path / "system"),
        mock.patch("flavor.config.policy.get_policy_file", return_value=tmp_path / "user" / "policy.toml"),
    ):
        op = load_operator_policy()
    assert op.require_trusted_key is False
    assert op.use_os_keychain is False
    assert op.refuse_root is False
    assert op.max_age_days is None
    assert op.allow_platforms == []
    assert op.require_sbom is False


def test_load_operator_policy_system_only(tmp_path: Path) -> None:
    """Load a real system policy.toml file."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    system_policy = system_dir / "policy.toml"
    system_policy.write_text(
        "[trust]\nrequire_trusted_key = true\n[execution]\nrefuse_root = true\nmax_age_days = 90\n"
    )
    with (
        mock.patch("flavor.config.policy.get_system_config_dir", return_value=system_dir),
        mock.patch("flavor.config.policy.get_policy_file", return_value=tmp_path / "no-user-policy.toml"),
    ):
        op = load_operator_policy(system=True, user=False)
    assert op.require_trusted_key is True
    assert op.refuse_root is True
    assert op.max_age_days == 90


def test_load_operator_policy_user_only(tmp_path: Path) -> None:
    """Load a real user policy.toml file."""
    user_policy = tmp_path / "policy.toml"
    user_policy.write_text(
        '[attestation]\nrequire_sbom = true\n[execution]\nallow_platforms = ["linux_amd64"]\n'
    )
    with (
        mock.patch("flavor.config.policy.get_system_config_dir", return_value=tmp_path / "no-system"),
        mock.patch("flavor.config.policy.get_policy_file", return_value=user_policy),
    ):
        op = load_operator_policy(system=False, user=True)
    assert op.require_sbom is True
    assert op.allow_platforms == ["linux_amd64"]


def test_load_operator_policy_user_overrides_system(tmp_path: Path) -> None:
    """User policy keys override system policy keys in the same section."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    system_policy = system_dir / "policy.toml"
    system_policy.write_text("[execution]\nrefuse_root = false\nmax_age_days = 180\n")

    user_policy = tmp_path / "policy.toml"
    user_policy.write_text("[execution]\nrefuse_root = true\n")

    with (
        mock.patch("flavor.config.policy.get_system_config_dir", return_value=system_dir),
        mock.patch("flavor.config.policy.get_policy_file", return_value=user_policy),
    ):
        op = load_operator_policy(system=True, user=True)
    # User overrides refuse_root; system max_age_days is retained
    assert op.refuse_root is True
    assert op.max_age_days == 180


def test_load_operator_policy_system_false_skips_system(tmp_path: Path) -> None:
    """system=False should not read system policy even if the file exists."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    system_policy = system_dir / "policy.toml"
    system_policy.write_text("[trust]\nrequire_trusted_key = true\n")

    with (
        mock.patch("flavor.config.policy.get_system_config_dir", return_value=system_dir),
        mock.patch("flavor.config.policy.get_policy_file", return_value=tmp_path / "no-policy.toml"),
    ):
        op = load_operator_policy(system=False, user=True)
    assert op.require_trusted_key is False


def test_load_operator_policy_malformed_system_toml(tmp_path: Path) -> None:
    """Malformed system TOML logs a warning and falls back to defaults."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    bad_system = system_dir / "policy.toml"
    bad_system.write_bytes(b"[broken toml\nnot valid ===\n")

    with (
        mock.patch("flavor.config.policy.get_system_config_dir", return_value=system_dir),
        mock.patch("flavor.config.policy.get_policy_file", return_value=tmp_path / "no-policy.toml"),
    ):
        op = load_operator_policy(system=True, user=False)
    # Should not raise; returns defaults
    assert op.require_trusted_key is False


def test_load_operator_policy_malformed_user_toml(tmp_path: Path) -> None:
    """Malformed user TOML logs a warning and uses whatever was loaded before."""
    bad_user = tmp_path / "policy.toml"
    bad_user.write_bytes(b"[broken\nnot = valid ===\n")

    with (
        mock.patch("flavor.config.policy.get_system_config_dir", return_value=tmp_path / "no-system"),
        mock.patch("flavor.config.policy.get_policy_file", return_value=bad_user),
    ):
        op = load_operator_policy(system=False, user=True)
    # Should not raise; returns defaults
    assert op.require_trusted_key is False


def test_load_operator_policy_user_non_dict_section(tmp_path: Path) -> None:
    """A top-level non-dict value in user policy is merged directly (not as sub-section)."""
    user_policy = tmp_path / "policy.toml"
    # TOML: top-level scalar (not a table section)
    user_policy.write_text("version = 1\n[trust]\nrequire_trusted_key = true\n")

    with (
        mock.patch("flavor.config.policy.get_system_config_dir", return_value=tmp_path / "no-system"),
        mock.patch("flavor.config.policy.get_policy_file", return_value=user_policy),
    ):
        op = load_operator_policy(system=False, user=True)
    assert op.require_trusted_key is True


# ---------------------------------------------------------------------------
# dataclass / attrs defaults
# ---------------------------------------------------------------------------


def test_package_policy_defaults() -> None:
    p = PackagePolicy()
    assert p.platforms == []
    assert p.refuse_root is False
    assert p.max_age_days is None
    assert p.require_env == []


def test_operator_policy_defaults() -> None:
    o = OperatorPolicy()
    assert o.require_trusted_key is False
    assert o.use_os_keychain is False
    assert o.refuse_root is False
    assert o.max_age_days is None
    assert o.allow_platforms == []
    assert o.require_sbom is False


def test_effective_policy_defaults() -> None:
    e = EffectivePolicy()
    assert e.platforms == []
    assert e.refuse_root is False
    assert e.max_age_days is None
    assert e.require_env == []
    assert e.require_trusted_key is False
    assert e.use_os_keychain is False
    assert e.require_sbom is False


# 🌶️📦🔚
