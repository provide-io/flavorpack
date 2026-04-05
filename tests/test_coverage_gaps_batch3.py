#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Coverage gap tests — batch 3 (small gaps, 1-3 lines each)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. binary_loader.py lines 154-156 — Rust binary already exists, skip
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBinaryLoaderRustSkipExisting:
    """Cover _build_rust_helpers skip when binary already exists."""

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_rust_helper_skipped_when_exists_and_not_force(self, mock_platform: Mock, tmp_path: Path) -> None:
        from flavor.helpers.binary_loader import BinaryLoader

        mock_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        rust_src = tmp_path / "rust_src"
        rust_src.mkdir()
        mock_manager.rust_src_dir = rust_src

        helpers_bin = tmp_path / "bin"
        helpers_bin.mkdir()
        mock_manager.helpers_bin = helpers_bin

        # Pre-create binaries so they exist
        for component in ("launcher", "builder"):
            (helpers_bin / f"flavor-rs-{component}-linux_x86_64").write_bytes(b"x")

        loader = BinaryLoader(mock_manager)
        result = loader._build_rust_helpers(force=False)

        assert len(result) == 2
        for p in result:
            assert p.exists()


# ---------------------------------------------------------------------------
# 2. slot_builder.py line 287 — trace log: no pyproject.toml
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSlotBuilderNoProjectToml:
    """Cover resolve_transitive_dependencies when pyproject.toml is missing."""

    def test_no_pyproject_toml_trace_log(self, tmp_path: Path) -> None:
        from flavor.packaging.python.slot_builder import PythonSlotBuilder

        dep_path = tmp_path / "some_dep"
        dep_path.mkdir()
        # No pyproject.toml created

        builder = PythonSlotBuilder.__new__(PythonSlotBuilder)
        result = builder.resolve_transitive_dependencies(dep_path, set(), 0)

        # dep_path is still added in post-order
        assert dep_path in result


# ---------------------------------------------------------------------------
# 3. uv_manager.py line 588 — manylinux2014_x86_64 platform tag
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUvManagerLinuxPlatformTag:
    """Cover the linux amd64 manylinux2014 branch."""

    @patch("flavor.packaging.python.uv_manager.get_os_name", return_value="linux")
    @patch("flavor.packaging.python.uv_manager.get_arch_name", return_value="amd64")
    @patch("flavor.packaging.python.uv_manager.run")
    def test_download_uv_linux_amd64_platform_tag(
        self, mock_run: Mock, _arch: Mock, _os: Mock, tmp_path: Path
    ) -> None:
        from flavor.packaging.python.uv_manager import UVManager

        mock_run.return_value = Mock(returncode=0)

        manager = UVManager()
        # download_uv_binary returns None when no wheel is found, but
        # the download_cmd should include the manylinux2014 platform tag.
        manager.download_uv_binary(dest_dir=tmp_path, python_exe=Path("/usr/bin/python3"))

        # Verify the download command included the manylinux platform tag
        assert mock_run.called
        cmd_args = mock_run.call_args[0][0]
        cmd_str = " ".join(str(a) for a in cmd_args)
        assert "manylinux2014_x86_64" in cmd_str


# ---------------------------------------------------------------------------
# 4. dist_manager.py line 165 — force_reinstall flag
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDistManagerForceReinstall:
    """Cover force_reinstall branch in install_wheels_to_environment."""

    @patch("flavor.packaging.python.dist_manager.run")
    def test_install_wheels_force_reinstall(self, mock_run: Mock, tmp_path: Path) -> None:
        from flavor.packaging.python.dist_manager import PythonDistManager

        mock_run.return_value = Mock(returncode=0)

        mgr = PythonDistManager(python_version="3.11")

        wheel = tmp_path / "fake-1.0-py3-none-any.whl"
        wheel.write_bytes(b"PK")

        venv_python = Path("/usr/bin/python3")

        mgr.install_wheels_to_environment(
            venv_python=venv_python,
            wheel_files=[wheel],
            force_reinstall=True,
        )

        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "--force-reinstall" in cmd


