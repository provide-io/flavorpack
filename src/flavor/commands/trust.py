#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""flavor trust — manage the trusted signing key store."""

from __future__ import annotations

from pathlib import Path

import click
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_public_key,
)
from provide.foundation.console import perr, pout

from flavor.config.dirs import get_system_config_dir, get_trusted_keys_dir
from flavor.config.trust import _load_keys_from_dir, compute_key_fingerprint, is_key_trusted, load_trusted_keys
from flavor.console import get_command_logger
from flavor.psp.format_2025.reader import PSPFReader

log = get_command_logger("trust")


@click.group("trust")
def trust_group() -> None:
    """Manage the trusted signing key store."""


@trust_group.command("add")
@click.argument("key_file", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--name", default=None, help="Human-readable label for this key.")
@click.option("--global", "global_", is_flag=True, default=False, help="Add to system store.")
def trust_add(key_file: str, name: str | None, global_: bool) -> None:
    """Add a public key to the trusted-keys store."""
    src = Path(key_file)
    try:
        raw_bytes = src.read_bytes()
        pem_lines = [
            line for line in raw_bytes.decode().splitlines() if not line.strip().startswith("# Name:")
        ]
        pub_key = load_pem_public_key("\n".join(pem_lines).encode())
        fp = compute_key_fingerprint(pub_key)
    except Exception as exc:
        perr(f"Failed to read key: {exc}")
        raise SystemExit(1) from exc

    store_dir = get_trusted_keys_dir(system=global_)
    store_dir.mkdir(parents=True, exist_ok=True)

    dest = store_dir / f"{fp[:16]}.pub"
    label = f"# Name: {name}\n".encode() if name else b""
    raw_pem = pub_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    dest.write_bytes(label + raw_pem)
    pout(f"Added key {fp[:16]}...  ({name or 'no label'})  → {dest}")


@trust_group.command("list")
@click.option("--global", "global_", is_flag=True, default=False, help="Show system store only.")
def trust_list(global_: bool) -> None:
    """List all trusted keys and their fingerprints."""
    keys = _load_keys_from_dir(get_system_config_dir() / "trusted-keys") if global_ else load_trusted_keys()

    if not keys:
        pout("No trusted keys found.")
        return

    for fp, info in sorted(keys.items()):
        label = info.get("name") or "(no label)"
        pout(f"  {fp}  {label}")


@trust_group.command("remove")
@click.argument("fingerprint")
@click.option("--global", "global_", is_flag=True, default=False, help="Remove from system store.")
def trust_remove(fingerprint: str, global_: bool) -> None:
    """Remove a key from the trusted-keys store by fingerprint."""
    store_dir = get_trusted_keys_dir(system=global_)
    if global_:
        keys = _load_keys_from_dir(get_system_config_dir() / "trusted-keys")
    else:
        keys = load_trusted_keys(include_system=False)

    if fingerprint not in keys:
        perr(f"Key not found: {fingerprint[:16]}...")
        raise SystemExit(1)

    key_path = Path(keys[fingerprint]["path"])
    key_path.unlink()
    pout(f"Removed {fingerprint[:16]}...  from {store_dir}")


@trust_group.command("verify")
@click.argument("package_file", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
def trust_verify(package_file: str) -> None:
    """Check whether a package's signing key is in the trusted store."""
    pkg_path = Path(package_file)
    with PSPFReader(pkg_path) as reader:
        index = reader.read_index()

    fp_bytes = index.attestation_key_fp.rstrip(b"\x00")
    if not fp_bytes:
        perr("Package has no key fingerprint in attestation field.")
        raise SystemExit(2)

    fp = fp_bytes.decode("ascii")
    result = is_key_trusted(fp)

    if result is None:
        pout(f"No trusted-keys store found. Key fingerprint: {fp[:16]}...")
        pout("Run `flavor init` to set up a key store.")
    elif result:
        pout(f"✓ Key {fp[:16]}... is trusted.")
    else:
        perr(f"✗ Key {fp[:16]}... is NOT in the trusted store.")
        raise SystemExit(1)


# 🌶️📦🔚
