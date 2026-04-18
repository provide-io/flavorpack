# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Parity tests: policy enforcement behavior across Python, Go, and Rust."""

from __future__ import annotations

import pytest

from flavor.config.policy import (
    EffectivePolicy,
    EnforcementMode,
    EnforcementPolicy,
    OperatorPolicy,
    PackagePolicy,
    enforce_policy,
    merge_policy,
)

pytestmark = [pytest.mark.cross_language, pytest.mark.ci, pytest.mark.security]


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_stricter_wins_refuse_root() -> None:
    """Operator refuse_root=true overrides package refuse_root=false.

    Go: MergePolicy(PackagePolicy{RefuseRoot:false}, OperatorPolicy{RefuseRoot:true}).RefuseRoot == true
    Rust: merge_policy(PackagePolicy{refuse_root:false}, OperatorPolicy{refuse_root:true}).refuse_root == true
    """
    pkg = PackagePolicy(refuse_root=False)
    op = OperatorPolicy(refuse_root=True)
    effective = merge_policy(pkg, op)
    assert effective.refuse_root is True


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_package_refuse_root_propagates() -> None:
    """Package refuse_root=true propagates even if operator doesn't set it.

    Go: MergePolicy(PackagePolicy{RefuseRoot:true}, OperatorPolicy{}).RefuseRoot == true
    Rust: merge_policy(PackagePolicy{refuse_root:true}, OperatorPolicy::default()).refuse_root == true
    """
    pkg = PackagePolicy(refuse_root=True)
    op = OperatorPolicy()
    effective = merge_policy(pkg, op)
    assert effective.refuse_root is True


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_max_age_lower_wins() -> None:
    """Lower max_age_days always wins between package and operator.

    Go: min(365, 90) == 90
    Rust: min(365, 90) == 90
    """
    pkg = PackagePolicy(max_age_days=365)
    op = OperatorPolicy(max_age_days=90)
    effective = merge_policy(pkg, op)
    assert effective.max_age_days == 90


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_max_age_package_only() -> None:
    """If only package sets max_age_days, it is used.

    Go: pkg.MaxAgeDays=180, op.MaxAgeDays=nil → effective=180
    Rust: pkg.max_age_days=Some(180), op.max_age_days=None → effective=Some(180)
    """
    pkg = PackagePolicy(max_age_days=180)
    op = OperatorPolicy()
    effective = merge_policy(pkg, op)
    assert effective.max_age_days == 180


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_platform_intersection() -> None:
    """Effective platform list = intersection of package and operator allow lists.

    Go: platforms=["linux_amd64"] after intersection of ["linux_amd64","darwin_arm64"] ∩ ["linux_amd64","linux_arm64"]
    Rust: same
    """
    pkg = PackagePolicy(platforms=["linux_amd64", "darwin_arm64"])
    op = OperatorPolicy(allow_platforms=["linux_amd64", "linux_arm64"])
    effective = merge_policy(pkg, op)
    assert effective.platforms == ["linux_amd64"]


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_empty_intersection_means_no_platform_allowed() -> None:
    """If intersection is empty, no platform is allowed (package will be blocked).

    Go: intersection of ["linux_amd64"] ∩ ["darwin_arm64"] == []
    Rust: same
    """
    pkg = PackagePolicy(platforms=["linux_amd64"])
    op = OperatorPolicy(allow_platforms=["darwin_arm64"])
    effective = merge_policy(pkg, op)
    assert effective.platforms == []


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_no_policy_is_permissive() -> None:
    """Empty/default policy from both sides allows execution.

    Go: EnforcePolicy(EffectivePolicy{}, 0, false) == nil
    Rust: enforce_policy(&EffectivePolicy::default(), 0, false) == Ok(())
    """
    pkg = PackagePolicy()
    op = OperatorPolicy()
    effective = merge_policy(pkg, op)
    assert effective.refuse_root is False
    assert effective.max_age_days is None
    assert effective.platforms == []
    assert effective.require_trusted_key is False
    assert effective.require_sbom is False


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_require_sbom_from_operator() -> None:
    """Operator require_sbom=true propagates to effective policy.

    Go: EffectivePolicy.RequireSBOM == true when OperatorPolicy.RequireSBOM == true
    Rust: EffectivePolicy.require_sbom == true when OperatorPolicy.require_sbom == true
    """
    pkg = PackagePolicy()
    op = OperatorPolicy(require_sbom=True)
    effective = merge_policy(pkg, op)
    assert effective.require_sbom is True


# ---------------------------------------------------------------------------
# Enforcement mode parity
# ---------------------------------------------------------------------------


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_enforcement_default_deny_blocks_violation() -> None:
    """Default enforcement mode 'deny' causes hard failure on first violation.

    Go: EnforcePolicy(eff, 0, false, true) returns error when platform blocked
    Rust: enforce_policy(&eff, 0, false, true) returns Err(...) when platform blocked
    """
    eff = EffectivePolicy(
        platforms=["mars_amd64"],
        enforcement=EnforcementPolicy(default=EnforcementMode.DENY),
    )
    try:
        enforce_policy(eff, 0, False, True)
        assert False, "should have raised ValueError"  # noqa: B011
    except ValueError as exc:
        assert "platform not permitted" in str(exc)


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_enforcement_warn_mode_returns_warnings() -> None:
    """Warn mode collects warnings instead of aborting.

    Go: EnforcePolicy returns (warnings, nil) with len(warnings) > 0
    Rust: enforce_policy returns Ok(warnings) with warnings.len() > 0
    """
    eff = EffectivePolicy(
        platforms=["mars_amd64"],
        enforcement=EnforcementPolicy(default=EnforcementMode.WARN),
    )
    warnings = enforce_policy(eff, 0, False, True)
    assert len(warnings) >= 1
    assert any("platform" in w for w in warnings)


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_enforcement_allow_mode_silent() -> None:
    """Allow mode silently passes all checks.

    Go: EnforcePolicy returns ([], nil)
    Rust: enforce_policy returns Ok(vec![])
    """
    eff = EffectivePolicy(
        platforms=["mars_amd64"],
        require_sbom=True,
        require_trusted_key=True,
        enforcement=EnforcementPolicy(default=EnforcementMode.ALLOW),
    )
    warnings = enforce_policy(eff, 0, False, False)
    assert warnings == []


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_enforcement_per_check_override() -> None:
    """Per-check mode overrides default.

    Go: EnforcePolicy with default=deny, missing_sbom=warn returns warnings for SBOM
    Rust: same — enforce_policy with default=deny, missing_sbom=warn returns Ok(warnings)
    """
    eff = EffectivePolicy(
        require_sbom=True,
        enforcement=EnforcementPolicy(
            default=EnforcementMode.DENY,
            missing_sbom=EnforcementMode.WARN,
        ),
    )
    warnings = enforce_policy(eff, 0, False, True)
    assert len(warnings) == 1
    assert "SBOM" in warnings[0]


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_enforcement_propagated_through_merge() -> None:
    """Enforcement policy from operator propagates through merge.

    Go: MergePolicy(...).Enforcement.Default == ModeWarn
    Rust: merge_policy(...).enforcement.default == EnforcementMode::Warn
    """
    pkg = PackagePolicy()
    op = OperatorPolicy(
        enforcement=EnforcementPolicy(default=EnforcementMode.WARN),
    )
    effective = merge_policy(pkg, op)
    assert effective.enforcement.default == EnforcementMode.WARN
