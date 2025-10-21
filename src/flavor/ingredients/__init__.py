# flavor/ingredients/__init__.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from flavor.ingredients.manager import IngredientInfo, IngredientManager

__all__ = ["IngredientInfo", "IngredientManager"]

# Try to import embedded ingredients if available
try:
    import flavor.ingredients.bin as _bin_module

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
    # No embedded ingredients - this is fine for development or universal wheels
    pass
# 🌶️📦📦🪄
