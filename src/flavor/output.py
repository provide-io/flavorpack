#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Output formatting and redirection for Flavor tools."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import sys
from typing import Any, TextIO

from provide.foundation.serialization import json_dumps


class OutputFormat(Enum):
    """Supported output formats."""

    TEXT = "text"
    JSON = "json"


class OutputHandler:
    """Handles output formatting and redirection."""

    def __init__(
        self,
        format: OutputFormat = OutputFormat.TEXT,
        file: str | None = None,
    ) -> None:
        """
        Initialize output handler.

        Args:
            format: Output format (text or json)
            file: Output file path, or "STDOUT", "STDERR" (default: STDOUT)
        """
        self.format = format
        self._output_file = file
        self._file_handle: TextIO | None = None
        self._output_buffer: list[dict[str, Any]] = []

    def __enter__(self) -> OutputHandler:
        """Context manager entry."""
        if self._output_file and self._output_file not in ("STDOUT", "STDERR"):
            self._file_handle = Path(self._output_file).open("w")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - flush any buffered output."""
        if self.format == OutputFormat.JSON:
            self._flush_json()
        if self._file_handle:
            self._file_handle.close()

    def _get_output_stream(self) -> TextIO:
        """Get the output stream to write to."""
        if self._file_handle:
            return self._file_handle
        elif self._output_file == "STDERR":
            return sys.stderr
        else:  # Default to STDOUT
            return sys.stdout

    def _flush_json(self) -> None:
        """Flush buffered JSON output."""
        if self._output_buffer:
            stream = self._get_output_stream()
            stream.write(json_dumps(self._output_buffer, indent=2))
            stream.write("\n")
            stream.flush()
            self._output_buffer.clear()

    def write(self, data: Any, **kwargs: Any) -> None:
        """
        Write output in the configured format.

        Args:
            data: Data to output (string for text, dict/list for JSON)
            **kwargs: Additional metadata for JSON output
        """
        if self.format == OutputFormat.JSON:
            # Buffer JSON output to write as single document
            if isinstance(data, str):
                entry = {"message": data}
            elif isinstance(data, dict):
                entry = data
            else:
                entry = {"data": data}

            if kwargs:
                entry.update(kwargs)

            self._output_buffer.append(entry)
        else:
            # Text output - write immediately
            stream = self._get_output_stream()
            if isinstance(data, dict):
                # Format dict as key=value pairs for text output
                for key, value in data.items():
                    stream.write(f"{key}: {value}\n")
            else:
                stream.write(str(data))
                if not str(data).endswith("\n"):
                    stream.write("\n")
            stream.flush()

    def error(self, message: str, **kwargs: Any) -> None:
        """Write an error message."""
        if self.format == OutputFormat.JSON:
            self.write({"error": message, **kwargs})
        else:
            # Errors always go to stderr in text mode
            sys.stderr.write(f"Error: {message}\n")
            sys.stderr.flush()

    def success(self, message: str, **kwargs: Any) -> None:
        """Write a success message."""
        if self.format == OutputFormat.JSON:
            self.write({"success": message, **kwargs})
        else:
            pass

    def info(self, message: str, **kwargs: Any) -> None:
        """Write an info message."""
        if self.format == OutputFormat.JSON:
            self.write({"info": message, **kwargs})
        else:
            self.write(message)


def get_output_handler(
    format_env: str | None = None,
    file_env: str | None = None,
) -> OutputHandler:
    """
    Create output handler from environment or defaults.

    Args:
        format_env: Environment variable name for format (default: FLAVOR_OUTPUT_FORMAT)
        file_env: Environment variable name for file (default: FLAVOR_OUTPUT_FILE)

    Returns:
        Configured OutputHandler
    """
    from provide.foundation.utils.environment import get_str

    format_env = format_env or "FLAVOR_OUTPUT_FORMAT"
    file_env = file_env or "FLAVOR_OUTPUT_FILE"

    format_str = get_str(format_env, default="text").lower()
    output_format = OutputFormat.JSON if format_str == "json" else OutputFormat.TEXT

    output_file = get_str(file_env)

    return OutputHandler(format=output_format, file=output_file)


# 🌶️📦🔚
