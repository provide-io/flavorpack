# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Logging level guards for avoiding expensive f-string evaluation."""

from __future__ import annotations

import logging

from provide.foundation.logger.core import GlobalLoggerProxy

_TRACE_LEVEL = 5  # TRACE is below DEBUG in structlog/logging hierarchy


def is_debug_enabled() -> bool:
    """Return True if the root logger has DEBUG or lower level active."""
    return logging.root.level <= logging.DEBUG


def is_trace_enabled() -> bool:
    """Return True if the root logger has TRACE (level 5) or lower level active."""
    return logging.root.level <= _TRACE_LEVEL


# Patch GlobalLoggerProxy so logger.is_debug_enabled() / logger.is_trace_enabled()
# work in all flavor modules without modifying the provide.foundation package.
if not hasattr(GlobalLoggerProxy, "is_debug_enabled"):
    GlobalLoggerProxy.is_debug_enabled = lambda self: is_debug_enabled()  # type: ignore[method-assign]
if not hasattr(GlobalLoggerProxy, "is_trace_enabled"):
    GlobalLoggerProxy.is_trace_enabled = lambda self: is_trace_enabled()  # type: ignore[method-assign]


# Also patch structlog logger classes for xdist compatibility — when structlog
# is reconfigured in parallel test workers, the logger may become a bare
# PrintLogger or BoundLoggerLazyProxy without foundation's extensions.
def _is_debug_enabled_method(self: object, *_args: object, **_kwargs: object) -> bool:
    return is_debug_enabled()


def _is_trace_enabled_method(self: object, *_args: object, **_kwargs: object) -> bool:
    return is_trace_enabled()


_structlog_classes: list[type] = []
try:
    from structlog._output import PrintLogger as _PrintLogger

    _structlog_classes.append(_PrintLogger)
except ImportError:
    pass
try:
    from structlog._config import BoundLoggerLazyProxy

    _structlog_classes.append(BoundLoggerLazyProxy)
except ImportError:
    pass

for _cls in _structlog_classes:
    if not hasattr(_cls, "is_debug_enabled"):
        _cls.is_debug_enabled = _is_debug_enabled_method  # type: ignore[attr-defined]
    if not hasattr(_cls, "is_trace_enabled"):
        _cls.is_trace_enabled = _is_trace_enabled_method  # type: ignore[attr-defined]
