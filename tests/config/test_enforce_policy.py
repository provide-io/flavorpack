#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Mutation-catching tests for enforce_policy — one test per check, plus ordering and integration."""

from __future__ import annotations

import time
from unittest import mock

import pytest

from flavor.config.policy import (
    EffectivePolicy,
    OperatorPolicy,
    PackagePolicy,
    enforce_policy,
    get_current_platform,
    merge_policy,
)

# ---------------------------------------------------------------------------
# enforce_policy — permissive baseline
# ---------------------------------------------------------------------------


def test_enforce_policy_permissive_defaults_pass() -> None:
    """All-default policy passes without error."""
    enforce_policy(EffectivePolicy(), 0, False, False)


# ---------------------------------------------------------------------------
# Check 1: Platform
# ---------------------------------------------------------------------------


def test_enforce_policy_platform_blocked_when_not_in_list() -> None:
    """Platform not in allowed list raises ValueError."""
    policy = EffectivePolicy(platforms=["__no_such_platform__"])
    with pytest.raises(ValueError, match="platform not permitted"):
        enforce_policy(policy, 0, False, True)


def test_enforce_policy_platform_allowed_when_in_list() -> None:
    """Current platform in allowed list passes."""
    current = get_current_platform()
    policy = EffectivePolicy(platforms=[current, "__other__"])
    enforce_policy(policy, 0, False, True)  # must not raise


def test_enforce_policy_platform_empty_list_allows_all() -> None:
    """Empty platforms list means no restriction — every host passes."""
    enforce_policy(EffectivePolicy(platforms=[]), 0, False, True)  # must not raise


def test_enforce_policy_platform_error_includes_current_platform() -> None:
    """Error message names the blocked platform for diagnostics."""
    current = get_current_platform()
    with pytest.raises(ValueError) as exc_info:
        enforce_policy(EffectivePolicy(platforms=["__no_such_platform__"]), 0, False, True)
    assert current in str(exc_info.value)


# ---------------------------------------------------------------------------
# Check 2: OS keychain
# ---------------------------------------------------------------------------


def test_enforce_policy_rejects_unsupported_os_keychain() -> None:
    """use_os_keychain must fail closed."""
    with pytest.raises(ValueError, match="use_os_keychain"):
        enforce_policy(EffectivePolicy(use_os_keychain=True), 0, False, True)


# ---------------------------------------------------------------------------
# Check 3: Root / Administrator
# ---------------------------------------------------------------------------


def test_enforce_policy_refuse_root_blocks_privileged_user() -> None:
    """refuse_root=True raises when the process is root."""
    with (
        mock.patch("flavor.config.policy.is_privileged_user", return_value=True),
        pytest.raises(ValueError, match="root"),
    ):
        enforce_policy(EffectivePolicy(refuse_root=True), 0, False, True)


def test_enforce_policy_refuse_root_allows_unprivileged_user() -> None:
    """refuse_root=True passes when not root."""
    with mock.patch("flavor.config.policy.is_privileged_user", return_value=False):
        enforce_policy(EffectivePolicy(refuse_root=True), 0, False, True)  # must not raise


def test_enforce_policy_refuse_root_false_allows_root() -> None:
    """refuse_root=False passes even when process is root."""
    with mock.patch("flavor.config.policy.is_privileged_user", return_value=True):
        enforce_policy(EffectivePolicy(refuse_root=False), 0, False, True)  # must not raise


# ---------------------------------------------------------------------------
# Check 4: Age
# ---------------------------------------------------------------------------


def test_enforce_policy_max_age_exceeded_raises() -> None:
    """Package older than max_age_days raises ValueError."""
    with pytest.raises(ValueError, match="days old"):
        # build_timestamp=1 (ancient), max_age_days=0
        enforce_policy(EffectivePolicy(max_age_days=0), 1, False, True)


def test_enforce_policy_max_age_not_exceeded_passes() -> None:
    """Package within max_age_days passes."""
    recent_ts = int(time.time()) - 3600
    enforce_policy(EffectivePolicy(max_age_days=9999), recent_ts, False, True)  # must not raise


