#!/bin/bash
set -e

# test-workflows-local.sh - Test GitHub Actions workflows locally using act
# Requires: act (https://github.com/nektos/act)

echo "======================================"
echo "🎭 GitHub Actions Local Testing with act"
echo "======================================"

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo "❌ act is not installed. Please install it first:"
    echo "   brew install act"
    echo "   or"
    echo "   curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
    exit 1
fi

# Configuration
ACT_BINARY="${ACT_BINARY:-act}"
WORKFLOW_DIR=".github/workflows"
RESULTS_DIR="act-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to test a specific workflow
test_workflow() {
    local workflow_file=$1
    local workflow_name=$2
    local job_filter=$3
    
    print_color "$BLUE" "\n📋 Testing: $workflow_name"
    print_color "$BLUE" "   File: $workflow_file"
    print_color "$BLUE" "   Job: ${job_filter:-all}"
    
    local output_file="$RESULTS_DIR/${workflow_name}_${TIMESTAMP}.log"
    
    # Build act command
    local act_cmd="$ACT_BINARY"
    
    # Add workflow file
    act_cmd="$act_cmd -W $workflow_file"
    
    # Add job filter if specified
    if [ -n "$job_filter" ]; then
        act_cmd="$act_cmd -j $job_filter"
    fi
    
    # Add common flags
    act_cmd="$act_cmd --artifact-server-path $RESULTS_DIR/artifacts"
    act_cmd="$act_cmd workflow_dispatch"
    
    # Run act and capture output
    print_color "$YELLOW" "   Running: $act_cmd"
    
    if $act_cmd 2>&1 | tee "$output_file"; then
        print_color "$GREEN" "   ✅ $workflow_name completed successfully"
        return 0
    else
        print_color "$RED" "   ❌ $workflow_name failed"
        print_color "$RED" "   Check log: $output_file"
        return 1
    fi
}

# Function to list available jobs in a workflow
list_workflow_jobs() {
    local workflow_file=$1
    print_color "$BLUE" "\n📑 Jobs in $workflow_file:"
    $ACT_BINARY -W "$workflow_file" -l 2>/dev/null | grep -E '^Stage|^ID' || true
}

# Create results directory
mkdir -p "$RESULTS_DIR/artifacts"

# Parse command line arguments
WORKFLOW_FILTER=""
JOB_FILTER=""
LIST_ONLY=false
QUICK_TEST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -w|--workflow)
            WORKFLOW_FILTER="$2"
            shift 2
            ;;
        -j|--job)
            JOB_FILTER="$2"
            shift 2
            ;;
        -l|--list)
            LIST_ONLY=true
            shift
            ;;
        -q|--quick)
            QUICK_TEST=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -w, --workflow NAME   Test specific workflow (go, rust, build)"
            echo "  -j, --job NAME        Test specific job within workflow"
            echo "  -l, --list            List available workflows and jobs"
            echo "  -q, --quick           Quick test (lint jobs only)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Test all workflows"
            echo "  $0 -w go              # Test Go helpers workflow"
            echo "  $0 -w rust -j lint    # Test Rust lint job only"
            echo "  $0 -q                 # Quick test of lint jobs"
            echo "  $0 -l                 # List all workflows and jobs"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# List mode
if [ "$LIST_ONLY" = true ]; then
    print_color "$GREEN" "🔍 Available workflows and jobs:\n"
    
    for workflow in "$WORKFLOW_DIR"/helpers-*.yml; do
        if [ -f "$workflow" ]; then
            list_workflow_jobs "$workflow"
        fi
    done
    exit 0
fi

# Main testing logic
print_color "$GREEN" "🚀 Starting workflow tests...\n"

# Track results
FAILED_TESTS=()
PASSED_TESTS=()

# Quick test mode - only test lint jobs
if [ "$QUICK_TEST" = true ]; then
    print_color "$YELLOW" "⚡ Quick test mode - testing lint jobs only\n"
    
    if test_workflow "$WORKFLOW_DIR/helpers-go.yml" "go-helpers-lint" "lint"; then
        PASSED_TESTS+=("go-helpers-lint")
    else
        FAILED_TESTS+=("go-helpers-lint")
    fi
    
    if test_workflow "$WORKFLOW_DIR/helpers-rust.yml" "rust-helpers-lint" "lint"; then
        PASSED_TESTS+=("rust-helpers-lint")
    else
        FAILED_TESTS+=("rust-helpers-lint")
    fi
    
# Test specific workflow
elif [ -n "$WORKFLOW_FILTER" ]; then
    case "$WORKFLOW_FILTER" in
        go)
            test_workflow "$WORKFLOW_DIR/helpers-go.yml" "go-helpers" "$JOB_FILTER"
            ;;
        rust)
            test_workflow "$WORKFLOW_DIR/helpers-rust.yml" "rust-helpers" "$JOB_FILTER"
            ;;
        build|main)
            test_workflow "$WORKFLOW_DIR/helpers-build.yml" "helpers-build" "$JOB_FILTER"
            ;;
        *)
            print_color "$RED" "Unknown workflow: $WORKFLOW_FILTER"
            print_color "$YELLOW" "Available: go, rust, build"
            exit 1
            ;;
    esac
    
# Test all workflows
else
    print_color "$YELLOW" "📦 Testing all helper workflows...\n"
    
    # Test individual language workflows first
    for test_case in \
        "helpers-go.yml:go-helpers:lint" \
        "helpers-go.yml:go-helpers:security" \
        "helpers-go.yml:go-helpers:test" \
        "helpers-rust.yml:rust-helpers:lint" \
        "helpers-rust.yml:rust-helpers:security" \
        "helpers-rust.yml:rust-helpers:test"
    do
        IFS=':' read -r workflow name job <<< "$test_case"
        
        if test_workflow "$WORKFLOW_DIR/$workflow" "$name-$job" "$job"; then
            PASSED_TESTS+=("$name-$job")
        else
            FAILED_TESTS+=("$name-$job")
        fi
    done
fi

# Print summary
echo ""
print_color "$BLUE" "======================================"
print_color "$BLUE" "📊 Test Summary"
print_color "$BLUE" "======================================"

if [ ${#PASSED_TESTS[@]} -gt 0 ]; then
    print_color "$GREEN" "\n✅ Passed Tests (${#PASSED_TESTS[@]}):"
    for test in "${PASSED_TESTS[@]}"; do
        print_color "$GREEN" "   • $test"
    done
fi

if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
    print_color "$RED" "\n❌ Failed Tests (${#FAILED_TESTS[@]}):"
    for test in "${FAILED_TESTS[@]}"; do
        print_color "$RED" "   • $test"
    done
fi

# Check artifacts
if [ -d "$RESULTS_DIR/artifacts" ]; then
    print_color "$BLUE" "\n📦 Artifacts generated:"
    find "$RESULTS_DIR/artifacts" -type f -name "*.zip" -o -name "*.tar.gz" 2>/dev/null | while read -r artifact; do
        print_color "$BLUE" "   • $(basename "$artifact")"
    done
fi

print_color "$BLUE" "\n📁 Results saved to: $RESULTS_DIR"

# Exit with appropriate code
if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
    exit 1
else
    exit 0
fi