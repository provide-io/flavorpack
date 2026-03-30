#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Additional validation coverage tests for uncovered branches in validation.py."""

from pathlib import Path

import pytest

from flavor.psp.format_2025.slots import SlotMetadata


@pytest.mark.unit
class TestBuildSpecValidationExtra:
    """Extra validation tests covering uncovered branches."""

    def test_validate_build_options_page_aligned_without_mmap(self) -> None:
        """page_aligned=True with enable_mmap=False yields warning error."""
        from flavor.psp.format_2025.spec import BuildOptions, BuildSpec
        from flavor.psp.format_2025.validation import validate_build_options

        opts = BuildOptions.__new__(BuildOptions)
        object.__setattr__(opts, "compression", "gzip")
        object.__setattr__(opts, "compression_level", 6)
        object.__setattr__(opts, "enable_mmap", False)
        object.__setattr__(opts, "page_aligned", True)
        object.__setattr__(opts, "strip_binaries", False)
        object.__setattr__(opts, "launcher_bin", None)
        object.__setattr__(opts, "reproducible", False)
        object.__setattr__(opts, "verbose", False)
        spec = BuildSpec(options=opts)
        errors = validate_build_options(spec)
        assert any("page" in e.lower() or "⚠️" in e for e in errors)

    def test_validate_spec_empty_name_error(self) -> None:
        """Package name that is empty string yields error."""
        from flavor.psp.format_2025.spec import BuildSpec
        from flavor.psp.format_2025.validation import validate_spec

        spec = BuildSpec(metadata={"package": {"name": "  "}})
        errors = validate_spec(spec)
        assert any("name" in e.lower() or "📛" in e for e in errors)

    def test_validate_spec_invalid_format(self) -> None:
        """Metadata with wrong format string yields error."""
        from flavor.psp.format_2025.spec import BuildSpec
        from flavor.psp.format_2025.validation import validate_spec

        spec = BuildSpec(metadata={"name": "mypkg", "format": "PSPF/1999"})
        errors = validate_spec(spec)
        assert any("format" in e.lower() or "📐" in e for e in errors)

    def test_validate_key_config_nonexistent_key_path(self, tmp_path: Path) -> None:
        """Key path that does not exist yields error."""
        from pathlib import Path

        from flavor.psp.format_2025.spec import BuildSpec, KeyConfig
        from flavor.psp.format_2025.validation import validate_key_config

        nonexistent = Path(str(tmp_path)) / "no_such_dir"
        kc = KeyConfig(key_path=nonexistent)
        spec = BuildSpec(keys=kc)
        errors = validate_key_config(spec)
        assert any("key" in e.lower() or "🔑" in e for e in errors)

    def test_validate_key_config_file_path_not_dir(self, tmp_path: Path) -> None:
        """Key path that is a file (not directory) yields error."""
        from pathlib import Path

        from flavor.psp.format_2025.spec import BuildSpec, KeyConfig
        from flavor.psp.format_2025.validation import validate_key_config

        key_file = Path(str(tmp_path)) / "keyfile.pem"
        key_file.write_text("key")
        kc = KeyConfig(key_path=key_file)
        spec = BuildSpec(keys=kc)
        errors = validate_key_config(spec)
        assert any("key" in e.lower() or "🔑" in e for e in errors)


@pytest.mark.unit
class TestValidateSlotsAdditional:
    """Additional validate_slots coverage for uncovered error branches."""

    def _make_slot(self, **kwargs: object) -> SlotMetadata:
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tf:
            tf.write(b"x")
        defaults: dict[str, object] = {
            "index": 0,
            "id": "test",
            "source": tf.name,
            "target": "x",
            "size": 0,
            "checksum": "abc",
        }
        defaults.update(kwargs)
        return SlotMetadata(**defaults)  # type: ignore[arg-type]

    def test_nonexistent_source_path_yields_error(self) -> None:
        """validate_slots reports error for nonexistent source path."""
        from flavor.psp.format_2025.validation import validate_slots

        slot = self._make_slot()
        object.__setattr__(slot, "source", "/no/such/path/xyz123.txt")
        errors = validate_slots([slot])  # ty: ignore[invalid-argument-type]
        assert any("source" in e.lower() or "🔍" in e for e in errors)

    def test_invalid_purpose_yields_error(self) -> None:
        """validate_slots reports error for invalid purpose."""
        from flavor.psp.format_2025.validation import validate_slots

        slot = self._make_slot(purpose="payload")
        object.__setattr__(slot, "purpose", "bad_purpose")
        errors = validate_slots([slot])  # ty: ignore[invalid-argument-type]
        assert any("purpose" in e.lower() or "🎯" in e for e in errors)

    def test_invalid_lifecycle_yields_error(self) -> None:
        """validate_slots reports error for invalid lifecycle."""
        from flavor.psp.format_2025.validation import validate_slots

        slot = self._make_slot()
        object.__setattr__(slot, "lifecycle", "bad_lifecycle")
        errors = validate_slots([slot])  # ty: ignore[invalid-argument-type]
        assert any("lifecycle" in e.lower() or "♻️" in e for e in errors)

    def test_empty_slot_name_yields_error(self) -> None:
        """validate_slots reports error for slot with empty name."""
        from flavor.psp.format_2025.validation import validate_slots

        slot = self._make_slot(id="valid")
        object.__setattr__(slot, "id", "  ")
        errors = validate_slots([slot])  # ty: ignore[invalid-argument-type]
        assert any("empty" in e.lower() or "📝" in e for e in errors)

    def test_negative_size_yields_error(self) -> None:
        """validate_slots reports error for slot with negative size."""
        from flavor.psp.format_2025.validation import validate_slots

        slot = self._make_slot()
        object.__setattr__(slot, "size", -1)
        errors = validate_slots([slot])  # ty: ignore[invalid-argument-type]
        assert any("size" in e.lower() or "📏" in e for e in errors)

    def test_non_string_operations_yields_error(self) -> None:
        """validate_slots reports error when operations is not a string."""
        from flavor.psp.format_2025.validation import validate_slots

        slot = self._make_slot()
        object.__setattr__(slot, "operations", 42)
        errors = validate_slots([slot])  # ty: ignore[invalid-argument-type]
        assert any("operations" in e.lower() or "🗜️" in e for e in errors)


@pytest.mark.unit
class TestValidateMetadataExtra:
    """Extra validate_metadata tests for uncovered branches."""

    def test_validate_metadata_empty_version_yields_error(self) -> None:
        """version that is only whitespace yields error via validate_metadata."""

        # patch _validate_spec_fields directly since validate_metadata delegates to it
        # We need to reach line 74: version is truthy but strip is empty
        from flavor.psp.format_2025.spec import BuildSpec
        from flavor.psp.format_2025.validation import validate_spec

        spec = BuildSpec(metadata={"name": "mypkg", "version": "  "})
        errors = validate_spec(spec)
        assert any("version" in e.lower() or "🏷️" in e for e in errors)

    def test_validate_key_config_valid_dir_no_error(self, tmp_path: Path) -> None:
        """Key path that is a valid directory produces no error (covers branch 210->213)."""
        from pathlib import Path

        from flavor.psp.format_2025.spec import BuildSpec, KeyConfig
        from flavor.psp.format_2025.validation import validate_key_config

        valid_dir = Path(str(tmp_path)) / "keys"
        valid_dir.mkdir()
        kc = KeyConfig(key_path=valid_dir)
        spec = BuildSpec(keys=kc)
        errors = validate_key_config(spec)
        assert errors == []


# 🌶️📦🔚
