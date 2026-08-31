#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Which Linux wheels a packaged build is allowed to see.

`pip download --platform TAG` does not mean "prefer TAG". It replaces the set of
platform tags pip will consider, and pip expands each one *downward* only:
asking for `manylinux2014` (an alias of `manylinux_2_17`) makes 2_17, 2_12, 2_5
and `manylinux1` wheels visible, and everything newer invisible. A single
hardcoded tag is therefore a ceiling on what the ecosystem is allowed to have
moved on to, not a floor under compatibility.

That ceiling is reached in practice. jq published manylinux2014 wheels through
1.10.0 and `manylinux_2_26/2_28` from 1.11.0, so a lock that resolved jq 1.12.0
failed the Linux build outright with "No matching distribution found", while
darwin and windows built fine.

pip accepts `--platform` more than once, and prefers the tag listed *first*.
The default here lists `manylinux2014` first, so a package that still publishes
a 2_17 wheel is selected exactly as before and the artifact's glibc floor is
unchanged; `manylinux_2_28` is a fallback that only applies where nothing older
is published at all. Widening the default in that direction is not the same as
choosing a newer glibc floor deliberately -- a package can set `manylinux` in
`[tool.flavor.build]` to state the floor it actually intends.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from provide.foundation import logger

#: Ordered by preference. `manylinux2014` first keeps the wheels chosen for an
#: artifact identical to what a single-tag build chose; `manylinux_2_28` is
#: reached only for packages that publish nothing older.
DEFAULT_MANYLINUX_TAGS: tuple[str, ...] = ("manylinux2014", "manylinux_2_28")

#: flavorpack's architecture names to the ones manylinux tags spell.
_ARCH_SUFFIXES: dict[str, str] = {
    "amd64": "x86_64",
    "x86_64": "x86_64",
    "arm64": "aarch64",
    "aarch64": "aarch64",
}

#: The key a package sets under `[tool.flavor.build]`.
CONFIG_KEY = "manylinux"


def resolve_manylinux_tags(build_config: dict[str, Any] | None) -> tuple[str, ...]:
    """Read the manylinux policy out of a package's build configuration.

    Accepts a single tag or an ordered list of them, most preferred first. An
    unusable value is reported and the default is used rather than failing the
    build: a malformed string here should not be the reason a package cannot be
    packaged at all.
    """
    if not build_config:
        return DEFAULT_MANYLINUX_TAGS

    configured = build_config.get(CONFIG_KEY)
    if configured is None:
        return DEFAULT_MANYLINUX_TAGS

    if isinstance(configured, str):
        configured = [configured]

    if not isinstance(configured, Sequence) or isinstance(configured, bytes):
        logger.warning(
            f"⚠️ Ignoring [tool.flavor.build] {CONFIG_KEY}: expected a tag or list of tags, "
            f"got {type(configured).__name__}. Using {', '.join(DEFAULT_MANYLINUX_TAGS)}."
        )
        return DEFAULT_MANYLINUX_TAGS

    tags = tuple(tag for tag in configured if isinstance(tag, str) and tag.strip())
    if len(tags) != len(list(configured)):
        logger.warning(f"⚠️ Ignoring non-string entries in [tool.flavor.build] {CONFIG_KEY}.")
    if not tags:
        logger.warning(
            f"⚠️ [tool.flavor.build] {CONFIG_KEY} is empty. Using {', '.join(DEFAULT_MANYLINUX_TAGS)}."
        )
        return DEFAULT_MANYLINUX_TAGS

    return tags


def platform_tags_for_arch(tags: Sequence[str], arch: str) -> list[str]:
    """Expand bare manylinux tags into the arch-qualified ones pip wants.

    An architecture with no manylinux spelling yields nothing, which leaves the
    caller passing no `--platform` at all -- the right outcome, since pip then
    resolves for the machine it is running on.
    """
    suffix = _ARCH_SUFFIXES.get(arch)
    if suffix is None:
        logger.debug(f"No manylinux tag mapping for arch {arch!r}; leaving platform unconstrained")
        return []
    expanded = [f"{tag}_{suffix}" for tag in tags]
    if logger.is_trace_enabled():
        logger.trace(f"Linux build detected, arch={arch}, requesting wheels for {', '.join(expanded)}")
    return expanded


def platform_constraint_hint(platform_tags: Sequence[str]) -> str:
    """Explain a download failure that a platform constraint could have caused.

    A bare "No matching distribution found" says nothing about the constraint
    that hid the distribution, which is what makes this class of failure cost
    hours. Naming the tags, and the fact that pip only expands them downward,
    turns it into a one-line diagnosis.
    """
    if not platform_tags:
        return ""
    requested = ", ".join(platform_tags)
    return (
        f"\n\nWheels were requested for platform tags: {requested}. "
        "pip only considers these tags and older ones, never newer, so a package that "
        "has moved to a newer manylinux baseline is invisible here even though it is "
        f"published. Set `{CONFIG_KEY}` under [tool.flavor.build] to the tags this "
        "artifact should accept, most preferred first."
    )
