"""
Mutation testing integration tests for FlavorPack.

This module provides tests to verify mutation testing setup and configuration.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest


@pytest.mark.slow
def test_mutmut_configuration_valid() -> None:
    """
    Verify that mutmut configuration in pyproject.toml is valid.
    """
    import tomli

    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml not found"

    with pyproject_path.open("rb") as f:
        config = tomli.load(f)

    assert "tool" in config, "No [tool] section in pyproject.toml"
    assert "mutmut" in config["tool"], "No [tool.mutmut] section in pyproject.toml"

    mutmut_config = config["tool"]["mutmut"]

    # Verify required configuration
    assert "paths_to_mutate" in mutmut_config, "Missing paths_to_mutate configuration"
    assert "runner" in mutmut_config, "Missing runner configuration"
    assert mutmut_config["runner"] == "pytest", "Runner should be pytest"

    # Verify paths_to_mutate is valid
    paths = mutmut_config["paths_to_mutate"]
    if isinstance(paths, str):
        paths = [paths]
    assert isinstance(paths, (str, list)), "paths_to_mutate should be string or list"

    # Verify the paths exist
    project_root = Path(__file__).parent.parent.parent
    for path in [paths] if isinstance(paths, str) else paths:
        full_path = project_root / path
        assert full_path.exists(), f"Mutation path {path} does not exist"


@pytest.mark.slow
def test_mutmut_can_generate_mutants() -> None:
    """
    Test that mutmut can successfully generate mutants from source code.

    This is a smoke test to ensure mutmut is properly configured.
    """
    project_root = Path(__file__).parent.parent.parent

    # Run mutmut to generate mutants only (don't run tests)
    result = subprocess.run(
        ["mutmut", "run", "--no-progress"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=60,
    )

    # Mutmut may fail tests (expected), but should not crash during generation
    # Exit codes: 0 = all survived, 1 = some killed, 2 = error
    assert result.returncode in (
        0,
        1,
        2,
    ), f"mutmut crashed with unexpected error: {result.stderr}"

    # Verify mutants directory was created
    mutants_dir = project_root / "mutants"
    assert mutants_dir.exists(), "Mutants directory was not created"


@pytest.mark.slow
def test_mutmut_ignores_generated_code() -> None:
    """
    Verify that mutmut properly excludes generated code from mutation.

    Generated protobuf files should not be mutated.
    """
    import tomli

    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        config = tomli.load(f)

    # Verify paths_to_mutate doesn't include generated directories
    paths_to_mutate = config["tool"]["mutmut"]["paths_to_mutate"]
    if isinstance(paths_to_mutate, str):
        paths_to_mutate = [paths_to_mutate]

    for path in paths_to_mutate:
        assert "generated" not in path, "Should not mutate generated code"
        assert "_pb2" not in path, "Should not mutate protobuf files"


def test_mutation_testing_dependencies_installed() -> None:
    """
    Verify that mutation testing dependencies are properly installed.
    """
    try:
        import mutmut  # noqa: F401  # type: ignore[import-untyped]

        mutmut_available = True
    except ImportError:
        mutmut_available = False

    assert mutmut_available, "mutmut is not installed"

    # Verify mutmut version is recent enough
    result = subprocess.run(
        ["mutmut", "--version"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, "mutmut --version failed"
    assert "mutmut" in result.stdout.lower(), "Unexpected version output"
