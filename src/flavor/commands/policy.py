#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""flavor policy — manage and inspect launch-time execution policy."""

from __future__ import annotations

from datetime import UTC
import json
import os
from pathlib import Path
import sys

import click
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from provide.foundation.console import perr, pout

from flavor.config.dirs import get_policy_file
from flavor.config.policy import (
    POLICY_VERSION,
    enforce_policy,
    get_current_platform,
    is_privileged_user,
    load_operator_policy,
    merge_policy,
    parse_package_policy,
)
from flavor.config.trust import compute_key_fingerprint, is_key_trusted
from flavor.console import get_command_logger

log = get_command_logger("policy")

_POLICY_JSON_SCAFFOLD = {
    "version": POLICY_VERSION,
    "trust": {
        "require_trusted_key": False,
        "use_os_keychain": False,
    },
    "execution": {
        "refuse_root": False,
        "allow_platforms": [],
    },
    "attestation": {
        "require_sbom": False,
    },
    "enforcement": {
        "default": "deny",
    },
}


@click.group("policy")
def policy_group() -> None:
    """Manage FlavorPack launch-time execution policy.

    Policy controls what packages are allowed to run on this host.
    Operator settings can only tighten package-declared constraints.
    """


@policy_group.command("init")
@click.option(
    "--global",
    "global_",
    is_flag=True,
    default=False,
    help="Scaffold system-wide policy at /etc/flavor/policy.json (requires root).",
)
def policy_init(global_: bool) -> None:
    """Scaffold a policy.json with all options at their defaults."""
    policy_file = get_policy_file(system=global_)
    policy_file.parent.mkdir(parents=True, exist_ok=True)

    if policy_file.exists():
        pout(f"  {policy_file}  (already exists, not modified)")
    else:
        policy_file.write_text(json.dumps(_POLICY_JSON_SCAFFOLD, indent=2) + "\n", encoding="utf-8")
        pout(f"✓ {policy_file}  (scaffolded)")

    scope = "system" if global_ else "user"
    pout(f"\nFlavorPack {scope} policy file ready. Edit it to enforce constraints.")


@policy_group.command("show")
def policy_show() -> None:
    """Print the effective policy (operator defaults) for this host."""
    op = load_operator_policy()
    pout("[trust]")
    pout(f"  require_trusted_key = {str(op.require_trusted_key).lower()}")
    pout(f"  use_os_keychain     = {str(op.use_os_keychain).lower()}")
    pout("")
    pout("[execution]")
    pout(f"  refuse_root     = {str(op.refuse_root).lower()}")
    if op.max_age_days is not None:
        pout(f"  max_age_days    = {op.max_age_days}")
    else:
        pout("  max_age_days    = (no limit)")
    if op.allow_platforms:
        pout(f"  allow_platforms = {op.allow_platforms}")
    else:
        pout("  allow_platforms = (all platforms)")
    pout("")
    pout("[attestation]")
    pout(f"  require_sbom = {str(op.require_sbom).lower()}")
    pout("")
    pout("[enforcement]")
    enf = op.enforcement
    pout(f"  default            = {enf.default.value}")
    for check in (
        "platform_mismatch",
        "root_execution",
        "expired_package",
        "missing_env",
        "missing_sbom",
        "untrusted_key",
        "os_keychain",
    ):
        val = getattr(enf, check, None)
        pout(f"  {check:20s} = {val.value if val else '(inherit default)'}")


@policy_group.command("check")
@click.argument("package_file", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
def policy_check(package_file: str) -> None:  # noqa: C901
    """Dry-run: would this package be allowed to run on this host?"""
    from datetime import datetime

    from flavor.psp.format_2025.reader import PSPFReader

    pkg_path = Path(package_file)
    with PSPFReader(pkg_path) as reader:
        metadata = reader.read_metadata()
        index = reader.read_index()

    pkg_raw = metadata.get("policy", {})
    pkg_policy = parse_package_policy(pkg_raw)
    op_policy = load_operator_policy()
    effective = merge_policy(pkg_policy, op_policy)
    has_sbom = any(slot.get("lifecycle") == "attestation" for slot in metadata.get("slots", []))

    current_platform = get_current_platform()
    if effective.platforms and current_platform not in effective.platforms:
        perr(f"❌ Platform not permitted: {current_platform} not in {effective.platforms}")
        sys.exit(1)

    if effective.refuse_root and is_privileged_user():
        perr("❌ Package refuses to run as root")
        sys.exit(1)

    if effective.max_age_days is not None:
        build_ts = index.build_timestamp
        if build_ts > 0:
            age_days = (datetime.now(UTC).timestamp() - build_ts) / 86400
            if age_days > effective.max_age_days:
                perr(f"❌ Package is {int(age_days)} days old; policy requires max {effective.max_age_days}")
                sys.exit(1)

    missing = [var for var in effective.require_env if not os.environ.get(var)]
    if missing:
        for var in missing:
            perr(f"❌ Required environment variable not set: {var}")
        sys.exit(1)

    if effective.require_sbom and not has_sbom:
        perr("❌ Package built without attestation slot — operator policy requires SBOM")
        sys.exit(1)

    metadata_error = _validate_package_key_metadata(index)
    if metadata_error:
        perr(f"❌ {metadata_error}")
        sys.exit(1)

    if effective.require_trusted_key:
        trusted, error = _check_package_key_trust(index)
        if not trusted:
            perr(f"❌ {error}")
            sys.exit(1)

    try:
        enforce_policy(effective, int(index.build_timestamp), has_sbom, True)
    except ValueError as exc:
        perr(f"❌ {exc}")
        sys.exit(1)

    pout("✓ Package would be allowed on this host.")
    pout(f"  Platform: {current_platform}")
    pout(f"  refuse_root: {effective.refuse_root}")
    pout(f"  max_age_days: {effective.max_age_days or '(no limit)'}")


def _validate_package_key_metadata(index: object) -> str | None:
    """Validate signer metadata consistency independently of trust-store policy."""
    public_key = bytes(getattr(index, "public_key", b""))
    stored_fingerprint = bytes(getattr(index, "attestation_key_fp", b"")).rstrip(b"\x00")

    if stored_fingerprint and (not public_key or set(public_key) == {0}):
        return "package attestation key fingerprint is present but embedded public key is missing"

    if not public_key or set(public_key) == {0}:
        return None

    try:
        public_key_obj = Ed25519PublicKey.from_public_bytes(public_key)
    except ValueError:
        return "embedded public key is not a valid Ed25519 key"

    fingerprint = compute_key_fingerprint(public_key_obj)
    if stored_fingerprint:
        try:
            stored_fingerprint_text = stored_fingerprint.decode("ascii")
        except UnicodeDecodeError:
            return "package attestation key fingerprint is not valid ASCII"
        if stored_fingerprint_text != fingerprint:
            return "package attestation key fingerprint does not match embedded public key"

    return None


def _check_package_key_trust(index: object) -> tuple[bool, str | None]:
    metadata_error = _validate_package_key_metadata(index)
    if metadata_error:
        return False, metadata_error

    public_key = bytes(getattr(index, "public_key", b""))
    if not public_key or set(public_key) == {0}:
        return False, "operator policy requires a trusted signing key — package is not signed"

    fingerprint = compute_key_fingerprint(Ed25519PublicKey.from_public_bytes(public_key))
    trusted = is_key_trusted(fingerprint)
    if trusted is True:
        return True, None
    if trusted is None:
        return (
            False,
            "operator policy requires a trusted signing key — no trusted-keys store is configured",
        )
    return False, "operator policy requires a trusted signing key — package key is not in the trusted store"


# 🌶️📦🔚
