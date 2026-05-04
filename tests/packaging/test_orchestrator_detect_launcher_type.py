from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flavor.packaging.orchestrator import PackagingOrchestrator


def _make_orchestrator(tmp_path: Path) -> PackagingOrchestrator:
    return PackagingOrchestrator(
        package_integrity_key_path=None,
        public_key_path=None,
        output_flavor_path=str(tmp_path / "out.psp"),
        build_config={},
        manifest_dir=tmp_path,
        package_name="testpkg",
        version="1.0.0",
        entry_point="main:cli",
    )


@pytest.mark.unit
def test_detect_launcher_type_prefers_filename_for_go(tmp_path: Path) -> None:
    orch = _make_orchestrator(tmp_path)
    launcher = tmp_path / "flavor-go-launcher-windows_amd64.exe"
    assert orch._detect_launcher_type(launcher) == "go"


@pytest.mark.unit
@patch("flavor.packaging.orchestrator.run")
def test_detect_launcher_type_handles_non_utf8_subprocess_output(
    mock_run: MagicMock,
    tmp_path: Path,
) -> None:
    orch = _make_orchestrator(tmp_path)
    launcher = tmp_path / "launcher.exe"
    mock_run.return_value.stdout = b"\x90\x91flavor-go-launcher 1.2.3\n"
    assert orch._detect_launcher_type(launcher) == "go"
