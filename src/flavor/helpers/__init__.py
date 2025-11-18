#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from flavor.helpers.manager import HelperInfo, HelperManager

__all__ = ["HelperInfo", "HelperManager"]

# Try to import embedded helpers if available
try:
    import flavor.helpers.bin as _bin_module  # type: ignore[import-untyped]

    # Re-export available functions
    __all__.extend(
        [
            name
            for name in dir(_bin_module)
            if not name.startswith("_") and callable(getattr(_bin_module, name))
        ]
    )
    # Make functions available at module level
    globals().update(
        {
            name: getattr(_bin_module, name)
            for name in dir(_bin_module)
            if not name.startswith("_") and callable(getattr(_bin_module, name))
        }
    )
except ImportError:
    # No embedded helpers - this is fine for development or universal wheels
    pass

# 🌶️📦🔚
