#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""FlavorPack launch-time policy: schema, parsing, and merge logic."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any

from attrs import define, field

from flavor.config.dirs import get_policy_file
from flavor.console import get_command_logger

log = get_command_logger("config.policy")

POLICY_VERSION = 1

_POLICY_SCHEMA: dict[str, dict[str, object]] = {
    "trust": {
        "require_trusted_key": bool,
        "use_os_keychain": bool,
    },
    "execution": {
        "refuse_root": bool,
        "max_age_days": int,
        "allow_platforms": list,
    },
    "attestation": {
        "require_sbom": bool,
    },
    "enforcement": {
        "default": str,
        "platform_mismatch": str,
        "untrusted_key": str,
        "expired_package": str,
        "missing_env": str,
        "missing_sbom": str,
        "root_execution": str,
        "os_keychain": str,
    },
}

_VALID_ENFORCEMENT_MODES = {"deny", "warn", "allow"}


class EnforcementMode(StrEnum):
    """How a policy check violation is handled."""

    DENY = "deny"
    WARN = "warn"
    ALLOW = "allow"


@define
class EnforcementPolicy:
    """Per-check enforcement modes. Omitted checks inherit from default."""

    default: EnforcementMode = field(default=EnforcementMode.DENY)
    platform_mismatch: EnforcementMode | None = field(default=None)
    root_execution: EnforcementMode | None = field(default=None)
    expired_package: EnforcementMode | None = field(default=None)
    missing_env: EnforcementMode | None = field(default=None)
    missing_sbom: EnforcementMode | None = field(default=None)
    untrusted_key: EnforcementMode | None = field(default=None)
    os_keychain: EnforcementMode | None = field(default=None)

    def mode_for(self, check: str) -> EnforcementMode:
        """Return the enforcement mode for a given check name."""
        val = getattr(self, check, None)
        return val if val is not None else self.default


@define
class PackagePolicy:
    """Constraints declared by the package builder in pyproject.toml."""

    platforms: list[str] = field(factory=list)
    refuse_root: bool = field(default=False)
    max_age_days: int | None = field(default=None)
    require_env: list[str] = field(factory=list)


@define
class OperatorPolicy:
    """Operator overlay from policy.json."""

    require_trusted_key: bool = field(default=False)
    use_os_keychain: bool = field(default=False)
    refuse_root: bool = field(default=False)
    max_age_days: int | None = field(default=None)
    allow_platforms: list[str] = field(factory=list)
    require_sbom: bool = field(default=False)
    enforcement: EnforcementPolicy = field(factory=EnforcementPolicy)


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
    enforcement: EnforcementPolicy = field(factory=EnforcementPolicy)


def parse_package_policy(raw: dict[str, Any]) -> PackagePolicy:
    """Parse [tool.flavor.policy] dict from pyproject.toml into a PackagePolicy."""
    return PackagePolicy(
        platforms=raw.get("platforms", []),
        refuse_root=bool(raw.get("refuse_root", False)),
        max_age_days=raw.get("max_age_days"),
        require_env=raw.get("require_env", []),
    )


def _parse_enforcement_section(raw: dict[str, Any]) -> EnforcementPolicy:
    """Parse the enforcement section of a policy file."""
    kwargs: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in _POLICY_SCHEMA["enforcement"]:
            raise ValueError(f"unknown enforcement key {key!r}")
        if value not in _VALID_ENFORCEMENT_MODES:
            raise ValueError(f"enforcement.{key} must be one of {_VALID_ENFORCEMENT_MODES}, got {value!r}")
        kwargs[key] = EnforcementMode(value)
    return EnforcementPolicy(**kwargs)


def _parse_operator_policy(raw: dict[str, Any]) -> OperatorPolicy:
    """Parse policy file content into an OperatorPolicy."""
    trust = raw.get("trust", {})
    execution = raw.get("execution", {})
    attestation = raw.get("attestation", {})
    enforcement_raw = raw.get("enforcement", {})

    enforcement = _parse_enforcement_section(enforcement_raw) if enforcement_raw else EnforcementPolicy()

    return OperatorPolicy(
        require_trusted_key=bool(trust.get("require_trusted_key", False)),
        use_os_keychain=bool(trust.get("use_os_keychain", False)),
        refuse_root=bool(execution.get("refuse_root", False)),
        max_age_days=execution.get("max_age_days"),
        allow_platforms=execution.get("allow_platforms", []),
        require_sbom=bool(attestation.get("require_sbom", False)),
        enforcement=enforcement,
    )


def _raise_invalid_policy(path: Path, message: str) -> None:
    raise ValueError(f"{path}: {message}")


def _validate_operator_policy_value(path: Path, section: str, key: str, value: Any) -> None:
    expected = _POLICY_SCHEMA[section][key]
    label = f"[{section}].{key}"

    if expected is bool:
        if type(value) is not bool:
            _raise_invalid_policy(path, f"{label} must be a boolean")
        return

    if expected is int:
        if type(value) is not int:
            _raise_invalid_policy(path, f"{label} must be an integer")
        return

    if expected is str:
        if type(value) is not str:
            _raise_invalid_policy(path, f"{label} must be a string")
        return

    if expected is list:
        if not isinstance(value, list) or any(type(item) is not str for item in value):
            _raise_invalid_policy(path, f"{label} must be a list of strings")
        return

    _raise_invalid_policy(path, f"{label} has unsupported schema type")


