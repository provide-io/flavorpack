#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PythonSlotBuilder._bundle_build_backends."""

from pathlib import Path
import subprocess
import tempfile
from unittest.mock import Mock, patch

import pytest

from flavor.packaging.python.slot_builder import PythonSlotBuilder


class TestBundleBuildBackends:
    """Test build-backends bundling into slot wheels directory."""

    def _make_builder(self, manifest_dir: Path) -> PythonSlotBuilder:
        wheel_builder = Mock()
        return PythonSlotBuilder(
            manifest_dir=manifest_dir,
            package_name="test-pkg",
            entry_point="test_pkg.cli:main",
            wheel_builder=wheel_builder,
        )

    def test_bundle_skips_when_no_build_backends_group(self) -> None:
        """If pyproject.toml has no build-backends group, skip silently."""
        with tempfile.TemporaryDirectory() as tmp:
            manifest_dir = Path(tmp)
            (manifest_dir / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
            wheels_dir = manifest_dir / "wheels"
            wheels_dir.mkdir()
            builder = self._make_builder(manifest_dir)
            with patch("flavor.packaging.python.slot_builder.run") as mock_run:
                builder._bundle_build_backends(wheels_dir)
                mock_run.assert_not_called()

    def test_bundle_exports_and_downloads_when_group_present(self) -> None:
        """When build-backends group exists, export with hashes and pip download."""
        with tempfile.TemporaryDirectory() as tmp:
            manifest_dir = Path(tmp)
            (manifest_dir / "pyproject.toml").write_text(
                '[project]\nname = "foo"\n'
                "[dependency-groups]\n"
                'build-backends = ["setuptools==82.0.1", "wheel==0.46.3"]\n'
            )
            (manifest_dir / "uv.lock").write_text("# mock lock file\n")
            wheels_dir = manifest_dir / "wheels"
            wheels_dir.mkdir()

            builder = self._make_builder(manifest_dir)

            mock_uv_exe = Path("/usr/bin/uv")
            with (
                patch.object(builder.uv_manager, "get_uv_executable", return_value=mock_uv_exe),
                patch("flavor.packaging.python.slot_builder.run") as mock_run,
                patch("flavor.packaging.python.slot_builder.sys") as mock_sys,
            ):
                mock_sys.executable = "/usr/bin/python3"
                mock_run.return_value = Mock(returncode=0, stdout="")
                builder._bundle_build_backends(wheels_dir)

            assert mock_run.call_count == 2
            export_call = mock_run.call_args_list[0][0][0]
            assert export_call[0] == "/usr/bin/uv"
            assert "export" in export_call
            assert "--frozen" in export_call
            assert "--only-group" in export_call
            assert "build-backends" in export_call
            assert "--hashes" in export_call

            download_call = mock_run.call_args_list[1][0][0]
            assert "download" in download_call
            assert "--require-hashes" in download_call

    def test_bundle_skips_when_no_uv_lock(self) -> None:
        """If uv.lock is missing, skip silently even if group exists."""
        with tempfile.TemporaryDirectory() as tmp:
            manifest_dir = Path(tmp)
            (manifest_dir / "pyproject.toml").write_text(
                '[project]\nname = "foo"\n[dependency-groups]\nbuild-backends = ["setuptools==82.0.1"]\n'
            )
            # No uv.lock created
            wheels_dir = manifest_dir / "wheels"
            wheels_dir.mkdir()
            builder = self._make_builder(manifest_dir)
            with patch("flavor.packaging.python.slot_builder.run") as mock_run:
                builder._bundle_build_backends(wheels_dir)
                mock_run.assert_not_called()

    def test_bundle_propagates_download_failure(self) -> None:
        """pip download failure must propagate — not be silently swallowed."""
        with tempfile.TemporaryDirectory() as tmp:
            manifest_dir = Path(tmp)
            (manifest_dir / "pyproject.toml").write_text(
                '[project]\nname = "foo"\n'
                "[dependency-groups]\n"
                'build-backends = ["setuptools==82.0.1", "wheel==0.46.3"]\n'
            )
            (manifest_dir / "uv.lock").write_text("# mock lock file\n")
            wheels_dir = manifest_dir / "wheels"
            wheels_dir.mkdir()

            builder = self._make_builder(manifest_dir)
            mock_uv_exe = Path("/usr/bin/uv")

            def fail_on_download(cmd: list[str], **kwargs: object) -> Mock:
                if "download" in cmd:
                    raise subprocess.CalledProcessError(1, cmd)
                return Mock(returncode=0, stdout="")

            with (
                patch.object(builder.uv_manager, "get_uv_executable", return_value=mock_uv_exe),
                patch("flavor.packaging.python.slot_builder.run", side_effect=fail_on_download),
                patch("flavor.packaging.python.slot_builder.sys") as mock_sys,
            ):
                mock_sys.executable = "/usr/bin/python3"
                with pytest.raises(subprocess.CalledProcessError):
                    builder._bundle_build_backends(wheels_dir)


# 🌶️📦🔚
