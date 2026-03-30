#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test metadata validation for PSPF/2025 format."""

from pathlib import Path

import pytest

from flavor.psp.format_2025.slots import SlotMetadata
from flavor.psp.format_2025.validation import extract_package_metadata
from flavor.psp.metadata.validators import validate_metadata


@pytest.mark.unit
class TestMetadataValidation:
    """Test validation of PSPF metadata structures."""

    def test_workenv_directories_validation(self) -> None:
        """Test workenv.directories paths must use {workenv} prefix."""
        # Valid metadata with {workenv} prefix
        valid_metadata = {
            "format": "PSPF/2025",
            "workenv": {
                "directories": [
                    {"path": "{workenv}/tmp", "mode": "0700"},
                    {"path": "{workenv}/var/log"},
                    {"path": "{workenv}/cache/{platform}"},
                ]
            },
        }

        # Should validate successfully
        assert validate_metadata(valid_metadata) is True

        # Invalid metadata without {workenv} prefix
        invalid_metadata = {
            "format": "PSPF/2025",
            "workenv": {
                "directories": [
                    {"path": "tmp"},  # Missing {workenv} prefix
                    {"path": "/var/log"},  # Absolute path without {workenv}
                ]
            },
        }

        # Should fail validation
        with pytest.raises(ValueError, match="must start with \\{workenv\\}"):
            validate_metadata(invalid_metadata)

    def test_workenv_env_validation(self) -> None:
        """Test workenv.env values can use placeholders."""
        metadata = {
            "format": "PSPF/2025",
            "workenv": {
                "env": {
                    "CACHE": "{workenv}/cache/{platform}",  # Valid placeholders
                    "TMP": "/tmp",  # Absolute paths allowed in env
                    "PLATFORM_DIR": "/opt/{os}/{arch}",  # Platform placeholders
                    "APP_HOME": "{workenv}/app",
                }
            },
        }

        # Should validate successfully
        assert validate_metadata(metadata) is True

    def test_workenv_umask_validation(self) -> None:
        """Test workenv.umask validation."""
        # Valid umask values
        valid_umasks = ["0077", "0022", "0002", "077", "22"]

        for umask in valid_umasks:
            metadata = {"format": "PSPF/2025", "workenv": {"umask": umask}}
            assert validate_metadata(metadata) is True

        # Invalid umask values
        invalid_umasks = ["invalid", "9999", "-077", "0888"]

        for umask in invalid_umasks:
            metadata = {"format": "PSPF/2025", "workenv": {"umask": umask}}
            with pytest.raises(ValueError, match="Invalid umask"):
                validate_metadata(metadata)

    def test_execution_env_renamed(self) -> None:
        """Test that execution.environment was renamed to execution.env."""
        # Old format (should fail)
        old_metadata = {
            "format": "PSPF/2025",
            "execution": {
                "environment": {  # Old name
                    "PATH": "/usr/bin"
                }
            },
        }

        with pytest.raises(ValueError, match="Use 'env' instead of 'environment'"):
            validate_metadata(old_metadata)

        # New format (should pass)
        new_metadata = {
            "format": "PSPF/2025",
            "execution": {
                "env": {  # New name
                    "PATH": "/usr/bin"
                }
            },
        }

        assert validate_metadata(new_metadata) is True

    def test_runtime_env_operations(self) -> None:
        """Test runtime.env security operations validation."""
        metadata = {
            "format": "PSPF/2025",
            "runtime": {
                "env": {
                    "unset": ["SENSITIVE_VAR", "API_KEY"],  # Remove vars
                    "pass": ["PATH", "HOME", "USER"],  # Whitelist vars
                    "map": {  # Rename vars
                        "OLD_VAR": "NEW_VAR",
                        "LEGACY_PATH": "APP_PATH",
                    },
                    "set": {  # Set/override vars
                        "SAFE_MODE": "true",
                        "LOG_LEVEL": "info",
                    },
                }
            },
        }

        assert validate_metadata(metadata) is True

    def test_directory_mode_validation(self) -> None:
        """Test validation of directory mode values."""
        # Valid modes
        valid_modes = ["0700", "0755", "0750", "0777", "700", "755"]

        for mode in valid_modes:
            metadata = {
                "format": "PSPF/2025",
                "workenv": {"directories": [{"path": "{workenv}/test", "mode": mode}]},
            }
            assert validate_metadata(metadata) is True

        # Invalid modes
        invalid_modes = ["not-a-mode", "9999", "-755", "0888", "abc"]

        for mode in invalid_modes:
            metadata = {
                "format": "PSPF/2025",
                "workenv": {"directories": [{"path": "{workenv}/test", "mode": mode}]},
            }
            with pytest.raises(ValueError, match="Invalid mode"):
                validate_metadata(metadata)

    def test_complete_metadata_structure(self) -> None:
        """Test complete metadata structure with all sections."""
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "test-package", "version": "1.0.0"},
            "runtime": {
                "env": {
                    "unset": ["DANGEROUS_VAR"],
                    "pass": ["PATH"],
                    "map": {"OLD": "NEW"},
                    "set": {"SAFE": "true"},
                }
            },
            "workenv": {
                "umask": "0077",
                "directories": [
                    {"path": "{workenv}/tmp", "mode": "0700"},
                    {"path": "{workenv}/var", "mode": "0755"},
                    {"path": "{workenv}/cache/{platform}"},
                ],
                "env": {
                    "TMPDIR": "{workenv}/tmp",
                    "XDG_CACHE_HOME": "{workenv}/cache",
                    "PLATFORM_CACHE": "{workenv}/cache/{os}_{arch}",
                },
            },
            "execution": {
                "command": "python",
                "args": ["-m", "app"],
                "env": {"APP_MODE": "production", "APP_HOME": "{workenv}/app"},
            },
        }

        assert validate_metadata(metadata) is True

    def test_placeholder_validation_in_paths(self) -> None:
        """Test that placeholders are validated in directory paths."""
        # Valid placeholders
        valid_metadata = {
            "format": "PSPF/2025",
            "workenv": {
                "directories": [
                    {"path": "{workenv}/cache/{os}"},
                    {"path": "{workenv}/lib/{arch}"},
                    {"path": "{workenv}/data/{platform}"},
                    {"path": "{workenv}/mixed/{os}/lib/{arch}"},
                ]
            },
        }

        assert validate_metadata(valid_metadata) is True

        # Invalid placeholders (should be left as-is but still validate)
        metadata_with_unknown = {
            "format": "PSPF/2025",
            "workenv": {
                "directories": [
                    {"path": "{workenv}/{unknown}/path"}  # Unknown placeholder
                ]
            },
        }

        # Should still validate (unknown placeholders are left as-is)
        assert validate_metadata(metadata_with_unknown) is True

    def test_missing_required_fields(self) -> None:
        """Test validation fails for missing required fields."""
        # Missing format
        metadata_no_format = {"workenv": {"directories": [{"path": "{workenv}/tmp"}]}}

        with pytest.raises(ValueError, match="Missing required field: format"):
            validate_metadata(metadata_no_format)

        # Wrong format version
        metadata_wrong_format = {
            "format": "PSPF/2024",  # Wrong version
            "workenv": {"directories": [{"path": "{workenv}/tmp"}]},
        }

        with pytest.raises(ValueError, match="Unsupported format"):
            validate_metadata(metadata_wrong_format)

    def test_empty_workenv_section(self) -> None:
        """Test that empty workenv section is valid."""
        metadata = {
            "format": "PSPF/2025",
            "workenv": {},  # Empty but present
        }

        assert validate_metadata(metadata) is True

        # No workenv section at all
        metadata_no_workenv = {"format": "PSPF/2025"}

        assert validate_metadata(metadata_no_workenv) is True


