#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for FlavorPack launch-time policy schema, parsing, and merge logic."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from flavor.config.policy import (
    EffectivePolicy,
    EnforcementMode,
    EnforcementPolicy,
    OperatorPolicy,
    PackagePolicy,
    enforce_policy,
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


def test_merge_enforcement_propagated() -> None:
    enf = EnforcementPolicy(default=EnforcementMode.WARN)
    pkg = PackagePolicy()
    op = OperatorPolicy(enforcement=enf)
    result = merge_policy(pkg, op)
    assert result.enforcement.default == EnforcementMode.WARN


# ---------------------------------------------------------------------------
# Helpers to write JSON policy files
# ---------------------------------------------------------------------------


def _write_policy(path: Path, data: dict) -> None:  # type: ignore[type-arg]
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# load_operator_policy
# ---------------------------------------------------------------------------


def test_load_operator_policy_missing_file_returns_defaults(tmp_path: Path) -> None:
    """When no policy files exist, all fields should be at their permissive defaults."""
    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=tmp_path / "system"),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=tmp_path / "user"),
    ):
        op = load_operator_policy()
    assert op.require_trusted_key is False
    assert op.use_os_keychain is False
    assert op.refuse_root is False
    assert op.max_age_days is None
    assert op.allow_platforms == []
    assert op.require_sbom is False


def test_load_operator_policy_system_only(tmp_path: Path) -> None:
    """Load a real system policy.json file."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    _write_policy(
        system_dir / "policy.json",
        {
            "version": 1,
            "trust": {"require_trusted_key": True},
            "execution": {"refuse_root": True, "max_age_days": 90},
        },
    )
    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=system_dir),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=tmp_path / "no-user"),
    ):
        op = load_operator_policy(system=True, user=False)
    assert op.require_trusted_key is True
    assert op.refuse_root is True
    assert op.max_age_days == 90


def test_load_operator_policy_user_only(tmp_path: Path) -> None:
    """Load a real user policy.json file."""
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_policy(
        user_dir / "policy.json",
        {
            "version": 1,
            "attestation": {"require_sbom": True},
            "execution": {"allow_platforms": ["linux_amd64"]},
        },
    )
    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=tmp_path / "no-system"),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=user_dir),
    ):
        op = load_operator_policy(system=False, user=True)
    assert op.require_sbom is True
    assert op.allow_platforms == ["linux_amd64"]


def test_load_operator_policy_user_overrides_system(tmp_path: Path) -> None:
    """User policy keys override system policy keys in the same section."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    _write_policy(
        system_dir / "policy.json",
        {
            "version": 1,
            "execution": {"refuse_root": False, "max_age_days": 180},
        },
    )

    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_policy(
        user_dir / "policy.json",
        {
            "version": 1,
            "execution": {"refuse_root": True},
        },
    )

    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=system_dir),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=user_dir),
    ):
        op = load_operator_policy(system=True, user=True)
    # User overrides refuse_root; system max_age_days is retained
    assert op.refuse_root is True
    assert op.max_age_days == 180


def test_load_operator_policy_system_false_skips_system(tmp_path: Path) -> None:
    """system=False should not read system policy even if the file exists."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    _write_policy(
        system_dir / "policy.json",
        {
            "version": 1,
            "trust": {"require_trusted_key": True},
        },
    )

    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=system_dir),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=tmp_path / "no-user"),
    ):
        op = load_operator_policy(system=False, user=True)
    assert op.require_trusted_key is False


def test_load_operator_policy_malformed_json(tmp_path: Path) -> None:
    """Malformed JSON is a hard failure when the file exists."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "policy.json").write_bytes(b"{broken json\nnot valid\n")

    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=system_dir),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=tmp_path / "no-user"),
        pytest.raises(ValueError, match=r"policy\.json"),
    ):
        load_operator_policy(system=True, user=False)


