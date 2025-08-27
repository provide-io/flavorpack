"""Flavor ingredients module for managing ingredient binaries."""

from flavor.ingredients.manager import IngredientInfo, IngredientManager

__all__ = ["IngredientManager", "IngredientInfo"]

# Try to import embedded ingredients if available
try:
    from flavor.ingredients.bin import (
        get_go_builder,
        get_go_launcher,
        get_ingredient_path,
        get_ingredients_dir,
        get_rs_builder,
        get_rs_launcher,
    )

    __all__.extend(
        [
            "get_go_builder",
            "get_go_launcher",
            "get_ingredient_path",
            "get_ingredients_dir",
            "get_rs_builder",
            "get_rs_launcher",
        ]
    )
except ImportError:
    # No embedded ingredients - this is fine for development or universal wheels
    pass
