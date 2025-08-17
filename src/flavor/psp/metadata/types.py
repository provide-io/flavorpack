"""
Type definitions for metadata structures.

These TypedDict definitions provide type hints for external APIs
and dictionary-based data structures.
"""

from typing import TypedDict, NotRequired, Literal, Any


class DirectoryDict(TypedDict):
    """Type hint for directory configuration."""
    path: str
    mode: NotRequired[str]


class WorkenvDict(TypedDict):
    """Type hint for workenv configuration."""
    directories: NotRequired[list[DirectoryDict]]
    env: NotRequired[dict[str, str]]
    umask: NotRequired[str]


class RuntimeEnvDict(TypedDict):
    """Type hint for runtime environment operations."""
    unset: NotRequired[list[str]]
    pass_: NotRequired[list[str]]  # 'pass' is a keyword, so use pass_
    map: NotRequired[dict[str, str]]
    set: NotRequired[dict[str, str]]


class RuntimeDict(TypedDict):
    """Type hint for runtime configuration."""
    env: NotRequired[RuntimeEnvDict]


class ExecutionDict(TypedDict):
    """Type hint for execution configuration."""
    command: NotRequired[str]
    args: NotRequired[list[str]]
    env: NotRequired[dict[str, str]]


class PackageDict(TypedDict):
    """Type hint for package information."""
    name: str
    version: str
    description: NotRequired[str]
    authors: NotRequired[list[str]]
    license: NotRequired[str]


class PSPF2025MetadataDict(TypedDict):
    """Complete PSPF/2025 metadata structure."""
    format: Literal["PSPF/2025"]
    package: NotRequired[PackageDict]
    runtime: NotRequired[RuntimeDict]
    workenv: NotRequired[WorkenvDict]
    execution: NotRequired[ExecutionDict]
    slots: NotRequired[list[dict[str, Any]]]


# Generic metadata dict for unknown formats
MetadataDict = dict[str, Any]