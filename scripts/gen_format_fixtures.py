#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Generate the committed PSPF format-compatibility fixtures.

The fixtures under ``tests/fixtures/format_compat/<gen>/`` are packages built by
one toolchain and verified by every later one. Their whole value is that they
are *old*: they are the only evidence that a package built before a signing,
hashing, or layout change still verifies after it. Nothing else in the suite
checks that, because every other test builds and verifies inside a single run,
so both sides of the comparison move together.

That makes regeneration a destructive act. Running this script over an existing
generation throws away the guarantee and replaces it with a tautology, so it
refuses to overwrite without ``--force``. When the format genuinely changes in a
way the old fixtures can no longer express, add a new generation directory and
keep the old one.

Usage:
    python scripts/gen_format_fixtures.py --generation v1
    python scripts/gen_format_fixtures.py --generation v1 --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

# Seed the fixtures are signed with. Committed on purpose: the derived key is a
# test key, and pinning the seed lets the tests assert that seed -> public key
# derivation has not drifted.
KEY_SEED = "flavorpack-format-compat-fixture-v1"

PACKAGE_NAME = "format-compat-fixture"
PACKAGE_VERSION = "1.0.0"


def find_repo_root(start: Path) -> Path:
    """Find the repository root by walking upward to the nearest VERSION file."""
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "VERSION").is_file() and (candidate / "src" / "flavor-rs").is_dir():
            return candidate

    raise SystemExit(f"❌ Could not locate the repository root from {start}")


