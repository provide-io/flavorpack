#!/usr/bin/env python3
"""
Post-install helper setup for Flavor.

This module handles first-run setup and helper binary management.
"""

import os
from pathlib import Path
import sys

from pyvider.telemetry import logger


def check_and_setup_helpers() -> bool:
    """Check if helpers are available and offer to download them.

    Returns:
        True if helpers are available, False otherwise
    """
    from flavor.helpers import HelperManager

    manager = HelperManager()
    helpers = manager.list_helpers(platform_filter=True)

    # Check if we have at least one launcher
    if helpers["launchers"]:
        return True

    # No helpers found - offer to download
    if not os.environ.get("FLAVOR_NO_AUTO_DOWNLOAD"):
        logger.info("🚀 Flavor helpers not found locally")
        logger.info("Helpers will be automatically downloaded when needed")
        logger.info("This only happens once and will be cached for future use")
        logger.info("")
        logger.info("To disable auto-download, set FLAVOR_NO_AUTO_DOWNLOAD=1")
        logger.info("To manually download helpers now, run: flavor helpers install")
        return True  # Will auto-download when needed

    # Auto-download disabled
    logger.warning("⚠️ Flavor helpers not found")
    logger.warning("Please install helpers using one of these methods:")
    logger.warning("1. Enable auto-download: unset FLAVOR_NO_AUTO_DOWNLOAD")
    logger.warning("2. Download manually: flavor helpers install")
    logger.warning("3. Build from source: flavor helpers build")
    return False


def ensure_helpers_available() -> None:
    """Ensure helpers are available before building a package.

    This is called by the orchestrator before building.
    """
    if os.environ.get("FLAVOR_NO_AUTO_DOWNLOAD"):
        # Check if helpers exist locally
        from flavor.helpers import HelperManager

        manager = HelperManager()
        helpers = manager.list_helpers(platform_filter=True)

        if not helpers["launchers"]:
            logger.error("❌ No helper binaries found and auto-download is disabled")
            logger.error("Please enable auto-download or install helpers manually")
            sys.exit(1)
    # If auto-download is enabled, helpers will be downloaded on demand
