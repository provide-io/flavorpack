#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Create test matrix JSON for parallel test execution
# Usage: create-test-matrix.sh

set -euo pipefail

# Log to stderr so it doesn't interfere with JSON output
echo "🧪 Creating test matrix..." >&2

# Define test categories with their configurations
# Output as single-line JSON for GitHub Actions compatibility
echo '{"include":[{"name":"unit","runner":"ubuntu-24.04","marker":"unit","timeout":10},{"name":"integration","runner":"ubuntu-24.04","marker":"integration","timeout":20},{"name":"security","runner":"ubuntu-24.04","marker":"security","timeout":15},{"name":"format-2025","runner":"ubuntu-24.04","path":"tests/format_2025","timeout":30},{"name":"packaging","runner":"ubuntu-24.04","path":"tests/packaging","timeout":25},{"name":"cross-language","runner":"ubuntu-24.04","marker":"cross_language","timeout":30}]}'

# 🌶️📦🔚
