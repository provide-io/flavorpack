#!/bin/bash
set -euo pipefail

# Pre-warm a local wheel cache directory for offline PSPF builds.
#
# On Windows GHA runners, Python subprocess network (urllib3/pip) cannot reach
# PyPI (getaddrinfo fails), but UV's Rust HTTP client CAN. This script uses
# `uv pip install` (Rust HTTP client) to download and cache packages, then
# collects the .whl files UV wrote into its cache. flavor pack subprocess then
# uses download_wheels_offline() with pip --no-index --find-links (no network).
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

# Export FLAVOR_WHEEL_CACHE FIRST so it's always set in GITHUB_ENV even if the
# download step below fails partway through. download_wheels_offline will use
# whatever wheels are present in the directory.
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "FLAVOR_WHEEL_CACHE=${WHEEL_CACHE_DIR}" >> "${GITHUB_ENV}"
  echo "Exported FLAVOR_WHEEL_CACHE to \$GITHUB_ENV"
fi

# Export pinned requirements from lockfile (no hashes, no dev deps)
RAW_REQS="${WHEEL_CACHE_DIR}/requirements-raw.txt"
REQS="${WHEEL_CACHE_DIR}/requirements.txt"

uv export --frozen --no-dev --no-hashes --output-file "${RAW_REQS}"

# Strip editable (-e .) and local file:// lines — pip install doesn't support them
grep -v '^-e \|file://' "${RAW_REQS}" > "${REQS}" || true

WHEEL_COUNT=$(wc -l < "${REQS}")
echo "Requirements: ${WHEEL_COUNT} lines"

# Use `uv pip install` (Rust HTTP client) rather than `pip download` (urllib3).
# On Windows GHA runners, Python subprocess network is broken (getaddrinfo fails)
# but UV's Rust HTTP client resolves DNS correctly. UV caches .whl files under
# the specified --cache-dir which we then collect into WHEEL_CACHE_DIR.
UV_PKG_CACHE="${WHEEL_CACHE_DIR}/.uv-cache"
INSTALL_TARGET="${WHEEL_CACHE_DIR}/.install-target"
mkdir -p "${UV_PKG_CACHE}" "${INSTALL_TARGET}"

# Export so the Python re-zip script can read them via os.environ
export UV_PKG_CACHE WHEEL_CACHE_DIR

echo "Downloading wheels via uv pip install (Rust HTTP client)..."
uv pip install \
  --cache-dir "${UV_PKG_CACHE}" \
  --target "${INSTALL_TARGET}" \
  -r "${REQS}" \
  --quiet

# Collect wheels from UV cache by re-zipping archive-v0 entries.
#
# UV does NOT store plain .whl files in its cache — it extracts them into
# archive-v0/{hash}/ directories and writes pointer files at:
#   wheels-v6/pypi/{pkg}/{version}-{python}-{abi}-{platform}.lock  -> wheel name
#   wheels-v6/pypi/{pkg}/{version}-{python}-{abi}-{platform}       -> archive-v0/{hash}
#
# We re-zip each archive-v0 entry into a proper .whl file (wheel = zip with
# the same internal layout: package/ + package-version.dist-info/).
echo "Collecting wheels from UV cache (re-zipping archive-v0 entries)..."
uv run --no-project python - <<'PYEOF'
import os, pathlib, sys, zipfile

cache_dir  = pathlib.Path(os.environ["UV_PKG_CACHE"])
out_dir    = pathlib.Path(os.environ["WHEEL_CACHE_DIR"])
wheels_idx = cache_dir / "wheels-v6" / "pypi"

if not wheels_idx.exists():
    print(f"No wheels-v6 index found at {wheels_idx}", file=sys.stderr)
    sys.exit(0)

created = errors = 0
for pkg_dir in wheels_idx.iterdir():
    if not pkg_dir.is_dir():
        continue
    for lock_file in pkg_dir.glob("*.lock"):
        wheel_name = lock_file.stem + ".whl"   # e.g. anyio-4.13.0-py3-none-any.whl
        out_path   = out_dir / wheel_name
        if out_path.exists():
            continue

        # The pointer file has the version+tag only (no package name prefix), e.g.
        # lock:    anyio-4.13.0-py3-none-any.lock      (pure Python)
        # lock:    provide_foundation-0.3.21-py3-none-any.lock  (hyphen→underscore in lock)
        # pointer: 4.13.0-py3-none-any
        # PyPI dir name uses hyphens; wheel/lock name uses underscores — normalize both.
        pkg_norm   = pkg_dir.name.replace("-", "_")
        pkg_prefix = pkg_norm + "-"
        stem = lock_file.stem   # e.g. "anyio-4.13.0-py3-none-any"
        if not stem.startswith(pkg_prefix):
            continue
        pointer = lock_file.parent / stem[len(pkg_prefix):]
        if not pointer.exists():
            continue

        # pointer content: "archive-v0/<hash>"
        archive_key  = pointer.read_text().strip().removeprefix("archive-v0/")
        archive_path = cache_dir / "archive-v0" / archive_key

        if not archive_path.exists():
            print(f"Archive missing for {wheel_name}: {archive_path}", file=sys.stderr)
            errors += 1
            continue

        try:
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in archive_path.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(archive_path))
            created += 1
        except Exception as exc:
            print(f"Error creating {wheel_name}: {exc}", file=sys.stderr)
            if out_path.exists():
                out_path.unlink()
            errors += 1

