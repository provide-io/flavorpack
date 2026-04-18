#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Combine Go, Rust, and tastesh helper artifacts into a single zip.
# Usage: ci/combine-helpers.sh <artifacts_dir> <output_dir> <version>

set -euo pipefail

ARTIFACTS_DIR="${1:?artifacts_dir required}"
OUTPUT_DIR="${2:?output_dir required}"
VERSION="${3:?version required}"

mkdir -p "$OUTPUT_DIR" all-helpers

# Collect Go + Rust helper zips
for platform_dir in "$ARTIFACTS_DIR"/flavor-*helpers-*; do
    [ -d "$platform_dir" ] && cp "$platform_dir"/*.zip "$OUTPUT_DIR/" || true
done

for zip in "$OUTPUT_DIR"/*.zip; do
    [ -f "$zip" ] && unzip -o "$zip" -d all-helpers/
done

# Collect tastesh binaries (uploaded as raw files, not zips)
for tastesh_dir in "$ARTIFACTS_DIR"/flavor-tastesh-*; do
    [ -d "$tastesh_dir" ] && cp "$tastesh_dir"/flavor-tastesh-* all-helpers/ || true
done

zip -r "$OUTPUT_DIR/flavor-helpers-${VERSION}-all.zip" all-helpers/
echo "📦 Combined artifacts:"
ls -la "$OUTPUT_DIR/"
