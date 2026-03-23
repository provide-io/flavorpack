#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF 2025 execution tests covering real command substitution paths."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from flavor.psp.format_2025 import PSPFBuilder, PSPFLauncher, PSPFReader
from flavor.psp.format_2025.executor import BundleExecutor


class TestPSPFExecution:
    """Test PSPF bundle execution."""

    @pytest.fixture
    def temp_dir(self) -> Iterator[Path]:
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        import shutil

        shutil.rmtree(temp_path)

    @pytest.fixture
    def executable_bundle(self, temp_dir: Path) -> Path:
        """Create an executable bundle."""
        script_path = temp_dir / "app.py"
        script_path.write_text(
            """
import sys
print(f"Hello from PSPF! Args: {sys.argv[1:]}")
""".strip()
            + "\n"
        )

        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "hello-app", "version": "1.0.0"},
            "execution": {
                "primary_slot": 0,
                "command": "/usr/bin/python3 {slot:0}",
            },
        }

        bundle_path = temp_dir / "app.psp"
        builder = PSPFBuilder().metadata(**metadata)
        builder = builder.add_slot(
            id="main-app",
            data=script_path,
            purpose="payload",
            lifecycle="runtime",
            operations="none",
            target="app.py",
        )
        builder.build(bundle_path)

        return bundle_path

    def test_slot_substitution_uses_extracted_target(self, executable_bundle: Path) -> None:
        """Test slot references resolve to the extracted target path."""
        launcher = PSPFLauncher(executable_bundle)
        workenv_dir = launcher.setup_workenv()
        metadata = launcher.read_metadata()

        executor = BundleExecutor(metadata, workenv_dir)
        prepared = executor.prepare_command("/usr/bin/python3 {slot:0}")

        assert "{slot:0}" not in prepared
        assert str(workenv_dir / "app.py") in prepared

    def test_slot_reference_substitution_helper_matches_extraction(self, executable_bundle: Path) -> None:
        """Test launcher helper substitution resolves against slot targets."""
        launcher = PSPFLauncher(executable_bundle)
        workenv_dir = launcher.setup_workenv()

        substituted = launcher._substitute_slot_references("python {slot:0}", workenv_dir)

        assert substituted == f"python {workenv_dir / 'app.py'}"

    def test_prepare_environment_sets_flavor_workenv(self, executable_bundle: Path) -> None:
        """Test execution environment includes the extracted workenv."""
        launcher = PSPFLauncher(executable_bundle)
        workenv_dir = launcher.setup_workenv()
        metadata = launcher.read_metadata()

        executor = BundleExecutor(metadata, workenv_dir)
        env = executor.prepare_environment()

        assert env["FLAVOR_WORKENV"] == str(workenv_dir)
        assert env["FLAVOR_PACKAGE"] == "hello-app"
        assert env["FLAVOR_VERSION"] == "1.0.0"

    def test_working_directory_setup(self, temp_dir: Path, executable_bundle: Path) -> None:
        """Test working directory is set correctly."""
        launcher = PSPFLauncher(executable_bundle)

        workenv_dir = temp_dir / "workenv"
        workenv_dir.mkdir(exist_ok=True)
        extracted = launcher.extract_all_slots(workenv_dir)

        assert extracted[0].exists()

        result = launcher.execute()
        assert result["working_directory"] is not None

    def test_resource_limits(self, temp_dir: Path) -> None:
        """Test handling of execution metadata."""
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "limited-app", "version": "1.0.0"},
            "execution": {
                "primary_slot": 0,
                "command": "/usr/bin/python3 {workenv}/app.py",
                "limits": {"memory": "1GB", "cpu": "2", "timeout": "300s"},
            },
        }

        bundle_path = temp_dir / "limited.psp"
        dummy_file = temp_dir / "dummy.txt"
        dummy_file.write_text("dummy")

        builder = PSPFBuilder().metadata(**metadata)
        builder = builder.add_slot(id="dummy", data=dummy_file, operations="none")
        builder.build(bundle_path)

        reader = PSPFReader(bundle_path)
        read_metadata = reader.read_metadata()

        limits = read_metadata["execution"]["limits"]
        assert limits["memory"] == "1GB"
        assert limits["cpu"] == "2"
        assert limits["timeout"] == "300s"

    def test_execution_error_handling(self, temp_dir: Path) -> None:
        """Test handling of execution errors."""
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "error-app", "version": "1.0.0"},
            "execution": {"primary_slot": 0, "command": "/nonexistent/binary"},
        }

        bundle_path = temp_dir / "error.psp"
        builder = PSPFBuilder().metadata(**metadata)
        builder.build(bundle_path)

        launcher = PSPFLauncher(bundle_path)
        result = launcher.execute()

        assert result is not None
        assert not result["executed"] or result["exit_code"] != 0


