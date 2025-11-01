#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for flavor.output module."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
import sys
from unittest.mock import patch

from flavor.output import OutputFormat, OutputHandler, get_output_handler


class TestOutputFormat:
    """Test OutputFormat enum."""

    def test_output_format_values(self) -> None:
        """Test that OutputFormat has correct values."""
        assert OutputFormat.TEXT.value == "text"
        assert OutputFormat.JSON.value == "json"


class TestOutputHandler:
    """Test suite for OutputHandler class."""

    def test_init_defaults(self) -> None:
        """Test OutputHandler initialization with defaults."""
        handler = OutputHandler()
        assert handler.format == OutputFormat.TEXT
        assert handler._output_file is None
        assert handler._file_handle is None
        assert handler._output_buffer == []

    def test_init_with_json_format(self) -> None:
        """Test OutputHandler initialization with JSON format."""
        handler = OutputHandler(format=OutputFormat.JSON)
        assert handler.format == OutputFormat.JSON

    def test_init_with_file_path(self) -> None:
        """Test OutputHandler initialization with file path."""
        handler = OutputHandler(file="/tmp/test.log")
        assert handler._output_file == "/tmp/test.log"

    def test_context_manager_stdout_default(self) -> None:
        """Test context manager with default stdout."""
        handler = OutputHandler()
        with handler as h:
            assert h is handler
            assert h._file_handle is None

    def test_context_manager_with_file(self, tmp_path: Path) -> None:
        """Test context manager with file output."""
        output_file = tmp_path / "output.txt"
        handler = OutputHandler(file=str(output_file))

        with handler as h:
            assert h._file_handle is not None
            assert h._file_handle.name == str(output_file)
            # Write something to verify file is open
            h._file_handle.write("test")

        # After exiting context, file should be closed
        assert h._file_handle.closed

    def test_context_manager_with_stdout_string(self) -> None:
        """Test context manager with explicit STDOUT string."""
        handler = OutputHandler(file="STDOUT")
        with handler as h:
            # Should not create file handle for STDOUT
            assert h._file_handle is None

    def test_context_manager_with_stderr_string(self) -> None:
        """Test context manager with explicit STDERR string."""
        handler = OutputHandler(file="STDERR")
        with handler as h:
            # Should not create file handle for STDERR
            assert h._file_handle is None

    def test_get_output_stream_stdout(self) -> None:
        """Test _get_output_stream returns stdout by default."""
        handler = OutputHandler()
        with handler:
            stream = handler._get_output_stream()
            assert stream is sys.stdout

    def test_get_output_stream_stderr(self) -> None:
        """Test _get_output_stream returns stderr when specified."""
        handler = OutputHandler(file="STDERR")
        with handler:
            stream = handler._get_output_stream()
            assert stream is sys.stderr

    def test_get_output_stream_file(self, tmp_path: Path) -> None:
        """Test _get_output_stream returns file handle when file specified."""
        output_file = tmp_path / "test.log"
        handler = OutputHandler(file=str(output_file))
        with handler:
            stream = handler._get_output_stream()
            assert stream is handler._file_handle

    def test_write_text_string(self) -> None:
        """Test write() with TEXT format and string data."""
        handler = OutputHandler(format=OutputFormat.TEXT)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write("Hello, world!")

        assert output.getvalue() == "Hello, world!\n"

    def test_write_text_string_with_newline(self) -> None:
        """Test write() with TEXT format and string already ending with newline."""
        handler = OutputHandler(format=OutputFormat.TEXT)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write("Hello, world!\n")

        # Should not add extra newline
        assert output.getvalue() == "Hello, world!\n"

    def test_write_text_dict(self) -> None:
        """Test write() with TEXT format and dict data."""
        handler = OutputHandler(format=OutputFormat.TEXT)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write({"name": "test", "value": 42})

        assert "name: test\n" in output.getvalue()
        assert "value: 42\n" in output.getvalue()

    def test_write_json_string(self) -> None:
        """Test write() with JSON format and string data."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write("test message")

        # JSON output is buffered until context exit
        result = output.getvalue()
        assert '"message": "test message"' in result

    def test_write_json_dict(self) -> None:
        """Test write() with JSON format and dict data."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write({"status": "success", "count": 5})

        result = output.getvalue()
        assert '"status": "success"' in result
        assert '"count": 5' in result

    def test_write_json_other_data(self) -> None:
        """Test write() with JSON format and non-string/dict data."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write([1, 2, 3])

        result = output.getvalue()
        assert '"data"' in result
        assert "1" in result and "2" in result and "3" in result

    def test_write_json_with_kwargs(self) -> None:
        """Test write() with JSON format and additional kwargs."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write({"status": "ok"}, extra="metadata", level="info")

        result = output.getvalue()
        assert '"status": "ok"' in result
        assert '"extra": "metadata"' in result
        assert '"level": "info"' in result

    def test_write_json_buffering(self) -> None:
        """Test that JSON output is buffered until context exit."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write("message 1")
            # Nothing written yet (buffered)
            assert output.getvalue() == ""
            handler.write("message 2")
            assert output.getvalue() == ""

        # After exit, all messages flushed
        result = output.getvalue()
        assert "message 1" in result
        assert "message 2" in result

    def test_flush_json_clears_buffer(self) -> None:
        """Test that _flush_json clears the output buffer."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write("test")
            assert len(handler._output_buffer) == 1
            handler._flush_json()
            assert len(handler._output_buffer) == 0

    def test_flush_json_empty_buffer(self) -> None:
        """Test that _flush_json handles empty buffer gracefully."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler._flush_json()

        # Should not write anything for empty buffer
        assert output.getvalue() == ""

    def test_error_text_format(self) -> None:
        """Test error() method with TEXT format."""
        handler = OutputHandler(format=OutputFormat.TEXT)

        with handler, patch("sys.stderr", new=StringIO()) as mock_stderr:
            handler.error("Something went wrong")

        assert "Error: Something went wrong\n" in mock_stderr.getvalue()

    def test_error_json_format(self) -> None:
        """Test error() method with JSON format."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.error("Something went wrong")

        result = output.getvalue()
        assert '"error": "Something went wrong"' in result

    def test_error_json_with_kwargs(self) -> None:
        """Test error() method with JSON format and additional kwargs."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.error("Failed", code=500, details="Internal error")

        result = output.getvalue()
        assert '"error": "Failed"' in result
        assert '"code": 500' in result
        assert '"details": "Internal error"' in result

    def test_success_text_format(self) -> None:
        """Test success() method with TEXT format."""
        handler = OutputHandler(format=OutputFormat.TEXT)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.success("Operation completed")

    def test_success_json_format(self) -> None:
        """Test success() method with JSON format."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.success("Operation completed")

        result = output.getvalue()
        assert '"success": "Operation completed"' in result

    def test_success_json_with_kwargs(self) -> None:
        """Test success() method with JSON format and kwargs."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.success("Done", duration=1.5, items=42)

        result = output.getvalue()
        assert '"success": "Done"' in result
        assert '"duration": 1.5' in result
        assert '"items": 42' in result

    def test_info_text_format(self) -> None:
        """Test info() method with TEXT format."""
        handler = OutputHandler(format=OutputFormat.TEXT)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.info("Processing data")

        assert "Processing data\n" in output.getvalue()

    def test_info_json_format(self) -> None:
        """Test info() method with JSON format."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.info("Processing data")

        result = output.getvalue()
        assert '"info": "Processing data"' in result

    def test_info_json_with_kwargs(self) -> None:
        """Test info() method with JSON format and kwargs."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.info("Status update", progress=75, stage="validation")

        result = output.getvalue()
        assert '"info": "Status update"' in result
        assert '"progress": 75' in result
        assert '"stage": "validation"' in result

    def test_context_exit_flushes_json(self) -> None:
        """Test that context manager exit flushes JSON output."""
        handler = OutputHandler(format=OutputFormat.JSON)
        output = StringIO()

        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write("buffered message")
            # Not flushed yet
            assert output.getvalue() == ""

        # After exit, should be flushed
        assert "buffered message" in output.getvalue()

    def test_context_exit_does_not_flush_text(self) -> None:
        """Test that context manager exit doesn't try to flush TEXT output."""
        handler = OutputHandler(format=OutputFormat.TEXT)
        output = StringIO()

        # TEXT mode writes immediately, no buffering
        with patch.object(handler, "_get_output_stream", return_value=output), handler:
            handler.write("immediate message")
            # Should already be written
            assert "immediate message" in output.getvalue()


