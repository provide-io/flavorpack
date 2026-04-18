#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Print Rust build environment info for CI debugging.
# Must be run from src/flavor-rs/.

set -eo pipefail

echo "🔍 Rust build environment"
echo "   Working directory: $(pwd)"
echo "   Rust toolchain:    $(rustc --version)"
echo "   Cargo:             $(cargo --version)"
echo ""
echo "📄 Cargo.toml:"
cat Cargo.toml
echo ""
echo "📁 src/bin/:"
ls -la src/bin/ 2>/dev/null || echo "   (not found)"
