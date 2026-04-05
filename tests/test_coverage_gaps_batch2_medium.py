#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Coverage gap tests — batch 2 medium gaps."""

from __future__ import annotations

from pathlib import Path
import struct
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ===========================================================================
# 1. helpers/manager.py — lines 87-88, 96, 105-106
#    builder type classification in helpers_bin + embedded_bin,
#    platform_filter in embedded_bin loop
# ===========================================================================


@pytest.mark.unit
class TestHelperManagerListHelpersBuilderBranches:
    """Cover builder-type and platform-filter branches in list_helpers."""

    @patch("flavor.helpers.manager.ensure_dir")
    @patch("flavor.helpers.manager.get_platform_string", return_value="linux_amd64")
    @patch("flavor.helpers.binary_loader.BinaryLoader")
    def _make_manager(
        self,
        mock_bl: MagicMock,
        mock_plat: MagicMock,
        mock_ed: MagicMock,
    ) -> Any:
        from flavor.helpers.manager import HelperManager

        return HelperManager()

    def test_builder_type_in_helpers_bin(self, tmp_path: Path) -> None:
        """Builders found in helpers_bin are classified correctly (lines 87-88)."""
        manager = self._make_manager()
        # Create a fake builder binary in helpers_bin
        manager.helpers_bin = tmp_path
        builder_file = tmp_path / "flavor-go-builder-linux_amd64"
        builder_file.write_bytes(b"\x00" * 100)

        result = manager.list_helpers(platform_filter=False)
        assert len(result["builders"]) == 1
        assert result["builders"][0].type == "builder"
        assert result["builders"][0].language == "go"

    def test_embedded_bin_platform_filter_and_builder(self, tmp_path: Path) -> None:
        """Embedded helpers are filtered by platform and builder type (lines 96, 105-106)."""
        manager = self._make_manager()
        # No helpers in helpers_bin
        manager.helpers_bin = tmp_path / "empty_bin"
        manager.helpers_bin.mkdir()

        # Patch Path(__file__).parent / "bin" to point to tmp_path / "embedded"
        embedded = tmp_path / "embedded"
        embedded.mkdir()
        # Create a builder that matches the current platform
        builder_file = embedded / "flavor-rs-builder-linux_amd64"
        builder_file.write_bytes(b"\x00" * 100)
        # Create a launcher that does NOT match the platform (should be filtered)
        other_file = embedded / "flavor-go-launcher-darwin_arm64"
        other_file.write_bytes(b"\x00" * 100)

        # The code does `embedded_bin = Path(__file__).parent / "bin"`.
        # We patch __file__ so "bin" resolves to our temp directory.
        fake_module_parent = tmp_path / "fake_parent"
        fake_bin = fake_module_parent / "bin"
        fake_bin.mkdir(parents=True)
        # builder in embedded bin
        (fake_bin / "flavor-rs-builder-linux_amd64").write_bytes(b"\x00" * 100)
        # launcher filtered out by platform
        (fake_bin / "flavor-go-launcher-darwin_arm64").write_bytes(b"\x00" * 100)

        with patch("flavor.helpers.manager.__file__", str(fake_module_parent / "manager.py")):
            result = manager.list_helpers(platform_filter=True)

        # Builder matching platform should be included
        assert any(h.type == "builder" for h in result["builders"])
        # Launcher for darwin should NOT be included (platform filtered)
        assert not any(h.name == "flavor-go-launcher-darwin_arm64" for h in result["launchers"])


# ===========================================================================
# 2. psp/format_2025/pe_utils/dos_stub.py — lines 52, 102
#    Invalid PE header offset (None) and post-expansion verification failure
# ===========================================================================


