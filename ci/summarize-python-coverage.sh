#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Print a coverage summary line from coverage.json to GITHUB_STEP_SUMMARY.
# Usage: summarize-python-coverage.sh [coverage.json]
# If the file doesn't exist, the script is a no-op.

set -euo pipefail

COVERAGE_JSON="${1:-coverage.json}"

if [ ! -f "$COVERAGE_JSON" ]; then
    exit 0
fi

python3 - "$COVERAGE_JSON" <<'EOF'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
totals = data.get("totals", {})
pct = totals.get("percent_covered_display", "unknown")
print(f"- Coverage: {pct}%")
EOF
