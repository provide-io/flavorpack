#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test script to verify cryptography and other binary dependencies are installed correctly."""

import sys


def test_imports() -> int:
    """Test that critical binary packages can be imported."""

    packages_to_test = [
        ("cryptography", "cryptography.hazmat.primitives.ciphers"),
        ("grpcio", "grpc"),
        ("requests", "requests"),
        ("urllib3", "urllib3"),
    ]

    failed = []
    for package_name, import_name in packages_to_test:
        try:
            __import__(import_name)
            # For cryptography, verify it's working
            if package_name == "cryptography":
                from cryptography.fernet import Fernet

                key = Fernet.generate_key()
                f = Fernet(key)
                token = f.encrypt(b"test")
                f.decrypt(token)
                print("     ✓ Cryptography encryption/decryption working")
        except ImportError as e:
            print(f"  ❌ {package_name}: import failed - {e}")
            failed.append(package_name)
        except Exception as e:
            print(f"  ❌ {package_name}: runtime error - {e}")
            failed.append(package_name)

    if failed:
        print(f"\n❌ Failed to import: {', '.join(failed)}")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(test_imports())

# 🌶️📦🔚