@pytest.mark.unit
class TestBuildSpecValidation:
    """Tests for validate_spec, validate_slots, validate_key_config, validate_build_options."""

    def _make_slot(self, tmp_path: Path | None = None, **kwargs: object) -> SlotMetadata:
        from flavor.psp.format_2025.slots import SlotMetadata

        # Create a real temp file for source path (validator checks existence)
        if tmp_path is not None:
            src = tmp_path / "slot_src.txt"
            src.write_text("x")
            source = str(src)
        else:
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tf:
                tf.write(b"x")
            source = tf.name

        defaults: dict[str, object] = {
            "index": 0,
            "id": "test",
            "source": source,
            "target": "x",
            "size": 0,
            "checksum": "abc",
        }
        defaults.update(kwargs)
        return SlotMetadata(**defaults)  # type: ignore[arg-type]

    def test_valid_spec_no_errors(self, tmp_path: Path) -> None:
        """A valid spec with metadata and slot returns no errors."""
        from flavor.psp.format_2025.spec import BuildSpec
        from flavor.psp.format_2025.validation import validate_spec

        slot = self._make_slot(tmp_path=tmp_path)
        spec = BuildSpec(
            metadata={"package": {"name": "mypkg"}},
            slots=[slot],  # ty: ignore[invalid-argument-type]
        )
        errors = validate_spec(spec)
        assert errors == []

    def test_empty_spec_requires_name(self) -> None:
        """Spec without package name has errors."""
        from flavor.psp.format_2025.spec import BuildSpec
        from flavor.psp.format_2025.validation import validate_spec

        spec = BuildSpec(metadata={"version": "1.0"})
        errors = validate_spec(spec)
        assert any("name" in e.lower() or "📛" in e for e in errors)

    def test_spec_without_slots_errors(self) -> None:
        """Spec with name but no slots has an error."""
        from flavor.psp.format_2025.spec import BuildSpec
        from flavor.psp.format_2025.validation import validate_spec

        spec = BuildSpec(metadata={"name": "mypkg"})
        errors = validate_spec(spec)
        assert any("slot" in e.lower() or "📦" in e for e in errors)

    def test_allow_empty_suppresses_slot_error(self) -> None:
        """allow_empty=True suppresses the no-slots error."""
        from flavor.psp.format_2025.spec import BuildSpec
        from flavor.psp.format_2025.validation import validate_spec

        spec = BuildSpec(metadata={"name": "mypkg", "allow_empty": True})
        errors = validate_spec(spec)
        # Name error should be present but no slot count error
        assert not any("slot" in e.lower() for e in errors)

    def test_validate_slots_empty_is_valid(self) -> None:
        """Empty slot list passes validation."""
        from flavor.psp.format_2025.validation import validate_slots

        errors = validate_slots([])
        assert errors == []

    def test_validate_slots_duplicate_index(self) -> None:
        """Duplicate slot indices cause an error."""
        from flavor.psp.format_2025.validation import validate_slots

        slot0a = self._make_slot(index=0, id="a")
        slot0b = self._make_slot(index=0, id="b")
        errors = validate_slots([slot0a, slot0b])  # ty: ignore[invalid-argument-type]
        assert any("duplicate" in e.lower() or "🔢" in e for e in errors)

    def test_validate_slots_duplicate_name(self) -> None:
        """Duplicate slot names cause an error."""
        from flavor.psp.format_2025.validation import validate_slots

        slot0 = self._make_slot(index=0, id="same")
        slot1 = self._make_slot(index=1, id="same")
        errors = validate_slots([slot0, slot1])  # ty: ignore[invalid-argument-type]
        assert any("duplicate" in e.lower() or "📝" in e for e in errors)

    def test_validate_key_config_both_keys_required(self) -> None:
        """Providing only private key without public key yields error."""
        from flavor.psp.format_2025.spec import BuildSpec, KeyConfig
        from flavor.psp.format_2025.validation import validate_key_config

        kc = KeyConfig(private_key=b"\x01" * 32)
        spec = BuildSpec(keys=kc)
        errors = validate_key_config(spec)
        assert any("key" in e.lower() or "🔑" in e for e in errors)

    def test_validate_key_config_wrong_key_size(self) -> None:
        """Keys of wrong size yield errors."""
        from flavor.psp.format_2025.spec import BuildSpec, KeyConfig
        from flavor.psp.format_2025.validation import validate_key_config

        kc = KeyConfig(private_key=b"\x01" * 16, public_key=b"\x02" * 16)
        spec = BuildSpec(keys=kc)
        errors = validate_key_config(spec)
        assert any("32 bytes" in e or "🔑" in e for e in errors)

    def test_validate_key_config_valid_keys(self) -> None:
        """Valid 32-byte explicit keys produce no errors."""
        from flavor.psp.format_2025.spec import BuildSpec, KeyConfig
        from flavor.psp.format_2025.validation import validate_key_config

        kc = KeyConfig(private_key=b"\x01" * 32, public_key=b"\x02" * 32)
        spec = BuildSpec(keys=kc)
        errors = validate_key_config(spec)
        assert errors == []

    def test_validate_build_options_invalid_level(self) -> None:
        """Compression level out of [0,9] yields error."""
        from flavor.psp.format_2025.spec import BuildOptions, BuildSpec
        from flavor.psp.format_2025.validation import validate_build_options

        opts = BuildOptions.__new__(BuildOptions)
        object.__setattr__(opts, "compression", "gzip")
        object.__setattr__(opts, "compression_level", 10)
        object.__setattr__(opts, "enable_mmap", True)
        object.__setattr__(opts, "page_aligned", True)
        object.__setattr__(opts, "strip_binaries", False)
        object.__setattr__(opts, "launcher_bin", None)
        object.__setattr__(opts, "reproducible", False)
        object.__setattr__(opts, "verbose", False)
        spec = BuildSpec(options=opts)
        errors = validate_build_options(spec)
        assert any("level" in e.lower() or "🗜️" in e for e in errors)

    def test_validate_complete_combines_all(self) -> None:
        """validate_complete runs all checks and combines errors."""
        from flavor.psp.format_2025.spec import BuildSpec
        from flavor.psp.format_2025.validation import validate_complete

        spec = BuildSpec()  # Empty spec - should have errors
        errors = validate_complete(spec)
        assert len(errors) > 0


@pytest.mark.unit
class TestExtractPackageMetadata:
    """Regression tests for extract_package_metadata normalization."""

    def test_extract_prefers_nested_package_dict(self) -> None:
        """extract_package_metadata must prefer nested package dict over top-level keys."""
        meta = {"package": {"name": "mypkg", "version": "1.0"}, "name": "ignored"}
        result = extract_package_metadata(meta)
        assert result == {"name": "mypkg", "version": "1.0"}

    def test_extract_falls_back_to_toplevel(self) -> None:
        """extract_package_metadata falls back to top-level keys when no nested package dict."""
        meta = {"name": "fallback", "version": "2.0"}
        result = extract_package_metadata(meta)
        assert result["name"] == "fallback"
        assert result["version"] == "2.0"

    def test_extract_returns_empty_dict_for_no_identity(self) -> None:
        """extract_package_metadata returns empty dict when no identity fields present."""
        meta = {"execution": {"command": "echo"}}
        result = extract_package_metadata(meta)
        assert result == {}


# 🌶️📦🔚
