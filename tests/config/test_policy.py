#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for Flavorpack launch-time policy schema, parsing, and merge logic."""

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
    _load_policy_file,
    _parse_enforcement_section,
    _validate_operator_policy_file,
    _validate_operator_policy_value,
    enforce_policy,
    get_current_platform,
    is_privileged_user,
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


# ---------------------------------------------------------------------------
# _parse_enforcement_section — unknown key and invalid mode
# ---------------------------------------------------------------------------


def test_parse_enforcement_unknown_key_raises() -> None:
    """Unknown enforcement key must be rejected."""
    with pytest.raises(ValueError, match="unknown enforcement key 'bogus'"):
        _parse_enforcement_section({"bogus": "deny"})


def test_parse_enforcement_invalid_mode_raises() -> None:
    """Invalid enforcement mode value must be rejected."""
    with pytest.raises(ValueError, match=r"enforcement\.default must be one of"):
        _parse_enforcement_section({"default": "explode"})


# ---------------------------------------------------------------------------
# _validate_operator_policy_value — wrong types
# ---------------------------------------------------------------------------


def test_validate_value_bool_wrong_type(tmp_path: Path) -> None:
    """Boolean field given a string must be rejected."""
    path = tmp_path / "policy.json"
    with pytest.raises(ValueError, match=r"must be a boolean"):
        _validate_operator_policy_value(path, "trust", "require_trusted_key", "yes")


def test_validate_value_int_wrong_type(tmp_path: Path) -> None:
    """Integer field given a string must be rejected."""
    path = tmp_path / "policy.json"
    with pytest.raises(ValueError, match=r"must be an integer"):
        _validate_operator_policy_value(path, "execution", "max_age_days", "thirty")


def test_validate_value_str_wrong_type(tmp_path: Path) -> None:
    """String field given an integer must be rejected."""
    path = tmp_path / "policy.json"
    with pytest.raises(ValueError, match=r"must be a string"):
        _validate_operator_policy_value(path, "enforcement", "default", 42)


def test_validate_value_list_wrong_type(tmp_path: Path) -> None:
    """List field given a string must be rejected."""
    path = tmp_path / "policy.json"
    with pytest.raises(ValueError, match=r"must be a list of strings"):
        _validate_operator_policy_value(path, "execution", "allow_platforms", "linux_amd64")


def test_validate_value_list_non_string_items(tmp_path: Path) -> None:
    """List field with non-string items must be rejected."""
    path = tmp_path / "policy.json"
    with pytest.raises(ValueError, match=r"must be a list of strings"):
        _validate_operator_policy_value(path, "execution", "allow_platforms", [1, 2])


def test_validate_value_unsupported_schema_type(tmp_path: Path) -> None:
    """Unsupported schema type triggers the safety-check branch."""
    from flavor.config import policy as policy_mod

    path = tmp_path / "policy.json"
    original = policy_mod._POLICY_SCHEMA["trust"]["require_trusted_key"]
    try:
        policy_mod._POLICY_SCHEMA["trust"]["require_trusted_key"] = float  # unsupported
        with pytest.raises(ValueError, match=r"unsupported schema type"):
            _validate_operator_policy_value(path, "trust", "require_trusted_key", 3.14)
    finally:
        policy_mod._POLICY_SCHEMA["trust"]["require_trusted_key"] = original


# ---------------------------------------------------------------------------
# _validate_operator_policy_file — version as string, non-dict section
# ---------------------------------------------------------------------------


def test_validate_policy_file_version_not_int(tmp_path: Path) -> None:
    """version field that is a string must be rejected."""
    path = tmp_path / "policy.json"
    with pytest.raises(ValueError, match=r"version must be an integer"):
        _validate_operator_policy_file(path, {"version": "one", "trust": {"require_trusted_key": True}})


def test_validate_policy_file_non_dict_section(tmp_path: Path) -> None:
    """Section value that is not a dict must be rejected."""
    path = tmp_path / "policy.json"
    with pytest.raises(ValueError, match=r"unknown top-level key"):
        _validate_operator_policy_file(path, {"version": 1, "trust": "bad"})


