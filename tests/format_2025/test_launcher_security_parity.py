#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Python launcher parity tests for launch-time security and cache identity."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from flavor.config.policy import OperatorPolicy
from flavor.psp.format_2025.launcher import PSPFLauncher
from flavor.psp.format_2025.workenv import WorkEnvManager


def _raw_public_key_bytes() -> bytes:
    """Generate a valid raw Ed25519 public key for trust checks."""
    public_key = Ed25519PrivateKey.generate().public_key()
    return public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)


def test_launcher_execute_blocks_untrusted_package_when_policy_requires_trusted_key(tmp_path: Path) -> None:
    """Execution must stop before setup when operator policy requires a trusted signing key."""
    bundle_path = tmp_path / "package.psp"
    bundle_path.write_bytes(b"bundle")

    launcher = PSPFLauncher(bundle_path)
    metadata = {
        "package": {"name": "pkg", "version": "1.0.0"},
        "execution": {"command": "echo hi"},
        "slots": [],
    }
    index = SimpleNamespace(public_key=_raw_public_key_bytes(), build_timestamp=0)

    with (
        patch.object(launcher, "read_metadata", return_value=metadata),
        patch.object(launcher, "read_index", return_value=index),
        patch("flavor.psp.format_2025.launcher.verify_package_integrity", return_value={"valid": True}),
        patch(
            "flavor.psp.format_2025.launcher.load_operator_policy",
            return_value=OperatorPolicy(require_trusted_key=True),
        ),
        patch("flavor.psp.format_2025.launcher.is_key_trusted", return_value=False),
        patch.object(launcher._workenv_manager, "setup_workenv") as mock_setup_workenv,
        patch("flavor.psp.format_2025.executor.BundleExecutor") as mock_executor,
    ):
        result = launcher.execute([])

    assert result["executed"] is False
    assert "trusted" in result["error"]
    mock_setup_workenv.assert_not_called()
    mock_executor.assert_not_called()


def test_workenv_path_is_bundle_specific_for_identical_package_metadata(tmp_path: Path) -> None:
    """Distinct bundles with the same package metadata must not share one Python workenv path."""
    bundle_one = tmp_path / "package-one.psp"
    bundle_two = tmp_path / "package-two.psp"
    bundle_one.write_bytes(b"bundle-one")
    bundle_two.write_bytes(b"bundle-two")

    reader = Mock()
    reader.read_metadata.return_value = {"package": {"name": "pkg", "version": "1.0.0"}}
    reader._index = SimpleNamespace(slot_count=0)
    manager = WorkEnvManager(reader)

    with (
        patch("flavor.cache.get_cache_dir", return_value=tmp_path / "cache"),
        patch.object(manager, "_check_cache_validity", return_value=True),
    ):
        path_one = manager.setup_workenv(bundle_one)
        path_two = manager.setup_workenv(bundle_two)

    assert path_one != path_two
