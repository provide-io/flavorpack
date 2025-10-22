#!/usr/bin/env python3
"""Cross-language compatibility testing command for PSPF packages."""

import json
import os
from pathlib import Path
import sys
import tempfile

import click
from provide.foundation import logger
from provide.foundation.process import run

from flavor.ingredients.manager import IngredientManager as HelperManager


class CrossLangTester:
    """Cross-language compatibility tester."""

    def __init__(self, verbose=False, json_output=False) -> None:
        self.verbose = verbose
        self.json_output = json_output
        self.results = {
            "build_tests": [],
            "verify_tests": [],
            "launch_tests": [],
            "cli_tests": [],
            "reproducible_tests": [],
            "summary": {},
        }

        # Initialize helper manager for finding helpers
        self.helper_manager = HelperManager()

        logger.debug(
            "Initializing CrossLangTester",
            cwd=str(Path.cwd()),
            initial_ingredients_bin=str(self.helper_manager.ingredients_bin),
            initial_ingredients_dir=str(self.helper_manager.ingredients_dir),
        )

        # When running crosslang tests, we need actual ingredient binaries
        # Look for FLAVOR_INGREDIENTS_DIR environment variable first
        ingredients_dir = os.environ.get("FLAVOR_INGREDIENTS_DIR")
        if ingredients_dir:
            ingredients_path = Path(ingredients_dir)
            logger.debug(
                "Found FLAVOR_INGREDIENTS_DIR env var",
                path=ingredients_dir,
                exists=ingredients_path.exists(),
            )
            if ingredients_path.exists():
                self.helper_manager.ingredients_bin = ingredients_path / "bin"
                self.helper_manager.ingredients_dir = ingredients_path
                logger.info(
                    "Using ingredients from FLAVOR_INGREDIENTS_DIR",
                    ingredients_bin=str(self.helper_manager.ingredients_bin),
                    ingredients_dir=str(self.helper_manager.ingredients_dir),
                )
        else:
            logger.debug("No FLAVOR_INGREDIENTS_DIR env var, searching directory tree")
            # Try to find ingredients relative to the current working directory
            # Look up the directory tree for a dist/bin directory
            current = Path.cwd()
            for parent in [current, *current.parents]:
                dist_bin = parent / "dist" / "bin"
                logger.trace("Checking for dist/bin", path=str(dist_bin))
                if dist_bin.exists():
                    self.helper_manager.ingredients_bin = dist_bin
                    self.helper_manager.ingredients_dir = parent / "dist"
                    logger.info(
                        "Found ingredients in directory tree",
                        ingredients_bin=str(dist_bin),
                        ingredients_dir=str(parent / "dist"),
                    )
                    break
            else:
                logger.warning("No dist/bin directory found in directory tree")

        # Log final state and contents
        logger.debug(
            "Final ingredient paths",
            ingredients_bin=str(self.helper_manager.ingredients_bin),
            ingredients_dir=str(self.helper_manager.ingredients_dir),
            bin_exists=self.helper_manager.ingredients_bin.exists(),
        )

        if self.helper_manager.ingredients_bin.exists():
            files = list(self.helper_manager.ingredients_bin.glob("*"))
            logger.debug(
                "Ingredients bin contents",
                file_count=len(files),
                files=[f.name for f in files],
            )

        # Find taster directory - look for manifest files
        current = Path.cwd()
        self.taster_dir = None

        # Check if we're already in taster directory
        if (current / "pyproject.toml").exists() and "taster" in str(current):
            self.taster_dir = current
        else:
            # Search for taster directory
            for parent in [current, *list(current.parents)]:
                taster_path = parent / "tests/taster"
                if taster_path.exists() and (taster_path / "pyproject.toml").exists():
                    self.taster_dir = taster_path
                    break

        if not self.taster_dir:
            self.taster_dir = Path.cwd()  # Fallback to current directory

    def log(self, message, level="info") -> None:
        """Log a message."""
        if not self.json_output:
            if level == "error":
                click.secho(message, fg="red")
            elif level == "success":
                click.secho(message, fg="green")
            elif level == "warning":
                click.secho(message, fg="yellow")
            else:
                click.echo(message)

    def build_with_launcher(self, launcher_info, key_seed="test123"):
        """Build package using Python builder with specified launcher."""
        # Extract language from launcher name (e.g., "flavor-go-launcher" -> "go")
        launcher_lang = launcher_info.language
        output = self.taster_dir / f"test-{launcher_lang}.psp"

        # Create a temporary test package
        temp_dir = tempfile.mkdtemp(prefix="crosslang_test_")

        # Create a simple Python module
        test_module = Path(temp_dir) / "crosslang_test.py"
        test_module.write_text("""#!/usr/bin/env python3
import sys

