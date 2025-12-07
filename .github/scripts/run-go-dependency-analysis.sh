#!/bin/bash

set -e

echo "## 🐹 Go Dependency Analysis" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

cd src/flavor-go

# List dependencies
echo "### Direct Dependencies" >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY
go list -m all | head -30 >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY

# Module graph
go mod graph > go-mod-graph.txt

# Download dependencies for scanning
go mod download
