#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test module import consistency after api.py → package.py refactoring."""

import pytest


def test_backward_compatibility_via_init() -> None:
    """Test that old imports still work via __init__.py re-exports."""
    # These should work exactly as before
    from flavor import build_package_from_manifest, clean_cache, verify_package

    # Verify they're callable
    assert callable(build_package_from_manifest)
    assert callable(verify_package)
    assert callable(clean_cache)


def test_direct_module_imports() -> None:
    """Test that new module names work directly."""
    # New direct imports should work
    from flavor.package import build_package_from_manifest, clean_cache, verify_package

    # Verify they're callable
    assert callable(build_package_from_manifest)
    assert callable(verify_package)
    assert callable(clean_cache)


def test_import_consistency() -> None:
    """Test that both import paths give the same objects."""
    from flavor import build_package_from_manifest as old_func
    from flavor.package import build_package_from_manifest as new_func

    # Should be the exact same function object
    assert old_func is new_func


def test_no_circular_imports() -> None:
    """Test that there are no circular import issues."""
    import flavor
    import flavor.package

    # Should be able to access without issues
    assert hasattr(flavor, "build_package_from_manifest")
    assert hasattr(flavor.package, "build_package_from_manifest")


def test_all_exports_accessible() -> None:
    """Test that __all__ is consistent."""
    import flavor
    import flavor.package

    # Main package should have all expected exports
    expected_exports = [
        "build_package_from_manifest",
        "verify_package",
        "clean_cache",
        "BuildError",
        "VerificationError",
        "__version__",
    ]

    for export in expected_exports:
        assert hasattr(flavor, export), f"flavor missing {export}"

    # Package module should have core functions
    package_exports = ["build_package_from_manifest", "verify_package", "clean_cache"]
    for export in package_exports:
        assert hasattr(flavor.package, export), f"flavor.package missing {export}"


# Note: Old API module test removed as part of Foundation config refactoring
# No backward compatibility is maintained per project requirements


if __name__ == "__main__":
    pytest.main([__file__])

# 🌶️📦🔚
