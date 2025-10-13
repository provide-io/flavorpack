#
# flavor/__init__.py
#
"""
This package contains the core logic for building and verifying the
Pyvider Secure Package Format (Flavor).
"""

# Set Foundation's setup log level before any imports
# This MUST happen first to control Foundation's initialization logs
import os

if "FOUNDATION_SETUP_LOG_LEVEL" not in os.environ:
    # Default to ERROR to suppress Foundation's debug/trace initialization logs
    # unless explicitly set via FOUNDATION_LOG_LEVEL
    setup_level = os.environ.get("FOUNDATION_LOG_LEVEL", "ERROR")
    os.environ["FOUNDATION_SETUP_LOG_LEVEL"] = setup_level

from flavor._version import __version__
from flavor.exceptions import BuildError, VerificationError
from flavor.package import (
    build_package_from_manifest,
    clean_cache,
    verify_package,
)

__all__ = [
    "BuildError",
    "VerificationError",
    "__version__",
    "build_package_from_manifest",
    "clean_cache",
    "verify_package",
]
# 🌐 📈 🔥


# 📦🍜🚀🪄
