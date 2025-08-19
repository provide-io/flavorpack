#!/bin/bash
set -e

# validate-workflows.sh - Validate GitHub Actions workflows syntax and structure
# This script checks workflows without actually running them

echo "======================================"
echo "🔍 GitHub Actions Workflow Validation"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Check for required tools
MISSING_TOOLS=()

if ! command -v yq &> /dev/null; then
    MISSING_TOOLS+=("yq")
fi

if ! command -v yamllint &> /dev/null; then
    MISSING_TOOLS+=("yamllint (optional)")
fi

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    print_color "$YELLOW" "⚠️  Some tools are not installed:"
    for tool in "${MISSING_TOOLS[@]}"; do
        print_color "$YELLOW" "   • $tool"
    done
    print_color "$YELLOW" "Install with: brew install yq yamllint"
fi

# Track validation results
PASSED=()
FAILED=()
WARNINGS=()

# Function to validate workflow structure
validate_workflow() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file" .yml)
    
    print_color "$BLUE" "\n📋 Validating: $workflow_name"
    
    # Check if file exists
    if [ ! -f "$workflow_file" ]; then
        print_color "$RED" "   ❌ File not found: $workflow_file"
        FAILED+=("$workflow_name: file not found")
        return 1
    fi
    
    # Basic YAML syntax check
    if command -v yq &> /dev/null; then
        if ! yq eval '.' "$workflow_file" > /dev/null 2>&1; then
            print_color "$RED" "   ❌ Invalid YAML syntax"
            FAILED+=("$workflow_name: invalid YAML")
            return 1
        fi
        print_color "$GREEN" "   ✅ Valid YAML syntax"
    fi
    
    # Check required workflow keys
    local has_name=$(grep -E '^name:' "$workflow_file" | head -1)
    local has_on=$(grep -E '^on:' "$workflow_file" | head -1)
    local has_jobs=$(grep -E '^jobs:' "$workflow_file" | head -1)
    
    if [ -z "$has_name" ]; then
        print_color "$RED" "   ❌ Missing 'name' field"
        FAILED+=("$workflow_name: missing name")
        return 1
    fi
    
    if [ -z "$has_on" ]; then
        print_color "$RED" "   ❌ Missing 'on' field (triggers)"
        FAILED+=("$workflow_name: missing triggers")
        return 1
    fi
    
    if [ -z "$has_jobs" ]; then
        print_color "$RED" "   ❌ Missing 'jobs' field"
        FAILED+=("$workflow_name: missing jobs")
        return 1
    fi
    
    print_color "$GREEN" "   ✅ Required fields present"
    
    # Check for specific OS versions (not -latest)
    if grep -E 'runs-on:.*-latest' "$workflow_file" > /dev/null; then
        print_color "$YELLOW" "   ⚠️  Found '-latest' OS version (should use specific versions)"
        WARNINGS+=("$workflow_name: uses -latest OS")
    fi
    
    # Check for proper OS versions
    local has_ubuntu_24=$(grep -E 'ubuntu-24\.04' "$workflow_file")
    local has_macos_15=$(grep -E 'macos-15' "$workflow_file")
    local has_windows_2025=$(grep -E 'windows-2025' "$workflow_file")
    
    if [ -n "$has_ubuntu_24" ] || [ -n "$has_macos_15" ] || [ -n "$has_windows_2025" ]; then
        print_color "$GREEN" "   ✅ Uses specific OS versions"
    fi
    
    # Check for artifact upload/download actions
    if grep -E 'actions/upload-artifact' "$workflow_file" > /dev/null; then
        print_color "$GREEN" "   ✅ Uploads artifacts"
    fi
    
    if grep -E 'actions/download-artifact' "$workflow_file" > /dev/null; then
        print_color "$GREEN" "   ✅ Downloads artifacts"
    fi
    
    # Check for matrix strategy (for cross-platform builds)
    if grep -E 'strategy:' "$workflow_file" > /dev/null && grep -E 'matrix:' "$workflow_file" > /dev/null; then
        print_color "$GREEN" "   ✅ Uses matrix strategy"
        
        # Count matrix combinations
        if command -v yq &> /dev/null; then
            local matrix_count=$(yq eval '.jobs.*.strategy.matrix.include | length' "$workflow_file" 2>/dev/null | grep -v null | paste -sd+ | bc 2>/dev/null || echo "0")
            if [ "$matrix_count" -gt 0 ]; then
                print_color "$BLUE" "   ℹ️  Matrix combinations: $matrix_count"
            fi
        fi
    fi
    
    PASSED+=("$workflow_name")
    return 0
}

