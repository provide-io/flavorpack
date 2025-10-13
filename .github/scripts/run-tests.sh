#!/bin/bash
# Run tests with comprehensive output and metadata collection
set -e

MARKER="${1:-}"
PATH_FILTER="${2:-}"
USER_FILTER="${3:-}"

# Build test command with comprehensive output options
TEST_CMD="python -m pytest"

# Always generate detailed reports
TEST_CMD="$TEST_CMD -xvs"
TEST_CMD="$TEST_CMD --tb=short"
TEST_CMD="$TEST_CMD --junit-xml=pytest-results.xml"
# JSON report only if pytest-json-report is installed
if python -m pip show pytest-json-report >/dev/null 2>&1; then
    TEST_CMD="$TEST_CMD --json-report --json-report-file=test-report.json"
fi

# Always generate coverage data for all tests
TEST_CMD="$TEST_CMD --cov=flavor"
TEST_CMD="$TEST_CMD --cov-report=xml:coverage.xml"
TEST_CMD="$TEST_CMD --cov-report=html:htmlcov"
TEST_CMD="$TEST_CMD --cov-report=term-missing"
TEST_CMD="$TEST_CMD --cov-report=json:coverage.json"

# Add marker if specified
if [ -n "$MARKER" ]; then
    TEST_CMD="$TEST_CMD -m $MARKER"
fi

# Add path if specified
if [ -n "$PATH_FILTER" ]; then
    TEST_CMD="$TEST_CMD $PATH_FILTER"
else
    TEST_CMD="$TEST_CMD tests/"
fi

# Add user filter if provided
if [ -n "$USER_FILTER" ]; then
    TEST_CMD="$TEST_CMD $USER_FILTER"
fi

# Create output directory for logs
mkdir -p test-outputs

echo "🧪 Running tests..."
echo "Command: $TEST_CMD"

# Run tests and capture output (don't fail immediately)
set +e
$TEST_CMD 2>&1 | tee test-outputs/pytest-output.log
TEST_EXIT_CODE=$?
set -e

# Save test exit code
echo $TEST_EXIT_CODE > test-outputs/exit-code.txt

# Collect metadata even if tests failed
echo "📊 Collecting test metadata..."
python3 .github/scripts/test-metadata.py collect test-metadata

# Exit with the test exit code
exit $TEST_EXIT_CODE