def host_platform() -> str:
    """Return the dist/bin platform suffix for this host (e.g. darwin_arm64)."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    machine = {"x86_64": "amd64", "aarch64": "arm64"}.get(machine, machine)
    return f"{system}_{machine}"


def find_builder(repo_root: Path, impl: str) -> Path:
    """Locate a built builder binary for this host, or explain how to build one."""
    suffix = ".exe" if platform.system().lower() == "windows" else ""
    binary = repo_root / "dist" / "bin" / f"flavor-{impl}-builder-{host_platform()}{suffix}"
    if not binary.is_file():
        raise SystemExit(f"❌ Builder not found: {binary}\n   Build the helpers first:  ./build.sh")
    return binary


def builder_version(binary: Path) -> str:
    """Ask a builder binary for its version string."""
    # The path is repo-local and constructed above, not taken from input.
    result = subprocess.run(
        [str(binary), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else "unknown"


def build_manifest(payload: str) -> dict[str, object]:
    """Return the build manifest the Go and Rust builders consume."""
    return {
        "package": {"name": PACKAGE_NAME, "version": PACKAGE_VERSION},
        "execution": {"command": "true", "env": {}},
        "slots": [
            {
                "slot": 0,
                "id": "payload",
                "source": payload,
                "target": "data/payload.txt",
                "operations": "",
                "purpose": "data",
                "lifecycle": "runtime",
                "permissions": "0644",
            }
        ],
    }


def build_with_binary(binary: Path, manifest: Path, launcher: Path, output: Path) -> None:
    """Build one fixture with the Go or Rust builder binary."""
    # Every argument is a repo-local path or the committed seed constant.
    result = subprocess.run(
        [
            str(binary),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
            "--launcher-bin",
            str(launcher),
            "--key-seed",
            KEY_SEED,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not output.is_file():
        raise SystemExit(
            f"❌ {binary.name} failed (exit {result.returncode})\n{result.stdout}\n{result.stderr}"
        )


def build_with_python(payload: Path, launcher: Path, output: Path) -> None:
    """Build one fixture through the Python PSPFBuilder API."""
    from flavor.psp.format_2025.pspf_builder import PSPFBuilder

    result = (
        PSPFBuilder.create()
        # The execution block has to be passed explicitly here; the Go and Rust
        # builders derive theirs from the manifest. primary_slot is spelled out
        # to keep this generation's fixtures byte-identical to the committed
        # ones. It is optional as of #36 -- Rust used to reject metadata without
        # it, which is why this comment used to say the field was required.
        .metadata(
            name=PACKAGE_NAME,
            version=PACKAGE_VERSION,
            execution={"primary_slot": 0, "command": "true", "env": {}},
        )
        .add_slot(
            id="payload",
            data=payload,
            target="data/payload.txt",
            operations="",
            purpose="data",
            lifecycle="runtime",
            permissions="0644",
        )
        .with_keys(seed=KEY_SEED)
        .with_options(launcher_bin=launcher)
        .build(output)
    )
    if not result.success or not output.is_file():
        raise SystemExit(f"❌ Python builder failed: {result.errors}")


def describe(fixture: Path) -> dict[str, object]:
    """Verify a freshly built fixture and record the facts the tests pin."""
    from flavor.psp.format_2025 import PSPFReader
    from flavor.verification import FlavorVerifier

    verified = FlavorVerifier.verify_package(fixture)
    if not verified["valid"]:
        raise SystemExit(f"❌ Freshly built fixture does not verify: {fixture}")

    reader = PSPFReader(fixture)
    index = reader.read_index()

    return {
        "sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "size": fixture.stat().st_size,
        "public_key": index.public_key.hex(),
        "key_fingerprint": index.attestation_key_fp.rstrip(b"\x00").decode("ascii"),
        "slot_count": index.slot_count,
    }


def generate(repo_root: Path, generation: str, force: bool) -> None:
    """Build every producer's fixture into the generation directory."""
    fixture_dir = repo_root / "tests" / "fixtures" / "format_compat" / generation
    inputs = fixture_dir / "inputs"
    payload = inputs / "payload.txt"
    launcher = inputs / "launcher-stub.sh"

    for required in (payload, launcher):
        if not required.is_file():
            raise SystemExit(f"❌ Missing fixture input: {required}")

    existing = sorted(fixture_dir.glob("*.psp"))
    if existing and not force:
        names = ", ".join(p.name for p in existing)
        raise SystemExit(
            f"❌ {generation} already holds fixtures ({names}).\n"
            "   Regenerating destroys the cross-version guarantee they exist to provide:\n"
            "   the point is that they were built by an older toolchain than the one\n"
            "   verifying them. If the format changed for real, add a new generation\n"
            "   directory instead. Pass --force only if you are certain."
        )

    launcher.chmod(0o755)

    with tempfile.TemporaryDirectory() as tmp:
        manifest = Path(tmp) / "manifest.json"
        manifest.write_text(json.dumps(build_manifest(str(payload)), indent=2) + "\n", encoding="utf-8")

        producers: dict[str, dict[str, object]] = {}

        for impl, label in (("rs", "rust"), ("go", "go")):
            binary = find_builder(repo_root, impl)
            output = fixture_dir / f"{label}.psp"
            build_with_binary(binary, manifest, launcher, output)
            producers[f"{label}.psp"] = {
                "producer": binary.name,
                "producer_version": builder_version(binary),
                **describe(output),
            }
            print(f"✅ built {output.relative_to(repo_root)}")

        output = fixture_dir / "python.psp"
        build_with_python(payload, launcher, output)
        producers["python.psp"] = {
            "producer": "flavor.psp.format_2025.pspf_builder",
            "producer_version": (repo_root / "VERSION").read_text(encoding="utf-8").strip(),
            **describe(output),
        }
        print(f"✅ built {output.relative_to(repo_root)}")

    # Record the manifest with a repo-relative source path, so the committed copy
    # does not carry the absolute path of whichever machine generated it.
    relative_payload = str(payload.relative_to(repo_root))
    (fixture_dir / "manifest.json").write_text(
        json.dumps(build_manifest(relative_payload), indent=2) + "\n", encoding="utf-8"
    )

    # Fixtures are read, never executed -- their launcher is a stub script. Keep
    # the executable bit off so nothing mistakes one for a runnable package.
    for fixture in fixture_dir.glob("*.psp"):
        fixture.chmod(0o644)

    expected = {
        "generation": generation,
        "key_seed": KEY_SEED,
        "package": {"name": PACKAGE_NAME, "version": PACKAGE_VERSION},
        "fixtures": producers,
    }
    (fixture_dir / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    print(f"✅ wrote {(fixture_dir / 'expected.json').relative_to(repo_root)}")


def main() -> int:
    """Parse arguments and generate the requested fixture generation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", default="v1", help="Fixture generation directory (default: v1)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing generation. Destroys its cross-version guarantee.",
    )
    args = parser.parse_args()

    repo_root = find_repo_root(Path(__file__))
    generate(repo_root, args.generation, args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# 🌶️📦🔚
