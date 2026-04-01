#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for package.py manifest parsing and validation logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.mark.unit
class TestParseJsonManifest:
    """Test _parse_json_manifest."""

    def _write_json(self, tmp_path: Path, data: dict[str, object]) -> Path:
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(data))
        return p

    def test_valid_manifest(self, tmp_path: Path) -> None:
        from flavor.package import _parse_json_manifest

        p = self._write_json(
            tmp_path,
            {
                "package": {"name": "mypkg", "version": "1.0"},
                "execution": {"command": "python -m mypkg"},
            },
        )
        result = _parse_json_manifest(p)
        assert result["project_name"] == "mypkg"
        assert result["version"] == "1.0"
        assert result["entry_point"] == "python -m mypkg"
        assert result["cli_scripts"] == {}

    def test_missing_name_raises(self, tmp_path: Path) -> None:
        from flavor.package import _parse_json_manifest

        p = self._write_json(
            tmp_path,
            {
                "package": {"version": "1.0"},
                "execution": {"command": "run"},
            },
        )
        with pytest.raises(ValueError, match="name"):
            _parse_json_manifest(p)

    def test_missing_version_raises(self, tmp_path: Path) -> None:
        from flavor.package import _parse_json_manifest

        p = self._write_json(
            tmp_path,
            {
                "package": {"name": "pkg"},
                "execution": {"command": "run"},
            },
        )
        with pytest.raises(ValueError, match="version"):
            _parse_json_manifest(p)

    def test_missing_command_raises(self, tmp_path: Path) -> None:
        from flavor.package import _parse_json_manifest

        p = self._write_json(
            tmp_path,
            {
                "package": {"name": "pkg", "version": "1.0"},
                "execution": {},
            },
        )
        with pytest.raises(ValueError, match="command"):
            _parse_json_manifest(p)

    def test_missing_execution_section_raises(self, tmp_path: Path) -> None:
        from flavor.package import _parse_json_manifest

        p = self._write_json(
            tmp_path,
            {
                "package": {"name": "pkg", "version": "1.0"},
            },
        )
        with pytest.raises(ValueError, match="command"):
            _parse_json_manifest(p)