@pytest.mark.unit
class TestDosStubCoverage:
    """Cover expand_dos_stub edge cases."""

    def test_expand_dos_stub_invalid_pe_offset(self) -> None:
        """get_pe_header_offset returns None -> ValueError (line 52)."""
        from flavor.psp.format_2025.pe_utils.dos_stub import expand_dos_stub

        # Valid MZ header but broken e_lfanew pointer
        data = bytearray(256)
        data[0:2] = b"MZ"
        # Set e_lfanew to an offset beyond the data length
        struct.pack_into("<I", data, 0x3C, 0)  # offset 0 means PE sig at 0 which is "MZ" not "PE"

        with (
            patch(
                "flavor.psp.format_2025.pe_utils.dos_stub.get_pe_header_offset",
                return_value=None,
            ),
            patch(
                "flavor.psp.format_2025.pe_utils.dos_stub.is_pe_executable",
                return_value=True,
            ),
            pytest.raises(ValueError, match="Invalid PE header offset"),
        ):
            expand_dos_stub(bytes(data))

    def test_expand_dos_stub_verification_failure(self) -> None:
        """Post-expansion PE offset mismatch -> ValueError (line 102)."""
        from flavor.psp.format_2025.pe_utils.dos_stub import expand_dos_stub

        # Build a minimal PE-like structure with a small stub
        current_pe_offset = 0x80  # Smaller than TARGET_DOS_STUB_SIZE
        data = bytearray(512)
        data[0:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, current_pe_offset)
        # Put PE signature at the expected offset
        data[current_pe_offset : current_pe_offset + 4] = b"PE\x00\x00"

        with (
            patch(
                "flavor.psp.format_2025.pe_utils.dos_stub.is_pe_executable",
                return_value=True,
            ),
            patch(
                "flavor.psp.format_2025.pe_utils.dos_stub.get_pe_header_offset",
                side_effect=[current_pe_offset, 0xBAD],  # first call: real, second: bad
            ),
            patch("flavor.psp.format_2025.pe_utils.dos_stub.update_section_offsets"),
            patch("flavor.psp.format_2025.pe_utils.dos_stub.update_size_of_headers"),
            patch("flavor.psp.format_2025.pe_utils.dos_stub.update_data_directories"),
            patch("flavor.psp.format_2025.pe_utils.dos_stub.update_debug_directory"),
            pytest.raises(ValueError, match="Failed to update PE offset"),
        ):
            expand_dos_stub(bytes(data))


# ===========================================================================
# 3. cache.py — lines 36-38, 44, 52, 58  (trace logging branches)
# ===========================================================================


@pytest.mark.unit
class TestCacheTraceLogging:
    """Cover trace-logging branches in get_cache_dir."""

    def test_cache_dir_trace_flavor_cache_dir(self) -> None:
        """FLAVOR_CACHE_DIR set + trace enabled -> trace log (lines 36-38)."""
        mock_log = MagicMock()
        mock_log.is_trace_enabled.return_value = True

        with (
            patch("flavor.cache.log", mock_log),
            patch(
                "flavor.cache.get_str",
                side_effect=lambda key: "/custom/cache" if key == "FLAVOR_CACHE_DIR" else None,
            ),
        ):
            from flavor.cache import get_cache_dir

            result = get_cache_dir()
            assert result == Path("/custom/cache")
            mock_log.trace.assert_called_once()

    def test_cache_dir_trace_flavor_cache_compat(self) -> None:
        """FLAVOR_CACHE set + trace enabled -> trace log (line 44)."""
        mock_log = MagicMock()
        mock_log.is_trace_enabled.return_value = True

        def fake_get_str(key: str) -> str | None:
            if key == "FLAVOR_CACHE":
                return "/compat/cache"
            return None

        with (
            patch("flavor.cache.log", mock_log),
            patch("flavor.cache.get_str", side_effect=fake_get_str),
        ):
            from flavor.cache import get_cache_dir

            result = get_cache_dir()
            assert result == Path("/compat/cache")
            mock_log.trace.assert_called_once()

    def test_cache_dir_trace_xdg_cache_home(self) -> None:
        """XDG_CACHE_HOME set + trace enabled -> trace log (line 52)."""
        mock_log = MagicMock()
        mock_log.is_trace_enabled.return_value = True

        def fake_get_str(key: str) -> str | None:
            if key == "XDG_CACHE_HOME":
                return "/xdg/cache"
            return None

        with (
            patch("flavor.cache.log", mock_log),
            patch("flavor.cache.get_str", side_effect=fake_get_str),
        ):
            from flavor.cache import get_cache_dir

            result = get_cache_dir()
            assert result == Path("/xdg/cache/flavor/workenv")
            mock_log.trace.assert_called_once()

    def test_cache_dir_trace_default(self) -> None:
        """No env vars + trace enabled -> default path trace log (line 58)."""
        mock_log = MagicMock()
        mock_log.is_trace_enabled.return_value = True

        with (
            patch("flavor.cache.log", mock_log),
            patch("flavor.cache.get_str", return_value=None),
        ):
            from flavor.cache import get_cache_dir

            result = get_cache_dir()
            assert result == Path.home() / ".cache" / "flavor" / "workenv"
            mock_log.trace.assert_called_once()