# ---------------------------------------------------------------------------
# _load_policy_file — non-dict root, string version, future version warning
# ---------------------------------------------------------------------------


def test_load_policy_file_non_dict_root(tmp_path: Path) -> None:
    """JSON root that is not an object must be rejected."""
    path = tmp_path / "policy.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match=r"policy file root must be an object"):
        _load_policy_file(path)


def test_load_policy_file_version_string(tmp_path: Path) -> None:
    """version field as string must be rejected by _load_policy_file."""
    path = tmp_path / "policy.json"
    path.write_text('{"version": "one"}', encoding="utf-8")
    with pytest.raises(ValueError, match=r"version must be an integer"):
        _load_policy_file(path)


def test_load_policy_file_future_version_warns(tmp_path: Path) -> None:
    """Policy version newer than supported should log a warning but not error."""
    path = tmp_path / "policy.json"
    path.write_text('{"version": 999}', encoding="utf-8")
    # Should not raise — just warn and return the raw dict
    raw = _load_policy_file(path)
    assert raw["version"] == 999


# ---------------------------------------------------------------------------
# load_operator_policy — user merge non-dict section value
# ---------------------------------------------------------------------------


def test_load_operator_policy_user_merge_non_dict_section(tmp_path: Path) -> None:
    """Non-dict section value during user merge hits the else branch (L259)."""
    from flavor.config import policy as policy_mod

    system_dir = tmp_path / "system"
    system_dir.mkdir()

    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_policy(user_dir / "policy.json", {"version": 1, "trust": {"require_trusted_key": True}})

    # Patch _load_policy_file for the user path to return a non-dict section
    original_load = policy_mod._load_policy_file

    def patched_load(path: Path) -> dict:  # type: ignore[type-arg]
        raw = original_load(path)
        raw["_nondict_section"] = 42  # inject non-dict for the merge branch
        return raw

    with (
        mock.patch("flavor.config.dirs.get_system_config_dir", return_value=system_dir),
        mock.patch("flavor.config.dirs.get_config_dir", return_value=user_dir),
        mock.patch("flavor.config.policy._load_policy_file", side_effect=patched_load),
    ):
        # Should not raise — the else branch just assigns the value
        op = load_operator_policy(system=False, user=True)
    assert op is not None


# ---------------------------------------------------------------------------
# get_current_platform — freebsd and fallback branches
# ---------------------------------------------------------------------------


def test_get_current_platform_linux() -> None:
    """get_current_platform returns linux_* on Linux."""
    with mock.patch("sys.platform", "linux"):
        plat = get_current_platform()
    assert plat.startswith("linux_")


def test_get_current_platform_darwin() -> None:
    """get_current_platform returns darwin_* on macOS."""
    with mock.patch("sys.platform", "darwin"):
        plat = get_current_platform()
    assert plat.startswith("darwin_")


def test_get_current_platform_freebsd() -> None:
    """get_current_platform returns freebsd_* on FreeBSD."""
    with mock.patch("sys.platform", "freebsd13"):
        plat = get_current_platform()
    assert plat.startswith("freebsd_")


def test_get_current_platform_win32() -> None:
    """get_current_platform returns windows_* on Windows."""
    with mock.patch("sys.platform", "win32"):
        plat = get_current_platform()
    assert plat.startswith("windows_")


def test_get_current_platform_unknown_os() -> None:
    """get_current_platform uses raw sys.platform for unknown OS."""
    with mock.patch("sys.platform", "sunos5"):
        plat = get_current_platform()
    assert plat.startswith("sunos5_")


# ---------------------------------------------------------------------------
# is_privileged_user — Windows AttributeError path
# ---------------------------------------------------------------------------


def test_is_privileged_user_attribute_error_returns_false() -> None:
    """is_privileged_user returns False when os.geteuid raises AttributeError (Windows)."""
    with mock.patch("os.geteuid", side_effect=AttributeError("no geteuid"), create=True):
        assert is_privileged_user() is False


# 🌶️📦🔚
