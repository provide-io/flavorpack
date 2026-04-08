# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
MkDocs hooks for Terraform provider documentation.

This module provides hooks to:
1. Convert Terraform-style callouts to MkDocs admonitions
2. Copy .provide directory assets to the built site

Converts:
  -> **Note:** text     → !!! note
  ~> **Note:** text     → !!! warning
  !> **Warning:** text  → !!! danger
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
from typing import Any


def on_page_markdown(
    markdown: str,
    page: Any,
    config: dict[str, Any],
    files: Any,
) -> str:
    """
    Process markdown to convert Terraform callouts before rendering.

    This hook is automatically called by MkDocs for each page.

    Args:
        markdown: The markdown content of the page
        page: The page object
        config: The MkDocs configuration
        files: The files collection

    Returns:
        The processed markdown content
    """
    # Pattern to match Terraform callouts at start of line
    pattern = r"^(->|~>|!>)\s+\*\*([^*]+):\*\*\s+(.+)$"

    def replace_callout(match: re.Match[str]) -> str:
        sigil = match.group(1)
        title_text = match.group(2)  # e.g., "Note" or "Warning"
        content = match.group(3)

        # Map Terraform sigils to MkDocs admonition types
        sigil_map = {
            "->": "note",  # Blue
            "~>": "warning",  # Orange/yellow
            "!>": "danger",  # Red
        }

        admonition_type = sigil_map.get(sigil, "note")

        # Build MkDocs admonition with proper indentation
        return f'!!! {admonition_type} "{title_text}"\n\n    {content}'

    # Process line by line
    lines = markdown.split("\n")
    result_lines = []

    for line in lines:
        match = re.match(pattern, line)
        if match:
            result_lines.append(replace_callout(match))
        else:
            result_lines.append(line)

    return "\n".join(result_lines)


def on_post_build(config: dict[str, Any]) -> None:
    """
    Copy .provide directory to built site after build completes.

    MkDocs doesn't copy hidden directories by default, so we manually
    copy .provide/foundry/theme assets to the site directory.

    Args:
        config: The MkDocs configuration dictionary
    """
    docs_provide = Path(config["docs_dir"]) / ".provide"
    site_provide = Path(config["site_dir"]) / ".provide"

    if docs_provide.exists():
        # Remove existing if present
        if site_provide.exists():
            shutil.rmtree(site_provide)

        # Copy .provide directory to site
        shutil.copytree(docs_provide, site_provide)
        print("✅ Copied .provide assets to site")
