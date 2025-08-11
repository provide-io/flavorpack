"""Tests for the packaging orchestrator."""

from pathlib import Path
from unittest.mock import patch

from flavor.packaging.orchestrator import PackagingOrchestrator


def test_orchestrator_constructs_correct_build_command(tmp_path: Path) -> None:
    """
    Verifies that the orchestrator calls the Go packager with the correct arguments.
    """
    manifest_dir = tmp_path
    output_path = tmp_path / "dist" / "provider"

    with patch("flavor.packaging.orchestrator.ensure_go_binary", return_value="go-packager") as mock_ensure:
        with patch("flavor.packaging.orchestrator.PackagingOrchestrator._run_subprocess") as mock_run:
            orchestrator = PackagingOrchestrator(
                package_integrity_key_path="keys/priv.key",
                public_key_path="keys/pub.key",
                                    output_flavor_path=str(output_path),
                build_config={},
                manifest_dir=manifest_dir,
                provider_name="myprovider",
                entry_point="main:serve",
            )
            orchestrator.build_package()

            # The orchestrator now calls ensure_go_binary twice
            assert mock_ensure.call_count == 2
            mock_ensure.assert_any_call("flavor-packager")
            mock_ensure.assert_any_call("pspf-launcher")
            
            # Find the final build command call
            build_call = None
            for c in mock_run.call_args_list:
                if "build" in c.args[0]:
                    build_call = c
                    break
            
            assert build_call is not None, "Go build command was not called"
            build_cmd_args = build_call.args[0]
            
            assert build_cmd_args[0] == "go-packager"
            assert "--package-key" in build_cmd_args
            assert "keys/priv.key" in build_cmd_args
            assert "--out" in build_cmd_args
            assert str(output_path) in build_cmd_args


# 📦🍜🧪🪄
