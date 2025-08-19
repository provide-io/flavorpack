#!/bin/bash
set -e

# Test workflows locally with act
# Usage: .github/scripts/test-with-act.sh [workflow] [event]

WORKFLOW="${1:-main-pipeline}"
EVENT="${2:-workflow_dispatch}"

echo "🎬 Testing workflow: $WORKFLOW with event: $EVENT"

# Ensure cache directories exist
mkdir -p ~/.cache/act
mkdir -p ~/.cache/actcache
mkdir -p ~/.cache/act-artifacts

case "$WORKFLOW" in
    platform-helpers)
        echo "🔨 Testing platform-helpers workflow..."
        act $EVENT \
            -W .github/workflows/platform-helpers.yml \
            --env-file .act-env \
            -P .act-platforms \
            --input force_rebuild=false
        ;;
        
    main-pipeline)
        echo "🎯 Testing main-pipeline workflow..."
        act $EVENT \
            -W .github/workflows/main-pipeline.yml \
            --env-file .act-env \
            -P .act-platforms \
            --input skip_helpers=false \
            --input fast_mode=true \
            --input platforms=linux
        ;;
        
    act-test)
        echo "🧪 Testing act-test workflow..."
        act $EVENT \
            -W .github/workflows/act-test.yml \
            --env-file .act-env \
            -P .act-platforms
        ;;
        
    list)
        echo "📋 Available workflows:"
        act -l --env-file .act-env
        ;;
        
    dry)
        echo "🔍 Dry run for $2..."
        act -n $EVENT \
            -W .github/workflows/${2:-main-pipeline.yml} \
            --env-file .act-env \
            -P .act-platforms
        ;;
        
    *)
        echo "❌ Unknown workflow: $WORKFLOW"
        echo "Available options:"
        echo "  platform-helpers - Test helper builds"
        echo "  main-pipeline    - Test main CI pipeline"
        echo "  act-test        - Test local act workflow"
        echo "  list            - List all workflows"
        echo "  dry <workflow>  - Dry run a workflow"
        exit 1
        ;;
esac

echo "✅ Workflow test completed"