# ===========================================================================
# 4. packaging/python/environment_builder.py
#    lines 151-152, 178-179, 243, 505-517, 559, 567, 571
# ===========================================================================


@pytest.mark.unit
class TestEnvironmentBuilderCoverage:
    """Cover missing branches in PythonEnvironmentBuilder."""

    def _make_builder(self, is_windows: bool = False) -> Any:
        with (
            patch("flavor.packaging.python.environment_builder.UVManager"),
            patch("flavor.packaging.python.environment_builder.PyPaPipManager"),
            patch("flavor.packaging.python.environment_builder.DependencyResolver"),
        ):
            from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder

            return PythonEnvironmentBuilder(is_windows=is_windows)

    def test_install_python_strategy1_exception(self) -> None:
        """Strategy 1 raises exception -> falls through to strategy 2 (lines 151-152)."""
        builder = self._make_builder()

        mock_result2 = MagicMock()
        mock_result2.returncode = 1
        mock_result2.stderr = ""

        with (
            patch.object(builder, "find_uv_command", return_value="uv"),
            patch.object(builder, "_log_uv_environment"),
            patch.object(builder, "_resolve_uv_python_spec", return_value="3.11"),
            patch(
                "flavor.packaging.python.environment_builder.run",
                side_effect=[Exception("network error"), mock_result2, mock_result2],
            ),
        ):
            result = builder._install_python_with_uv("/tmp/uv_install")
            assert result is None

    def test_install_python_strategy2_exception(self) -> None:
        """Strategy 2 raises exception -> returns None (lines 178-179)."""
        builder = self._make_builder()

        mock_result1 = MagicMock()
        mock_result1.returncode = 0
        mock_result1.stderr = ""

        with (
            patch.object(builder, "find_uv_command", return_value="uv"),
            patch.object(builder, "_log_uv_environment"),
            patch.object(builder, "_resolve_uv_python_spec", return_value="3.11"),
            patch.object(builder, "_find_python_installation", return_value=None),
            patch(
                "flavor.packaging.python.environment_builder.run",
                side_effect=[mock_result1, Exception("strategy 2 failed")],
            ),
        ):
            result = builder._install_python_with_uv("/tmp/uv_install")
            assert result is None

    def test_find_python_installation_no_cpython_no_subdirs(self, tmp_path: Path) -> None:
        """No cpython dirs and no subdirectories -> returns None (line 243)."""
        builder = self._make_builder()
        install_dir = tmp_path / "empty_install"
        install_dir.mkdir()
        # Put only a file, no directories
        (install_dir / "somefile.txt").write_text("x")

        with (
            patch.object(builder, "_fallback_find_python", return_value=None),
        ):
            result = builder._find_python_installation(str(install_dir), "uv")
            assert result is None

    def test_create_fallback_python_tarball_no_system_python(self, tmp_path: Path) -> None:
        """Non-linux, no system python -> placeholder tarball (lines 505-517)."""
        builder = self._make_builder()
        python_tgz = tmp_path / "python.tgz"

        with (
            patch("flavor.packaging.python.environment_builder.get_os_name", return_value="freebsd"),
            patch("flavor.packaging.python.environment_builder.get_arch_name", return_value="amd64"),
            patch("shutil.which", return_value=None),
        ):
            builder._create_fallback_python_tarball(python_tgz)

        assert python_tgz.exists()
        assert python_tgz.stat().st_size > 0

    def test_tarball_filter_windows_bin_rename(self) -> None:
        """Windows tarball filter renames ./bin/ to ./Scripts/ (lines 559, 567, 571)."""
        builder = self._make_builder(is_windows=True)
        stats: dict[str, int] = {"files_added": 0, "bytes_added": 0}

        filter_func = builder._create_tarball_filter(stats)

        import tarfile

        # Test ./bin/python.exe -> ./Scripts/python.exe (line 565-567 trace)
        tarinfo_file = tarfile.TarInfo(name="./bin/python.exe")
        tarinfo_file.type = tarfile.REGTYPE
        tarinfo_file.size = 100
        with patch(
            "flavor.packaging.python.environment_builder.deterministic_filter", side_effect=lambda x: x
        ):
            result = filter_func(tarinfo_file)
        assert result is not None
        assert result.name == "./Scripts/python.exe"

        # Test ./bin -> ./Scripts (line 569-571 trace)
        tarinfo_dir = tarfile.TarInfo(name="./bin")
        tarinfo_dir.type = tarfile.DIRTYPE
        tarinfo_dir.size = 0
        with patch(
            "flavor.packaging.python.environment_builder.deterministic_filter", side_effect=lambda x: x
        ):
            result2 = filter_func(tarinfo_dir)
        assert result2 is not None
        assert result2.name == "./Scripts"


