# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
MkDocs hook to parse VERSION file and set documentation metadata.

This hook:
1. Reads the VERSION file from the project root
2. Determines if the version is alpha, beta, or stable
3. Sets config.extra.version_status for use in templates
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any


def parse_version(version_str: str) -> dict[str, str | int]:
    """
    Parse version string into components.

    Supports formats like:
    - 0.0.1000-0 (alpha)
    - 0.1.0-beta.1 (beta)
    - 1.0.0 (stable)
    """
    # Remove whitespace
    version_str = version_str.strip()

    # Check for pre-release indicators
    if re.search(r"-(alpha|a\d+|0)$", version_str, re.IGNORECASE):
        status = "alpha"
    elif re.search(r"-(beta|b\d+|rc\d+)", version_str, re.IGNORECASE):
        status = "beta"
    elif version_str.startswith("0.0."):
        # Semantic versioning: 0.0.x is considered alpha
        status = "alpha"
    elif version_str.startswith("0."):
        # Semantic versioning: 0.x.y is considered beta
        status = "beta"
    else:
        status = "stable"

    return {
        "version": version_str,
        "status": status,
    }


def on_config(config: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """
    Hook called when MkDocs config is loaded.

    Reads VERSION file and sets extra.version_status.
    """
    # Find VERSION file (look in docs_dir parent, i.e., project root)
    docs_dir = Path(config.get("docs_dir", "docs"))
    version_file = docs_dir.parent / "VERSION"

    if version_file.exists():
        version_str = version_file.read_text()
        version_info = parse_version(version_str)

        # Set in config.extra for template access
        if "extra" not in config:
            config["extra"] = {}

        config["extra"]["version_status"] = version_info["status"]
        config["extra"]["version_string"] = version_info["version"]

    return config


def define_env(env: Any) -> None:
    """
    Hook for mkdocs-macros plugin to define custom variables and macros.
    """

    @env.macro  # type: ignore[untyped-decorator]
    def audit_status(
        audited: bool = False,
        reviewer: str = "",
        notes: str = "",
    ) -> dict[str, str | bool]:
        """
        Generate audit status metadata for inclusion in page frontmatter.

        Usage in markdown:
        ---
        audited: true
        reviewer: "John Doe"
        audit_notes: "Reviewed 2025-11-06"
        ---
        """
        return {
            "audited": audited,
            "reviewer": reviewer,
            "audit_notes": notes,
        }
