#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Targeted coverage gap tests — final2 batch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ===========================================================================
# 1. verify.py branches
# ===========================================================================


class TestVerifyDisplayBranches:
    """Cover branch gaps in verify.py display helpers."""

    @pytest.mark.unit
    def test_display_package_metadata_no_package_key(self) -> None:
        """When result has no 'package' key, _display_package_metadata is a no-op (72->exit)."""
        from flavor.commands.verify import _display_package_metadata

        result: dict[str, object] = {"format": "PSPF/2025"}
        # Should not raise — just silently skip
        _display_package_metadata(result)  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_display_build_metadata_with_timestamp(self) -> None:
        """When build has a timestamp, it is printed (81->83)."""
        from flavor.commands.verify import _display_build_metadata

        with patch("flavor.commands.verify.pout") as mock_pout:
            result = {"build": {"timestamp": "2025-01-01T00:00:00Z"}}
            _display_build_metadata(result)
            mock_pout.assert_any_call("Built: 2025-01-01T00:00:00Z")

    @pytest.mark.unit
    def test_display_build_metadata_builder_version_no_timestamp(self) -> None:
        """When build has builder_version but no timestamp (83->85)."""
        from flavor.commands.verify import _display_build_metadata

        with patch("flavor.commands.verify.pout") as mock_pout:
            result = {"build": {"builder_version": "1.2.3"}}
            _display_build_metadata(result)
            mock_pout.assert_any_call("Builder: 1.2.3")
            # Ensure timestamp was NOT printed
            for call in mock_pout.call_args_list:
                assert not str(call).startswith("call('Built:")

    @pytest.mark.unit
    def test_display_build_metadata_with_launcher_type(self) -> None:
        """When build has launcher_type (85->exit)."""
        from flavor.commands.verify import _display_build_metadata

        with patch("flavor.commands.verify.pout") as mock_pout:
            result = {"build": {"launcher_type": "rust"}}
            _display_build_metadata(result)
            mock_pout.assert_any_call("Launcher Type: rust")

    @pytest.mark.unit
    def test_display_slot_information_no_slots_key(self) -> None:
        """When result has no 'slots' key, _display_slot_information is a no-op (91->exit)."""
        from flavor.commands.verify import _display_slot_information

        result: dict[str, object] = {"format": "PSPF/2025"}
        _display_slot_information(result)  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_verify_command_integration_no_package_no_slots(self, tmp_path: Path) -> None:
        """Full CLI verify with result missing 'package' and 'slots' keys."""
        from click.testing import CliRunner

        from flavor.cli import cli

        dummy_file = tmp_path / "test.psp"
        dummy_file.write_bytes(b"\x00" * 64)

        mock_result = {
            "format": "PSPF/2025",
            "version": "1.0",
            "launcher_size": 1024 * 1024,
            "slot_count": 0,
            "build": None,
            "valid": True,
        }

        with patch("flavor.commands.verify.verify_package", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(cli, ["verify", str(dummy_file)])
            assert result.exit_code == 0

    @pytest.mark.unit
    def test_verify_command_integration_with_build_and_slots(self, tmp_path: Path) -> None:
        """Full CLI verify with build metadata and slots present."""
        from click.testing import CliRunner

        from flavor.cli import cli

        dummy_file = tmp_path / "test.psp"
        dummy_file.write_bytes(b"\x00" * 64)

        mock_result = {
            "format": "PSPF/2025",
            "version": "1.0",
            "launcher_size": 2 * 1024 * 1024,
            "slot_count": 1,
            "build": {
                "timestamp": "2025-06-01T12:00:00Z",
                "builder_version": "2.0.0",
                "launcher_type": "go",
            },
            "package": {"name": "myapp", "version": "1.0.0"},
            "slots": [
                {
                    "index": 0,
                    "id": "payload",
                    "size": 512,
                    "operations": "gzip",
                    "purpose": "payload",
                    "lifecycle": "runtime",
                }
            ],
            "valid": True,
        }

        with patch("flavor.commands.verify.verify_package", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(cli, ["verify", str(dummy_file)])
            assert result.exit_code == 0
            assert "Built: 2025-06-01T12:00:00Z" in result.output
            assert "Builder: 2.0.0" in result.output
            assert "Launcher Type: go" in result.output


# ===========================================================================
# 2. orchestrator.py — BuildError for json manifest_type with None path,
#    and --public-key append logic
# ===========================================================================


class TestOrchestratorJsonManifest:
    """Cover orchestrator.py build paths."""

    @pytest.mark.unit
    def test_build_with_json_manifest_raises_when_path_is_none(self) -> None:
        """build_package raises BuildError when manifest_type=json but json_manifest_path is None (line 331)."""
        from flavor.exceptions import BuildError
        from flavor.packaging.orchestrator import PackagingOrchestrator

        orch = PackagingOrchestrator(
            package_integrity_key_path=None,
            public_key_path=None,
            output_flavor_path="/tmp/out.psp",
            build_config={},
            manifest_dir=Path("/tmp"),
            package_name="test",
            version="1.0",
            entry_point="main:app",
            manifest_type="json",
            json_manifest_path=None,
            builder_bin="/usr/bin/fake-builder",
        )

        # Simulate the external builder path being chosen and launcher already resolved
        mock_launcher = MagicMock()
        mock_launcher.exists.return_value = True
        mock_launcher.name = "launcher-darwin_arm64"
        mock_launcher.as_posix.return_value = "/tmp/launcher"
        orch._launcher_path = mock_launcher

        with (
            patch.object(orch, "_detect_launcher_type", return_value="go"),
            patch(
                "flavor.packaging.orchestrator.find_builder_executable",
                return_value=Path("/tmp/builder"),
            ),
            pytest.raises(BuildError, match="json_manifest_path is required"),
        ):
            orch._build_with_json_manifest()

    @pytest.mark.unit
    def test_external_builder_appends_public_key(self) -> None:
        """--public-key is appended when both key paths are set (318->321)."""
        from flavor.packaging.orchestrator import PackagingOrchestrator

        orch = PackagingOrchestrator(
            package_integrity_key_path="/keys/private.pem",
            public_key_path="/keys/public.pem",
            output_flavor_path="/tmp/out.psp",
            build_config={},
            manifest_dir=Path("/tmp"),
            package_name="test",
            version="1.0",
            entry_point="main:app",
            manifest_type="toml",
        )

        mock_launcher = MagicMock()
        mock_launcher.exists.return_value = True
        mock_launcher.name = "launcher-darwin_arm64"
        mock_launcher.as_posix.return_value = "/tmp/launcher"
        orch._launcher_path = mock_launcher

        captured_cmd: list[str] = []

        def capture_run(cmd: list[str], **_kwargs: object) -> MagicMock:
            captured_cmd.extend(cmd)
            return MagicMock(stdout="", stderr="", returncode=0)

        with (
            patch.object(orch, "_detect_launcher_type", return_value="go"),
            patch(
                "flavor.packaging.orchestrator.find_builder_executable",
                return_value=Path("/tmp/builder"),
            ),
            patch(
                "flavor.packaging.orchestrator.find_launcher_executable",
                return_value=mock_launcher,
            ),
            patch("flavor.packaging.orchestrator.run", side_effect=capture_run),
            patch(
                "flavor.packaging.orchestrator_helpers.create_slot_tarballs",
                return_value=[],
            ),
            patch(
                "flavor.packaging.orchestrator.create_builder_manifest",
                return_value={},
            ),
            patch(
                "flavor.packaging.orchestrator.write_manifest_file",
                return_value=Path("/tmp/manifest.json"),
            ),
            patch("flavor.packaging.orchestrator.PythonPackager") as mock_pp,
        ):
            mock_pp.return_value.prepare_artifacts.return_value = {}
            orch._build_with_external_builder()

        assert "--public-key" in captured_cmd
        assert "/keys/public.pem" in captured_cmd
        assert "--private-key" in captured_cmd
        assert "/keys/private.pem" in captured_cmd

    @pytest.mark.unit
    def test_external_builder_no_public_key_when_none(self) -> None:
        """--public-key is NOT appended when public_key_path is None (357->360)."""
        from flavor.packaging.orchestrator import PackagingOrchestrator

        orch = PackagingOrchestrator(
            package_integrity_key_path="/keys/private.pem",
            public_key_path=None,
            output_flavor_path="/tmp/out.psp",
            build_config={},
            manifest_dir=Path("/tmp"),
            package_name="test",
            version="1.0",
            entry_point="main:app",
            manifest_type="toml",
        )

        mock_launcher = MagicMock()
        mock_launcher.exists.return_value = True
        mock_launcher.name = "launcher-darwin_arm64"
        mock_launcher.as_posix.return_value = "/tmp/launcher"
        orch._launcher_path = mock_launcher

        captured_cmd: list[str] = []

        def capture_run(cmd: list[str], **_kwargs: object) -> MagicMock:
            captured_cmd.extend(cmd)
            return MagicMock(stdout="", stderr="", returncode=0)

        with (
            patch.object(orch, "_detect_launcher_type", return_value="go"),
            patch(
                "flavor.packaging.orchestrator.find_builder_executable",
                return_value=Path("/tmp/builder"),
            ),
            patch("flavor.packaging.orchestrator.run", side_effect=capture_run),
            patch(
                "flavor.packaging.orchestrator_helpers.create_slot_tarballs",
                return_value=[],
            ),
            patch(
                "flavor.packaging.orchestrator.create_builder_manifest",
                return_value={},
            ),
            patch(
                "flavor.packaging.orchestrator.write_manifest_file",
                return_value=Path("/tmp/manifest.json"),
            ),
            patch("flavor.packaging.orchestrator.PythonPackager") as mock_pp,
        ):
            mock_pp.return_value.prepare_artifacts.return_value = {}
            orch._build_with_external_builder()

        assert "--private-key" in captured_cmd
        assert "--public-key" not in captured_cmd


# ===========================================================================
# 3. launcher.py — _is_package_key_trusted and _enforce_launch_security
# ===========================================================================


class TestLauncherSecurityBranches:
    """Cover launcher.py security methods."""

    @pytest.mark.unit
    def test_is_package_key_trusted_no_index_arg(self) -> None:
        """_is_package_key_trusted with no index arg reads index itself (line 307)."""
        from flavor.psp.format_2025.launcher import PSPFLauncher

        mock_index = MagicMock()
        mock_index.public_key = b"\x00" * 32  # all zeros -> not trusted
        mock_index.attestation_key_fp = b""

        with (
            patch.object(PSPFLauncher, "__init__", lambda self, **kw: None),
            patch.object(PSPFLauncher, "read_index", return_value=mock_index),
        ):
            launcher = PSPFLauncher.__new__(PSPFLauncher)
            result = launcher._is_package_key_trusted()  # no index arg
            assert result is False

    @pytest.mark.unit
    def test_is_package_key_trusted_non_ascii_attestation_fp(self) -> None:
        """Non-ASCII attestation_key_fp raises ValueError (318-319)."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        from flavor.psp.format_2025.launcher import PSPFLauncher

        # Generate a real key so the fingerprint computation works
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        raw_public = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

        mock_index = MagicMock()
        mock_index.public_key = raw_public
        # Non-ASCII bytes that will fail .decode("ascii")
        mock_index.attestation_key_fp = b"\xff\xfe\xfd\x00"

        with (
            patch.object(PSPFLauncher, "__init__", lambda self, **kw: None),
            pytest.raises(ValueError, match="not valid ASCII"),
        ):
            launcher = PSPFLauncher.__new__(PSPFLauncher)
            launcher._is_package_key_trusted(index=mock_index)

    @pytest.mark.unit
    def test_enforce_launch_security_invalid_verification(self) -> None:
        """_enforce_launch_security raises when verify returns invalid (line 330)."""
        from flavor.psp.format_2025.launcher import PSPFLauncher

        with (
            patch.object(PSPFLauncher, "__init__", lambda self, **kw: None),
            patch(
                "flavor.psp.format_2025.launcher.verify_package_integrity",
                return_value={"valid": False},
            ),
        ):
            launcher = PSPFLauncher.__new__(PSPFLauncher)
            launcher.bundle_path = Path("/tmp/fake.psp")
            with pytest.raises(ValueError, match="package integrity verification failed"):
                launcher._enforce_launch_security({"slots": []})


# ===========================================================================
# 4. dependency_resolver.py key gaps
# ===========================================================================


class TestDependencyResolverGaps:
    """Cover dependency_resolver.py branch gaps."""

    @pytest.mark.unit
    def test_find_uv_command_system_none_pipx_finds_it(self) -> None:
        """find_uv_command when system UV is None but pipx finds it (64->78, 80)."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)

        with (
            patch.object(resolver.uv_manager, "find_system_uv", return_value=None),
            patch.object(resolver, "_find_uv_via_pipx", return_value="/usr/local/bin/uv"),
        ):
            result = resolver.find_uv_command(raise_if_not_found=True)
            assert result == "/usr/local/bin/uv"

    @pytest.mark.unit
    def test_find_downloaded_uv_wheel_no_whl_found(self, tmp_path: Path) -> None:
        """_find_downloaded_uv_wheel returns None when no .whl file found (293-294)."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)
        # Create a temp dir with no .whl files
        (tmp_path / "somefile.txt").write_text("not a wheel")
        result = resolver._find_downloaded_uv_wheel(str(tmp_path))
        assert result is None

    @pytest.mark.unit
    def test_get_platform_tag_linux_arm64(self) -> None:
        """_get_platform_tag returns manylinux2014_aarch64 for linux/arm64 (249->251)."""
        from flavor.packaging.python.dependency_resolver import DependencyResolver

        resolver = DependencyResolver(is_windows=False)
        # Renamed internal method — it's _get_uv_platform_tag
        with (
            patch("flavor.packaging.python.dependency_resolver.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.dependency_resolver.get_arch_name", return_value="arm64"),
        ):
            result = resolver._get_uv_platform_tag()
            assert result == "manylinux2014_aarch64"


# ===========================================================================
# 5. environment_builder.py — _find_python_installation returns None
#    when cpython dir exists but _find_python_binary returns None (line 243)
# ===========================================================================


class TestEnvironmentBuilderGaps:
    """Cover environment_builder.py branch gaps."""

    @pytest.mark.unit
    def test_find_python_installation_cpython_dir_no_binary(self, tmp_path: Path) -> None:
        """_find_python_installation returns None when cpython dir exists but no binary found."""
        from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

        builder = PythonEnvironmentBuilder(python_version="3.11", is_windows=False)

        # Create a fake cpython directory
        cpython_dir = tmp_path / "cpython-3.11.0"
        cpython_dir.mkdir()

        # _find_python_binary will return None because there is no actual binary
        with patch.object(builder, "_find_python_binary", return_value=None):
            result = builder._find_python_installation(str(tmp_path), "uv")
            assert result is None


# ===========================================================================
# 6. package.py — line 79 (JSON manifest parsing) and line 326 (execution in build_config)
# ===========================================================================


class TestPackageModuleGaps:
    """Cover package.py branch gaps."""

    @pytest.mark.unit
    def test_parse_json_manifest(self, tmp_path: Path) -> None:
        """_parse_json_manifest correctly parses a JSON manifest (line 79)."""
        import json

        from flavor.package import _parse_json_manifest

        manifest = {
            "package": {"name": "myapp", "version": "2.0.0"},
            "execution": {"command": "python -m myapp"},
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        result = _parse_json_manifest(manifest_path)
        assert result["project_name"] == "myapp"
        assert result["version"] == "2.0.0"
        assert result["entry_point"] == "python -m myapp"
        assert result["package_name"] == "myapp"

    @pytest.mark.unit
    def test_get_build_config_with_execution(self) -> None:
        """_get_build_config_from_toml merges execution into build_config (line 326)."""
        from flavor.package import _get_build_config_from_toml

        flavor_config = {
            "build": {"optimize": True},
            "execution": {"command": "python -m app", "args": ["--serve"]},
        }
        # Use a manifest_path in a directory with no buildconfig.toml
        manifest_path = Path("/nonexistent/dir/pyproject.toml")
        result = _get_build_config_from_toml(flavor_config, manifest_path)
        assert result["optimize"] is True
        assert result["execution"]["command"] == "python -m app"
        assert result["execution"]["args"] == ["--serve"]

    @pytest.mark.unit
    def test_get_build_config_without_execution(self) -> None:
        """_get_build_config_from_toml with no execution key."""
        from flavor.package import _get_build_config_from_toml

        flavor_config = {"build": {"strip": False}}
        manifest_path = Path("/nonexistent/dir/pyproject.toml")
        result = _get_build_config_from_toml(flavor_config, manifest_path)
        assert result["strip"] is False
        assert "execution" not in result


# 🌶️📦🔚
