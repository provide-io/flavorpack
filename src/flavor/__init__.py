#
# flavor/__init__.py
#
"""
This package contains the core logic for building and verifying the
Pyvider Secure Package Format (Flavor).
"""

from flavor._version import __version__

from flavor.api import (
    build_package_from_manifest,
    clean_cache,
    verify_package,
)
from flavor.exceptions import BuildError, VerificationError

__all__ = [
    "__version__",
    "BuildError",
    "VerificationError",
    "build_package_from_manifest",
    "clean_cache",
    "verify_package",
]
# 🌐 📈 🔥


# 📦🍜🚀🪄
