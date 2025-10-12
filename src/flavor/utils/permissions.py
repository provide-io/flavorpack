"""File permission utilities.

DEPRECATED: This module is a compatibility shim. Import directly from:
    from provide.foundation.file import (
        parse_permissions,
        set_file_permissions,
        ensure_secure_permissions,
        get_permissions,
        format_permissions,
        DEFAULT_FILE_PERMS,
        DEFAULT_DIR_PERMS,
        DEFAULT_EXECUTABLE_PERMS,
    )
"""

from provide.foundation.file import (
    DEFAULT_DIR_PERMS,
    DEFAULT_EXECUTABLE_PERMS,
    DEFAULT_FILE_PERMS,
    ensure_secure_permissions,
    format_permissions,
    get_permissions,
    parse_permissions,
    set_file_permissions,
)

__all__ = [
    "DEFAULT_DIR_PERMS",
    "DEFAULT_EXECUTABLE_PERMS",
    "DEFAULT_FILE_PERMS",
    "ensure_secure_permissions",
    "format_permissions",
    "get_permissions",
    "parse_permissions",
    "set_file_permissions",
]
