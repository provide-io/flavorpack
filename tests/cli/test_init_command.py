"""Tests for `flavor init [--global]`."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from flavor.cli import cli


def test_init_creates_trusted_keys_dir(tmp_path: Path) -> None:
    """flavor init creates trusted-keys directory."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "trusted-keys").is_dir()


def test_init_creates_policy_toml(tmp_path: Path) -> None:
    """flavor init creates a scaffolded policy.toml."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        runner.invoke(cli, ["init"])
    assert (tmp_path / "policy.toml").exists()


def test_init_policy_toml_all_commented(tmp_path: Path) -> None:
    """Scaffolded policy.toml has no uncommented assignments."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        runner.invoke(cli, ["init"])
    content = (tmp_path / "policy.toml").read_text(encoding="utf-8")
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            raise AssertionError(f"Uncommented assignment in policy.toml: {line!r}")


def test_init_is_idempotent(tmp_path: Path) -> None:
    """Running flavor init twice does not overwrite existing policy.toml."""
    runner = CliRunner()
    env = {"FLAVOR_CONFIG_DIR": str(tmp_path)}
    with mock.patch.dict(os.environ, env):
        runner.invoke(cli, ["init"])
    policy_file = tmp_path / "policy.toml"
    policy_file.write_text("# MY CUSTOM CONTENT\n", encoding="utf-8")
    with mock.patch.dict(os.environ, env):
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "MY CUSTOM CONTENT" in policy_file.read_text(encoding="utf-8")


def test_init_global_uses_system_dir(tmp_path: Path) -> None:
    """flavor init --global targets the system config dir."""
    runner = CliRunner()
    with mock.patch("flavor.commands.init.get_system_config_dir", return_value=tmp_path):
        result = runner.invoke(cli, ["init", "--global"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "trusted-keys").is_dir()
    assert (tmp_path / "policy.toml").exists()