def test_enforce_policy_max_age_zero_timestamp_skips_check() -> None:
    """build_timestamp=0 means no timestamp — age check is always skipped."""
    # max_age_days=0 would fail any non-zero timestamp; zero skips it
    enforce_policy(EffectivePolicy(max_age_days=0), 0, False, True)  # must not raise


def test_enforce_policy_max_age_none_skips_check() -> None:
    """max_age_days=None means no age policy."""
    # Ancient build_timestamp; check must be skipped
    enforce_policy(EffectivePolicy(max_age_days=None), 1, False, True)  # must not raise


def test_enforce_policy_max_age_error_includes_age_and_limit() -> None:
    """Age error reports actual age and policy limit."""
    with pytest.raises(ValueError) as exc_info:
        enforce_policy(EffectivePolicy(max_age_days=0), 1, False, True)
    msg = str(exc_info.value)
    assert "days old" in msg
    assert "0" in msg  # limit


# ---------------------------------------------------------------------------
# Check 5: Environment variables
# ---------------------------------------------------------------------------


def test_enforce_policy_require_env_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """require_env variable absent from environment raises."""
    monkeypatch.delenv("__FLAVOR_TEST_MISSING__", raising=False)
    with pytest.raises(ValueError, match="required environment variable not set"):
        enforce_policy(EffectivePolicy(require_env=["__FLAVOR_TEST_MISSING__"]), 0, False, True)


def test_enforce_policy_require_env_present_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """require_env variable present in environment passes."""
    monkeypatch.setenv("__FLAVOR_TEST_PRESENT__", "yes")
    enforce_policy(EffectivePolicy(require_env=["__FLAVOR_TEST_PRESENT__"]), 0, False, True)


def test_enforce_policy_require_env_empty_string_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """require_env variable set to empty string is treated as absent."""
    monkeypatch.setenv("__FLAVOR_TEST_EMPTY__", "")
    with pytest.raises(ValueError, match="required environment variable not set"):
        enforce_policy(EffectivePolicy(require_env=["__FLAVOR_TEST_EMPTY__"]), 0, False, True)


