#!/bin/bash

set -e

cd src/flavor-go
echo "## 🐹 Go Code Quality" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# golangci-lint
echo "### GolangCI-Lint Analysis" >> $GITHUB_STEP_SUMMARY
if golangci-lint run --out-format=json > golangci.json 2>&1; then
  echo "✅ GolangCI-Lint passed" >> $GITHUB_STEP_SUMMARY
else
  golangci-lint run 2>&1 | tee golangci.log || true
  echo "⚠️ GolangCI-Lint found issues:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  head -50 golangci.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
fi

# Static check
echo "### Static Analysis" >> $GITHUB_STEP_SUMMARY
if staticcheck ./... 2>&1 | tee staticcheck.log; then
  echo "✅ Staticcheck passed" >> $GITHUB_STEP_SUMMARY
else
  echo "⚠️ Staticcheck found issues:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat staticcheck.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
fi

# Go vet
echo "### Go Vet" >> $GITHUB_STEP_SUMMARY
if go vet ./... 2>&1 | tee govet.log; then
  echo "✅ Go vet passed" >> $GITHUB_STEP_SUMMARY
else
  echo "⚠️ Go vet found issues:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat govet.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
fi

# Cyclomatic complexity
echo "### Cyclomatic Complexity" >> $GITHUB_STEP_SUMMARY
gocyclo -over 10 . 2>&1 | tee gocyclo.log || true
if [ -s gocyclo.log ]; then
  echo "⚠️ High complexity functions:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat gocyclo.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ All functions have acceptable complexity" >> $GITHUB_STEP_SUMMARY
fi
