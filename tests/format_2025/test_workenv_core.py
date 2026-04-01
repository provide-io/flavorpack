#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for psp/format_2025/workenv.py - Core functionality."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from flavor.psp.format_2025.workenv import WorkEnvManager


class TestWorkEnvManagerInit:
    """Test WorkEnvManager initialization."""

    def test_init(self) -> None:
        """Test basic initialization."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        assert manager.reader is mock_reader


class TestSetupWorkenv:
    """Test setup_workenv method."""

    @staticmethod
    def _write_bundle(tmp_path: Path, name: str = "bundle.psp") -> Path:
        bundle_path = tmp_path / name
        bundle_path.write_bytes(b"pspf-test-bundle")
        return bundle_path

    @patch("flavor.psp.format_2025.workenv.ensure_dir")
    def test_setup_workenv_with_valid_cache(self, mock_ensure_dir: Mock, tmp_path: Path) -> None:
        """Test setup with valid cache (no extraction)."""
        mock_reader = Mock()
        metadata = {
            "package": {"name": "testpkg", "version": "1.0.0"},
            "cache_validation": {
                "check_file": "{workenv}/.version",
                "expected_content": "{version}",
            },
        }
        mock_reader.read_metadata.return_value = metadata

        manager = WorkEnvManager(mock_reader)
        bundle_path = self._write_bundle(tmp_path)
        cache_root = tmp_path / "cache"
        cache_dir = cache_root / f"testpkg_1.0.0_{manager._bundle_identity(bundle_path)}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / ".version").write_text("1.0.0")

        with patch("flavor.cache.get_cache_dir", return_value=cache_root):
            result = manager.setup_workenv(bundle_path)

        # Should use cached environment
        assert result == cache_dir
        mock_ensure_dir.assert_called_once()

    @patch("flavor.psp.format_2025.workenv.ensure_dir")
    def test_setup_workenv_with_invalid_cache(self, mock_ensure_dir: Mock, tmp_path: Path) -> None:
        """Test setup with invalid cache (forces extraction)."""
        mock_reader = Mock()
        mock_index = Mock()
        mock_index.slot_count = 2
        mock_reader._index = mock_index

        metadata = {
            "package": {"name": "testpkg2", "version": "2.0.0"},  # Different name/version
            "cache_validation": {
                "check_file": "{workenv}/.version",
                "expected_content": "{version}",
            },
            "slots": [{"id": "runtime"}, {"id": "app"}],
        }
        mock_reader.read_metadata.return_value = metadata

        # Mock extraction
        slot1_path = tmp_path / "runtime"
        slot2_path = tmp_path / "app"
        mock_reader.extract_slot.side_effect = [slot1_path, slot2_path]

        manager = WorkEnvManager(mock_reader)
        bundle_path = self._write_bundle(tmp_path)

        # Cache file doesn't exist, so extraction happens
        with patch("flavor.cache.get_cache_dir", return_value=tmp_path / "cache"):
            manager.setup_workenv(bundle_path)

        # Should extract both slots
        assert mock_reader.extract_slot.call_count == 2

    @patch("flavor.psp.format_2025.workenv.ensure_dir")
    def test_setup_workenv_with_setup_commands(self, mock_ensure_dir: Mock, tmp_path: Path) -> None:
        """Test setup with setup commands."""
        mock_reader = Mock()
        mock_index = Mock()
        mock_index.slot_count = 1
        mock_reader._index = mock_index

        metadata = {
            "package": {"name": "testpkg", "version": "1.0.0"},
            "slots": [{"id": "runtime"}],
            "setup_commands": [{"type": "write_file", "path": "{workenv}/.initialized", "content": "done"}],
        }
        mock_reader.read_metadata.return_value = metadata

        slot1_path = tmp_path / "runtime"
        mock_reader.extract_slot.return_value = slot1_path

        manager = WorkEnvManager(mock_reader)
        bundle_path = self._write_bundle(tmp_path)

        with patch.object(manager, "_run_setup_commands") as mock_run_setup:
            with patch("flavor.cache.get_cache_dir", return_value=tmp_path / "cache"):
                manager.setup_workenv(bundle_path)

            # Should run setup commands
            mock_run_setup.assert_called_once()

    @patch("flavor.psp.format_2025.workenv.ensure_dir")
    def test_setup_workenv_with_lifecycle_cleanup(self, mock_ensure_dir: Mock, tmp_path: Path) -> None:
        """Test setup with lifecycle-based cleanup."""
        mock_reader = Mock()
        mock_index = Mock()
        mock_index.slot_count = 2
        mock_reader._index = mock_index

        metadata = {
            "package": {"name": "testpkg", "version": "1.0.0"},
            "slots": [{"id": "init", "lifecycle": "init"}, {"id": "runtime", "lifecycle": "runtime"}],
        }
        mock_reader.read_metadata.return_value = metadata

        slot1_path = tmp_path / "init"
        slot2_path = tmp_path / "runtime"
        mock_reader.extract_slot.side_effect = [slot1_path, slot2_path]

        manager = WorkEnvManager(mock_reader)
        bundle_path = self._write_bundle(tmp_path)

        with patch.object(manager, "_cleanup_lifecycle_slots") as mock_cleanup:
            with patch("flavor.cache.get_cache_dir", return_value=tmp_path / "cache"):
                manager.setup_workenv(bundle_path)

            # Should cleanup lifecycle slots
            mock_cleanup.assert_called_once()


class TestCheckCacheValidity:
    """Test _check_cache_validity method."""

    def test_check_cache_validity_valid(self, tmp_path: Path) -> None:
        """Test cache validity check with valid cache."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()
        version_file = workenv_dir / ".version"
        version_file.write_text("1.0.0")

        metadata = {
            "cache_validation": {
                "check_file": "{workenv}/.version",
                "expected_content": "{version}",
            }
        }

        result = manager._check_cache_validity(metadata, workenv_dir, "1.0.0")

        assert result is True

    def test_check_cache_validity_mismatch(self, tmp_path: Path) -> None:
        """Test cache validity check with content mismatch."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()
        version_file = workenv_dir / ".version"
        version_file.write_text("2.0.0")  # Wrong version

        metadata = {
            "cache_validation": {
                "check_file": "{workenv}/.version",
                "expected_content": "{version}",
            }
        }

        result = manager._check_cache_validity(metadata, workenv_dir, "1.0.0")

        assert result is False

    def test_check_cache_validity_file_not_found(self, tmp_path: Path) -> None:
        """Test cache validity check when file doesn't exist."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        metadata = {
            "cache_validation": {
                "check_file": "{workenv}/.version",
                "expected_content": "{version}",
            }
        }

        result = manager._check_cache_validity(metadata, workenv_dir, "1.0.0")

        assert result is False

    def test_check_cache_validity_no_cache_config(self, tmp_path: Path) -> None:
        """Test cache validity check with no cache_validation config."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        metadata: dict[str, Any] = {}  # No cache_validation

        result = manager._check_cache_validity(metadata, workenv_dir, "1.0.0")

        assert result is False


class TestCleanupLifecycleSlots:
    """Test _cleanup_lifecycle_slots method."""

    @patch("flavor.psp.format_2025.workenv.safe_rmtree")
    def test_cleanup_init_lifecycle_directory(self, mock_rmtree: Mock, tmp_path: Path) -> None:
        """Test cleanup of 'init' lifecycle slot (directory)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        slot_dir = tmp_path / "init_slot"
        slot_dir.mkdir(parents=True)

        metadata = {"slots": [{"id": "init", "lifecycle": "init"}]}
        extracted_slots = {0: slot_dir}

        manager._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)

        # Should remove directory
        mock_rmtree.assert_called_once_with(slot_dir)

    def test_cleanup_init_lifecycle_file(self, tmp_path: Path) -> None:
        """Test cleanup of 'init' lifecycle slot (file)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        slot_file = tmp_path / "init_slot.txt"
        slot_file.write_text("init data")

        metadata = {"slots": [{"id": "init", "lifecycle": "init"}]}
        extracted_slots = {0: slot_file}

        manager._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)

        # Should remove file
        assert not slot_file.exists()

    def test_cleanup_temp_lifecycle(self, tmp_path: Path) -> None:
        """Test handling of 'temporary' lifecycle slot (not removed immediately)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        slot_dir = tmp_path / "temp_slot"
        slot_dir.mkdir(parents=True)

        metadata = {"slots": [{"id": "temp", "lifecycle": "temporary"}]}
        extracted_slots = {0: slot_dir}

        manager._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)

        # Should NOT remove temporary slot immediately
        assert slot_dir.exists()

    def test_cleanup_runtime_lifecycle(self, tmp_path: Path) -> None:
        """Test handling of 'runtime' lifecycle slot (not removed)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        slot_dir = tmp_path / "runtime_slot"
        slot_dir.mkdir(parents=True)

        metadata = {"slots": [{"id": "runtime", "lifecycle": "runtime"}]}
        extracted_slots = {0: slot_dir}

        manager._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)

        # Should NOT remove runtime slot
        assert slot_dir.exists()

    def test_cleanup_missing_lifecycle_field(self, tmp_path: Path) -> None:
        """Test handling of slot without lifecycle field (defaults to runtime)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        slot_dir = tmp_path / "slot"
        slot_dir.mkdir(parents=True)

        metadata = {"slots": [{"id": "slot"}]}  # No lifecycle field
        extracted_slots = {0: slot_dir}

        manager._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)

        # Should NOT remove (defaults to runtime)
        assert slot_dir.exists()

    def test_cleanup_refuses_to_remove_workenv_root(self, tmp_path: Path) -> None:
        """Guard: init slot whose path IS the workenv root must not be deleted."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        metadata = {"slots": [{"id": "init", "lifecycle": "init"}]}
        # slot_path IS the workenv root — the guard must prevent deletion
        extracted_slots = {0: tmp_path}

        manager._cleanup_lifecycle_slots(tmp_path, metadata, extracted_slots)

        assert tmp_path.exists()  # root must survive


@pytest.mark.unit
class TestRunEnumerateExecuteCommand:
    """Regression tests for _run_enumerate_execute_command nested enumerate schema."""

    def test_enumerate_command_reads_nested_enumerate_key(self, tmp_path: Path) -> None:
        """Runtime must read enumerate.path and enumerate.pattern from nested key."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        cmd = {
            "type": "enumerate_and_execute",
            "command": "echo {file}",
            "enumerate": {"path": str(tmp_path), "pattern": "*.txt"},
        }
        (tmp_path / "foo.txt").write_text("x")
        metadata = {"package": {"name": "test", "version": "1.0"}}

        with patch("flavor.psp.format_2025.workenv.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            # Should not raise — nested enumerate schema is correct
            manager._run_enumerate_execute_command(cmd, tmp_path, metadata, {})

    def test_enumerate_command_missing_enumerate_raises(self, tmp_path: Path) -> None:
        """Missing enumerate key must raise RuntimeError."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        cmd = {"type": "enumerate_and_execute", "command": "echo {file}", "pattern": "*.whl"}
        metadata = {"package": {"name": "test", "version": "1.0"}}

        with pytest.raises(RuntimeError):
            manager._run_enumerate_execute_command(cmd, tmp_path, metadata, {})


@pytest.mark.unit
class TestPrepareSetupEnvironmentPathHandling:
    """Regression tests for cross-platform PATH handling in _prepare_setup_environment.

    The fix uses sys.platform to choose 'Scripts' vs 'bin' and os.pathsep
    instead of a hardcoded '/bin:' prefix.
    """

    @patch("flavor.psp.format_2025.workenv.apply_environment_layers")
    def test_native_path_uses_platform_bin_and_sep(self, mock_apply: Mock, tmp_path: Path) -> None:
        """PATH should be prepended with the platform-appropriate bin dir and separator."""
        mock_apply.side_effect = lambda **kwargs: {
            **kwargs.get("base_env", {}),
            **kwargs.get("workenv_env", {}),
        }
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        env = manager._prepare_setup_environment(workenv_dir, runtime_env={})

        import sys

        bin_dir = "Scripts" if sys.platform == "win32" else "bin"
        expected_bin = str(workenv_dir / bin_dir)
        assert env["PATH"].startswith(expected_bin)
        # The separator after the bin dir should be the native os.pathsep
        rest = env["PATH"][len(expected_bin) :]
        assert rest.startswith(os.pathsep)

    @patch("flavor.psp.format_2025.workenv.apply_environment_layers")
    @patch("flavor.psp.format_2025.workenv.sys")
    @patch("flavor.psp.format_2025.workenv.os")
    def test_win32_path_uses_scripts_and_semicolon(
        self, mock_os: Mock, mock_sys: Mock, mock_apply: Mock, tmp_path: Path
    ) -> None:
        """When sys.platform == 'win32', PATH should use Scripts and semicolon."""
        mock_sys.platform = "win32"
        # Provide os.pathsep and os.environ for the win32 mock
        mock_os.pathsep = ";"
        mock_os.environ = {"PATH": "/usr/bin"}

        mock_apply.side_effect = lambda **kwargs: {
            **kwargs.get("base_env", {}),
            **kwargs.get("workenv_env", {}),
        }

        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        env = manager._prepare_setup_environment(workenv_dir, runtime_env={})

        expected_scripts = str(workenv_dir / "Scripts")
        assert expected_scripts in env["PATH"], f"Expected '{expected_scripts}' in PATH, got: {env['PATH']}"
        # Must use semicolon as separator (Windows pathsep)
        assert ";" in env["PATH"]

    @pytest.mark.parametrize(
        ("plat", "sep", "bin_dir"),
        [
            ("linux", ":", "bin"),
            ("darwin", ":", "bin"),
            ("win32", ";", "Scripts"),
        ],
    )
    @patch("flavor.psp.format_2025.workenv.apply_environment_layers")
    @patch("flavor.psp.format_2025.workenv.sys")
    @patch("flavor.psp.format_2025.workenv.os")
    def test_path_separator_matches_os_pathsep(
        self,
        mock_os: Mock,
        mock_sys: Mock,
        mock_apply: Mock,
        tmp_path: Path,
        plat: str,
        sep: str,
        bin_dir: str,
    ) -> None:
        """The PATH separator must always match os.pathsep for the platform."""
        mock_sys.platform = plat
        mock_os.pathsep = sep
        mock_os.environ = {"PATH": "/original"}

        captured: dict[str, dict[str, str]] = {}

        def capture_layers(**kwargs: Any) -> dict[str, str]:
            captured["workenv_env"] = kwargs.get("workenv_env", {})
            return {**kwargs.get("base_env", {}), **kwargs.get("workenv_env", {})}

        mock_apply.side_effect = capture_layers

        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir(exist_ok=True)

        manager._prepare_setup_environment(workenv_dir, runtime_env={})

        path_val = captured["workenv_env"]["PATH"]
        expected_prefix = str(workenv_dir / bin_dir)
        assert path_val.startswith(expected_prefix), (
            f"[{plat}] PATH should start with '{expected_prefix}', got: {path_val}"
        )
        # Character right after the bin/Scripts dir must be the pathsep
        after_prefix = path_val[len(expected_prefix)]
        assert after_prefix == sep, f"[{plat}] Expected separator '{sep}' after bin dir, got '{after_prefix}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
