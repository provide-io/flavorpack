# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
MkDocs hook to fix navigation URLs for monorepo included projects.

The mkdocs-monorepo plugin includes sub-project navigation but doesn't
prefix the nav URLs with the project namespace. This hook fixes that
by detecting nav items under known sub-project sections and prefixing
their URLs appropriately.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.nav import Navigation

log = logging.getLogger("mkdocs.hooks.monorepo_nav_fix")

# Sub-projects that need nav URL prefixing when included via monorepo
# Maps section title patterns to their URL prefix
MONOREPO_SECTIONS = {
    "terraform-provider-pyvider": "terraform-provider-pyvider",
    "terraform-provider-tofusoup": "terraform-provider-tofusoup",
}


def on_nav(nav: Navigation, config: MkDocsConfig, files: Files) -> Navigation:
    """
    Fix navigation URLs for monorepo included projects.

    Walks the nav tree and prefixes URLs for items under known
    monorepo sub-project sections.

    Args:
        nav: Navigation object
        config: MkDocs config
        files: File collection

    Returns:
        Modified navigation object
    """
    for item in nav.items:
        _process_nav_item(item, None)

    return nav


def _process_nav_item(item: Any, current_prefix: str | None) -> None:
    """
    Recursively process nav items, applying URL prefixes where needed.

    Args:
        item: Navigation item (Section, Page, or Link)
        current_prefix: The URL prefix to apply (from parent section)
    """
    # Get item title for matching
    title = getattr(item, "title", "")

    # Check if this is a monorepo section that needs prefixing
    new_prefix = current_prefix
    if title:
        title_lower = title.lower().replace(" ", "-")
        for section_pattern, prefix in MONOREPO_SECTIONS.items():
            if section_pattern in title_lower or title_lower == section_pattern:
                new_prefix = prefix
                log.debug(f"Found monorepo section: {title} -> prefix: {prefix}")
                break

    # If we have a prefix and this item has a URL, prefix it
    if new_prefix and hasattr(item, "url") and item.url:
        url = item.url
        # Only prefix if it's a relative URL that doesn't already have the prefix
        # and doesn't look like an already-prefixed sub-project path
        if (
            not url.startswith("/")
            and not url.startswith("http")
            and not url.startswith(f"{new_prefix}/")
            and not any(url.startswith(f"{p}/") for p in MONOREPO_SECTIONS.values())
        ):
            new_url = f"{new_prefix}/{url}"
            item.url = new_url
            log.debug(f"Prefixed nav URL: {url} -> {new_url}")

    # Process children recursively
    if hasattr(item, "children") and item.children:
        for child in item.children:
            _process_nav_item(child, new_prefix)
