#!/bin/bash
set -e

# Generate pipeline summary for GitHub Actions
# Usage: .github/scripts/generate-summary.sh <helpers-result> <flavor-tests-result> <taster-tests-result> <flavor-packaging-result> <taster-self-packaging-result> <integration-tests-result>

HELPERS_RESULT="${1:-skipped}"
FLAVOR_TESTS_RESULT="${2:-skipped}"
TASTER_TESTS_RESULT="${3:-skipped}"
FLAVOR_PACKAGING_RESULT="${4:-skipped}"
TASTER_SELF_PACKAGING_RESULT="${5:-skipped}"
INTEGRATION_TESTS_RESULT="${6:-skipped}"

echo "# 🎯 Main CI Pipeline Summary" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "## 📈 Overall Status" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Determine overall status
overall="success"
if [ "$HELPERS_RESULT" != "success" ]; then
    overall="failure"
fi
if [ "$FLAVOR_TESTS_RESULT" != "success" ] && [ "$FLAVOR_TESTS_RESULT" != "skipped" ]; then
    overall="failure"
fi
if [ "$TASTER_TESTS_RESULT" != "success" ] && [ "$TASTER_TESTS_RESULT" != "skipped" ]; then
    overall="failure"
fi
if [ "$FLAVOR_PACKAGING_RESULT" != "success" ] && [ "$FLAVOR_PACKAGING_RESULT" != "skipped" ]; then
    overall="failure"
fi
if [ "$TASTER_SELF_PACKAGING_RESULT" != "success" ] && [ "$TASTER_SELF_PACKAGING_RESULT" != "skipped" ]; then
    overall="failure"
fi
if [ "$INTEGRATION_TESTS_RESULT" != "success" ] && [ "$INTEGRATION_TESTS_RESULT" != "skipped" ]; then
    overall="failure"
fi

if [ "$overall" = "success" ]; then
    echo "### ✅ All workflows completed successfully!" >> $GITHUB_STEP_SUMMARY
else
    echo "### ❌ Some workflows failed - see details below" >> $GITHUB_STEP_SUMMARY
fi

echo "" >> $GITHUB_STEP_SUMMARY
echo "## 📋 Workflow Results" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "| Workflow | Status | Description |" >> $GITHUB_STEP_SUMMARY
echo "|----------|--------|-------------|" >> $GITHUB_STEP_SUMMARY

# Helper Builds
case "$HELPERS_RESULT" in
    success)
        echo "| 🔨 Helper Builds | ✅ Success | Go/Rust helpers built for all platforms |" >> $GITHUB_STEP_SUMMARY
        ;;
    skipped)
        echo "| 🔨 Helper Builds | ⏭️ Skipped | - |" >> $GITHUB_STEP_SUMMARY
        ;;
    *)
        echo "| 🔨 Helper Builds | ❌ Failed | Check build logs |" >> $GITHUB_STEP_SUMMARY
        ;;
esac

# Flavor Tests
case "$FLAVOR_TESTS_RESULT" in
    success)
        echo "| 🧪 Flavor Tests | ✅ Success | All test marks passed |" >> $GITHUB_STEP_SUMMARY
        ;;
    skipped)
        echo "| 🧪 Flavor Tests | ⏭️ Skipped | - |" >> $GITHUB_STEP_SUMMARY
        ;;
    *)
        echo "| 🧪 Flavor Tests | ❌ Failed | Check test results |" >> $GITHUB_STEP_SUMMARY
        ;;
esac

# Taster Tests
case "$TASTER_TESTS_RESULT" in
    success)
        echo "| 🍯 Taster Tests | ✅ Success | Unit and integration tests passed |" >> $GITHUB_STEP_SUMMARY
        ;;
    skipped)
        echo "| 🍯 Taster Tests | ⏭️ Skipped | - |" >> $GITHUB_STEP_SUMMARY
        ;;
    *)
        echo "| 🍯 Taster Tests | ❌ Failed | Check test results |" >> $GITHUB_STEP_SUMMARY
        ;;
esac

# Flavor Packaging
case "$FLAVOR_PACKAGING_RESULT" in
    success)
        echo "| 📦 Flavor Packaging | ✅ Success | Self-packaging and Taster packaging work |" >> $GITHUB_STEP_SUMMARY
        ;;
    skipped)
        echo "| 📦 Flavor Packaging | ⏭️ Skipped | - |" >> $GITHUB_STEP_SUMMARY
        ;;
    *)
        echo "| 📦 Flavor Packaging | ❌ Failed | Check packaging logs |" >> $GITHUB_STEP_SUMMARY
        ;;
esac

# Taster Self-Packaging
case "$TASTER_SELF_PACKAGING_RESULT" in
    success)
        echo "| 🔄 Taster Self-Package | ✅ Success | Cross-combination packaging works |" >> $GITHUB_STEP_SUMMARY
        ;;
    skipped)
        echo "| 🔄 Taster Self-Package | ⏭️ Skipped | - |" >> $GITHUB_STEP_SUMMARY
        ;;
    *)
        echo "| 🔄 Taster Self-Package | ❌ Failed | Check self-packaging logs |" >> $GITHUB_STEP_SUMMARY
        ;;
esac

# Integration Tests
case "$INTEGRATION_TESTS_RESULT" in
    success)
        echo "| 🔧 Integration Tests | ✅ Success | Cross-platform integration tests passed |" >> $GITHUB_STEP_SUMMARY
        ;;
    skipped)
        echo "| 🔧 Integration Tests | ⏭️ Skipped | - |" >> $GITHUB_STEP_SUMMARY
        ;;
    *)
        echo "| 🔧 Integration Tests | ❌ Failed | Check integration test logs |" >> $GITHUB_STEP_SUMMARY
        ;;
esac

echo "" >> $GITHUB_STEP_SUMMARY
echo "## 🔗 Quick Links" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "- [View All Artifacts](https://github.com/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID#artifacts)" >> $GITHUB_STEP_SUMMARY
echo "- [Download Helpers](https://github.com/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID#artifacts)" >> $GITHUB_STEP_SUMMARY
echo "- [Coverage Report](https://codecov.io/gh/$GITHUB_REPOSITORY)" >> $GITHUB_STEP_SUMMARY

echo "" >> $GITHUB_STEP_SUMMARY
echo "---" >> $GITHUB_STEP_SUMMARY
echo "_Generated at $(date -u '+%Y-%m-%d %H:%M:%S UTC')_" >> $GITHUB_STEP_SUMMARY

# Exit with appropriate code
if [ "$overall" = "success" ]; then
    echo "✅ All required workflows passed!"
    exit 0
else
    echo "❌ Some workflows failed!"
    exit 1
fi