#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for psp.metadata.paths utility functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from flavor.psp.metadata.paths import (
    expand_workenv_path,
    make_relative_to_workenv,
    parse_mode,
    substitute_placeholders,
    validate_metadata_dict,
    validate_metadata_list,
    validate_metadata_path,
)


@pytest.mark.unit
class TestValidateMetadataPath:
    """Tests for validate_metadata_path."""

    def test_empty_path_returned_unchanged(self) -> None:
        """Empty string is returned as-is."""
        assert validate_metadata_path("") == ""

    def test_placeholder_only_returned_unchanged(self) -> None:
        """{version} placeholder (no slash) returned unchanged."""
        assert validate_metadata_path("{version}") == "{version}"
        assert validate_metadata_path("{package_name}") == "{package_name}"

    def test_absolute_path_returned_unchanged(self) -> None:
        """Absolute paths are kept as-is."""
        assert validate_metadata_path("/usr/bin/python") == "/usr/bin/python"

    def test_workenv_prefix_respected(self) -> None:
        """{workenv}-prefixed paths are returned unchanged."""
        assert validate_metadata_path("{workenv}/bin/python") == "{workenv}/bin/python"

    def test_workenv_literal_prefix_replaced(self) -> None:
        """Literal 'workenv/' prefix is replaced with {workenv}/."""
        result = validate_metadata_path("workenv/bin/python")
        assert result == "{workenv}/bin/python"

    def test_dot_becomes_workenv(self) -> None:
        """'.' maps to {workenv}."""
        assert validate_metadata_path(".") == "{workenv}"

    def test_dot_slash_becomes_workenv(self) -> None:
        """'./' maps to {workenv}."""
        assert validate_metadata_path("./") == "{workenv}"

    def test_relative_dot_path(self) -> None:
        """'./bin/python' maps to {workenv}/bin/python."""
        assert validate_metadata_path("./bin/python") == "{workenv}/bin/python"

    def test_bare_relative_path_prefixed(self) -> None:
        """Plain relative path gets {workenv}/ prefix."""
        assert validate_metadata_path("bin/python") == "{workenv}/bin/python"

    def test_double_slashes_collapsed(self) -> None:
        """Double slashes are collapsed to single."""
        result = validate_metadata_path("{workenv}//bin//python")
        assert "//" not in result

    def test_workenv_trailing_slash_normalized(self) -> None:
        """{workenv}/ is normalized to {workenv}."""
        assert validate_metadata_path("{workenv}/") == "{workenv}"

    @pytest.mark.parametrize(
        "inp,expected",
        [
            (".", "{workenv}"),
            ("./", "{workenv}"),
            ("./foo", "{workenv}/foo"),
            ("workenv/foo", "{workenv}/foo"),
            ("/abs/path", "/abs/path"),
            ("{version}", "{version}"),
            ("", ""),
        ],
    )
    def test_parametrized_conversions(self, inp: str, expected: str) -> None:
        """Parametrized round-trip checks for validate_metadata_path."""
        assert validate_metadata_path(inp) == expected


@pytest.mark.unit
class TestValidateMetadataDict:
    """Tests for validate_metadata_dict."""

    def test_path_key_is_normalized(self) -> None:
        """Fields in PATH_KEYS are validated."""
        result = validate_metadata_dict({"command": "bin/app"})
        assert result["command"] == "{workenv}/bin/app"

    def test_non_path_key_unchanged(self) -> None:
        """Non-path fields are kept as-is."""
        result = validate_metadata_dict({"name": "mypackage"})
        assert result["name"] == "mypackage"

    def test_nested_dict_recurses(self) -> None:
        """Nested dicts are recursed into."""
        result = validate_metadata_dict({"execution": {"command": "bin/app"}})
        assert result["execution"]["command"] == "{workenv}/bin/app"

    def test_workenv_directories_kept_as_is(self) -> None:
        """workenv.directories are not path-normalized (they're relative specs)."""
        dirs = [{"path": "{workenv}/logs"}]
        result = validate_metadata_dict({"workenv": {"directories": dirs}})
        assert result["workenv"]["directories"] == dirs

    def test_workenv_env_values_normalized(self) -> None:
        """workenv.env values are recursed via validate_metadata_dict."""
        # "command" is in PATH_KEYS so it gets normalized even inside env
        result = validate_metadata_dict({"workenv": {"env": {"command": "bin/app"}}})
        assert result["workenv"]["env"]["command"] == "{workenv}/bin/app"

    def test_list_of_dicts_recurses(self) -> None:
        """Lists containing dicts are recursed into."""
        result = validate_metadata_dict({"slots": [{"command": "bin/app"}]})
        assert result["slots"][0]["command"] == "{workenv}/bin/app"

    def test_enumerate_pattern_path_normalized(self) -> None:
        """'enumerate' key with 'path' sub-key gets path normalized."""
        result = validate_metadata_dict({"enumerate": {"path": "bin/tools", "other": "x"}})
        assert result["enumerate"]["path"] == "{workenv}/bin/tools"
        assert result["enumerate"]["other"] == "x"

    def test_source_key_normalized(self) -> None:
        """'source' is in PATH_KEYS and gets normalized."""
        result = validate_metadata_dict({"source": "data/file.txt"})
        assert result["source"] == "{workenv}/data/file.txt"


