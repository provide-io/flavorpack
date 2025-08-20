#!/bin/bash
set -e

# Run tests that require helpers after ensuring helpers are available
# Usage: .github/scripts/run-tests-with-helpers.sh <test-mark>

TEST_MARK="${1:-integration}"
PYTHON_VERSION="${2:-3.11}"

echo "🧪 Running tests marked: $TEST_MARK"

# Check if helpers are available
if [ ! -d "helpers/bin" ] || [ -z "$(ls -A helpers/bin 2>/dev/null)" ]; then
    echo "❌ No helpers found in helpers/bin"
    echo "   Please run organize-artifacts.sh first"
    exit 1
fi

echo "✅ Helpers available:"
ls -la helpers/bin/

# Setup Python environment
source workenv/flavor_*/bin/activate || {
    echo "⚠️ Workenv not activated, setting up..."
    uv venv workenv/flavor_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m)
    source workenv/flavor_*/bin/activate
    uv pip install -e .[dev]
}

# Export helper paths for tests
export FLAVOR_GO_LAUNCHER="$(pwd)/helpers/bin/flavor-go-launcher"
export FLAVOR_GO_BUILDER="$(pwd)/helpers/bin/flavor-go-builder"
export FLAVOR_RS_LAUNCHER="$(pwd)/helpers/bin/flavor-rs-launcher"
export FLAVOR_RS_BUILDER="$(pwd)/helpers/bin/flavor-rs-builder"

# Run tests with coverage
echo "🚀 Running pytest -m \"$TEST_MARK\""
pytest tests/ -m "$TEST_MARK" \
    --cov=src/flavor \
    --cov-report=xml:coverage-$TEST_MARK.xml \
    --cov-report=term \
    --tb=short \
    -v

echo "✅ Tests completed. Coverage saved to coverage-$TEST_MARK.xml"