#!/usr/bin/env bash
#
# pr-pretaster.sh - Build helpers from source and run the pretaster suite.
#
# Pull requests never reach the pretaster/taster pipelines: 01 Helper Prep is
# workflow_dispatch-only and 02/03/04 are workflow_run-gated to main/develop.
# This script is the end-to-end coverage a PR gets, so it builds the helpers
# under test rather than downloading them from a prior pipeline stage.
#
# Usage: pr-pretaster.sh [test_target]

set -euo pipefail

TEST_TARGET="${1:-test}"

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "🔨 Building Go and Rust helpers from source..."
# tests/pretaster's build-helpers target no-ops whenever CI is set, assuming a
# prior pipeline stage published the binaries. This job has no prior stage, so
# invoke the build directly. For the same reason `make all` is not used here:
# its build step would be skipped and the suite would test stale or absent
# binaries.
./build.sh

echo "📦 Helpers built:"
ls -la dist/bin/

# The security suites need the flavor CLI for the policy tests. Without a venv
# they skipped it silently, so CI was not running those checks at all.
echo "🐍 Installing the flavor CLI..."
uv sync --quiet

echo "🧪 Running pretaster suite (${TEST_TARGET})..."
make -C tests/pretaster "${TEST_TARGET}"
