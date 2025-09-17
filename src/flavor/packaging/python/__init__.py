#
# flavor/packaging/python/__init__.py
#
from __future__ import annotations


"""Python-specific packaging utilities for FlavorPack."""

from flavor.packaging.python.pypapip_manager import PyPaPipManager

__all__ = [
    "PyPaPipManager",
]
