#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the crosslang command."""

import json
from pathlib import Path
import tempfile
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import click.testing
import pytest
from taster.commands.crosslang import CrossLangTester, crosslang_command


class TestCrossLangTester:
    """Test the CrossLangTester class."""

    def test_init(self) -> None:
        """Test initialization."""
        tester = CrossLangTester(verbose=True, json_output=True)
        assert tester.verbose is True
        assert tester.json_output is True
        assert "build_tests" in tester.results
        assert "verify_tests" in tester.results
        assert "cli_tests" in tester.results

    def test_log_json_mode(self) -> None:
        """Test that logging is suppressed in JSON mode."""
        tester = CrossLangTester(json_output=True)
        # Should not raise any exceptions
        tester.log("Test message")
        tester.log("Error", level="error")
        tester.log("Success", level="success")

    def test_log_normal_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test logging in normal mode."""
        tester = CrossLangTester(json_output=False)
        tester.log("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    @patch("taster.commands.crosslang.run_command")
    def test_build_with_python(self, mock_run_command: MagicMock) -> None:
        """Test Python builder."""
        mock_run_command.return_value = Mock(returncode=0, stderr="", stdout="Built successfully")

        with tempfile.TemporaryDirectory() as tmpdir:
            taster_dir = Path(tmpdir) / "tests/taster"
            taster_dir.mkdir(parents=True)
            (taster_dir / "pyproject.toml").touch()

            tester = CrossLangTester()
            tester.taster_dir = taster_dir

            # Create fake output file with correct name
            output_file = taster_dir / "test-go.psp"
            output_file.touch()

            # Method renamed to build_with_launcher
            from unittest.mock import MagicMock

            launcher_info = MagicMock()
            launcher_info.language = "go"
            launcher_info.path = Path("/fake/go/launcher")
            launcher_info.name = "flavor-go-launcher"
            result = tester.build_with_launcher(launcher_info)
            assert result == output_file
            assert len(tester.results["build_tests"]) == 1
            assert tester.results["build_tests"][0]["success"] is True

    def test_verify_with_python(self) -> None:
        """Test Python verification."""
        with tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile:
            package_path = Path(tmpfile.name)

            # Mock the PSPFReader
            with patch("flavor.psp.format_2025.PSPFReader") as mock_reader:
                mock_instance = MagicMock()
                mock_instance.__enter__.return_value = mock_instance
                mock_instance.__exit__.return_value = None
                mock_instance.verify_integrity.return_value = {
                    "valid": True,
                    "details": "OK",
                }
                mock_reader.return_value = mock_instance

                tester = CrossLangTester()
                result = tester.verify_with_python(package_path)

                assert result is True
                assert len(tester.results["verify_tests"]) == 1
                assert tester.results["verify_tests"][0]["success"] is True

    @patch("subprocess.run")
    def test_verify_with_launcher_cli(self, mock_run: MagicMock) -> None:
        """Test launcher CLI verification."""
        mock_run.return_value = Mock(returncode=0, stderr="", stdout="Verified")

        with tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile:
            package_path = Path(tmpfile.name)

            tester = CrossLangTester()
            result = tester.verify_with_launcher_cli(package_path, "go")

            assert result is True
            assert len(tester.results["verify_tests"]) == 1
            assert tester.results["verify_tests"][0]["verifier"] == "go_cli"

    @patch("subprocess.run")
    def test_test_cli_command(self, mock_run: MagicMock) -> None:
        """Test CLI command testing."""
        mock_run.return_value = Mock(returncode=0, stderr="", stdout="Help text")

        with tempfile.NamedTemporaryFile(suffix=".psp") as tmpfile:
            package_path = Path(tmpfile.name)

            tester = CrossLangTester()
            result = tester.test_cli_command(package_path, "--help")

            assert result is True
            assert len(tester.results["cli_tests"]) == 1
            assert tester.results["cli_tests"][0]["command"] == "--help"

    def test_test_reproducible_build(self) -> None:
        """Test reproducible build testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            taster_dir = Path(tmpdir)

            # Track created files to prevent deletion issues
            created_files = []

            # Create mock launcher info
            from unittest.mock import MagicMock

            launcher_info = MagicMock()
            launcher_info.name = "test-launcher"
            launcher_info.language = "test"
            launcher_info.path = Path("/fake/launcher")

            def mock_builder(launcher_info: Any, key_seed: str | None) -> Path:
                """Mock builder that creates a file."""
                output = taster_dir / f"test-{key_seed}-{len(created_files)}.psp"
                output.write_bytes(b"FAKE_LAUNCHER" + b"PSPF2025" + b"DATA")
                created_files.append(output)
                return output

            # Mock PSPFReader to return launcher size
            with patch("flavor.psp.format_2025.PSPFReader") as mock_reader:
                mock_instance = MagicMock()
                mock_instance.__enter__.return_value = mock_instance
                mock_instance.__exit__.return_value = None
                mock_instance.read_index.return_value = Mock(launcher_size=13)  # len(b"FAKE_LAUNCHER")
                mock_reader.return_value = mock_instance

                # Patch build_with_launcher to use our mock
                tester = CrossLangTester()
                with patch.object(
                    tester,
                    "build_with_launcher",
                    side_effect=lambda li, key_seed=None: mock_builder(li, key_seed),
                ):
                    result = tester.test_reproducible_build(launcher_info)

                    assert result is True
                    assert len(tester.results["reproducible_tests"]) == 1
                    assert tester.results["reproducible_tests"][0]["success"] is True

    @patch("subprocess.run")
    @patch("os.chdir")
    def test_run_all_tests_json_output(self, mock_chdir: MagicMock, mock_run: MagicMock) -> None:
        """Test running all tests with JSON output."""
        mock_run.return_value = Mock(returncode=0, stderr="", stdout="OK")

        with tempfile.TemporaryDirectory() as tmpdir:
            taster_dir = Path(tmpdir) / "tests/taster"
            taster_dir.mkdir(parents=True)
            (taster_dir / "pyproject.toml").touch()
            (taster_dir / "manifest.json").touch()

            tester = CrossLangTester(json_output=True)
            tester.taster_dir = taster_dir
            tester.python_builder = Path("/fake/python/builder")
            tester.go_builder = Path("/fake/go/builder")
            tester.rust_builder = Path("/fake/rust/builder")

            # Mock the build methods to return None (simulating failure)
            tester.build_with_python = Mock(return_value=None)
            tester.build_with_go = Mock(return_value=None)
            tester.build_with_rust = Mock(return_value=None)

            exit_code = tester.run_all_tests()

            # Should fail since no builds succeeded
            assert exit_code == 1
            assert tester.results["summary"]["overall_success"] is False


