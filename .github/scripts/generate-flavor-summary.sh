#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Generate comprehensive GitHub step summary for Flavor pipeline
# Usage: generate-flavor-summary.sh <test_results_dir> <wheel_artifacts_dir> <flavor_artifacts_dir> <helper_version> <test_job_result> <build_wheels_result> <build_flavor_result> <test_psp_result> <run_id>

set -euo pipefail

TEST_RESULTS_DIR="${1:-test-results}"
WHEEL_ARTIFACTS_DIR="${2:-wheel-artifacts}"
FLAVOR_ARTIFACTS_DIR="${3:-flavor-artifacts}"
HELPER_VERSION="${4:-unknown}"
TEST_JOB_RESULT="${5:-unknown}"
BUILD_WHEELS_RESULT="${6:-unknown}"
BUILD_FLAVOR_RESULT="${7:-unknown}"
TEST_PSP_RESULT="${8:-unknown}"
RUN_ID="${9:-unknown}"

# Initialize step summary
echo "🌶️ Generating Flavor Pipeline Summary..."

# Ensure GITHUB_STEP_SUMMARY is set (fallback to /dev/null in non-GitHub environments)
if [[ -n "${GITHUB_STEP_SUMMARY:-}" && -f "$GITHUB_STEP_SUMMARY" ]]; then
    SUMMARY_FILE="$GITHUB_STEP_SUMMARY"