@pytest.mark.unit
class TestBundleExecutorUnit:
    """Unit tests for BundleExecutor covering uncovered branches."""

    def _make_executor(
        self,
        command: str = "/usr/bin/python3",
        slots: list | None = None,
        execution_env: dict | None = None,
        primary_slot: int = 0,
    ) -> BundleExecutor:
        metadata: dict = {
            "package": {"name": "test-pkg", "version": "1.2.3"},
            "execution": {
                "primary_slot": primary_slot,
                "command": command,
            },
        }
        if slots is not None:
            metadata["slots"] = slots
        if execution_env is not None:
            metadata["execution"]["env"] = execution_env
        return BundleExecutor(metadata, Path("/workenv"))

    def test_prepare_command_no_args(self) -> None:
        """prepare_command with no args returns command with substitutions only."""
        executor = self._make_executor(command="/usr/bin/python3")
        result = executor.prepare_command("/usr/bin/python3")
        assert result == "/usr/bin/python3"

    def test_prepare_command_args_with_space_get_quoted(self) -> None:
        """Args containing spaces are wrapped in double quotes."""
        executor = self._make_executor()
        result = executor.prepare_command("/bin/run", args=["arg with space", "normal"])
        assert '"arg with space"' in result
        assert "normal" in result
        assert '"normal"' not in result

    def test_prepare_command_workenv_substitution(self) -> None:
        """prepare_command replaces {workenv} with workenv_dir path."""
        executor = self._make_executor(command="{workenv}/bin/app")
        result = executor.prepare_command("{workenv}/bin/app")
        assert "{workenv}" not in result
        assert "/workenv" in result

    def test_prepare_command_package_name_version(self) -> None:
        """{package_name} and {version} are substituted."""
        executor = self._make_executor(command="echo {package_name} {version}")
        result = executor.prepare_command("echo {package_name} {version}")
        assert "test-pkg" in result
        assert "1.2.3" in result

    def test_substitute_primary_no_placeholder(self) -> None:
        """_substitute_primary returns command unchanged when no {primary}."""
        executor = self._make_executor()
        result = executor._substitute_primary("/bin/app")
        assert result == "/bin/app"

    def test_substitute_primary_slot_out_of_range(self) -> None:
        """_substitute_primary logs warning when primary_slot index out of range."""
        executor = self._make_executor(command="{primary}", slots=[], primary_slot=5)
        result = executor._substitute_primary("{primary}")
        # {primary} not substituted (slot list is empty)
        assert "{primary}" in result

    def test_substitute_slots_out_of_range(self) -> None:
        """_substitute_slots keeps placeholder when slot index is out of range."""
        executor = self._make_executor(slots=[])
        result = executor._substitute_slots("{slot:0}")
        assert "{slot:0}" in result

    def test_substitute_slots_in_range(self) -> None:
        """_substitute_slots replaces {slot:N} with workenv path."""
        executor = self._make_executor(slots=[{"target": "app.py", "id": "main", "name": "main"}])
        result = executor._substitute_slots("{slot:0}")
        assert "{slot:0}" not in result
        assert "app.py" in result

    def test_normalize_slot_target_workenv_placeholder(self) -> None:
        """{workenv} target is returned as-is."""
        executor = self._make_executor()
        assert executor._normalize_slot_target("{workenv}") == "{workenv}"

    def test_normalize_slot_target_strips_workenv_prefix(self) -> None:
        """{workenv}/path becomes path."""
        executor = self._make_executor()
        assert executor._normalize_slot_target("{workenv}/lib/foo.so") == "lib/foo.so"

    def test_normalize_slot_target_bare_path(self) -> None:
        """Bare path is returned unchanged."""
        executor = self._make_executor()
        assert executor._normalize_slot_target("app.py") == "app.py"

    def test_prepare_environment_execution_env_substitution(self) -> None:
        """Execution env values with {workenv} are substituted."""
        executor = self._make_executor(execution_env={"MY_DIR": "{workenv}/cache"})
        env = executor.prepare_environment()
        assert env["MY_DIR"] == "/workenv/cache"

    def test_execute_raises_when_no_command(self) -> None:
        """execute raises ValueError when no command in execution config."""
        metadata = {
            "package": {"name": "pkg", "version": "1.0"},
            "execution": {},
        }
        executor = BundleExecutor(metadata, Path("/workenv"))
        with pytest.raises(ValueError, match="No command specified"):
            executor.execute()

    def test_execute_exception_returns_error_dict(self) -> None:
        """execute catches exceptions and returns error dict."""
        executor = self._make_executor(command="/nonexistent/binary/xyz")
        with patch("flavor.psp.format_2025.executor.run", side_effect=OSError("not found")):
            result = executor.execute()
        assert result["executed"] is False
        assert result["error"] is not None
        assert "not found" in result["error"]

    def test_execute_nonzero_exit_is_not_crash(self) -> None:
        """exit_code > 0 is not flagged as crash."""
        executor = self._make_executor(command="/bin/false")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch("flavor.psp.format_2025.executor.run", return_value=mock_result):
            result = executor.execute()
        assert result["exit_code"] == 1
        assert result["crashed"] is False

    def test_execute_negative_exit_is_crash(self) -> None:
        """Negative exit_code (signal) is flagged as crash."""
        executor = self._make_executor(command="/bin/app")
        mock_result = MagicMock()
        mock_result.returncode = -11  # SIGSEGV
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch("flavor.psp.format_2025.executor.run", return_value=mock_result):
            result = executor.execute()
        assert result["crashed"] is True

    def test_execute_stderr_logged_on_nonzero_exit(self) -> None:
        """Nonzero exit with stderr content is logged (line 235 coverage)."""
        executor = self._make_executor(command="/bin/app")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "some error output"
        with patch("flavor.psp.format_2025.executor.run", return_value=mock_result):
            result = executor.execute()
        assert result["exit_code"] == 1

    def test_substitute_primary_with_slot_target(self) -> None:
        """{primary} is replaced when slots exist and primary_slot is in range."""
        executor = self._make_executor(
            command="{primary}",
            slots=[{"target": "main.py", "id": "main", "name": "main"}],
            primary_slot=0,
        )
        result = executor._substitute_primary("{primary}")
        assert "{primary}" not in result
        assert "main.py" in result

    def test_substitute_primary_tarball_uses_workenv(self) -> None:
        """{primary} for a .tar.gz target uses {workenv} as primary path."""
        executor = self._make_executor(
            command="{primary}",
            slots=[{"target": "bundle.tar.gz", "id": "bundle", "name": "bundle"}],
            primary_slot=0,
        )
        result = executor._substitute_primary("{primary}")
        assert "{workenv}" in result or "workenv" in result.lower()


# 🌶️📦🔚