class TestCrossLangCommand:
    """Test the crosslang CLI command."""

    def test_command_basic(self) -> None:
        """Test basic command invocation."""
        runner = click.testing.CliRunner()

        with patch("taster.commands.crosslang.CrossLangTester") as mock_tester_class:
            mock_tester = Mock()
            mock_tester.run_all_tests.return_value = 0
            mock_tester.results = {"summary": {"overall_success": True}}
            mock_tester_class.return_value = mock_tester

            result = runner.invoke(crosslang_command, [])
            assert result.exit_code == 0
            mock_tester.run_all_tests.assert_called_once()

    def test_command_verbose(self) -> None:
        """Test verbose flag."""
        runner = click.testing.CliRunner()

        with patch("taster.commands.crosslang.CrossLangTester") as mock_tester_class:
            mock_tester = Mock()
            mock_tester.run_all_tests.return_value = 0
            mock_tester.results = {"summary": {"overall_success": True}}
            mock_tester_class.return_value = mock_tester

            result = runner.invoke(crosslang_command, ["--verbose"])
            assert result.exit_code == 0
            mock_tester_class.assert_called_with(verbose=True, json_output=False)

    def test_command_json_output(self) -> None:
        """Test JSON output flag."""
        runner = click.testing.CliRunner()

        with patch("taster.commands.crosslang.CrossLangTester") as mock_tester_class:
            mock_tester = Mock()
            mock_tester.run_all_tests.return_value = 0
            mock_tester.results = {"summary": {"overall_success": True}}
            mock_tester_class.return_value = mock_tester

            result = runner.invoke(crosslang_command, ["--json"])
            assert result.exit_code == 0
            mock_tester_class.assert_called_with(verbose=False, json_output=True)

    def test_command_output_file(self) -> None:
        """Test output to file."""
        runner = click.testing.CliRunner()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmpfile:
            output_file = tmpfile.name

        try:
            with patch("taster.commands.crosslang.CrossLangTester") as mock_tester_class:
                test_results = {
                    "build_tests": [],
                    "verify_tests": [],
                    "summary": {"overall_success": True},
                }

                mock_tester = Mock()
                mock_tester.run_all_tests.return_value = 0
                mock_tester.results = test_results
                mock_tester_class.return_value = mock_tester

                result = runner.invoke(crosslang_command, ["--json", "--output-file", output_file])
                assert result.exit_code == 0

                # Check file was written
                with Path(output_file).open(encoding="utf-8") as f:
                    written_data = json.load(f)
                assert written_data == test_results
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_command_failure(self) -> None:
        """Test command with test failures."""
        runner = click.testing.CliRunner()

        with patch("taster.commands.crosslang.CrossLangTester") as mock_tester_class:
            mock_tester = Mock()
            mock_tester.run_all_tests.return_value = 1  # Failure
            mock_tester.results = {"summary": {"overall_success": False}}
            mock_tester_class.return_value = mock_tester

            result = runner.invoke(crosslang_command, [])
            assert result.exit_code == 1


# 🌶️📦🔚
