#!/usr/bin/env sh
# Run pretaster combination tests inside a container.
# Called by the compatibility-check workflow's test-pretaster job.
#
# Usage: run-compat-pretaster.sh <install_cmd>
#   install_cmd  Package manager command to install Python (e.g. "apt-get update && apt-get install -y python3 python3-pip")
#
# Expects to be run inside a Docker container with /workspace mounted.
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

set -eu

INSTALL_CMD="${1:?Usage: run-compat-pretaster.sh <install_cmd>}"

# Install Python
eval "$INSTALL_CMD"

# Install pretaster package
cd tests/pretaster
pip3 install --break-system-packages . 2>/dev/null || pip3 install .

# Run combination tests
echo "Running combination tests..."
./tests/combo/test-combinations.sh
