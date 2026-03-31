#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Check that all language packages share the same major.minor.patch as VERSION.

VERSION file contains "MAJOR.MINOR.PATCH" (e.g. "0.3.21").
Each language package version must match exactly.

Usage:
    python scripts/check_version_sync.py
"""

from __future__ import annotations

from pathlib import Path
import re

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read_version_file() -> str:
    """Read version from VERSION file."""
    return (_REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _python_version() -> str | None:
    """Read Python package version from pyproject.toml."""
    pyproject = _REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return None
    text = pyproject.read_text(encoding="utf-8")
    # Dynamic version from VERSION file
    if re.search(r'version\s*=\s*\{\s*file\s*=\s*"VERSION"\s*\}', text):
        return _read_version_file()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else None


def _go_builder_version() -> str | None:
    """Read version constant from Go builder main.go."""
    main_go = _REPO_ROOT / "src" / "flavor-go" / "cmd" / "flavor-go-builder" / "main.go"
    if not main_go.exists():
        return None
    text = main_go.read_text(encoding="utf-8")
    match = re.search(r'const\s+version\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


def _rust_cargo_version() -> str | None:
    """Read version from Cargo.toml."""
    cargo = _REPO_ROOT / "src" / "flavor-rs" / "Cargo.toml"
    if not cargo.exists():
        return None
    text = cargo.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else None


def _rust_version_rs() -> str | None:
    """Read version constant from Rust version.rs."""
    version_rs = _REPO_ROOT / "src" / "flavor-rs" / "src" / "version.rs"
    if not version_rs.exists():
        return None
    text = version_rs.read_text(encoding="utf-8")
    match = re.search(r'pub\s+const\s+VERSION:\s*&str\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


_LANG_READERS: dict[str, callable] = {
    "python (pyproject.toml)": _python_version,
    "go (builder main.go)": _go_builder_version,
    "rust (Cargo.toml)": _rust_cargo_version,
    "rust (version.rs)": _rust_version_rs,
}


def main() -> int:
    """Check version sync. Returns 0 on success, 1 on mismatch."""
    canonical = _read_version_file()
    print(f"VERSION file: {canonical}")

    errors: list[str] = []
    for lang, reader in _LANG_READERS.items():
        version = reader()
        if version is None:
            print(f"  {lang}: not found (skipped)")
            continue

        if version == canonical:
            print(f"  {lang}: {version} — OK")
        else:
            print(f"  {lang}: {version} — MISMATCH (expected {canonical})")
            errors.append(f"{lang} version {version} does not match {canonical}")

    if errors:
        print(f"\nFAILED — {len(errors)} version mismatch(es).")
        return 1

    print("\nPASSED — all versions match VERSION file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
