#!/bin/bash
set -e

# Local testing script for GitHub Actions workflows
# Usage: .github/scripts/test-local.sh [workflow] [options]

WORKFLOW="${1:-main-pipeline}"
SKIP_TESTS="${2:-false}"
SKIP_PACKAGING="${3:-false}"

echo "🚀 Triggering workflow: $WORKFLOW"
echo "   Skip tests: $SKIP_TESTS"
echo "   Skip packaging: $SKIP_PACKAGING"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ gh CLI is not installed. Please install it first:"
    echo "   brew install gh  # macOS"
    echo "   https://cli.github.com/  # Other platforms"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub. Run: gh auth login"
    exit 1
fi

case "$WORKFLOW" in
    main|main-pipeline)
        echo "📦 Running main pipeline..."
        gh workflow run "main-pipeline.yml" \
            -f skip_tests="$SKIP_TESTS" \
            -f skip_packaging="$SKIP_PACKAGING"
        ;;
    
    helpers|build-helpers)
        echo "🔨 Building helpers..."
        gh workflow run "helpers-build.yml"
        ;;
    
    flavor-tests|tests)
        echo "🧪 Running Flavor tests..."
        gh workflow run "flavor-tests.yml"
        ;;
    
    packaging|flavor-packaging)
        echo "📦 Running packaging tests..."
        gh workflow run "flavor-packaging.yml"
        ;;
    
    integration)
        echo "🔧 Running integration tests..."
        gh workflow run "integration-tests.yml"
        ;;
    
    *)
        echo "❌ Unknown workflow: $WORKFLOW"
        echo "Available workflows:"
        echo "  main-pipeline    - Main CI pipeline"
        echo "  helpers          - Build Go/Rust helpers"
        echo "  flavor-tests     - Run Flavor core tests"
        echo "  packaging        - Run packaging tests"
        echo "  integration      - Run integration tests"
        exit 1
        ;;
esac

# Wait a moment for the workflow to start
sleep 3

# Show recent runs
echo ""
echo "📊 Recent workflow runs:"
gh run list --limit 5

echo ""
echo "💡 To watch the run:"
echo "   gh run watch"
echo ""
echo "💡 To see logs:"
echo "   gh run view --log"