# ===========================================================================
# 5. packaging/python/pypapip_manager.py — lines 179, 199, 248-250
#    trace log for linux arch, find_links, download failure error
# ===========================================================================


@pytest.mark.unit
class TestPyPaPipManagerCoverage:
    """Cover missing branches in PyPaPipManager."""

    def test_download_cmd_trace_logging_for_linux_arch(self) -> None:
        """Linux binary download triggers trace log for arch (line 179)."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager(python_version="3.11")

        mock_logger = MagicMock()
        mock_logger.is_trace_enabled.return_value = True

        with (
            patch("flavor.packaging.python.pypapip_manager.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.pypapip_manager.get_arch_name", return_value="amd64"),
            patch("flavor.packaging.python.pypapip_manager.logger", mock_logger),
            patch("sys.platform", "linux"),
        ):
            cmd = mgr._get_pypapip_download_cmd(
                Path("/usr/bin/python3"), Path("/tmp"), packages=["test"], binary_only=True
            )
        assert "manylinux2014_x86_64" in cmd
        mock_logger.trace.assert_called_once()

    def test_download_cmd_find_links(self) -> None:
        """find_links parameter adds --find-links to command (line 199)."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager(python_version="3.11")

        with (
            patch("flavor.packaging.python.pypapip_manager.get_os_name", return_value="darwin"),
            patch("sys.platform", "linux"),
        ):
            cmd = mgr._get_pypapip_download_cmd(
                Path("/usr/bin/python3"),
                Path("/tmp"),
                packages=["test"],
                binary_only=True,
                find_links="/local/wheels",
            )
        assert "--find-links" in cmd
        assert "/local/wheels" in cmd

    def test_download_wheels_from_requirements_failure(self) -> None:
        """Download failure raises RuntimeError (lines 248-250)."""
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        mgr = PyPaPipManager(python_version="3.11")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "network error"

        with (
            patch("flavor.packaging.python.pypapip_manager.run", return_value=mock_result),
            pytest.raises(RuntimeError, match="Failed to download required wheels"),
        ):
            mgr.download_wheels_from_requirements(
                Path("/usr/bin/python3"),
                Path("/tmp/requirements.txt"),
                Path("/tmp/wheels"),
            )


# ===========================================================================
# 6. package.py — lines 79, 141-143, 202, 326
#    JSON manifest entry_point, verify_package, generate_keys,
#    buildconfig.toml merge
# ===========================================================================


