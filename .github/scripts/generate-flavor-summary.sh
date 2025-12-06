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

# Header
echo "## 🌶️ Flavor Pipeline Summary" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"
echo "**Helper Version:** $HELPER_VERSION" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

# Test Results Section
echo "### Test Results" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

if [ -d "$TEST_RESULTS_DIR" ]; then
    # Parse test results
    for result_dir in "$TEST_RESULTS_DIR"/test-results-*; do
        if [ -d "$result_dir" ]; then
            TEST_NAME=$(basename "$result_dir" | sed 's/test-results-//' | sed "s/-${RUN_ID}//")
            echo -n "- **$TEST_NAME**: " >> "$GITHUB_STEP_SUMMARY"

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
                    echo "✅ $RESULT" >> "$GITHUB_STEP_SUMMARY"
                else
                    echo "✅ Completed" >> "$GITHUB_STEP_SUMMARY"
                fi
            else
                echo "⚠️ No results" >> "$GITHUB_STEP_SUMMARY"
            fi
        fi
    done
else
    echo "⚠️ No test results directory found" >> "$GITHUB_STEP_SUMMARY"
fi

# Show wheel artifacts if they were built
if [ -d "$WHEEL_ARTIFACTS_DIR" ] && [ "$(ls -A "$WHEEL_ARTIFACTS_DIR" 2>/dev/null)" ]; then
    echo "" >> "$GITHUB_STEP_SUMMARY"
    echo "### 🎡 Python Wheels" >> "$GITHUB_STEP_SUMMARY"
    echo "" >> "$GITHUB_STEP_SUMMARY"

    WHEEL_COUNT=0
    for wheel in "$WHEEL_ARTIFACTS_DIR"/*.whl; do
        if [ -f "$wheel" ]; then
            SIZE=$(du -h "$wheel" | cut -f1)
            WHEEL_NAME=$(basename "$wheel")
            echo "- \`$WHEEL_NAME\` ($SIZE)" >> "$GITHUB_STEP_SUMMARY"
            ((WHEEL_COUNT++))
        fi
    done

    if [ "$WHEEL_COUNT" -eq 0 ]; then
        echo "⚠️ No wheel files found" >> "$GITHUB_STEP_SUMMARY"
    fi
else
    echo "" >> "$GITHUB_STEP_SUMMARY"
    echo "### 🎡 Python Wheels" >> "$GITHUB_STEP_SUMMARY"
    echo "" >> "$GITHUB_STEP_SUMMARY"
    echo "⏭️ Wheel building was skipped or no artifacts directory" >> "$GITHUB_STEP_SUMMARY"
fi

# Only show Flavor packages section if they were built
if [ -d "$FLAVOR_ARTIFACTS_DIR" ] && [ "$(ls -A "$FLAVOR_ARTIFACTS_DIR" 2>/dev/null)" ]; then
    echo "" >> "$GITHUB_STEP_SUMMARY"
    echo "### 📦 Flavor & Taster Packages" >> "$GITHUB_STEP_SUMMARY"
    echo "" >> "$GITHUB_STEP_SUMMARY"

    # List Flavor packages
    echo "#### Flavor PSP Packages:" >> "$GITHUB_STEP_SUMMARY"
    FLAVOR_COUNT=0
    for pkg in "$FLAVOR_ARTIFACTS_DIR"/flavor-*.psp "$FLAVOR_ARTIFACTS_DIR"/flavor-*.exe; do
        if [ -f "$pkg" ]; then
            SIZE=$(du -h "$pkg" | cut -f1)
            PKG_NAME=$(basename "$pkg")
            echo "- \`$PKG_NAME\` ($SIZE)" >> "$GITHUB_STEP_SUMMARY"
            ((FLAVOR_COUNT++))
        fi
    done

    if [ "$FLAVOR_COUNT" -eq 0 ]; then
        echo "⚠️ No Flavor packages found" >> "$GITHUB_STEP_SUMMARY"
    fi

    echo "" >> "$GITHUB_STEP_SUMMARY"
    echo "#### Taster Test Packages:" >> "$GITHUB_STEP_SUMMARY"
    TASTER_COUNT=0
    for pkg in "$FLAVOR_ARTIFACTS_DIR"/taster-*.psp "$FLAVOR_ARTIFACTS_DIR"/taster-*.exe; do
        if [ -f "$pkg" ]; then
            SIZE=$(du -h "$pkg" | cut -f1)
            PKG_NAME=$(basename "$pkg")
            echo "- \`$PKG_NAME\` ($SIZE)" >> "$GITHUB_STEP_SUMMARY"
            ((TASTER_COUNT++))
        fi
    done

    if [ "$TASTER_COUNT" -eq 0 ]; then
        echo "⚠️ No Taster packages found" >> "$GITHUB_STEP_SUMMARY"
    fi
fi

# Add PSP test results
echo "" >> "$GITHUB_STEP_SUMMARY"
echo "### 🧪 Flavor PSP Self-Contained Tests" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

if [ "$TEST_PSP_RESULT" == "success" ]; then
    echo "✅ All Flavor PSP packages verified successfully (self-contained, no external dependencies)" >> "$GITHUB_STEP_SUMMARY"
elif [ "$TEST_PSP_RESULT" == "skipped" ]; then
    echo "⏭️ PSP tests were skipped" >> "$GITHUB_STEP_SUMMARY"
else
    echo "❌ Some PSP self-contained tests failed" >> "$GITHUB_STEP_SUMMARY"
fi

# Artifacts section
echo "" >> "$GITHUB_STEP_SUMMARY"
echo "### Artifacts" >> "$GITHUB_STEP_SUMMARY"

if [ "$RUN_ID" != "unknown" ]; then
    echo "- [View test results](https://github.com/\${GITHUB_REPOSITORY}/actions/runs/$RUN_ID)" >> "$GITHUB_STEP_SUMMARY"
    echo "- [Download Flavor packages](https://github.com/\${GITHUB_REPOSITORY}/actions/runs/$RUN_ID#artifacts)" >> "$GITHUB_STEP_SUMMARY"
else
    echo "- View test results in the Actions tab" >> "$GITHUB_STEP_SUMMARY"
    echo "- Download Flavor packages from the artifacts section" >> "$GITHUB_STEP_SUMMARY"
fi

echo ""
echo "✅ Summary generation complete"

# 🌶️📦🔚
