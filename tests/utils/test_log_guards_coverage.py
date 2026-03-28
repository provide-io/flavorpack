#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for log_guards utility — debug/trace level guards."""

from __future__ import annotations

import logging

import pytest


@pytest.mark.unit
class TestIsDebugEnabled:
    """Test is_debug_enabled()."""

    def test_returns_true_at_debug_level(self) -> None:
        from flavor.utils.log_guards import is_debug_enabled

        original = logging.root.level
        try:
            logging.root.setLevel(logging.DEBUG)
            assert is_debug_enabled() is True
        finally:
            logging.root.setLevel(original)

    def test_returns_false_at_warning_level(self) -> None:
        from flavor.utils.log_guards import is_debug_enabled

        original = logging.root.level
        try:
            logging.root.setLevel(logging.WARNING)
            assert is_debug_enabled() is False
        finally:
            logging.root.setLevel(original)

    def test_returns_false_at_info_level(self) -> None:
        from flavor.utils.log_guards import is_debug_enabled

        original = logging.root.level
        try:
            logging.root.setLevel(logging.INFO)
            assert is_debug_enabled() is False
        finally:
            logging.root.setLevel(original)

    def test_returns_true_at_notset(self) -> None:
        from flavor.utils.log_guards import is_debug_enabled

        original = logging.root.level
        try:
            logging.root.setLevel(logging.NOTSET)  # level=0, below DEBUG(10)
            assert is_debug_enabled() is True
        finally:
            logging.root.setLevel(original)


@pytest.mark.unit
class TestIsTraceEnabled:
    """Test is_trace_enabled()."""

    def test_returns_true_at_trace_level(self) -> None:
        from flavor.utils.log_guards import is_trace_enabled

        original = logging.root.level
        try:
            logging.root.setLevel(5)  # TRACE level
            assert is_trace_enabled() is True
        finally:
            logging.root.setLevel(original)

    def test_returns_true_at_notset(self) -> None:
        from flavor.utils.log_guards import is_trace_enabled

        original = logging.root.level
        try:
            logging.root.setLevel(logging.NOTSET)  # level=0
            assert is_trace_enabled() is True
        finally:
            logging.root.setLevel(original)

    def test_returns_false_at_debug_level(self) -> None:
        from flavor.utils.log_guards import is_trace_enabled

        original = logging.root.level
        try:
            logging.root.setLevel(logging.DEBUG)  # DEBUG=10, above TRACE=5
            assert is_trace_enabled() is False
        finally:
            logging.root.setLevel(original)

    def test_returns_false_at_warning_level(self) -> None:
        from flavor.utils.log_guards import is_trace_enabled

        original = logging.root.level
        try:
            logging.root.setLevel(logging.WARNING)
            assert is_trace_enabled() is False
        finally:
            logging.root.setLevel(original)


@pytest.mark.unit
class TestGlobalLoggerProxyPatch:
    """Test that GlobalLoggerProxy gets patched with is_debug_enabled / is_trace_enabled."""

    def test_global_logger_proxy_has_is_debug_enabled(self) -> None:
        import flavor.utils.log_guards  # noqa: F401 — ensure module is imported

        from provide.foundation.logger.core import GlobalLoggerProxy

        assert hasattr(GlobalLoggerProxy, "is_debug_enabled")

    def test_global_logger_proxy_has_is_trace_enabled(self) -> None:
        import flavor.utils.log_guards  # noqa: F401

        from provide.foundation.logger.core import GlobalLoggerProxy

        assert hasattr(GlobalLoggerProxy, "is_trace_enabled")

    def test_proxy_is_debug_enabled_callable(self) -> None:
        import flavor.utils.log_guards  # noqa: F401

        from provide.foundation.logger import logger

        result = logger.is_debug_enabled()
        assert isinstance(result, bool)

    def test_proxy_is_trace_enabled_callable(self) -> None:
        import flavor.utils.log_guards  # noqa: F401

        from provide.foundation import logger

        result = logger.is_trace_enabled()
        assert isinstance(result, bool)