elif [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    # Create the file if it doesn't exist (GitHub Actions should have done this)
    touch "$GITHUB_STEP_SUMMARY" 2>/dev/null || true
    SUMMARY_FILE="${GITHUB_STEP_SUMMARY}"
else
    SUMMARY_FILE="/dev/null"
fi
echo "Using summary file: $SUMMARY_FILE"

# Header
echo "## 🌶️ Flavor Pipeline Summary" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "**Helper Version:** $HELPER_VERSION" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

# Test Results Section
echo "### Test Results" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

if [ -d "$TEST_RESULTS_DIR" ]; then
    # Parse test results
    for result_dir in "$TEST_RESULTS_DIR"/test-results-*; do
        if [ -d "$result_dir" ]; then
            TEST_NAME=$(basename "$result_dir" | sed 's/test-results-//' | sed "s/-${RUN_ID}//")
            echo -n "- **$TEST_NAME**: " >> "$SUMMARY_FILE"

            if [ -f "$result_dir/pytest-results.xml" ]; then
                # Parse pytest XML for pass/fail counts
                if command -v python3 >/dev/null 2>&1; then
                    RESULT=$(python3 -c "
import xml.etree.ElementTree as ET
import sys
try:
    tree = ET.parse('$result_dir/pytest-results.xml')
    root = tree.getroot()
    testsuite = root.find('.//testsuite')
    if testsuite is not None:
        tests = testsuite.get('tests', '0')
        failures = testsuite.get('failures', '0')
        errors = testsuite.get('errors', '0')
        skipped = testsuite.get('skipped', '0')
        passed = int(tests) - int(failures) - int(errors) - int(skipped)
        print(f'{passed}/{tests} passed')
    else:
        print('Completed')
except Exception as e:
    print('Completed')
" 2>/dev/null) || RESULT="Completed"
                    echo "✅ $RESULT" >> "$SUMMARY_FILE"
                else
                    echo "✅ Completed" >> "$SUMMARY_FILE"
                fi
            else
                echo "⚠️ No results" >> "$SUMMARY_FILE"
            fi
        fi
    done
else
    echo "⚠️ No test results directory found" >> "$SUMMARY_FILE"
fi

# Show wheel artifacts if they were built
if [ -d "$WHEEL_ARTIFACTS_DIR" ] && [ "$(ls -A "$WHEEL_ARTIFACTS_DIR" 2>/dev/null)" ]; then
    echo "" >> "$SUMMARY_FILE"
    echo "### 🎡 Python Wheels" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"

    WHEEL_COUNT=0
    for wheel in "$WHEEL_ARTIFACTS_DIR"/*.whl; do
        if [ -f "$wheel" ]; then
            SIZE=$(du -h "$wheel" | cut -f1)
            WHEEL_NAME=$(basename "$wheel")
            echo "- \`$WHEEL_NAME\` ($SIZE)" >> "$SUMMARY_FILE"
            WHEEL_COUNT=$((WHEEL_COUNT + 1))
        fi
    done

    if [ "$WHEEL_COUNT" -eq 0 ]; then
        echo "⚠️ No wheel files found" >> "$SUMMARY_FILE"
    fi
else
    echo "" >> "$SUMMARY_FILE"
    echo "### 🎡 Python Wheels" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"
    echo "⏭️ Wheel building was skipped or no artifacts directory" >> "$SUMMARY_FILE"
fi

# Only show Flavor packages section if they were built
if [ -d "$FLAVOR_ARTIFACTS_DIR" ] && [ "$(ls -A "$FLAVOR_ARTIFACTS_DIR" 2>/dev/null)" ]; then
    echo "" >> "$SUMMARY_FILE"
    echo "### 📦 Flavor & Taster Packages" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"

    # List Flavor packages
    echo "#### Flavor PSP Packages:" >> "$SUMMARY_FILE"
    FLAVOR_COUNT=0
    for pkg in "$FLAVOR_ARTIFACTS_DIR"/flavor-*.psp "$FLAVOR_ARTIFACTS_DIR"/flavor-*.exe; do
        if [ -f "$pkg" ]; then
            SIZE=$(du -h "$pkg" | cut -f1)
            PKG_NAME=$(basename "$pkg")
            echo "- \`$PKG_NAME\` ($SIZE)" >> "$SUMMARY_FILE"
            FLAVOR_COUNT=$((FLAVOR_COUNT + 1))
        fi
    done

    if [ "$FLAVOR_COUNT" -eq 0 ]; then
        echo "⚠️ No Flavor packages found" >> "$SUMMARY_FILE"
    fi

    echo "" >> "$SUMMARY_FILE"
    echo "#### Taster Test Packages:" >> "$SUMMARY_FILE"
    TASTER_COUNT=0
    for pkg in "$FLAVOR_ARTIFACTS_DIR"/taster-*.psp "$FLAVOR_ARTIFACTS_DIR"/taster-*.exe; do
        if [ -f "$pkg" ]; then
            SIZE=$(du -h "$pkg" | cut -f1)
            PKG_NAME=$(basename "$pkg")
            echo "- \`$PKG_NAME\` ($SIZE)" >> "$SUMMARY_FILE"
            TASTER_COUNT=$((TASTER_COUNT + 1))
        fi
    done

    if [ "$TASTER_COUNT" -eq 0 ]; then
        echo "⚠️ No Taster packages found" >> "$SUMMARY_FILE"
    fi
fi

# Add PSP test results
echo "" >> "$SUMMARY_FILE"
echo "### 🧪 Flavor PSP Self-Contained Tests" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

if [ "$TEST_PSP_RESULT" == "success" ]; then
    echo "✅ All Flavor PSP packages verified successfully (self-contained, no external dependencies)" >> "$SUMMARY_FILE"
elif [ "$TEST_PSP_RESULT" == "skipped" ]; then
    echo "⏭️ PSP tests were skipped" >> "$SUMMARY_FILE"
else
    echo "❌ Some PSP self-contained tests failed" >> "$SUMMARY_FILE"
fi

# Artifacts section
echo "" >> "$SUMMARY_FILE"
echo "### Artifacts" >> "$SUMMARY_FILE"

if [ "$RUN_ID" != "unknown" ]; then
    echo "- [View test results](https://github.com/\${GITHUB_REPOSITORY}/actions/runs/$RUN_ID)" >> "$SUMMARY_FILE"
    echo "- [Download Flavor packages](https://github.com/\${GITHUB_REPOSITORY}/actions/runs/$RUN_ID#artifacts)" >> "$SUMMARY_FILE"
else
    echo "- View test results in the Actions tab" >> "$SUMMARY_FILE"
    echo "- Download Flavor packages from the artifacts section" >> "$SUMMARY_FILE"
fi

echo ""
echo "✅ Summary generation complete"

# 🌶️📦🔚
