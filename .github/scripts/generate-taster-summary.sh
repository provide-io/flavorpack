#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 Provide Technologies, LLC
#
# generate-taster-summary.sh
# Create GitHub step summary from taster test results
#
# Usage:
#   generate-taster-summary.sh <results_dir> <helper_version>
#
# Arguments:
#   results_dir     - Directory containing test result JSON files
#   helper_version  - Helper version used in testing
#
# Environment:
#   GITHUB_STEP_SUMMARY - GitHub Actions output file for step summary
#
# Exit codes:
#   0 - Summary generated successfully
#   1 - Error generating summary

set -euo pipefail

# Parse arguments
RESULTS_DIR="${1:-}"
HELPER_VERSION="${2:-}"

if [[ -z "$RESULTS_DIR" || -z "$HELPER_VERSION" ]]; then
    echo "Usage: $0 <results_dir> <helper_version>"
    exit 1
fi

if [[ ! -d "$RESULTS_DIR" ]]; then
    echo "❌ Results directory not found: $RESULTS_DIR"
    exit 1
fi

# Determine output file
OUTPUT_FILE="${GITHUB_STEP_SUMMARY:-/dev/stdout}"

# Helper function to write to summary
write_summary() {
    echo "$1" >> "$OUTPUT_FILE"
}

# Start summary
write_summary "## 🍰 Taster Pipeline Summary"
write_summary ""
write_summary "**Helper Version:** $HELPER_VERSION"
write_summary ""

# Platform test results section
write_summary "### Platform Test Results"
write_summary ""
write_summary "| Platform | Status | Runner | Timestamp |"
write_summary "|----------|--------|--------|-----------|"

# Track statistics
TOTAL_PLATFORMS=0
SUCCESSFUL_PLATFORMS=0
FAILED_PLATFORMS=0

# Parse test results
for result_dir in "$RESULTS_DIR"/taster-results-*; do
    if [[ -d "$result_dir" ]]; then
        for json_file in "$result_dir"/*.json; do
            if [[ -f "$json_file" ]]; then
                # Extract data from JSON
                PLATFORM=$(jq -r '.platform' "$json_file")
                STATUS=$(jq -r '.status' "$json_file")
                RUNNER=$(jq -r '.runner' "$json_file")
                TIMESTAMP=$(jq -r '.timestamp' "$json_file")

<<<<<<< HEAD
                TOTAL_PLATFORMS=$((TOTAL_PLATFORMS + 1))
=======
                ((TOTAL_PLATFORMS++))
>>>>>>> fixing up building stuff

                # Convert status to emoji
                if [[ "$STATUS" == "success" ]]; then
                    STATUS_EMOJI="✅"
<<<<<<< HEAD
                    SUCCESSFUL_PLATFORMS=$((SUCCESSFUL_PLATFORMS + 1))
                else
                    STATUS_EMOJI="❌"
                    FAILED_PLATFORMS=$((FAILED_PLATFORMS + 1))
=======
                    ((SUCCESSFUL_PLATFORMS++))
                else
                    STATUS_EMOJI="❌"
                    ((FAILED_PLATFORMS++))
>>>>>>> fixing up building stuff
                fi

                write_summary "| $PLATFORM | $STATUS_EMOJI $STATUS | $RUNNER | $TIMESTAMP |"
            fi
        done
    fi
done

# Platform summary
write_summary ""
write_summary "**Platform Summary:** $SUCCESSFUL_PLATFORMS/$TOTAL_PLATFORMS passed"

# Test coverage section
write_summary ""
write_summary "### Test Coverage"
write_summary ""
write_summary "✅ Basic commands (--help, info, env)"
write_summary "✅ Exit codes and error handling"
write_summary "✅ File operations and workenv persistence"
write_summary "✅ Cache management"
write_summary "✅ Argument parsing"
write_summary "✅ Cross-language compatibility"
write_summary "✅ Signal handling"
write_summary "✅ Pipe operations"

# Comprehensive tests section
write_summary ""
write_summary "### Comprehensive Tests"
write_summary ""
write_summary "🧪 Flavor pack with explicit launcher"
write_summary "🧪 Taster command suite (help, info, env, cache, exit)"
write_summary "🧪 Launcher validation (Rust and Go)"
write_summary "🧪 Pipe operations and stdin/stdout handling"
write_summary "🧪 Signal handling and process control"
write_summary "🧪 Memory-mapped I/O operations"
write_summary "🧪 Self-packaging capability (pretaster build)"

# Artifacts section
if [[ -n "${GITHUB_REPOSITORY:-}" && -n "${GITHUB_RUN_ID:-}" ]]; then
    write_summary ""
    write_summary "### Artifacts"
    write_summary "- [View test results](https://github.com/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID)"
fi

# Overall status
write_summary ""
if [[ $FAILED_PLATFORMS -eq 0 ]]; then
    write_summary "## 🎉 All Tests Passed!"
    write_summary ""
    write_summary "All $TOTAL_PLATFORMS platforms successfully validated."
else
    write_summary "## ⚠️ Some Tests Failed"
    write_summary ""
    write_summary "$FAILED_PLATFORMS out of $TOTAL_PLATFORMS platforms failed."
fi

echo "📊 Summary generated successfully"
echo "  Total platforms: $TOTAL_PLATFORMS"
echo "  Successful: $SUCCESSFUL_PLATFORMS"
echo "  Failed: $FAILED_PLATFORMS"

# Exit with error if any platform failed
if [[ $FAILED_PLATFORMS -gt 0 ]]; then
    exit 1
fi

# 🌶️📦🔚