@pytest.mark.unit
class TestParseTomlManifest:
    """Test _parse_toml_manifest and helpers."""

    def _write_toml(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "pyproject.toml"
        p.write_text(content)
        return p

    def test_valid_manifest_with_version(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        p = self._write_toml(
            tmp_path,
            """
[project]
name = "mypkg"
version = "2.0.0"

[project.scripts]
mypkg = "mypkg.__main__:main"

[tool.flavor]
entry_point = "mypkg.__main__:main"
""",
        )
        result = _parse_toml_manifest(p)
        assert result["project_name"] == "mypkg"
        assert result["version"] == "2.0.0"

    def test_missing_name_raises(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        p = self._write_toml(
            tmp_path,
            """
[project]
version = "1.0"
""",
        )
        with pytest.raises(ValueError, match="name"):
            _parse_toml_manifest(p)

    def test_no_version_not_dynamic_raises(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        p = self._write_toml(
            tmp_path,
            """
[project]
name = "mypkg"
""",
        )
        with pytest.raises(ValueError, match="version"):
            _parse_toml_manifest(p)

    def test_dynamic_version_from_version_file(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        (tmp_path / "VERSION").write_text("3.1.4")
        p = self._write_toml(
            tmp_path,
            """
[project]
name = "mypkg"
dynamic = ["version"]

[tool.flavor]
entry_point = "mypkg:main"
""",
        )
        result = _parse_toml_manifest(p)
        assert result["version"] == "3.1.4"

    def test_dynamic_version_falls_back_to_importlib(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        p = self._write_toml(
            tmp_path,
            """
[project]
name = "flavor"
dynamic = ["version"]

[tool.flavor]
entry_point = "flavor:main"
""",
        )
        # "flavor" may or may not be installed; either importlib returns something or falls back
        result = _parse_toml_manifest(p)
        assert isinstance(result["version"], str)
        assert len(result["version"]) > 0

    def test_dynamic_version_falls_back_to_default(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        p = self._write_toml(
            tmp_path,
            """
[project]
name = "definitely-not-installed-xyz123"
dynamic = ["version"]

[tool.flavor]
entry_point = "xyz:main"
""",
        )
        result = _parse_toml_manifest(p)
        assert result["version"] == "0.0.0"

    def test_entry_point_from_flavor_config(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        p = self._write_toml(
            tmp_path,
            """
[project]
name = "mypkg"
version = "1.0"

[tool.flavor]
entry_point = "mypkg.cli:main"
""",
        )
        result = _parse_toml_manifest(p)
        assert result["entry_point"] == "mypkg.cli:main"

    def test_entry_point_from_scripts(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        p = self._write_toml(
            tmp_path,
            """
[project]
name = "mypkg"
version = "1.0"

[project.scripts]
mypkg = "mypkg.cli:main"
""",
        )
        result = _parse_toml_manifest(p)
        assert result["entry_point"] == "mypkg.cli:main"

    def test_entry_point_not_found_raises(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        p = self._write_toml(
            tmp_path,
            """
[project]
name = "mypkg"
version = "1.0"
""",
        )
        with pytest.raises(ValueError, match="entry_point"):
            _parse_toml_manifest(p)

    def test_buildconfig_toml_is_merged(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        (tmp_path / "buildconfig.toml").write_text("[build]\nstip = true\n")
        p = self._write_toml(
            tmp_path,
            """
[project]
name = "mypkg"
version = "1.0"

[tool.flavor]
entry_point = "mypkg:main"
""",
        )
        result = _parse_toml_manifest(p)
        # buildconfig.toml was merged — stip key should be present in build_config
        assert "stip" in result["build_config"]

    def test_cli_scripts_extracted(self, tmp_path: Path) -> None:
        from flavor.package import _parse_toml_manifest

        p = self._write_toml(
            tmp_path,
            """
[project]
name = "mypkg"
version = "1.0"

[project.scripts]
mypkg = "mypkg:main"
othercmd = "mypkg.other:run"

[tool.flavor]
entry_point = "mypkg:main"
""",
        )
        result = _parse_toml_manifest(p)
        assert result["cli_scripts"] == {"mypkg": "mypkg:main", "othercmd": "mypkg.other:run"}


@pytest.mark.unit
class TestSetupKeyPaths:
    """Test _setup_key_paths."""

    def test_public_without_private_raises(self, tmp_path: Path) -> None:
        from flavor.package import _setup_key_paths

        with pytest.raises(ValueError, match="private key"):
            _setup_key_paths(
                private_key_path=None,
                public_key_path=tmp_path / "pub.key",
                manifest_dir=tmp_path,
                key_seed=None,
            )

    def test_key_seed_returns_early(self, tmp_path: Path) -> None:
        from flavor.package import _setup_key_paths

        priv, pub = _setup_key_paths(
            private_key_path=None,
            public_key_path=tmp_path / "pub.key",
            manifest_dir=tmp_path,
            key_seed="my-seed",
        )
        # With key_seed, returns early without validation
        assert priv is None
        assert pub == tmp_path / "pub.key"

    def test_both_paths_returned_as_is(self, tmp_path: Path) -> None:
        from flavor.package import _setup_key_paths

        priv_path = tmp_path / "priv.key"
        pub_path = tmp_path / "pub.key"
        priv, pub = _setup_key_paths(
            private_key_path=priv_path,
            public_key_path=pub_path,
            manifest_dir=tmp_path,
            key_seed=None,
        )
        assert priv == priv_path
        assert pub == pub_path

    def test_no_keys_returns_none(self, tmp_path: Path) -> None:
        from flavor.package import _setup_key_paths

        priv, pub = _setup_key_paths(
            private_key_path=None,
            public_key_path=None,
            manifest_dir=tmp_path,
            key_seed=None,
        )
        assert priv is None
        assert pub is None


@pytest.mark.unit
class TestDetermineOutputPath:
    """Test _determine_output_path."""

    def test_explicit_output_path_returned_as_is(self, tmp_path: Path) -> None:
        from flavor.package import _determine_output_path

        explicit = tmp_path / "out" / "my.psp"
        result = _determine_output_path(explicit, tmp_path, "mypkg")
        assert result == explicit

    def test_default_path_constructed(self, tmp_path: Path) -> None:
        from flavor.package import _determine_output_path

        result = _determine_output_path(None, tmp_path, "mypkg")
        assert result == tmp_path / "dist" / "mypkg.psp"