print(f"Created {created} wheel files ({errors} errors)")
PYEOF

DOWNLOADED=$(ls "${WHEEL_CACHE_DIR}"/*.whl 2>/dev/null | wc -l || echo 0)
echo "✅ Collected ${DOWNLOADED} wheels to ${WHEEL_CACHE_DIR}"

# Download build-backends wheels (setuptools, wheel, packaging) for hermetic slot builds.
#
# _bundle_build_backends() in slot_builder.py uses FLAVOR_WHEEL_CACHE for offline installs.
# These packages may already be cached in the shared UV_CACHE_DIR (set by setup-uv), so the
# main uv pip install above may NOT download them fresh into UV_PKG_CACHE (UV uses the shared
# cache as a read-through). We fix this by using a completely isolated UV cache (BB_UV_CACHE)
# with UV_CACHE_DIR *unset*, forcing a fresh download of all build-backends packages.
BB_RAW="${WHEEL_CACHE_DIR}/build-backends-raw.txt"
BB_REQS="${WHEEL_CACHE_DIR}/build-backends-reqs.txt"
if uv export --frozen --only-group build-backends --no-hashes --output-file "${BB_RAW}" 2>/dev/null; then
  grep -v '^-e \|file://' "${BB_RAW}" | grep -v '^$' > "${BB_REQS}" || true
  if [ -s "${BB_REQS}" ]; then
    echo "Downloading build-backends wheels (isolated cache, no UV_CACHE_DIR fallback)..."
    BB_UV_CACHE="${WHEEL_CACHE_DIR}/.bb-uv-cache"
    BB_INSTALL="${WHEEL_CACHE_DIR}/.bb-install"
    mkdir -p "${BB_UV_CACHE}" "${BB_INSTALL}"
    export BB_UV_CACHE
    # Unset UV_CACHE_DIR in a subshell so UV cannot use the shared cache as a fallback.
    # This forces every build-backends package to be downloaded fresh into BB_UV_CACHE,
    # making its archive-v0 entries available for re-zipping below.
    (unset UV_CACHE_DIR; uv pip install \
      --cache-dir "${BB_UV_CACHE}" \
      --target "${BB_INSTALL}" \
      -r "${BB_REQS}" \
      --quiet)
    # Re-zip BB_UV_CACHE archive-v0 entries into .whl files using the same mechanism as above.
    uv run --no-project python - <<'BBEOF'
import os, pathlib, sys, zipfile
cache_dir  = pathlib.Path(os.environ["BB_UV_CACHE"])
out_dir    = pathlib.Path(os.environ["WHEEL_CACHE_DIR"])
wheels_idx = cache_dir / "wheels-v6" / "pypi"
if not wheels_idx.exists():
    print(f"No build-backends wheels-v6 index at {wheels_idx}", file=sys.stderr)
    sys.exit(0)
created = errors = 0
for pkg_dir in wheels_idx.iterdir():
    if not pkg_dir.is_dir():
        continue
    for lock_file in pkg_dir.glob("*.lock"):
        wheel_name = lock_file.stem + ".whl"
        out_path   = out_dir / wheel_name
        if out_path.exists():
            continue
        pkg_norm   = pkg_dir.name.replace("-", "_")
        pkg_prefix = pkg_norm + "-"
        stem = lock_file.stem
        if not stem.startswith(pkg_prefix):
            continue
        pointer = lock_file.parent / stem[len(pkg_prefix):]
        if not pointer.exists():
            continue
        archive_key  = pointer.read_text().strip().removeprefix("archive-v0/")
        archive_path = cache_dir / "archive-v0" / archive_key
        if not archive_path.exists():
            print(f"Archive missing for {wheel_name}: {archive_path}", file=sys.stderr)
            errors += 1
            continue
        try:
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in archive_path.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(archive_path))
            created += 1
        except Exception as exc:
            print(f"Error creating {wheel_name}: {exc}", file=sys.stderr)
            if out_path.exists():
                out_path.unlink()
            errors += 1
print(f"Created {created} build-backends wheel files ({errors} errors)")
BBEOF
    BB_DOWNLOADED=$(ls "${WHEEL_CACHE_DIR}"/*.whl 2>/dev/null | wc -l || echo 0)
    echo "✅ After build-backends: ${BB_DOWNLOADED} total wheels in cache"
  fi
fi
