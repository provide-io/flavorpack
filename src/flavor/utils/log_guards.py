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
