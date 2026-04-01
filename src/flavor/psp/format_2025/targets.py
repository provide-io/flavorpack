#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Helpers for validating workenv-relative target paths."""

from __future__ import annotations

from pathlib import PurePosixPath
import re

_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


def normalize_workenv_target(slot_target: str) -> str:
    """Normalize a slot target and reject values that escape the workenv."""
    normalized_target = slot_target.strip()
    if not normalized_target:
        raise ValueError("Invalid slot target: target must not be empty")

    if normalized_target == "{workenv}":
        return "{workenv}"

    if normalized_target.startswith("{workenv}/"):
        normalized_target = normalized_target.removeprefix("{workenv}/")
        if not normalized_target:
            return "."
    elif "{workenv}" in normalized_target:
        raise ValueError(f"Invalid slot target: unsupported placeholder usage in '{slot_target}'")

    if _WINDOWS_DRIVE_PATTERN.match(normalized_target):
        raise ValueError(f"Invalid slot target: absolute paths are not allowed: '{slot_target}'")

    posix_target = normalized_target.replace("\\", "/")
    target_path = PurePosixPath(posix_target)

    if target_path.is_absolute():
        raise ValueError(f"Invalid slot target: absolute paths are not allowed: '{slot_target}'")

    if any(part == ".." for part in target_path.parts):
        raise ValueError(f"Invalid slot target: path traversal is not allowed: '{slot_target}'")

    normalized = target_path.as_posix()
    if normalized in {"", "."}:
        return normalized
    return normalized
