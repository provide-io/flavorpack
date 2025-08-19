#!/bin/bash
set -e

# Download helper artifacts from the latest successful helper pipeline run
# If artifacts don't exist, optionally trigger the helper pipeline and wait
# Usage: .github/scripts/download-helper-artifacts.sh [--trigger-if-missing] [--output-dir DIR]

TRIGGER_IF_MISSING=false
OUTPUT_DIR="helpers"
WORKFLOW_NAME="helper-pipeline.yml"
ARTIFACT_NAME_PREFIX="flavor-helpers"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --trigger-if-missing)
            TRIGGER_IF_MISSING=true
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--trigger-if-missing] [--output-dir DIR]"
            echo "  --trigger-if-missing  Trigger helper pipeline if artifacts not found"
            echo "  --output-dir DIR      Directory to extract artifacts to (default: helpers)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🔍 Looking for helper artifacts..."
echo "   Workflow: $WORKFLOW_NAME"
echo "   Output directory: $OUTPUT_DIR"

# Get the latest successful run of the helper pipeline
echo "📥 Checking for latest successful helper pipeline run..."

# Find the latest successful run
LATEST_RUN=$(gh run list \
    --workflow="$WORKFLOW_NAME" \
    --status=success \
    --limit=1 \
    --json=databaseId,createdAt,headSha,headBranch \
    --jq='.[0]' 2>/dev/null || echo "{}")

if [ "$LATEST_RUN" = "{}" ] || [ -z "$LATEST_RUN" ]; then
    echo "❌ No successful helper pipeline runs found"
    
    if [ "$TRIGGER_IF_MISSING" = true ]; then
        echo "🚀 Triggering helper pipeline..."
        
        # Trigger the helper pipeline
        gh workflow run "$WORKFLOW_NAME" --ref="$(git branch --show-current)"
        
        # Wait for the run to start
        echo "⏳ Waiting for pipeline to start..."
        sleep 10
        
        # Get the run ID of the triggered pipeline
        RUN_ID=$(gh run list \
            --workflow="$WORKFLOW_NAME" \
            --limit=1 \
            --json=databaseId \
            --jq='.[0].databaseId')
        
        if [ -z "$RUN_ID" ]; then
            echo "❌ Failed to trigger helper pipeline"
            exit 1
        fi
        
        echo "📊 Pipeline started: Run ID $RUN_ID"
        echo "⏳ Waiting for completion..."
        
        # Wait for the pipeline to complete
        gh run watch "$RUN_ID" --exit-status
        
        if [ $? -ne 0 ]; then
            echo "❌ Helper pipeline failed"
            exit 1
        fi
        
        echo "✅ Helper pipeline completed successfully"
        
        # Update LATEST_RUN with the new run info
        LATEST_RUN=$(gh run view "$RUN_ID" --json=databaseId,createdAt,headSha,headBranch)
    else
        echo "❌ No artifacts available. Use --trigger-if-missing to build them."
        exit 1
    fi
fi

# Extract run information
RUN_ID=$(echo "$LATEST_RUN" | jq -r '.databaseId')
HEAD_SHA=$(echo "$LATEST_RUN" | jq -r '.headSha')
HEAD_BRANCH=$(echo "$LATEST_RUN" | jq -r '.headBranch')
CREATED_AT=$(echo "$LATEST_RUN" | jq -r '.createdAt')

echo "✅ Found successful run:"
echo "   Run ID: $RUN_ID"
echo "   Branch: $HEAD_BRANCH"
echo "   SHA: ${HEAD_SHA:0:8}"
echo "   Created: $CREATED_AT"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Download artifacts
echo "📥 Downloading artifacts..."

# Get list of artifacts from the run
ARTIFACTS=$(gh api \
    "/repos/${GITHUB_REPOSITORY}/actions/runs/${RUN_ID}/artifacts" \
    --jq '.artifacts[] | select(.name | startswith("'"$ARTIFACT_NAME_PREFIX"'")) | {id, name}')

if [ -z "$ARTIFACTS" ]; then
    echo "❌ No helper artifacts found in run $RUN_ID"
    exit 1
fi

# Download each artifact
echo "$ARTIFACTS" | while read -r artifact; do
    if [ -z "$artifact" ]; then
        continue
    fi
    
    ARTIFACT_ID=$(echo "$artifact" | jq -r '.id')
    ARTIFACT_NAME=$(echo "$artifact" | jq -r '.name')
    
    echo "  📦 Downloading $ARTIFACT_NAME..."
    
    # Download using gh CLI
    gh api \
        "/repos/${GITHUB_REPOSITORY}/actions/artifacts/${ARTIFACT_ID}/zip" \
        --output="${OUTPUT_DIR}/${ARTIFACT_NAME}.zip"
    
    # Extract the artifact
    echo "  📂 Extracting $ARTIFACT_NAME..."
    unzip -q -o "${OUTPUT_DIR}/${ARTIFACT_NAME}.zip" -d "${OUTPUT_DIR}/"
    rm "${OUTPUT_DIR}/${ARTIFACT_NAME}.zip"
done

# List what was downloaded
echo "📋 Downloaded artifacts:"
ls -la "$OUTPUT_DIR"/*.zip 2>/dev/null || ls -la "$OUTPUT_DIR"/ | head -10

echo "✅ Helper artifacts downloaded successfully to $OUTPUT_DIR"

# Export information for other steps
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "run_id=$RUN_ID" >> "$GITHUB_OUTPUT"
    echo "head_sha=$HEAD_SHA" >> "$GITHUB_OUTPUT"
    echo "head_branch=$HEAD_BRANCH" >> "$GITHUB_OUTPUT"
    echo "created_at=$CREATED_AT" >> "$GITHUB_OUTPUT"
fi