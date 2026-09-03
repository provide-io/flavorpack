#!/bin/bash
set -euo pipefail

# Generate checksums.txt for the assets attached to a release.
# Usage: generate-release-checksums.sh <release_dir>
#
# The release notes tell every user to run `sha256sum -c checksums.txt`, so an
# asset missing from this file is an asset nobody can verify. The generator
# globbed *.whl and *.psp only, which left both Windows .exe packages of v0.5.0
# with no checksum line and nothing in the job to say so.

RELEASE_DIR="${1:-release}"

if [ ! -d "$RELEASE_DIR" ]; then
    echo "❌ Release directory not found: $RELEASE_DIR"
    echo "   Nothing was assembled, so there is nothing to checksum."
    exit 1
fi

# macOS ships shasum, not sha256sum. Both write `<hash>  <name>`, which is what
# `sha256sum -c` reads back, so either tool produces a file users can verify.
if command -v sha256sum > /dev/null 2>&1; then
    sha256() { sha256sum "$@"; }
elif command -v shasum > /dev/null 2>&1; then
    sha256() { shasum -a 256 "$@"; }
else
    echo "❌ No sha256 tool available (looked for sha256sum and shasum)"
    exit 1
fi

cd "$RELEASE_DIR"

CHECKSUMS="checksums.txt"
TOTAL=0

# Written to a temp file and moved into place at the end: checksums.txt cannot
# appear in its own listing, and a failure partway through leaves no half-file
# that a later step would read as complete.
TMP_CHECKSUMS=$(mktemp)
trap 'rm -f "$TMP_CHECKSUMS"' EXIT

: > "$TMP_CHECKSUMS"

# checksum <glob>...
# Writes one `<hash>  <name>` line per matching file and nothing else. No
# headings or blank lines: GNU sha256sum skips `#` comments, but the shasum
# macOS ships does not, and reported "3 lines are improperly formatted" against
# a checksums.txt that was entirely correct. A verification step that warns on a
# good file teaches users to ignore it.
#
# Files are hashed one at a time rather than gathered into an array, because
# bash 3.2 -- which is what macOS ships -- treats an empty array as unset under
# `set -u`.
checksum() {
    local candidate
    for candidate in "$@"; do
        if [ -f "$candidate" ]; then
            # ./ is stripped so checksums.txt names the file as a user sees it,
            # and -- keeps a name that starts with a dash from reading as a flag.
            sha256 -- "${candidate#./}" >> "$TMP_CHECKSUMS"
            TOTAL=$((TOTAL + 1))
        fi
    done
}

# .psp and .exe are the same thing under two names: a Windows flavor package is
# written .exe so it is directly runnable. Both are packages, and both get a
# checksum.
checksum ./*.whl ./*.psp ./*.exe

if [ "$TOTAL" -eq 0 ]; then
    echo "❌ No release assets found in $RELEASE_DIR — no checksums generated."
    echo "   A checksums.txt with no entries verifies nothing."
    exit 1
fi

mv "$TMP_CHECKSUMS" "$CHECKSUMS"
trap - EXIT

echo "📊 Checksummed $TOTAL asset(s):"
cat "$CHECKSUMS"
