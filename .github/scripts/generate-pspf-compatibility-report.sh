#!/bin/bash
# Generate PSPF compatibility report from pretaster logs
# Usage: generate-pspf-compatibility-report.sh <logs_directory>

set -euo pipefail

LOGS_DIR="${1:-all-logs}"

echo "## 🧪 PSPF Compatibility Report"
echo ""
echo "**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# Check if logs directory exists
if [ ! -d "$LOGS_DIR" ]; then
    echo "⚠️ No logs directory found at: $LOGS_DIR"
    exit 0
fi

echo "### Test Matrix Results"
echo ""
echo "| Platform | Builder | Launcher | Status |"
echo "|----------|---------|----------|--------|"

# Track overall statistics
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Parse logs from each platform
for platform_dir in "$LOGS_DIR"/pretaster-logs-*; do
    if [ -d "$platform_dir" ]; then
        PLATFORM=$(basename "$platform_dir" | sed 's/pretaster-logs-//' | sed 's/-[0-9]*$//')
        
        # Check for combination test results
        for combo in "rs-rs" "rs-go" "go-rs" "go-go"; do
            BUILDER=$(echo "$combo" | cut -d'-' -f1)
            LAUNCHER=$(echo "$combo" | cut -d'-' -f2)
            
            # Map short names to full names
            case "$BUILDER" in
                rs) BUILDER_NAME="Rust" ;;
                go) BUILDER_NAME="Go" ;;
                *) BUILDER_NAME="Unknown" ;;
            esac
            
            case "$LAUNCHER" in
                rs) LAUNCHER_NAME="Rust" ;;
                go) LAUNCHER_NAME="Go" ;;
                *) LAUNCHER_NAME="Unknown" ;;
            esac
            
            # Look for log files matching this combination
            LOG_PATTERN="$platform_dir/logs/pretaster-b_${BUILDER}-l_${LAUNCHER}*.log"
            STATUS="⚠️ SKIP"
            
            for log_file in $LOG_PATTERN; do
                if [ -f "$log_file" ]; then
                    TOTAL_TESTS=$((TOTAL_TESTS + 1))
                    
                    # Check test results in the log
                    if grep -q "✅ All tests passed" "$log_file" 2>/dev/null || \
                       grep -q "✅ Pretaster tests completed" "$log_file" 2>/dev/null || \
                       grep -q "All tests completed successfully" "$log_file" 2>/dev/null; then
                        STATUS="✅ PASS"
                        PASSED_TESTS=$((PASSED_TESTS + 1))
                    elif grep -q "❌" "$log_file" 2>/dev/null || \
                         grep -q "FAILED" "$log_file" 2>/dev/null || \
                         grep -q "Error" "$log_file" 2>/dev/null; then
                        STATUS="❌ FAIL"
                        FAILED_TESTS=$((FAILED_TESTS + 1))
                    else
                        # If we have a log but can't determine status, mark as unknown
                        STATUS="❓ UNKNOWN"
                    fi
                    break
                fi
            done
            
            echo "| $PLATFORM | $BUILDER_NAME | $LAUNCHER_NAME | $STATUS |"
        done
    fi
done

echo ""
echo "### Summary Statistics"
echo ""

# Calculate success rate
if [ $TOTAL_TESTS -gt 0 ]; then
    SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
else
    SUCCESS_RATE=0
fi

echo "- **Total Tests Run:** $TOTAL_TESTS"
echo "- **Tests Passed:** $PASSED_TESTS"
echo "- **Tests Failed:** $FAILED_TESTS"
echo "- **Success Rate:** ${SUCCESS_RATE}%"
echo ""

# Check overall status
if [ $FAILED_TESTS -eq 0 ] && [ $TOTAL_TESTS -gt 0 ]; then
    echo "### ✅ Overall Status: **PASSED**"
    echo ""
    echo "All PSPF compatibility tests passed successfully!"
elif [ $TOTAL_TESTS -eq 0 ]; then
    echo "### ⚠️ Overall Status: **NO TESTS RUN**"
    echo ""
    echo "No test results found. Please check the test execution."
else
    echo "### ❌ Overall Status: **FAILED**"
    echo ""
    echo "$FAILED_TESTS test(s) failed. Please review the logs for details."
fi

echo ""
echo "### Test Coverage"
echo ""
echo "The pretaster suite validates:"
echo "- ✅ Cross-language builder/launcher compatibility"
echo "- ✅ PSPF format compliance"
echo "- ✅ Command execution and argument passing"
echo "- ✅ Environment variable handling"
echo "- ✅ Multi-slot package orchestration"
echo "- ✅ Exit code propagation"
echo "- ✅ File I/O in workenv"

# Add to GitHub step summary if available
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    {
        echo "## 🧪 PSPF Compatibility Report"
        echo ""
        echo "**Success Rate:** ${SUCCESS_RATE}%"
        echo ""
        echo "| Tests | Count |"
        echo "|-------|-------|"
        echo "| Total | $TOTAL_TESTS |"
        echo "| Passed | $PASSED_TESTS |"
        echo "| Failed | $FAILED_TESTS |"
    } >> "$GITHUB_STEP_SUMMARY"
fi