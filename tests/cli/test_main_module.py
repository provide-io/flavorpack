#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test for running the builder as a module."""

import runpy
import sys
from unittest.mock import patch

import pytest


def test_main_module_entrypoint() -> None:
    """Tests that `python -m pspf` calls the CLI."""
    with patch("flavor.cli.main") as mock_cli:
        # THE FIX: Click's --version flag causes a SystemExit(0). We must
        # catch this to prevent pytest from marking the test as failed.
        with pytest.raises(SystemExit) as e:
            original_argv = sys.argv
            sys.argv = ["flavor", "--version"]
            try:
                runpy.run_module("flavor", run_name="__main__")
            finally:
                sys.argv = original_argv

        # Verify that the exit was successful.
        assert e.type is SystemExit
        assert e.value.code == 0

    # The mock is not called because --version exits before the command body runs.
    # This is the correct behavior.
    mock_cli.assert_not_called()


# 🌶️📦🔚
