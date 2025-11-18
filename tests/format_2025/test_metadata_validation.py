#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test metadata validation for PSPF/2025 format."""

import pytest

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


# 🌶️📦🔚