class TestGetOutputHandler:
    """Test suite for get_output_handler factory function."""

    def test_default_output_handler(self) -> None:
        """Test get_output_handler with defaults."""
        with patch("provide.foundation.utils.environment.get_str", side_effect=["text", None]):
            handler = get_output_handler()

        assert handler.format == OutputFormat.TEXT
        assert handler._output_file is None

    def test_output_handler_json_format_from_env(self) -> None:
        """Test get_output_handler with JSON format from environment."""
        with patch(
            "provide.foundation.utils.environment.get_str",
            side_effect=lambda k, default=None: "json" if k == "FLAVOR_OUTPUT_FORMAT" else default,
        ):
            handler = get_output_handler()

        assert handler.format == OutputFormat.JSON

    def test_output_handler_text_format_from_env(self) -> None:
        """Test get_output_handler with explicit TEXT format from environment."""
        with patch(
            "provide.foundation.utils.environment.get_str",
            side_effect=lambda k, default=None: "text" if k == "FLAVOR_OUTPUT_FORMAT" else default,
        ):
            handler = get_output_handler()

        assert handler.format == OutputFormat.TEXT

    def test_output_handler_case_insensitive(self) -> None:
        """Test that format string is case-insensitive."""
        with patch(
            "provide.foundation.utils.environment.get_str",
            side_effect=lambda k, default=None: "JSON" if k == "FLAVOR_OUTPUT_FORMAT" else default,
        ):
            handler = get_output_handler()

        assert handler.format == OutputFormat.JSON

    def test_output_handler_unknown_format_defaults_to_text(self) -> None:
        """Test that unknown format defaults to TEXT."""
        with patch(
            "provide.foundation.utils.environment.get_str",
            side_effect=lambda k, default=None: "xml" if k == "FLAVOR_OUTPUT_FORMAT" else default,
        ):
            handler = get_output_handler()

        assert handler.format == OutputFormat.TEXT

    def test_output_handler_with_file_from_env(self) -> None:
        """Test get_output_handler with file path from environment."""
        with patch(
            "provide.foundation.utils.environment.get_str",
            side_effect=lambda k, default=None: "/tmp/output.log" if k == "FLAVOR_OUTPUT_FILE" else "text",
        ):
            handler = get_output_handler()

        assert handler._output_file == "/tmp/output.log"

    def test_output_handler_custom_env_var_names(self) -> None:
        """Test get_output_handler with custom environment variable names."""

        def mock_get_env(key: str, default: str | None = None) -> str | None:
            if key == "CUSTOM_FORMAT":
                return "json"
            elif key == "CUSTOM_FILE":
                return "/custom/path.log"
            return default

        with patch("provide.foundation.utils.environment.get_str", side_effect=mock_get_env):
            handler = get_output_handler(format_env="CUSTOM_FORMAT", file_env="CUSTOM_FILE")

        assert handler.format == OutputFormat.JSON
        assert handler._output_file == "/custom/path.log"

    def test_output_handler_default_env_var_names(self) -> None:
        """Test that default environment variable names are used."""

        def mock_get_env(key: str, default: str | None = None) -> str | None:
            if key == "FLAVOR_OUTPUT_FORMAT":
                return "json"
            elif key == "FLAVOR_OUTPUT_FILE":
                return "/default/path.log"
            return default

        with patch("provide.foundation.utils.environment.get_str", side_effect=mock_get_env):
            handler = get_output_handler()

        assert handler.format == OutputFormat.JSON
        assert handler._output_file == "/default/path.log"

    def test_output_handler_no_file_env(self) -> None:
        """Test get_output_handler when file environment variable is not set."""
        with patch(
            "provide.foundation.utils.environment.get_str",
            side_effect=lambda k, default=None: "text" if k == "FLAVOR_OUTPUT_FORMAT" else None,
        ):
            handler = get_output_handler()

        assert handler._output_file is None


# 🌶️📦🔚
