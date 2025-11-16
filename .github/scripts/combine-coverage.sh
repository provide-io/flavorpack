#!/bin/bash
set -e

# Combine coverage reports from multiple test runs
# Usage: .github/scripts/combine-coverage.sh

echo "📊 Combining coverage reports..."

# Find all coverage XML files
COVERAGE_FILES=$(find . -name "coverage-*.xml" -type f 2>/dev/null)

if [ -z "$COVERAGE_FILES" ]; then
    echo "⚠️ No coverage files found"
    exit 0
fi

echo "Found coverage files:"
echo "$COVERAGE_FILES"

# Install coverage tool if needed
pip install coverage[toml] > /dev/null 2>&1 || true

# Combine coverage data
coverage combine || true

# Generate combined XML report
coverage xml -o coverage-combined.xml

# Generate HTML report
coverage html -d htmlcov

# Generate terminal report
coverage report

echo "✅ Combined coverage saved to:"
echo "   - coverage-combined.xml (for CI upload)"
echo "   - htmlcov/ (for local viewing)"

# Show summary statistics
echo ""
echo "📈 Coverage Summary:"
coverage report | tail -1