@pytest.mark.unit
class TestValidateMetadataList:
    """Tests for validate_metadata_list."""

    def test_dict_items_recursed(self) -> None:
        """Dict items in a list are recursed into."""
        items = [{"command": "bin/app"}]
        result = validate_metadata_list(items)
        assert result[0]["command"] == "{workenv}/bin/app"

    def test_string_paths_normalized_when_flag_set(self) -> None:
        """String items in a path list are normalized."""
        result = validate_metadata_list(["bin/app", "lib/foo"], is_path_list=True)
        assert result[0] == "{workenv}/bin/app"
        assert result[1] == "{workenv}/lib/foo"

    def test_string_items_kept_when_not_path_list(self) -> None:
        """String items are kept as-is when is_path_list=False."""
        result = validate_metadata_list(["hello", "world"], is_path_list=False)
        assert result == ["hello", "world"]

    def test_mixed_list(self) -> None:
        """Mixed list: dicts recurse, non-path strings stay."""
        result = validate_metadata_list([{"target": "bin/x"}, 42, "raw"], is_path_list=False)
        assert result[0]["target"] == "{workenv}/bin/x"
        assert result[1] == 42
        assert result[2] == "raw"


@pytest.mark.unit
class TestExpandWorkenvPath:
    """Tests for expand_workenv_path."""

    def test_workenv_placeholder_expanded(self) -> None:
        """{workenv} in path is replaced with actual dir."""
        result = expand_workenv_path("{workenv}/bin/python", "/tmp/work123")
        assert result == "/tmp/work123/bin/python"

    def test_no_placeholder_unchanged(self) -> None:
        """Path without {workenv} is returned unchanged."""
        result = expand_workenv_path("/usr/bin/python", "/tmp/work")
        assert result == "/usr/bin/python"

    def test_workenv_only(self) -> None:
        """Just {workenv} expands to the dir itself."""
        result = expand_workenv_path("{workenv}", "/tmp/work")
        assert result == "/tmp/work"


@pytest.mark.unit
class TestMakeRelativeToWorkenv:
    """Tests for make_relative_to_workenv."""

    def test_path_under_workenv_relativized(self) -> None:
        """Path inside workenv gets {workenv} prefix."""
        result = make_relative_to_workenv("/tmp/build/bin/python", "/tmp/build")
        assert result == "{workenv}/bin/python"

    def test_workenv_root_returns_workenv(self) -> None:
        """Path equal to workenv returns {workenv}."""
        result = make_relative_to_workenv("/tmp/build", "/tmp/build")
        assert result == "{workenv}"

    def test_path_outside_workenv_falls_back(self) -> None:
        """Path not under workenv falls back to validate_metadata_path."""
        result = make_relative_to_workenv("/other/path/bin", "/tmp/build")
        # Falls back to validate_metadata_path — absolute so unchanged
        assert result == "/other/path/bin"


@pytest.mark.unit
class TestSubstitutePlaceholders:
    """Tests for substitute_placeholders."""

    def test_empty_path_returned(self) -> None:
        """Empty path returns empty."""
        assert substitute_placeholders("", Path("/work")) == ""

    def test_workenv_substituted(self) -> None:
        """{workenv} is replaced with the workenv path."""
        result = substitute_placeholders("{workenv}/bin/app", Path("/tmp/work"))
        assert result == "/tmp/work/bin/app"

    def test_os_substituted(self) -> None:
        """{os} is replaced with OS name."""
        result = substitute_placeholders("prefix_{os}_suffix", Path("/work"))
        assert "prefix_" in result and "_suffix" in result
        assert "{os}" not in result

    def test_arch_substituted(self) -> None:
        """{arch} is replaced with architecture."""
        result = substitute_placeholders("prefix_{arch}_suffix", Path("/work"))
        assert "{arch}" not in result

    def test_platform_substituted(self) -> None:
        """{platform} is replaced with OS_arch string."""
        result = substitute_placeholders("{platform}/app", Path("/work"))
        assert "{platform}" not in result
        assert "_" in result  # darwin_arm64 style

    def test_no_placeholders_unchanged(self) -> None:
        """Path with no placeholders is returned unchanged."""
        result = substitute_placeholders("/usr/bin/python", Path("/work"))
        assert result == "/usr/bin/python"


@pytest.mark.unit
class TestParseMode:
    """Tests for parse_mode."""

    def test_empty_string_returns_default(self) -> None:
        """Empty mode string returns default 0o755."""
        assert parse_mode("") == 0o755

    def test_octal_string_parsed(self) -> None:
        """Octal string is parsed correctly."""
        assert parse_mode("755") == 0o755
        assert parse_mode("644") == 0o644
        assert parse_mode("700") == 0o700

    def test_0o_prefix_stripped(self) -> None:
        """0o-prefixed strings are handled."""
        assert parse_mode("0o755") == 0o755

    def test_out_of_range_raises(self) -> None:
        """Mode > 0o777 raises ValueError."""
        with pytest.raises(ValueError):
            parse_mode("1000")

    def test_invalid_string_raises(self) -> None:
        """Non-numeric string raises ValueError."""
        with pytest.raises(ValueError):
            parse_mode("xyz")

    @pytest.mark.parametrize(
        "mode_str,expected",
        [
            ("755", 0o755),
            ("644", 0o644),
            ("0o700", 0o700),
            ("777", 0o777),
            ("000", 0o000),
        ],
    )
    def test_parametrized_modes(self, mode_str: str, expected: int) -> None:
        """Parametrized mode parsing."""
        assert parse_mode(mode_str) == expected


# 🌶️📦🔚
