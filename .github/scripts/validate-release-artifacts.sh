#!/bin/bash
set -euo pipefail

# Validate release artifacts before publishing
# Usage: validate-release-artifacts.sh <artifacts_dir>

ARTIFACTS_DIR="${1:-release}"

echo "🔍 Validating release artifacts in ${ARTIFACTS_DIR}"

# Check directory exists
if [ ! -d "$ARTIFACTS_DIR" ]; then
    echo "❌ Artifacts directory not found: $ARTIFACTS_DIR"
    exit 1
fi

cd "$ARTIFACTS_DIR"

# Initialize counters
WHEEL_COUNT=0
PSP_COUNT=0
ERRORS=0

echo ""
echo "📦 Checking Python wheels..."

# Expected platforms for wheels
EXPECTED_WHEEL_PLATFORMS=(
    "manylinux2014_x86_64"
    "manylinux2014_aarch64"
    "macosx_10_9_x86_64"
    "macosx_11_0_arm64"
)

# Check wheels
for platform in "${EXPECTED_WHEEL_PLATFORMS[@]}"; do
    if ls *"${platform}.whl" >/dev/null 2>&1; then
        for wheel in *"${platform}.whl"; do
            echo "  ✅ Found: $wheel"
            
            # Verify it's a valid zip file
            if unzip -t "$wheel" >/dev/null 2>&1; then
                echo "     ✓ Valid wheel format"
            else
                echo "     ❌ Invalid wheel format!"
                ((ERRORS++))
            fi
            
            # Check size (should be > 1MB for platform wheels with helpers)
            size=$(du -k "$wheel" | cut -f1)
            if [ "$size" -gt 1024 ]; then
                echo "     ✓ Size: ${size}KB"
            else
                echo "     ⚠️ Unusually small wheel: ${size}KB"
            fi
            
            ((WHEEL_COUNT++))
        done
    else
        echo "  ⚠️ Missing wheel for platform: ${platform}"
    fi
done

echo ""
echo "📦 Checking PSP packages..."

# Expected platforms for PSP
EXPECTED_PSP_PLATFORMS=(
    "linux_amd64"
    "linux_arm64"
    "darwin_amd64"
    "darwin_arm64"
)

# Check PSP packages
for platform in "${EXPECTED_PSP_PLATFORMS[@]}"; do
    if ls *"${platform}.psp" >/dev/null 2>&1; then
        for psp in *"${platform}.psp"; do
            echo "  ✅ Found: $psp"
            
            # Check if executable
            if [ -x "$psp" ]; then
                echo "     ✓ Executable"
            else
                echo "     ⚠️ Not marked executable"
                chmod +x "$psp"
            fi
            
            # Check size (should be > 10MB for PSP with Python runtime)
            size=$(du -k "$psp" | cut -f1)
            if [ "$size" -gt 10240 ]; then
                echo "     ✓ Size: ${size}KB"
            else
                echo "     ⚠️ Unusually small PSP: ${size}KB"
            fi
            
            # Check for magic footer (🪄)
            if tail -c 8 "$psp" | grep -q "🪄" >/dev/null 2>&1; then
                echo "     ✓ Valid PSP format (has magic footer)"
            else
                echo "     ❌ Invalid PSP format (missing magic footer)!"
                ((ERRORS++))
            fi
            
            ((PSP_COUNT++))
        done
    else
        echo "  ℹ️ No PSP for platform: ${platform}"
    fi
done

echo ""
echo "📋 Checking checksums file..."

if [ -f "checksums.txt" ]; then
    echo "  ✅ Found checksums.txt"
    
    # Verify checksums
    if command -v sha256sum >/dev/null 2>&1; then
        # Filter out markdown headers from checksums.txt
        grep -E "^[a-f0-9]{64}" checksums.txt > /tmp/checksums_clean.txt || true
        
        if [ -s /tmp/checksums_clean.txt ]; then
            if sha256sum -c /tmp/checksums_clean.txt >/dev/null 2>&1; then
                echo "     ✓ All checksums valid"
            else
                echo "     ❌ Checksum verification failed!"
                ((ERRORS++))
            fi
        else
            echo "     ⚠️ No valid checksums found in file"
        fi
        
        rm -f /tmp/checksums_clean.txt
    else
        echo "     ⚠️ sha256sum not available, skipping verification"
    fi
else
    echo "  ❌ Missing checksums.txt"
    ((ERRORS++))
fi

echo ""
echo "📋 Checking release notes..."

if [ -f "release-notes.md" ]; then
    echo "  ✅ Found release-notes.md"
    
    # Check for required sections
    for section in "Quick Install" "Release Assets" "What's New"; do
        if grep -q "$section" release-notes.md; then
            echo "     ✓ Has '$section' section"
        else
            echo "     ⚠️ Missing '$section' section"
        fi
    done
else
    echo "  ❌ Missing release-notes.md"
    ((ERRORS++))
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Validation Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Python Wheels: ${WHEEL_COUNT}"
echo "  PSP Packages: ${PSP_COUNT}"
echo "  Errors: ${ERRORS}"
echo ""

if [ "$ERRORS" -eq 0 ]; then
    if [ "$WHEEL_COUNT" -ge 4 ] && [ "$PSP_COUNT" -ge 4 ]; then
        echo "✅ All release artifacts validated successfully!"
        exit 0
    else
        echo "⚠️ Some expected artifacts may be missing"
        echo "   Expected: 4+ wheels, 4+ PSP packages"
        exit 0  # Warning only, don't fail
    fi
else
    echo "❌ Validation failed with ${ERRORS} error(s)"
    exit 1
fi