#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the verify command with JSON output support."""

import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import click.testing
from taster.commands.verify import verify_command


class TestVerifyCommand:
    """Test the verify command with JSON output."""

    def test_verify_basic(self) -> None:
        """Test basic verification without JSON."""
        runner = click.testing.CliRunner()

        with (
            tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile,
            patch("flavor.verification.FlavorVerifier") as mock_verifier,
        ):
            mock_verifier.verify_package.return_value = {
                "format": "PSPF2025",
                "version": "1.0.0",
                "launcher_size": 1024000,
                "signature_valid": True,
                "index_checksum_valid": True,
                "metadata": {"name": "test"},
                "package": {"name": "test-pkg", "version": "1.0.0"},
                "slots": [{}],
            }

            result = runner.invoke(verify_command, [tmpfile.name])
            assert result.exit_code == 0
            assert "PSPF PACKAGE VERIFICATION" in result.output

    def test_verify_json_output(self) -> None:
        """Test verification with JSON output."""
        runner = click.testing.CliRunner()

        with (
            tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile,
            patch("flavor.verification.FlavorVerifier") as mock_verifier,
        ):
            verification_result = {
                "format": "PSPF2025",
                "version": "1.0.0",
                "launcher_size": 1024000,
                "signature_valid": True,
            }
            mock_verifier.verify_package.return_value = verification_result

            result = runner.invoke(verify_command, [tmpfile.name, "--json"])
            assert result.exit_code == 0

            output_data = json.loads(result.output)
            assert output_data["package"] == tmpfile.name
            assert output_data["exists"] is True
            assert output_data["verification"] == verification_result

    def test_verify_json_output_to_file(self) -> None:
        """Test verification with JSON output to file."""
        runner = click.testing.CliRunner()

        with tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as output_file:
                output_path = output_file.name

            try:
                verification_result = {"format": "PSPF2025", "signature_valid": True}

                with patch("flavor.verification.FlavorVerifier") as mock_verifier:
                    mock_verifier.verify_package.return_value = verification_result

                    result = runner.invoke(
                        verify_command,
                        [tmpfile.name, "--json", "--output-file", output_path],
                    )
                    assert result.exit_code == 0

                    # Check file contents
                    with Path(output_path).open(encoding="utf-8") as f:
                        output_data = json.load(f)
                    assert output_data["verification"] == verification_result
            finally:
                Path(output_path).unlink(missing_ok=True)

    def test_verify_package_not_found(self) -> None:
        """Test verification when package doesn't exist."""
        runner = click.testing.CliRunner()

        result = runner.invoke(verify_command, ["/nonexistent/package.psp"])
        assert result.exit_code == 0
        assert "Package file not found" in result.output

    def test_verify_package_not_found_json(self) -> None:
        """Test verification when package doesn't exist with JSON output."""
        runner = click.testing.CliRunner()

        result = runner.invoke(verify_command, ["/nonexistent/package.psp", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["exists"] is False
        assert "error" in output_data
        assert "not found" in output_data["error"]

    def test_verify_with_error(self) -> None:
        """Test verification when an error occurs."""
        runner = click.testing.CliRunner()

        with (
            tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile,
            patch("flavor.verification.FlavorVerifier") as mock_verifier,
        ):
            mock_verifier.verify_package.side_effect = Exception("Verification error")

            result = runner.invoke(verify_command, [tmpfile.name])
            assert result.exit_code == 0
            assert "Verification failed" in result.output

    def test_verify_with_error_json(self) -> None:
        """Test verification error with JSON output."""
        runner = click.testing.CliRunner()

        with (
            tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile,
            patch("flavor.verification.FlavorVerifier") as mock_verifier,
        ):
            mock_verifier.verify_package.side_effect = Exception("Verification error")

            result = runner.invoke(verify_command, [tmpfile.name, "--json"])
            assert result.exit_code == 0

            output_data = json.loads(result.output)
            assert "error" in output_data
            assert "Verification error" in output_data["error"]

    def test_verify_fallback_basic_checks(self) -> None:
        """Test fallback to basic checks when flavor module not available."""
        runner = click.testing.CliRunner()

        with tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile:
            # Write some test data with PSPF magic
            tmpfile.write(b"LAUNCHER_DATA" + b"PSPF2025" + b"PACKAGE_DATA")
            tmpfile.flush()

            # Mock the imports to raise ImportError
            with patch.dict("sys.modules", {"flavor.verification": None}):
                result = runner.invoke(verify_command, [tmpfile.name])
                assert result.exit_code == 0
                assert "Flavor verification module not available" in result.output
                assert "Basic Information" in result.output
                assert "PSPF2025 magic found" in result.output

    def test_verify_fallback_basic_checks_json(self) -> None:
        """Test fallback to basic checks with JSON output."""
        runner = click.testing.CliRunner()

        with tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile:
            # Write some test data with PSPF magic
            tmpfile.write(b"LAUNCHER_DATA" + b"PSPF2025" + b"PACKAGE_DATA")
            tmpfile.flush()

            # Mock the imports to raise ImportError
            with patch.dict("sys.modules", {"flavor.verification": None}):
                result = runner.invoke(verify_command, [tmpfile.name, "--json"])
                assert result.exit_code == 0

                output_data = json.loads(result.output)
                assert "basic_info" in output_data
                assert output_data["basic_info"]["magic_found"] is True
                assert "warning" in output_data
                assert "not available" in output_data["warning"]

    def test_verify_uses_current_executable(self) -> None:
        """Test that verify uses current executable when no path provided."""
        runner = click.testing.CliRunner()

        with (
            tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile,
            patch("sys.argv", [tmpfile.name]),
            patch("flavor.verification.FlavorVerifier") as mock_verifier,
        ):
            mock_verifier.verify_package.return_value = {
                "format": "PSPF2025",
                "signature_valid": True,
            }

            result = runner.invoke(verify_command, [])
            assert result.exit_code == 0
            mock_verifier.verify_package.assert_called_once()

    def test_verify_signature_failed(self) -> None:
        """Test output when signature verification fails."""
        runner = click.testing.CliRunner()

        with (
            tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile,
            patch("flavor.verification.FlavorVerifier") as mock_verifier,
        ):
            mock_verifier.verify_package.return_value = {
                "format": "PSPF2025",
                "signature_valid": False,
                "index_checksum_valid": False,
            }

            result = runner.invoke(verify_command, [tmpfile.name])
            assert result.exit_code == 0
            assert "❌ Signature verification: FAILED" in result.output
            assert "❌ Index checksum invalid" in result.output


# 🌶️📦🔚