# ---------------------------------------------------------------------------
# 5a. backends.py lines 202-203 — posix_fadvise AttributeError
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMMapBackendPrefetchFallback:
    """Cover posix_fadvise AttributeError catch in MMapBackend.prefetch."""

    def test_prefetch_fadvise_attribute_error(self, tmp_path: Path) -> None:
        """Trigger the AttributeError catch by making posix_fadvise raise."""
        from flavor.psp.format_2025.backends import MMapBackend

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"\x00" * 8192)

        backend = MMapBackend()
        backend.open(test_file)
        try:
            # On macOS, os doesn't have posix_fadvise, so the hasattr check
            # fails and we go to else branch. We need to mock hasattr to
            # pretend we have it, then have it raise AttributeError.
            real_hasattr = hasattr

            def fake_hasattr(obj: object, name: str) -> bool:
                if obj is os and name in ("posix_fadvise", "POSIX_FADV_WILLNEED"):
                    return True
                return real_hasattr(obj, name)

            fake_fadvise = Mock(side_effect=AttributeError("not available"))

            with (
                patch("flavor.psp.format_2025.backends.hasattr", fake_hasattr),
                patch.object(os, "posix_fadvise", fake_fadvise, create=True),
                patch.object(os, "POSIX_FADV_WILLNEED", 3, create=True),
            ):
                backend.prefetch(0, 4096)
        finally:
            backend.close()


# ---------------------------------------------------------------------------
# 5b. backends.py line 357 — StreamBackend.read_slot empty chunk
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStreamBackendReadSlotEmptyChunk:
    """Cover StreamBackend.read_slot raising RuntimeError on empty read."""

    def test_read_slot_empty_chunk_raises(self, tmp_path: Path) -> None:
        from flavor.psp.format_2025.backends import StreamBackend
        from flavor.psp.format_2025.slots import SlotDescriptor

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"\x00" * 100)

        backend = StreamBackend(chunk_size=32)
        backend.open(test_file)
        try:
            descriptor = SlotDescriptor(
                id=0,
                offset=0,
                size=50,
                checksum=0,
            )
            with (
                patch.object(backend, "read_at", return_value=b""),
                pytest.raises(RuntimeError, match="empty read"),
            ):
                backend.read_slot(descriptor)
        finally:
            backend.close()


# ---------------------------------------------------------------------------
# 6. pspf_builder.py line 107 — invalid data type in add_slot
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPSPFBuilderInvalidDataType:
    """Cover add_slot raising BuildError for invalid data type."""

    def test_add_slot_invalid_data_type_raises(self) -> None:
        from flavor.psp.format_2025.pspf_builder import PSPFBuilder

        builder = PSPFBuilder()
        with pytest.raises(Exception, match="Invalid data type"):
            builder.add_slot("test", data=12345)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 7. validation.py line 135 — source path exists but not file or dir
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationSourceNotFileOrDir:
    """Cover validate_slots for source path that exists but is not file/dir."""

    def test_source_exists_but_not_file_or_dir(self, tmp_path: Path) -> None:
        from flavor.psp.format_2025.slots import SlotMetadata
        from flavor.psp.format_2025.validation import validate_slots

        fake_path = tmp_path / "special_device"
        fake_path.write_bytes(b"x")  # create it so it exists

        slot = SlotMetadata(
            index=0,
            id="test",
            source=str(fake_path),
            target="x",
            size=0,
            checksum="abc",
        )

        # Mock is_file and is_dir to both return False
        with (
            patch.object(Path, "is_file", return_value=False),
            patch.object(Path, "is_dir", return_value=False),
        ):
            errors = validate_slots([slot])

        assert any("not a file or directory" in e for e in errors)


