#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Create a temporary trust store with the public key derived from a seed.

Usage:
    python3 setup_trust_store.py <seed> <trust_dir>

Derives the deterministic Ed25519 keypair from the seed (SHA-256 → Ed25519),
computes the fingerprint, and writes a .pub file to trust_dir.

Exit codes:
    0 — success (prints fingerprint to stdout)
    1 — failure
"""

import hashlib
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <seed> <trust_dir>", file=sys.stderr)
        return 1

    seed = sys.argv[1]
    trust_dir = Path(sys.argv[2])
    trust_dir.mkdir(parents=True, exist_ok=True)

    # Derive the same keypair that PSPFBuilder.with_keys(seed=...) produces
    seed_bytes = hashlib.sha256(seed.encode("utf-8")).digest()
    private_key = Ed25519PrivateKey.from_private_bytes(seed_bytes)
    public_key = private_key.public_key()

    raw_pub = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    fingerprint = hashlib.sha256(raw_pub).hexdigest()

    pem_pub = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    pub_file = trust_dir / f"{fingerprint[:16]}.pub"
    pub_file.write_bytes(f"# Name: seed:{seed}\n".encode() + pem_pub)

    print(fingerprint)
    return 0


if __name__ == "__main__":
    sys.exit(main())