@pytest.mark.unit
class TestPackageCoverage:
    """Cover missing branches in package.py."""

    def test_parse_json_manifest_missing_command(self, tmp_path: Path) -> None:
        """Missing execution.command -> ValueError (line 79 vicinity)."""
        import json

        from flavor.package import _parse_json_manifest

        p = tmp_path / "manifest.json"
        p.write_text(
            json.dumps(
                {
                    "package": {"name": "pkg", "version": "1.0"},
                    "execution": {},
                }
            )
        )
        with pytest.raises(ValueError, match="command"):
            _parse_json_manifest(p)

    def test_verify_package_delegates(self, tmp_path: Path) -> None:
        """verify_package calls FlavorVerifier.verify_package (lines 141-143)."""
        from flavor.package import verify_package

        pkg = tmp_path / "test.psp"
        pkg.write_bytes(b"\x00" * 100)

        mock_verifier_cls = MagicMock()
        mock_verifier_cls.verify_package.return_value = {"valid": True}

        # The import is lazy: `from .verification import FlavorVerifier`
        # Patch at the module that gets imported.
        with patch.dict(
            "sys.modules",
            {"flavor.verification": MagicMock(FlavorVerifier=mock_verifier_cls)},
        ):
            result = verify_package(pkg)
        assert result == {"valid": True}

    def test_generate_keys_delegates(self, tmp_path: Path) -> None:
        """generate_keys calls generate_key_pair (line 202)."""
        from flavor.package import generate_keys

        with patch("flavor.package.generate_key_pair", return_value=(Path("a"), Path("b"))) as mock_gkp:
            result = generate_keys(tmp_path)
            mock_gkp.assert_called_once_with(tmp_path)
            assert result == (Path("a"), Path("b"))

    def test_get_build_config_from_toml_with_buildconfig(self, tmp_path: Path) -> None:
        """buildconfig.toml merges into build_config (line 326)."""
        from flavor.package import _get_build_config_from_toml

        # Create a buildconfig.toml next to the manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.touch()
        buildconfig = tmp_path / "buildconfig.toml"
        buildconfig.write_text("[build]\noptimize = true\n")

        flavor_config: dict[str, Any] = {"build": {"debug": False}}
        result = _get_build_config_from_toml(flavor_config, manifest_path)

        assert result["debug"] is False
        assert result["optimize"] is True


# ===========================================================================
# 7. packaging/keys.py — lines 123, 171
#    Unknown key type fallback (not EC, RSA, or DSA)
# ===========================================================================


@pytest.mark.unit
class TestKeysCoverage:
    """Cover unknown key type else branches in keys.py."""

    def test_load_private_key_raw_unknown_key_type(self, tmp_path: Path) -> None:
        """Unknown private key type -> class name in error (line 123)."""
        from flavor.packaging.keys import load_private_key_raw

        key_path = tmp_path / "unknown.key"
        key_path.write_bytes(b"fake")

        # Mock load_pem_private_key to return an unknown key type
        mock_key = MagicMock()
        mock_key.__class__.__name__ = "WeirdKey"

        with (
            patch("flavor.packaging.keys.serialization.load_pem_private_key", return_value=mock_key),
            pytest.raises(ValueError, match="Incompatible key type"),
        ):
            # isinstance checks for Ed25519, EC, RSA, DSA will all fail on MagicMock
            load_private_key_raw(key_path)

    def test_load_public_key_raw_unknown_key_type(self, tmp_path: Path) -> None:
        """Unknown public key type -> class name in error (line 171)."""
        from flavor.packaging.keys import load_public_key_raw

        key_path = tmp_path / "unknown_pub.key"
        key_path.write_bytes(b"fake")

        mock_key = MagicMock()
        mock_key.__class__.__name__ = "WeirdPubKey"

        with (
            patch("flavor.packaging.keys.serialization.load_pem_public_key", return_value=mock_key),
            pytest.raises(ValueError, match="Incompatible key type"),
        ):
            load_public_key_raw(key_path)


# ===========================================================================
# 8. packaging/orchestrator.py — lines 245, 331
#    Python builder with key files (no seed), JSON manifest key handling
# ===========================================================================