def _validate_operator_policy_file(path: Path, raw: dict[str, Any]) -> None:
    for section, values in raw.items():
        if section == "version":
            if type(values) is not int:
                _raise_invalid_policy(path, "version must be an integer")
            continue
        if section not in _POLICY_SCHEMA:
            _raise_invalid_policy(path, f"unknown policy section [{section}]")
        if not isinstance(values, dict):
            _raise_invalid_policy(path, f"unknown top-level key {section!r}")

        allowed_keys = _POLICY_SCHEMA[section]
        for key, value in values.items():
            if key not in allowed_keys:
                _raise_invalid_policy(path, f"unknown policy key [{section}].{key}")
            _validate_operator_policy_value(path, section, key, value)


def _load_policy_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r") as f:
            raw: dict[str, Any] = json.load(f)
    except Exception as exc:
        raise ValueError(f"{path}: invalid policy file ({exc})") from exc

    if not isinstance(raw, dict):
        _raise_invalid_policy(path, "policy file root must be an object")

    version = raw.get("version")
    if version is None:
        _raise_invalid_policy(path, "missing required 'version' field")
    if type(version) is not int:
        _raise_invalid_policy(path, "version must be an integer")
    if version > POLICY_VERSION:
        log.warning(
            f"⚠️  {path}: policy version {version} is newer than supported version {POLICY_VERSION} "
            "— unknown fields will be ignored"
        )

    _validate_operator_policy_file(path, raw)
    return raw


def load_operator_policy(*, system: bool = True, user: bool = True) -> OperatorPolicy:
    """Load the operator policy file(s).

    System policy is loaded first, then user policy overrides it.
    If neither file exists, returns a permissive default.
    """
    merged: dict[str, Any] = {}

    if system:
        system_file = get_policy_file(system=True)
        if system_file.exists():
            merged.update(_load_policy_file(system_file))

    if user:
        user_file = get_policy_file(system=False)
        if user_file.exists():
            user_raw = _load_policy_file(user_file)
            for section, values in user_raw.items():
                if section == "version":
                    continue
                if isinstance(values, dict):
                    merged.setdefault(section, {}).update(values)
                else:
                    merged[section] = values

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
        enforcement=op.enforcement,
    )


def get_current_platform() -> str:
    """Return the normalized FlavorPack platform string for the current host."""
    if sys.platform.startswith("linux"):
        os_name = "linux"
    elif sys.platform == "darwin":
        os_name = "darwin"
    elif sys.platform.startswith("freebsd"):
        os_name = "freebsd"
    elif sys.platform == "win32":
        os_name = "windows"
    else:
        os_name = sys.platform
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
    return f"{os_name}_{arch}"


def is_privileged_user() -> bool:
    """Return True when the current process is privileged/root."""
    try:
        return os.geteuid() == 0  # type: ignore[attr-defined,unused-ignore]
    except AttributeError:
        return False


def _apply_enforcement(
    mode: EnforcementMode,
    message: str,
    warnings: list[str],
) -> None:
    """Apply enforcement mode: deny raises, warn appends, allow is silent."""
    if mode == EnforcementMode.DENY:
        raise ValueError(message)
    if mode == EnforcementMode.WARN:
        log.warning(f"⚠️  policy warning: {message}")
        warnings.append(message)


def enforce_policy(
    policy: EffectivePolicy,
    build_timestamp: int,
    has_sbom: bool,
    key_trusted: bool,
) -> list[str]:
    """Enforce the effective launch policy for the current runtime environment.

    Returns a list of warning messages for checks in 'warn' mode.
    Raises ValueError for checks in 'deny' mode.
    Checks in 'allow' mode are silently skipped.
    """
    warnings: list[str] = []
    enf = policy.enforcement
    current_platform = get_current_platform()

    # 1. Platform check
    if policy.platforms and current_platform not in policy.platforms:
        _apply_enforcement(
            enf.mode_for("platform_mismatch"),
            f"platform not permitted: {current_platform} not in {policy.platforms}",
            warnings,
        )

    # 2. OS keychain check
    if policy.use_os_keychain:
        _apply_enforcement(
            enf.mode_for("os_keychain"),
            "use_os_keychain is not supported by this launcher",
            warnings,
        )

    # 3. Root / Administrator check
    if policy.refuse_root and is_privileged_user():
        _apply_enforcement(
            enf.mode_for("root_execution"),
            "refused to run as root or Administrator",
            warnings,
        )

    # 4. Age check
    if policy.max_age_days is not None and build_timestamp > 0:
        age_days = int((datetime.now(UTC).timestamp() - build_timestamp) / 86400)
        if age_days > policy.max_age_days:
            _apply_enforcement(
                enf.mode_for("expired_package"),
                f"package is {age_days} days old — policy requires max {policy.max_age_days} days",
                warnings,
            )

    # 5. Environment variable check
    missing = [var for var in policy.require_env if not os.environ.get(var)]
    if missing:
        _apply_enforcement(
            enf.mode_for("missing_env"),
            f"required environment variable not set: {missing[0]}",
            warnings,
        )

    # 6. SBOM check
    if policy.require_sbom and not has_sbom:
        _apply_enforcement(
            enf.mode_for("missing_sbom"),
            "package built without attestation slot — operator policy requires SBOM",
            warnings,
        )

    # 7. Trusted key check
    if policy.require_trusted_key and not key_trusted:
        _apply_enforcement(
            enf.mode_for("untrusted_key"),
            "operator policy requires a trusted signing key — package key is not in the trusted store",
            warnings,
        )

    return warnings


# 🌶️📦🔚
