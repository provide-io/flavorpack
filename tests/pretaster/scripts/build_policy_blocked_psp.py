#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Build a minimal PSP with platforms: ["mars_amd64"] for policy enforcement testing.

This script uses the Python PSPFBuilder API directly, which correctly embeds
the "policy" key into the signed package metadata.  The Go and Rust builders
do not propagate the policy field from the build manifest.

Usage:
    python3 build_policy_blocked_psp.py <output.psp> [launcher_bin]

    launcher_bin  Optional path to the launcher binary.  When omitted the
                  script tries FLAVOR_LAUNCHER_BIN env var, then common local
                  build locations.

Exit codes:
    0 — success
    1 — failure (error message on stderr)
"""

import os
from pathlib import Path
import sys
import tempfile


def _find_launcher() -> Path | None:
    """Try to locate a launcher binary without relying on dist/bin/."""
    # 1. Environment override
    env_bin = os.environ.get("FLAVOR_LAUNCHER_BIN")
    if env_bin:
        p = Path(env_bin)
        if p.exists():
            return p

    # 2. Local Go/Rust source build
    script_dir = Path(__file__).parent
    # Walk up from scripts/ to find the project root (scripts/ → pretaster/ → tests/ → project)
    # Try both 3 and 4 levels to support different checkout structures.
    for levels in (3, 4):
        p = script_dir
        for _ in range(levels):
            p = p.parent
        candidate_go = p / "src" / "flavor-go" / "flavor-go-launcher"
        candidate_rs = p / "src" / "flavor-rs" / "target" / "release" / "flavor-rs-launcher"
        for c in (candidate_go, candidate_rs):
            if c.exists() and os.access(c, os.X_OK):
                return c
    return None


def main() -> int:
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"Usage: {sys.argv[0]} <output.psp> [launcher_bin]", file=sys.stderr)
        return 1

    output_path = Path(sys.argv[1])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Resolve launcher binary
    launcher_bin: Path | None = None
    if len(sys.argv) == 3:
        launcher_bin = Path(sys.argv[2])
        if not launcher_bin.exists():
            print(f"ERROR: Launcher binary not found: {launcher_bin}", file=sys.stderr)
            return 1
    else:
        launcher_bin = _find_launcher()
        if launcher_bin is None:
            print(
                "ERROR: Could not find a launcher binary.\n"
                "  Pass it as the second argument or set FLAVOR_LAUNCHER_BIN.",
                file=sys.stderr,
            )
            return 1

    try:
        from flavor.psp.format_2025.pspf_builder import PSPFBuilder
    except ImportError as exc:
        print(f"ERROR: Cannot import PSPFBuilder — is flavorpack installed? {exc}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="flavor_policy_test_") as tmp:
        tmp_path = Path(tmp)
        # Minimal payload slot — content is irrelevant; the launcher should never reach it.
        slot_file = tmp_path / "payload.txt"
        slot_file.write_bytes(b"policy test: this should never be read")

        metadata = {
            "package": {
                "name": "pretaster-policy-block",
                "version": "1.0.0",
                "description": "Tests that platform policy enforcement blocks execution",
            },
            "policy": {
                "platforms": ["mars_amd64"],
            },
        }

        result = (
            PSPFBuilder.create()
            .with_keys(seed="pretaster-security-test")
            .metadata(**metadata, allow_empty=True)
            .add_slot(
                id="payload",
                data=slot_file,
                purpose="data",
                lifecycle="runtime",
                operations="none",
            )
            .with_options(launcher_bin=launcher_bin)
            .build(output_path)
        )

        if result.success:
            print(f"Built: {output_path} ({output_path.stat().st_size} bytes)")
            return 0
        else:
            print(f"Build failed: {result.errors}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())

# 🌶️📦🔚