# ---------------------------------------------------------------------------
# 8. policy.py lines 160, 168 — warnings printed and warning count shown
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPolicyCheckWarnings:
    """Cover policy check printing warnings (lines 160 and 168)."""

    def test_policy_check_with_warnings(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from flavor.cli import cli
        from flavor.config.policy import OperatorPolicy

        pkg = tmp_path / "test.psp"
        pkg.write_bytes(b"fake")

        mock_index = Mock()
        mock_index.build_timestamp = 0
        mock_index.public_key = b"\x00" * 32
        mock_index.attestation_key_fp = b"\x00" * 64

        mock_reader = Mock()
        mock_reader.__enter__ = Mock(return_value=mock_reader)
        mock_reader.__exit__ = Mock(return_value=False)
        mock_reader.read_metadata.return_value = {}
        mock_reader.read_index.return_value = mock_index

        runner = CliRunner()
        with (
            patch("flavor.psp.format_2025.reader.PSPFReader", return_value=mock_reader),
            patch(
                "flavor.commands.policy.load_operator_policy",
                return_value=OperatorPolicy(),
            ),
            patch(
                "flavor.commands.policy.enforce_policy",
                return_value=["test warning 1", "test warning 2"],
            ),
        ):
            result = runner.invoke(cli, ["policy", "check", str(pkg)])

        assert result.exit_code == 0
        assert "test warning 1" in result.output
        assert "test warning 2" in result.output
        assert "warnings: 2" in result.output


# ---------------------------------------------------------------------------
# 9. workenv.py line 187 — extraction incomplete
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWorkenvInspectIncompleteExtraction:
    """Cover extraction incomplete branch in workenv inspect."""

    def test_inspect_incomplete_extraction(self) -> None:
        from click.testing import CliRunner

        from flavor.commands.workenv import workenv_group

        runner = CliRunner()
        info = {
            "name": "mypkg",
            "exists": True,
            "content_dir": "/cache/mypkg",
            "metadata_type": "instance",
            "metadata_dir": None,
            "checksum": None,
            "extraction_complete": False,
            "package_info": {"name": "mypkg"},
        }
        with patch("flavor.cache.CacheManager") as MockMgr:
            MockMgr.return_value.inspect_workenv.return_value = info
            result = runner.invoke(workenv_group, ["inspect", "mypkg"])

        assert result.exit_code == 0
        assert "Incomplete" in result.output


# ---------------------------------------------------------------------------
# 12. writer.py branch 118->122 — no slots; branch 188->191 — already aligned
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriterBranches:
    """Cover writer.py branch gaps."""

    def test_write_package_no_slots(self, tmp_path: Path) -> None:
        """write_package with empty slots list skips _write_slots."""
        from flavor.psp.format_2025.writer import write_package

        output = tmp_path / "test.psp"
        launcher_data = b"\x00" * 64

        mock_spec = Mock()
        mock_spec.metadata = {"name": "test", "version": "1.0"}
        mock_spec.slots = []
        mock_spec.options = Mock(page_aligned=False)

        mock_index = Mock()
        mock_index.launcher_size = 0
        mock_index.integrity_signature = b""

        private_key = b"\x00" * 32
        public_key = b"\x00" * 32

        with (
            patch("flavor.psp.format_2025.writer._load_launcher", return_value=launcher_data),
            patch(
                "flavor.psp.format_2025.writer.process_launcher_for_pspf",
                return_value=launcher_data,
            ),
            patch("flavor.psp.format_2025.writer.assemble_metadata", return_value={"test": True}),
            patch("flavor.psp.format_2025.writer._create_launcher_info", return_value={}),
            patch("flavor.psp.format_2025.writer._get_or_create_signer") as mock_signer,
            patch("flavor.psp.format_2025.writer._write_metadata"),
            patch("flavor.psp.format_2025.writer._write_trailer"),
            patch("flavor.psp.format_2025.writer.set_file_permissions"),
            patch("flavor.psp.format_2025.writer.clear_signer_cache"),
        ):
            mock_signer.return_value.sign.return_value = b"\x00" * 64
            result = write_package(
                spec=mock_spec,
                output_path=output,
                slots=[],
                index=mock_index,
                private_key=private_key,
                public_key=public_key,
            )
            assert result >= 0

    def test_write_slots_page_aligned_already_aligned(self, tmp_path: Path) -> None:
        """_write_slots with page_aligned where offset already at page boundary."""
        from flavor.psp.format_2025.writer import _write_slots

        test_file = tmp_path / "test.bin"

        mock_spec = Mock()
        mock_spec.options = Mock(page_aligned=True)

        mock_index = Mock()

        # Create a real-ish PreparedSlot mock with proper int checksum
        data = b"hello"
        hash_bytes = hashlib.sha256(data).digest()[:8]
        checksum_int = int.from_bytes(hash_bytes, byteorder="little")

        mock_slot = Mock()
        mock_slot.get_data_to_write.return_value = data
        mock_slot.data = data  # uncompressed data
        mock_slot.operations = 0
        mock_slot.metadata = Mock()
        mock_slot.metadata.id = "test"
        mock_slot.metadata.purpose = "data"
        mock_slot.metadata.lifecycle = "runtime"
        mock_slot.metadata.permissions = "0644"
        mock_slot.checksum = checksum_int

        with test_file.open("wb") as f:
            # Write enough to place us somewhere
            f.write(b"\x00" * 4096)
            # Mock align functions to return current position (already aligned)
            with (
                patch(
                    "flavor.psp.format_2025.writer.align_offset",
                    return_value=f.tell(),
                ),
                patch(
                    "flavor.psp.format_2025.writer.align_to_page",
                    return_value=f.tell() + 32,  # after slot table
                ),
                patch("flavor.psp.format_2025.writer.DEFAULT_SLOT_DESCRIPTOR_SIZE", 32),
            ):
                _write_slots(f, [mock_slot], mock_spec, mock_index)


# 🌶️📦🔚