@pytest.mark.unit
class TestOrchestratorCoverage:
    """Cover key-handling branches in orchestrator."""

    def _make_orchestrator(self, tmp_path: Path, **kwargs: Any) -> Any:
        from flavor.packaging.orchestrator import PackagingOrchestrator

        defaults: dict[str, Any] = {
            "package_integrity_key_path": None,
            "public_key_path": None,
            "output_flavor_path": str(tmp_path / "out.psp"),
            "build_config": {},
            "manifest_dir": tmp_path,
            "package_name": "testpkg",
            "version": "1.0.0",
            "entry_point": "main:cli",
        }
        defaults.update(kwargs)
        return PackagingOrchestrator(**defaults)

    @patch("os.access", return_value=True)
    @patch("pathlib.Path.exists", return_value=True)
    @patch("flavor.psp.format_2025.pspf_builder.PSPFBuilder")
    @patch("flavor.packaging.orchestrator.PythonPackager")
    @patch("flavor.packaging.orchestrator.find_launcher_executable")
    @patch("flavor.packaging.orchestrator.PackagingOrchestrator._detect_launcher_type", return_value="rust")
    def test_python_builder_with_key_files(
        self,
        mock_detect: MagicMock,
        mock_find_launcher: MagicMock,
        mock_packager_cls: MagicMock,
        mock_pspf_cls: MagicMock,
        mock_path_exists: MagicMock,
        mock_access: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Python builder with private key file (no seed) loads keys (line 245)."""
        # Create fake key files
        priv_key = tmp_path / "private.key"
        pub_key = tmp_path / "public.key"
        priv_key.write_bytes(b"fake-private")
        pub_key.write_bytes(b"fake-public")

        orch = self._make_orchestrator(
            tmp_path,
            package_integrity_key_path=str(priv_key),
            public_key_path=str(pub_key),
        )

        mock_find_launcher.return_value = Path("/fake/launcher")
        mock_packager = mock_packager_cls.return_value
        mock_packager.prepare_artifacts.return_value = {
            "payload_dir": tmp_path / "payload",
            "python_tgz": tmp_path / "python.tgz",
        }
        (tmp_path / "python.tgz").touch()
        (tmp_path / "payload").mkdir(exist_ok=True)

        mock_builder = mock_pspf_cls.create.return_value
        mock_result = MagicMock(success=True)
        mock_builder.metadata.return_value = mock_builder
        mock_builder.add_slot.return_value = mock_builder
        mock_builder.with_options.return_value = mock_builder
        mock_builder.with_keys.return_value = mock_builder

        def create_file(output_path: Path) -> MagicMock:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"pkg" * 100)
            return mock_result

        mock_builder.build.side_effect = create_file

        with (
            patch("flavor.packaging.keys.load_private_key_raw", return_value=b"\x00" * 32),
            patch("flavor.packaging.keys.load_public_key_raw", return_value=b"\x01" * 32),
        ):
            orch.build_package()

        mock_builder.with_keys.assert_called_once()

    @patch("os.access", return_value=True)
    @patch("pathlib.Path.exists", return_value=True)
    @patch("flavor.packaging.orchestrator.find_launcher_executable")
    @patch("flavor.packaging.orchestrator.find_builder_executable")
    @patch("flavor.packaging.orchestrator.run")
    @patch("flavor.packaging.orchestrator.PackagingOrchestrator._detect_launcher_type", return_value="rust")
    def test_json_manifest_with_key_seed(
        self,
        mock_detect: MagicMock,
        mock_run: MagicMock,
        mock_find_builder: MagicMock,
        mock_find_launcher: MagicMock,
        mock_path_exists: MagicMock,
        mock_access: MagicMock,
        tmp_path: Path,
    ) -> None:
        """JSON manifest build with key_seed passes --key-seed (line 331)."""
        manifest = tmp_path / "manifest.json"
        manifest.write_text('{"package":{"name":"p","version":"1"}}')

        orch = self._make_orchestrator(
            tmp_path,
            manifest_type="json",
            json_manifest_path=manifest,
            builder_bin="/fake/builder",
            key_seed="test-seed-123",
        )

        mock_find_launcher.return_value = Path("/fake/launcher")
        mock_find_builder.return_value = Path("/fake/builder")

        orch.build_package()

        call_args = mock_run.call_args[0][0]
        assert "--key-seed" in call_args
        assert "test-seed-123" in call_args


# ===========================================================================
# 9. config/defaults.py — lines 20-21, 27-28
#    Platform branches for non-darwin, non-linux/win32
# ===========================================================================


@pytest.mark.unit
class TestConfigDefaultsCoverage:
    """Cover platform-specific branches in defaults.py."""

    def test_darwin_branch(self) -> None:
        """Darwin platform -> 16KB page size (lines 19-21)."""
        import importlib

        with patch("sys.platform", "darwin"):
            import flavor.config.defaults as mod

            importlib.reload(mod)
            assert mod.DEFAULT_PAGE_SIZE == 16384
            assert mod.DEFAULT_CACHE_LINE == 128

    def test_linux_branch(self) -> None:
        """Linux platform -> 4KB page size (lines 22-24)."""
        import importlib

        with patch("sys.platform", "linux"):
            import flavor.config.defaults as mod

            importlib.reload(mod)
            assert mod.DEFAULT_PAGE_SIZE == 4096
            assert mod.DEFAULT_CACHE_LINE == 64

    def test_fallback_branch(self) -> None:
        """Unknown platform -> fallback 4KB page size (lines 27-28)."""
        import importlib

        with patch("sys.platform", "freebsd"):
            import flavor.config.defaults as mod

            importlib.reload(mod)
            assert mod.DEFAULT_PAGE_SIZE == 4096
            assert mod.DEFAULT_CACHE_LINE == 64


# ===========================================================================
# 10. psp/format_2025/metadata/assembly.py — lines 39, 54, 63, 65-73
#     _launcher_candidate_names with is_windows, _semver_key no match,
#     _find_launcher_in_dir glob paths + windows patterns
# ===========================================================================


@pytest.mark.unit
class TestAssemblyCoverage:
    """Cover missing branches in metadata/assembly.py."""

    def test_launcher_candidate_names_windows(self) -> None:
        """is_windows=True prepends .exe variants (line 39)."""
        from flavor.psp.format_2025.metadata.assembly import _launcher_candidate_names

        names = _launcher_candidate_names("flavor-rs-launcher", "windows_amd64", is_windows=True)
        assert names[0] == "flavor-rs-launcher-windows_amd64.exe"
        assert names[1] == "flavor-rs-launcher.exe"
        assert "flavor-rs-launcher-windows_amd64" in names
        assert "flavor-rs-launcher" in names

    def test_semver_key_no_match(self) -> None:
        """Filename without version segment returns (0,) (line 54)."""
        from flavor.psp.format_2025.metadata.assembly import _semver_key

        result = _semver_key(Path("flavor-rs-launcher-darwin_arm64"))
        assert result == (0,)

    def test_semver_key_with_version(self) -> None:
        """Filename with version segment returns parsed tuple."""
        from flavor.psp.format_2025.metadata.assembly import _semver_key

        result = _semver_key(Path("flavor-rs-launcher-0.3.21-darwin_arm64"))
        assert result == (0, 3, 21)

    def test_find_launcher_in_dir_glob_fallback(self, tmp_path: Path) -> None:
        """No exact name match -> glob pattern fallback (lines 63, 65-73)."""
        from flavor.psp.format_2025.metadata.assembly import _find_launcher_in_dir

        # Create a versioned launcher file that won't match exact names
        versioned = tmp_path / "flavor-rs-launcher-0.3.21-linux_amd64"
        versioned.write_bytes(b"\x00")

        # Exact names won't match (no version in candidate names)
        names = ["flavor-rs-launcher-linux_amd64", "flavor-rs-launcher"]
        result = _find_launcher_in_dir(tmp_path, "flavor-rs-launcher", "linux_amd64", names, is_windows=False)
        assert result == versioned

    def test_find_launcher_in_dir_windows_glob(self, tmp_path: Path) -> None:
        """Windows glob pattern tries .exe first (lines 65-73, is_windows branch)."""
        from flavor.psp.format_2025.metadata.assembly import _find_launcher_in_dir

        # Create a versioned .exe launcher
        versioned_exe = tmp_path / "flavor-rs-launcher-0.3.21-windows_amd64.exe"
        versioned_exe.write_bytes(b"\x00")

        names = ["flavor-rs-launcher-windows_amd64.exe", "flavor-rs-launcher.exe"]
        result = _find_launcher_in_dir(tmp_path, "flavor-rs-launcher", "windows_amd64", names, is_windows=True)
        # Should find via exact name match first (if it exists) or glob
        # The exact name "flavor-rs-launcher-windows_amd64.exe" doesn't exist,
        # but the glob "flavor-rs-launcher-*-windows_amd64.exe" should match
        assert result == versioned_exe

    def test_find_launcher_in_dir_not_a_dir(self, tmp_path: Path) -> None:
        """Non-directory base_path with no exact match -> None."""
        from flavor.psp.format_2025.metadata.assembly import _find_launcher_in_dir

        fake_file = tmp_path / "not_a_dir"
        fake_file.write_text("x")
        result = _find_launcher_in_dir(fake_file, "launcher", "linux_amd64", ["launcher"], is_windows=False)
        assert result is None


# 🌶️📦🔚
