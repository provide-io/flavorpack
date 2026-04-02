#!/usr/bin/env bash
# Run Go test suite inside the FreeBSD VM.
# Usage: freebsd-test-go.sh

set -eo pipefail

echo "🧪 Running Go test suite..."
cd src/flavor-go
go test ./... -count=1 -timeout=300s
cd ../..
echo "✅ Go tests passed"
