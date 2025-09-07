#!/usr/bin/env python3
"""Embed platform-specific ingredients into the Flavor package."""

import argparse
import shutil
import sys
from pathlib import Path


def embed_ingredients(platform: str, ingredients_dir: str, version: str) -> bool:
    """
    Embed platform-specific ingredients into src/flavor/ingredients.
    
    Args:
        platform: Target platform (e.g., darwin_arm64, linux_amd64)
        ingredients_dir: Directory containing ingredient binaries
        version: Flavor version
    
    Returns:
        True if successful, False otherwise
    """
    ingredients_path = Path(ingredients_dir)
    if not ingredients_path.exists():
        print(f"❌ Ingredients directory not found: {ingredients_path}")
        return False
    
    # Create target directory - use ingredients/bin to avoid conflict with ingredients.py
    target_dir = Path("src/flavor/ingredients/bin")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Ingredient binary names
    ingredient_names = [
        "flavor-go-builder",
        "flavor-go-launcher", 
        "flavor-rs-builder",
        "flavor-rs-launcher"
    ]
    
    ingredients_copied = 0
    for ingredient in ingredient_names:
        # Try different naming patterns
        patterns = [
            f"{ingredient}-{version}-{platform}",
            f"{ingredient}-{platform}",
            ingredient
        ]
        
        for pattern in patterns:
            source = ingredients_path / pattern
            if source.exists():
                # Determine target name
                target_name = ingredient
                if platform.startswith("windows"):
                    target_name += ".exe"
                
                target = target_dir / target_name
                
                # Copy the ingredient
                shutil.copy2(source, target)
                
                # Make executable (Unix-like systems)
                if not platform.startswith("windows"):
                    target.chmod(0o755)
                
                print(f"  ✓ Embedded {ingredient}")
                ingredients_copied += 1
                break
        else:
            print(f"  ⚠️  Ingredient not found: {ingredient}")
    
    if ingredients_copied == 0:
        print("❌ No ingredients were embedded")
        return False
    
    # Create __init__.py for ingredients/bin package
    init_file = target_dir / "__init__.py"
    init_file.write_text('''"""Embedded ingredient binaries for Flavor."""
import os
from pathlib import Path

from provide.foundation.platform import is_windows


def get_ingredients_dir() -> Path:
    """Get the directory containing ingredient binaries."""
    return Path(__file__).parent


def get_ingredient_path(ingredient_name: str) -> Path:
    """Get the path to a specific ingredient binary."""
    ingredients_dir = get_ingredients_dir()
    
    # Add .exe extension on Windows
    if is_windows():
        ingredient_name = f"{ingredient_name}.exe"
    
    ingredient_path = ingredients_dir / ingredient_name
    
    # Make executable if needed
    if ingredient_path.exists() and not os.access(ingredient_path, os.X_OK):
        try:
            ingredient_path.chmod(0o755)
        except:
            pass
    
    return ingredient_path


# Ingredient shortcuts
def get_go_builder() -> Path:
    """Get path to Go builder."""
    return get_ingredient_path('flavor-go-builder')


def get_go_launcher() -> Path:
    """Get path to Go launcher."""
    return get_ingredient_path('flavor-go-launcher')


def get_rs_builder() -> Path:
    """Get path to Rust builder."""
    return get_ingredient_path('flavor-rs-builder')


def get_rs_launcher() -> Path:
    """Get path to Rust launcher."""
    return get_ingredient_path('flavor-rs-launcher')
''')
    
    print(f"✅ Embedded {ingredients_copied} ingredients for {platform}")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Embed ingredients for platform-specific wheel")
    parser.add_argument("platform", help="Target platform (e.g., darwin_arm64)")
    parser.add_argument("ingredients_dir", help="Directory containing ingredient binaries")
    parser.add_argument("version", help="Flavor version")
    
    args = parser.parse_args()
    
    success = embed_ingredients(args.platform, args.ingredients_dir, args.version)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()