def test_enforce_policy_require_env_error_names_missing_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Error message includes the name of the missing variable."""
    monkeypatch.delenv("__FLAVOR_ABSENT_VAR__", raising=False)
    with pytest.raises(ValueError, match="__FLAVOR_ABSENT_VAR__"):
        enforce_policy(EffectivePolicy(require_env=["__FLAVOR_ABSENT_VAR__"]), 0, False, True)


# ---------------------------------------------------------------------------
# Check 6: SBOM
# ---------------------------------------------------------------------------


def test_enforce_policy_require_sbom_missing_raises() -> None:
    """require_sbom=True with has_sbom=False raises."""
    with pytest.raises(ValueError, match="SBOM"):
        enforce_policy(EffectivePolicy(require_sbom=True), 0, False, True)


def test_enforce_policy_require_sbom_present_passes() -> None:
    """require_sbom=True with has_sbom=True passes."""
    enforce_policy(EffectivePolicy(require_sbom=True), 0, True, True)  # must not raise


def test_enforce_policy_require_sbom_false_passes_without_sbom() -> None:
    """require_sbom=False always passes regardless of has_sbom."""
    enforce_policy(EffectivePolicy(require_sbom=False), 0, False, False)  # must not raise


# ---------------------------------------------------------------------------
# Check 7: Trusted key
# ---------------------------------------------------------------------------


def test_enforce_policy_require_trusted_key_untrusted_raises() -> None:
    """require_trusted_key=True with untrusted key raises."""
    with pytest.raises(ValueError, match="trusted signing key"):
        enforce_policy(EffectivePolicy(require_trusted_key=True), 0, False, False)


def test_enforce_policy_require_trusted_key_trusted_passes() -> None:
    """require_trusted_key=True with trusted key passes."""
    enforce_policy(EffectivePolicy(require_trusted_key=True), 0, False, True)  # must not raise


def test_enforce_policy_require_trusted_key_false_allows_untrusted() -> None:
    """require_trusted_key=False passes even with untrusted key."""
    enforce_policy(EffectivePolicy(require_trusted_key=False), 0, False, False)  # must not raise


# ---------------------------------------------------------------------------
# Check ordering — each check fires before the ones after it
# ---------------------------------------------------------------------------


def test_check_order_platform_before_os_keychain() -> None:
    """Platform check (1) fires before os_keychain check (2)."""
    policy = EffectivePolicy(platforms=["__no_such_platform__"], use_os_keychain=True)
    with pytest.raises(ValueError, match="platform not permitted"):
        enforce_policy(policy, 0, False, True)


def test_check_order_os_keychain_before_refuse_root() -> None:
    """os_keychain check (2) fires before refuse_root check (3)."""
    policy = EffectivePolicy(use_os_keychain=True, refuse_root=True)
    with (
        mock.patch("flavor.config.policy.is_privileged_user", return_value=True),
        pytest.raises(ValueError, match="use_os_keychain"),
    ):
        enforce_policy(policy, 0, False, True)


def test_check_order_refuse_root_before_age() -> None:
    """refuse_root check (3) fires before age check (4)."""
    policy = EffectivePolicy(refuse_root=True, max_age_days=0)
    with (
        mock.patch("flavor.config.policy.is_privileged_user", return_value=True),
        pytest.raises(ValueError, match="root"),
    ):
        enforce_policy(policy, 1, False, True)


def test_check_order_sbom_before_trusted_key() -> None:
    """SBOM check (6) fires before trusted-key check (7)."""
    policy = EffectivePolicy(require_sbom=True, require_trusted_key=True)
    with pytest.raises(ValueError, match="SBOM"):
        enforce_policy(policy, 0, False, False)


# ---------------------------------------------------------------------------
# merge_policy + enforce_policy integration — platform semantics
# ---------------------------------------------------------------------------


def test_merge_then_enforce_empty_intersection_is_unrestricted() -> None:
    """Disjoint platform sets → empty intersection → no restriction (current behavior).

    Documents that merge_policy returns [] when pkg/op platforms don't overlap,
    and enforce_policy treats [] as "unrestricted".  Pinning this so mutations
    that change the semantics are caught.
    """
    effective = merge_policy(
        PackagePolicy(platforms=["linux_amd64"]),
        OperatorPolicy(allow_platforms=["darwin_arm64"]),
    )
    assert effective.platforms == []
    enforce_policy(effective, 0, False, True)  # must not raise — [] = unrestricted


def test_merge_then_enforce_intersection_blocks_excluded_platform() -> None:
    """Non-empty intersection blocks a platform outside the intersection."""
    effective = merge_policy(
        PackagePolicy(platforms=["linux_amd64", "darwin_arm64"]),
        OperatorPolicy(allow_platforms=["linux_amd64", "linux_arm64"]),
    )
    assert effective.platforms == ["linux_amd64"]
    with (
        mock.patch("flavor.config.policy.get_current_platform", return_value="windows_amd64"),
        pytest.raises(ValueError, match="platform not permitted"),
    ):
        enforce_policy(effective, 0, False, True)


def test_merge_then_enforce_operator_only_restriction_applied() -> None:
    """Operator-only platform restriction is enforced when package has none."""
    effective = merge_policy(
        PackagePolicy(platforms=[]),
        OperatorPolicy(allow_platforms=["linux_amd64"]),
    )
    assert effective.platforms == ["linux_amd64"]
    with (
        mock.patch("flavor.config.policy.get_current_platform", return_value="darwin_arm64"),
        pytest.raises(ValueError, match="platform not permitted"),
    ):
        enforce_policy(effective, 0, False, True)


def test_merge_then_enforce_package_only_restriction_applied() -> None:
    """Package-only platform restriction is enforced when operator has none."""
    effective = merge_policy(
        PackagePolicy(platforms=["darwin_arm64"]),
        OperatorPolicy(allow_platforms=[]),
    )
    assert effective.platforms == ["darwin_arm64"]
    with (
        mock.patch("flavor.config.policy.get_current_platform", return_value="linux_amd64"),
        pytest.raises(ValueError, match="platform not permitted"),
    ):
        enforce_policy(effective, 0, False, True)


# 🌶️📦🔚
