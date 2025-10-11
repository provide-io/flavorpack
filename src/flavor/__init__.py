#
# flavor/__init__.py
#
"""
This package contains the core logic for building and verifying the
Pyvider Secure Package Format (Flavor).
"""

import os

# Set service name for Foundation logging/telemetry (uses OTEL standard)
os.environ.setdefault("PROVIDE_SERVICE_NAME", "flavor")

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
