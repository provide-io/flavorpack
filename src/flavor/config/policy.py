#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""FlavorPack launch-time policy: schema, parsing, and merge logic."""

from __future__ import annotations

from datetime import UTC, datetime
import os
import platform
import sys
import tomllib
from typing import Any

from attrs import define, field

from flavor.config.dirs import get_policy_file, get_system_config_dir
from flavor.console import get_command_logger

log = get_command_logger("config.policy")


@define
class PackagePolicy:
    """Constraints declared by the package builder in pyproject.toml."""

    platforms: list[str] = field(factory=list)
    refuse_root: bool = field(default=False)
    max_age_days: int | None = field(default=None)
    require_env: list[str] = field(factory=list)


@define
class OperatorPolicy:
    """Operator overlay from /etc/flavor/policy.toml or user policy.toml."""

    require_trusted_key: bool = field(default=False)
    use_os_keychain: bool = field(default=False)
    refuse_root: bool = field(default=False)
    max_age_days: int | None = field(default=None)
    allow_platforms: list[str] = field(factory=list)
    require_sbom: bool = field(default=False)


@define
class EffectivePolicy:
    """Merged policy: the stricter of package + operator wins per field."""

    platforms: list[str] = field(factory=list)
    refuse_root: bool = field(default=False)
    max_age_days: int | None = field(default=None)
    require_env: list[str] = field(factory=list)
    require_trusted_key: bool = field(default=False)
    use_os_keychain: bool = field(default=False)
    require_sbom: bool = field(default=False)


def parse_package_policy(raw: dict[str, Any]) -> PackagePolicy:
    """Parse [tool.flavor.policy] dict from pyproject.toml into a PackagePolicy."""
    return PackagePolicy(
        platforms=raw.get("platforms", []),
        refuse_root=bool(raw.get("refuse_root", False)),
        max_age_days=raw.get("max_age_days"),
        require_env=raw.get("require_env", []),
    )


def _parse_operator_policy(raw: dict[str, Any]) -> OperatorPolicy:
    """Parse policy.toml content into an OperatorPolicy."""
    trust = raw.get("trust", {})
    execution = raw.get("execution", {})
    attestation = raw.get("attestation", {})
    return OperatorPolicy(
        require_trusted_key=bool(trust.get("require_trusted_key", False)),
        use_os_keychain=bool(trust.get("use_os_keychain", False)),
        refuse_root=bool(execution.get("refuse_root", False)),
        max_age_days=execution.get("max_age_days"),
        allow_platforms=execution.get("allow_platforms", []),
        require_sbom=bool(attestation.get("require_sbom", False)),
    )


def load_operator_policy(*, system: bool = True, user: bool = True) -> OperatorPolicy:
    """Load the operator policy file(s).

    System policy (/etc/flavor/policy.toml) is loaded first, then user policy
    overrides it. If neither file exists, returns a permissive default.
    """
    merged: dict[str, Any] = {}

    if system:
        system_file = get_system_config_dir() / "policy.toml"
        if system_file.exists():
            try:
                with system_file.open("rb") as f:
                    merged.update(tomllib.load(f))
            except Exception as exc:
                log.warning("Failed to read system policy", path=str(system_file), error=str(exc))

    if user:
        user_file = get_policy_file(system=False)
        if user_file.exists():
            try:
                with user_file.open("rb") as f:
                    user_raw = tomllib.load(f)
                for section, values in user_raw.items():
                    if isinstance(values, dict):
                        merged.setdefault(section, {}).update(values)
                    else:
                        merged[section] = values
            except Exception as exc:
                log.warning("Failed to read user policy", path=str(user_file), error=str(exc))

    return _parse_operator_policy(merged)


def merge_policy(pkg: PackagePolicy, op: OperatorPolicy) -> EffectivePolicy:
    """Merge package-declared and operator policies. Stricter always wins."""
    # Platforms: intersection of both non-empty lists
    if pkg.platforms and op.allow_platforms:
        platforms = [p for p in pkg.platforms if p in op.allow_platforms]
    elif op.allow_platforms:
        platforms = list(op.allow_platforms)
    else:
        platforms = list(pkg.platforms)

    refuse_root = pkg.refuse_root or op.refuse_root

    if pkg.max_age_days is not None and op.max_age_days is not None:
        max_age_days: int | None = min(pkg.max_age_days, op.max_age_days)
    elif pkg.max_age_days is not None:
        max_age_days = pkg.max_age_days
    else:
        max_age_days = op.max_age_days

    require_env = list(set(pkg.require_env))

    return EffectivePolicy(
        platforms=platforms,
        refuse_root=refuse_root,
        max_age_days=max_age_days,
        require_env=require_env,
        require_trusted_key=op.require_trusted_key,
        use_os_keychain=op.use_os_keychain,
        require_sbom=op.require_sbom,
    )


def get_current_platform() -> str:
    """Return the normalized FlavorPack platform string for the current host."""
    os_name = (
        "linux" if sys.platform.startswith("linux") else ("darwin" if sys.platform == "darwin" else "windows")
    )
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
    return f"{os_name}_{arch}"


def is_privileged_user() -> bool:
    """Return True when the current process is privileged/root."""
    try:
        return os.geteuid() == 0  # type: ignore[attr-defined,unused-ignore]
    except AttributeError:
        return False


def enforce_policy(policy: EffectivePolicy, build_timestamp: int, has_sbom: bool, key_trusted: bool) -> None:
    """Enforce the effective launch policy for the current runtime environment."""
    current_platform = get_current_platform()

    if policy.platforms and current_platform not in policy.platforms:
        raise ValueError(f"platform not permitted: {current_platform} not in {policy.platforms}")

    if policy.refuse_root and is_privileged_user():
        raise ValueError("refused to run as root or Administrator")

    if policy.max_age_days is not None and build_timestamp > 0:
        age_days = int((datetime.now(UTC).timestamp() - build_timestamp) / 86400)
        if age_days > policy.max_age_days:
            raise ValueError(
                f"package is {age_days} days old — policy requires max {policy.max_age_days} days"
            )

    missing = [var for var in policy.require_env if not os.environ.get(var)]
    if missing:
        raise ValueError(f"required environment variable not set: {missing[0]}")

    if policy.require_sbom and not has_sbom:
        raise ValueError("package built without attestation slot — operator policy requires SBOM")

    if policy.require_trusted_key and not key_trusted:
        raise ValueError(
            "operator policy requires a trusted signing key — package key is not in the trusted store"
        )


# 🌶️📦🔚
