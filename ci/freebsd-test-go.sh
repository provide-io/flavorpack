#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Run Go test suite inside the FreeBSD VM.
# Usage: freebsd-test-go.sh

set -eo pipefail

echo "🧪 Running Go test suite..."
cd src/flavor-go
go test ./... -count=1 -timeout=300s
cd ../..
echo "✅ Go tests passed"