def test_load_operator_policy_missing_version(tmp_path: Path) -> None:
    """Policy file without version field is rejected."""
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    (user_dir / "policy.json").write_text('{"trust": {"require_trusted_key": true}}')

    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=tmp_path / "no-system"),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=user_dir),
        pytest.raises(ValueError, match=r"version"),
    ):
        load_operator_policy(system=False, user=True)


def test_load_operator_policy_unknown_section_raises(tmp_path: Path) -> None:
    """Unknown sections are rejected to prevent silent policy drift."""
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_policy(
        user_dir / "policy.json",
        {
            "version": 1,
            "mystery": {"flag": True},
        },
    )

    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=tmp_path / "no-system"),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=user_dir),
        pytest.raises(ValueError, match=r"unknown policy section"),
    ):
        load_operator_policy(system=False, user=True)


def test_load_operator_policy_unknown_key_raises(tmp_path: Path) -> None:
    """Unknown keys in known sections are rejected to keep runtimes aligned."""
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_policy(
        user_dir / "policy.json",
        {
            "version": 1,
            "trust": {"require_trusted_key": True, "surprise": True},
        },
    )

    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=tmp_path / "no-system"),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=user_dir),
        pytest.raises(ValueError, match=r"unknown policy key"),
    ):
        load_operator_policy(system=False, user=True)


def test_load_operator_policy_with_enforcement(tmp_path: Path) -> None:
    """Enforcement section is correctly parsed."""
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_policy(
        user_dir / "policy.json",
        {
            "version": 1,
            "enforcement": {"default": "warn", "untrusted_key": "deny"},
        },
    )

    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=tmp_path / "no-system"),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=user_dir),
    ):
        op = load_operator_policy(system=False, user=True)
    assert op.enforcement.default == EnforcementMode.WARN
    assert op.enforcement.untrusted_key == EnforcementMode.DENY


# ---------------------------------------------------------------------------
# enforce_policy with enforcement modes
# ---------------------------------------------------------------------------


def test_enforce_policy_rejects_unsupported_os_keychain() -> None:
    """use_os_keychain must fail closed until a real backend exists."""
    policy = EffectivePolicy(use_os_keychain=True)

    with pytest.raises(ValueError, match="use_os_keychain"):
        enforce_policy(policy, 0, False, True)


def test_enforce_policy_warn_mode_returns_warnings() -> None:
    """Warn mode adds to warnings list instead of raising."""
    enf = EnforcementPolicy(default=EnforcementMode.WARN)
    policy = EffectivePolicy(
        platforms=["__nonexistent__"],
        use_os_keychain=True,
        require_sbom=True,
        enforcement=enf,
    )
    warnings = enforce_policy(policy, 0, False, True)
    assert len(warnings) >= 2
    assert any("platform" in w for w in warnings)
    assert any("keychain" in w for w in warnings)


def test_enforce_policy_allow_mode_silent() -> None:
    """Allow mode produces no warnings and no errors."""
    enf = EnforcementPolicy(default=EnforcementMode.ALLOW)
    policy = EffectivePolicy(
        platforms=["__nonexistent__"],
        use_os_keychain=True,
        require_sbom=True,
        require_trusted_key=True,
        enforcement=enf,
    )
    warnings = enforce_policy(policy, 0, False, False)
    assert warnings == []


def test_enforce_policy_per_check_override() -> None:
    """Per-check mode overrides default."""
    enf = EnforcementPolicy(
        default=EnforcementMode.DENY,
        missing_sbom=EnforcementMode.WARN,
    )
    policy = EffectivePolicy(require_sbom=True, enforcement=enf)
    warnings = enforce_policy(policy, 0, False, True)
    assert len(warnings) == 1
    assert "SBOM" in warnings[0]


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
    assert o.enforcement.default == EnforcementMode.DENY


def test_effective_policy_defaults() -> None:
    e = EffectivePolicy()
    assert e.platforms == []
    assert e.refuse_root is False
    assert e.max_age_days is None
    assert e.require_env == []
    assert e.require_trusted_key is False
    assert e.use_os_keychain is False
    assert e.require_sbom is False
    assert e.enforcement.default == EnforcementMode.DENY


# 🌶️📦🔚
