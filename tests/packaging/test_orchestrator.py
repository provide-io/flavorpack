"""Tests for the packaging orchestrator."""

import pytest
from pathlib import Path
from unittest.mock import patch

from flavor.packaging.orchestrator import PackagingOrchestrator


@pytest.mark.packaging
@pytest.mark.unit
def test_orchestrator_constructs_correct_build_command(tmp_path: Path) -> None:
    """
    Verifies that the orchestrator calls the Go builder with the correct arguments.
    """
    manifest_dir = tmp_path
    output_path = tmp_path / "dist" / "package.psp"

    # Create mock keys
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    (keys_dir / "priv.key").write_text("mock private key")
    (keys_dir / "pub.key").write_text("mock public key")

    with patch(
        "flavor.packaging.orchestrator.run_command"
    ) as mock_run, patch(
        "flavor.packaging.python_packager.PythonPackager.prepare_artifacts"
    ) as mock_prepare:
        
        # Mock run_command to prevent actual execution
        mock_run.return_value = None
        
        # Mock the artifacts returned by the python packager
        mock_prepare.return_value = {
            "payload_tgz": tmp_path / "payload.tgz",
            "python_tgz": tmp_path / "python.tgz",
            "payload_dir": tmp_path / "payload",
        }
        (tmp_path / "payload" / "bin").mkdir(parents=True)
        (tmp_path / "payload" / "bin" / "uv").touch()
        (tmp_path / "payload" / "wheels").mkdir()

        orchestrator = PackagingOrchestrator(
            package_integrity_key_path=str(keys_dir / "priv.key"),
            public_key_path=str(keys_dir / "pub.key"),
            output_flavor_path=str(output_path),
            build_config={},
            manifest_dir=manifest_dir,
            package_name="mypackage",
            entry_point="main:serve",
        )
        orchestrator.build_package()

        # Find the final build command call
        build_call = None
        for c in mock_run.call_args_list:
            if "flavor-rs-builder" in c.args[0][0] or "flavor-go-builder" in c.args[0][0]:
                build_call = c
                break

        assert build_call is not None, "Builder command was not called"
        build_cmd_args = build_call.args[0]
        
        assert "flavor-rs-builder" in build_cmd_args[0] or "flavor-go-builder" in build_cmd_args[0]
        assert "--manifest" in build_cmd_args
        assert "--output" in build_cmd_args
        assert str(output_path) in build_cmd_args


# 📦🍜🧪🪄
