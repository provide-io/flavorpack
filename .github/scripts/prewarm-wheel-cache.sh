#!/bin/bash
set -euo pipefail

# Pre-warm a local wheel cache directory for offline PSPF builds.
#
# flavor pack spawns subprocesses (pip/uv) that cannot reach PyPI on Windows
# GHA runners (getaddrinfo fails in subprocess context). This script runs in
# the workflow context where network is available, downloads all required wheels
# into a local directory, and exports FLAVOR_WHEEL_CACHE so that the flavor pack
# subprocess can find them via pip --no-index --find-links.
#
# Usage: prewarm-wheel-cache.sh <wheel-cache-dir>
#
# Outputs:
#   FLAVOR_WHEEL_CACHE env var written to $GITHUB_ENV (if set)
#   <wheel-cache-dir>/ populated with .whl files

WHEEL_CACHE_DIR="${1:-${GITHUB_WORKSPACE:-.}/.flavor-wheel-cache}"

echo "=== Pre-warming wheel cache ==="
echo "Cache dir: ${WHEEL_CACHE_DIR}"

mkdir -p "${WHEEL_CACHE_DIR}"

# Export pinned requirements from lockfile (no hashes, no dev deps)
RAW_REQS="${WHEEL_CACHE_DIR}/requirements-raw.txt"
REQS="${WHEEL_CACHE_DIR}/requirements.txt"

uv export --frozen --no-dev --no-hashes --output-file "${RAW_REQS}"

# Strip editable (-e .) and local file:// lines — pip download doesn't support them
grep -v '^-e \|file://' "${RAW_REQS}" > "${REQS}" || true

WHEEL_COUNT=$(wc -l < "${REQS}")
echo "Requirements: ${WHEEL_COUNT} lines"

# Download actual .whl files using pip (which has network access in workflow context).
# Use `uv run --no-project --with pip` so uv manages Python and pip without pulling
# in the current project's dev dependencies.
uv run --no-project --with pip python -m pip download \
  -r "${REQS}" \
  --dest "${WHEEL_CACHE_DIR}" \
  --quiet

DOWNLOADED=$(ls "${WHEEL_CACHE_DIR}"/*.whl 2>/dev/null | wc -l)
echo "✅ Downloaded ${DOWNLOADED} wheels to ${WHEEL_CACHE_DIR}"

# Export the cache dir for flavor pack subprocess to find via FLAVOR_WHEEL_CACHE
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "FLAVOR_WHEEL_CACHE=${WHEEL_CACHE_DIR}" >> "${GITHUB_ENV}"
  echo "Exported FLAVOR_WHEEL_CACHE to \$GITHUB_ENV"
fi