# Function to check cross-workflow dependencies
check_workflow_dependencies() {
    print_color "$BLUE" "\n🔗 Checking workflow dependencies..."
    
    # Check if helpers-build.yml calls the other workflows
    if grep -E 'uses:.*helpers-go\.yml' .github/workflows/helpers-build.yml > /dev/null; then
        print_color "$GREEN" "   ✅ helpers-build.yml calls helpers-go.yml"
    else
        print_color "$RED" "   ❌ helpers-build.yml doesn't call helpers-go.yml"
        FAILED+=("workflow dependency: missing go")
    fi
    
    if grep -E 'uses:.*helpers-rust\.yml' .github/workflows/helpers-build.yml > /dev/null; then
        print_color "$GREEN" "   ✅ helpers-build.yml calls helpers-rust.yml"
    else
        print_color "$RED" "   ❌ helpers-build.yml doesn't call helpers-rust.yml"
        FAILED+=("workflow dependency: missing rust")
    fi
}

# Function to validate artifact structure
check_artifact_structure() {
    print_color "$BLUE" "\n📦 Checking artifact naming conventions..."
    
    # Check for proper artifact names in workflows
    for workflow in .github/workflows/helpers-*.yml; do
        if grep -E 'flavor-(go|rs)-helpers-(linux|darwin|windows)_(amd64|arm64)' "$workflow" > /dev/null; then
            print_color "$GREEN" "   ✅ $(basename $workflow): correct artifact naming"
        fi
    done
}

# Main validation
print_color "$GREEN" "🚀 Starting workflow validation...\n"

# Validate each workflow
for workflow in .github/workflows/helpers-*.yml; do
    if [ -f "$workflow" ]; then
        validate_workflow "$workflow"
    fi
done

# Check dependencies
check_workflow_dependencies

# Check artifact structure
check_artifact_structure

# Use act for deeper validation if available
if command -v act &> /dev/null; then
    print_color "$BLUE" "\n🎭 Using act for workflow structure validation..."
    
    for workflow in .github/workflows/helpers-*.yml; do
        if [ -f "$workflow" ]; then
            workflow_name=$(basename "$workflow" .yml)
            print_color "$BLUE" "\n   Checking $workflow_name jobs:"
            
            # List jobs without running them
            if act -l -W "$workflow" 2>/dev/null | grep -E '^[0-9]' > /dev/null; then
                act -l -W "$workflow" 2>/dev/null | grep -E '^[0-9]' | while read -r line; do
                    job_name=$(echo "$line" | awk '{print $3, $4, $5}' | sed 's/[[:space:]]*$//')
                    print_color "$GREEN" "      ✅ $job_name"
                done
            else
                print_color "$RED" "      ❌ No jobs found or workflow invalid"
                FAILED+=("$workflow_name: act validation failed")
            fi
        fi
    done
fi

# Print summary
echo ""
print_color "$BLUE" "======================================"
print_color "$BLUE" "📊 Validation Summary"
print_color "$BLUE" "======================================"

if [ ${#PASSED[@]} -gt 0 ]; then
    print_color "$GREEN" "\n✅ Passed (${#PASSED[@]}):"
    for item in "${PASSED[@]}"; do
        print_color "$GREEN" "   • $item"
    done
fi

if [ ${#WARNINGS[@]} -gt 0 ]; then
    print_color "$YELLOW" "\n⚠️  Warnings (${#WARNINGS[@]}):"
    for item in "${WARNINGS[@]}"; do
        print_color "$YELLOW" "   • $item"
    done
fi

if [ ${#FAILED[@]} -gt 0 ]; then
    print_color "$RED" "\n❌ Failed (${#FAILED[@]}):"
    for item in "${FAILED[@]}"; do
        print_color "$RED" "   • $item"
    done
fi

# Summary counts
echo ""
print_color "$BLUE" "Total workflows validated: $((${#PASSED[@]} + ${#FAILED[@]}))"
print_color "$GREEN" "Passed: ${#PASSED[@]}"
print_color "$YELLOW" "Warnings: ${#WARNINGS[@]}"
print_color "$RED" "Failed: ${#FAILED[@]}"

# Exit code
if [ ${#FAILED[@]} -gt 0 ]; then
    print_color "$RED" "\n❌ Validation failed!"
    exit 1
else
    print_color "$GREEN" "\n✅ All validations passed!"
    exit 0
fi