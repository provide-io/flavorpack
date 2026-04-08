# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
MkDocs hook to filter navigation entries.

This hook removes specific navigation entries from the built navigation tree,
allowing documentation to be included and accessible via URL without appearing
in the navigation sidebar or top tabs.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.nav import Navigation

log = logging.getLogger("mkdocs.hooks.nav_filter")


def on_nav(nav: Navigation, config: MkDocsConfig, files: Files) -> Navigation:
    """
    Filter navigation entries based on configuration.

    Removes nav items whose URL path starts with any of the configured
    hidden path prefixes.

    Args:
        nav: Navigation object
        config: MkDocs config
        files: File collection

    Returns:
        Modified navigation object
    """
    # Get list of path prefixes to hide from navigation
    hidden_paths_str = os.getenv("MKDOCS_HIDDEN_NAV_PATHS", "")
    hidden_paths = [p.strip() for p in hidden_paths_str.split(",") if p.strip()]

    # No default hidden paths - all navigation is explicit in mkdocs.yml
    all_hidden_paths = hidden_paths

    if not all_hidden_paths:
        return nav

    # Filter the navigation items
    filtered_items = []
    removed_count = 0

    for item in nav.items:
        if should_hide_nav_item(item, all_hidden_paths):
            removed_count += 1
            log.info(f"Hiding navigation item: {get_nav_item_title(item)}")
        else:
            filtered_items.append(item)

    # Update the navigation items
    nav.items = filtered_items

    if removed_count > 0:
        log.info(f"Filtered {removed_count} navigation item(s) from sidebar")

    return nav


def should_hide_nav_item(item: Any, hidden_paths: list[str]) -> bool:
    """
    Check if a navigation item should be hidden.

    Args:
        item: Navigation item
        hidden_paths: List of path prefixes to hide

    Returns:
        True if item should be hidden, False otherwise
    """
    # Get the URL from the item if it has one
    url = getattr(item, "url", None)

    if url:
        # Check if URL starts with any hidden path
        for hidden_path in hidden_paths:
            # Normalize paths for comparison
            normalized_url = url.lstrip("/")
            normalized_hidden = hidden_path.lstrip("/")

            if normalized_url.startswith(normalized_hidden):
                return True

    # Check children if this is a section
    if hasattr(item, "children") and item.children:
        # If ALL children are hidden, hide the parent too
        all_children_hidden = all(should_hide_nav_item(child, hidden_paths) for child in item.children)
        if all_children_hidden:
            return True

    return False


def get_nav_item_title(item: Any) -> str:
    """
    Get a readable title for a navigation item.

    Args:
        item: Navigation item

    Returns:
        String title
    """
    if hasattr(item, "title"):
        return str(item.title)
    if hasattr(item, "url"):
        return str(item.url)
    return str(item)
