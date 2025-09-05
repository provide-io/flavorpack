#!/bin/bash
# Cleanup script for flavorpack release preparation

set -e

echo "🧹 Preparing flavorpack for release..."
echo "====================================="

# Create archive directory for stale files
ARCHIVE_DIR="archive_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ARCHIVE_DIR"
echo "📁 Created archive directory: $ARCHIVE_DIR"

# Clear Python caches and build artifacts
echo ""
echo "🗑️  Clearing Python caches and build artifacts..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
rm -rf .pytest_cache
rm -rf .ruff_cache
rm -rf .cache
rm -f .coverage
rm -rf htmlcov

# Clear dist directories
echo "📦 Clearing dist directories..."
rm -rf dist/*
rm -rf build/*
rm -rf site/*  # mkdocs build output

# Clear test artifacts in helpers
echo "🧪 Clearing test artifacts in helpers..."
rm -rf helpers/pretaster/dist/*
rm -rf helpers/pretaster/logs/*
rm -rf helpers/pretaster/workenv/*
rm -rf helpers/taster/dist/*
rm -rf helpers/taster/logs/*
rm -rf helpers/taster/workenv/*

# Clear ingredients build artifacts
echo "🔧 Clearing ingredients build artifacts..."
rm -rf ingredients/flavor-go/dist/*
rm -rf ingredients/flavor-rs/target/release/*.d
rm -rf ingredients/flavor-rs/target/release/deps
rm -rf ingredients/flavor-rs/target/release/build
rm -rf ingredients/flavor-rs/target/release/examples
rm -rf ingredients/flavor-rs/target/release/incremental
rm -rf ingredients/flavor-go/pkg/psp/format_2025/*.test

# Clear workenv directories (keeping structure)
echo "💾 Clearing workenv caches..."
rm -rf workenv/*/
rm -rf /REDACTED_ABS_PATH*
rm -rf /REDACTED_ABS_PATH*
rm -rf /REDACTED_ABS_PATH*

# Move stale/temporary files to archive
echo ""
echo "📂 Moving stale files to archive..."

# Move old logs
if [ -d "logs" ] && [ "$(ls -A logs)" ]; then
    mv logs "$ARCHIVE_DIR/"
    mkdir logs
fi

# Move .venv if exists (should use workenv instead)
if [ -d ".venv" ]; then
    echo "  Moving .venv to archive (use workenv instead)"
    mv .venv "$ARCHIVE_DIR/"
fi

# Move any core dumps
if ls core* 1> /dev/null 2>&1; then
    echo "  Moving core dumps to archive"
    mv core* "$ARCHIVE_DIR/" 2>/dev/null || true
fi

# Move workenv core dumps
if [ -f "workenv/core" ]; then
    echo "  Moving workenv/core to archive"
    mv workenv/core "$ARCHIVE_DIR/"
fi

# Move terraform provider artifacts if any
if ls workenv/*.zip 1> /dev/null 2>&1; then
    echo "  Moving terraform artifacts to archive"
    mv workenv/*.zip "$ARCHIVE_DIR/"
fi

# Move any old terraform executables
if ls workenv/terraform-provider-* 1> /dev/null 2>&1; then
    echo "  Moving old terraform executables to archive"
    mv workenv/terraform-provider-* "$ARCHIVE_DIR/"
fi

# Clean up /tmp test artifacts
echo "🗑️  Clearing /tmp test artifacts..."
rm -rf /tmp/crypto_test
rm -rf /tmp/packager_test
rm -rf /tmp/packager_proof
rm -rf /tmp/test-*.psp
rm -rf /tmp/workenv-test.txt

# Clear pip cache for clean builds
echo "🐍 Clearing pip cache..."
pip cache purge 2>/dev/null || true

# Create fresh directories
echo ""
echo "📁 Creating fresh directories..."
mkdir -p dist
mkdir -p logs
mkdir -p helpers/pretaster/dist
mkdir -p helpers/pretaster/logs
mkdir -p helpers/taster/dist
mkdir -p helpers/taster/logs

# Summary
echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📊 Summary:"
echo "  • Cleared all Python caches and __pycache__ directories"
echo "  • Cleared all dist and build directories"
echo "  • Cleared test artifacts from helpers"
echo "  • Cleared workenv caches"
echo "  • Moved stale files to: $ARCHIVE_DIR"
echo "  • Cleared /tmp test artifacts"
echo "  • Created fresh directories"
echo ""
echo "🎉 Package is ready for release preparation!"
echo ""
echo "Next steps:"
echo "  1. Review files in $ARCHIVE_DIR and delete if not needed"
echo "  2. Run 'make build-ingredients' to rebuild binaries"
echo "  3. Run tests to ensure everything works"
echo "  4. Update VERSION file if needed"
echo "  5. Create release with 'make release'"