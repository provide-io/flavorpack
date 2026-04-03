#!/usr/bin/env bash
# Build Flavor PSP inside a FreeBSD VM (called from cross-platform-actions step).
# Usage: build-flavor-freebsd.sh <platform> <version>
#
# Expects:
#   _stage/flavorpack-*.whl  — staged wheel (gitignored *.whl staged before VM sync)
#   helpers/bin/             — helper binaries synced from runner
#
# cryptography has no pre-built FreeBSD wheel on PyPI and fails to build from
# source via maturin (FreeBSD SOABI is "cpython-311" which maturin rejects).
# Install it via pkg (pre-compiled), then use pip (not uv pip) to install into
# a --system-site-packages venv: pip honors system-site-packages when checking
# what is already installed and skips rebuilding cryptography.

set -euo pipefail

PLATFORM="${1}"
VERSION="${2}"

sudo env IGNORE_OSVERSION=yes pkg install -y python311 uv py311-cryptography

WHEEL=$(find _stage -name "flavorpack-*.whl" | head -1)
if [ -z "$WHEEL" ]; then
    echo "❌ Staged wheel not found in _stage/"
    ls _stage/ || true
    exit 1
fi

# Create a --system-site-packages venv with pip seeded (--seed).
# Use pip (not uv pip): pip checks system-site-packages when deciding whether
# a package is already installed, so it finds cryptography 45.x from pkg and
# skips the source build entirely.  uv pip does not honour system-site-packages
# for that check and would attempt to rebuild cryptography from source.
WHEEL_ABS=$(realpath "$WHEEL")
uv venv /tmp/flavorenv --python python3.11 --system-site-packages --seed

# Stub out the uv PyPI package — flavorpack calls uv via shutil.which(), not
# as a Python import.  pkg installs the uv binary to /usr/local/bin/uv but
# does not create a Python dist-info; without a dist-info pip tries to build
# uv from source (a Rust/maturin build that fails on FreeBSD).
# Create a minimal dist-info so pip considers uv already installed.
UV_PKG_VER=$(pkg query '%v' uv 2>/dev/null | sed 's/[_,].*//' || echo "0.9.6")
VENV_SP="/tmp/flavorenv/lib/python3.11/site-packages"
UV_DIST="${VENV_SP}/uv-${UV_PKG_VER}.dist-info"
mkdir -p "$UV_DIST"
printf "Metadata-Version: 2.1\nName: uv\nVersion: %s\n" "$UV_PKG_VER" > "${UV_DIST}/METADATA"
printf "uv-${UV_PKG_VER}.dist-info/METADATA,,\n" > "${UV_DIST}/RECORD"
ln -sf /usr/local/bin/uv /tmp/flavorenv/bin/uv

/tmp/flavorenv/bin/pip install --no-build-isolation \
    'cryptography<46.0.0' \
    "$WHEEL_ABS"
export PATH="/tmp/flavorenv/bin:$PATH"

LAUNCHER="helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}"
if [ ! -f "$LAUNCHER" ]; then
    LAUNCHER="helpers/bin/flavor-go-launcher-${VERSION}-${PLATFORM}"
fi
if [ ! -f "$LAUNCHER" ]; then
    echo "❌ No launcher found in helpers/bin/"
    ls helpers/bin/ || true
    exit 1
fi
chmod +x "$LAUNCHER"

# Pre-build C-extension wheels that have no pre-built FreeBSD wheel on PyPI.
# flavor pack uses pip download internally; without pre-built wheels it fails.
# Build them here and pass the output dir via FLAVOR_WHEEL_CACHE so
# flavor pack finds them via --find-links (offline fallback path).
#
# Packages without FreeBSD wheels on PyPI (known):
#   cffi          — required by cryptography; no FreeBSD wheel on PyPI (1.x or 2.x)
#   psutil        — process/platform info used by provide-foundation
#   setproctitle  — process title; small C build
#   zstandard     — PSP compression; medium C build
#
# grpcio has no FreeBSD wheel either and takes 20+ min to build.
# Remove it entirely by switching provide-foundation[all] to the non-gRPC
# extras subset — gRPC telemetry is never used in the FreeBSD PSP anyway.
WHEEL_CACHE=/tmp/freebsd-wheel-cache
mkdir -p "$WHEEL_CACHE"

# Build C-extension wheels from source for packages with no PyPI FreeBSD wheel.
# Use --no-deps so we only build the wheel we're requesting, not its subtree.
# cryptography 45.x uses Rust (maturin); skip pip wheel — repackage the
# pkg-compiled binary directly (see below).
/tmp/flavorenv/bin/pip wheel \
    'cffi>=1.14,<2.0.0' \
    'psutil' \
    'setproctitle' \
    'zstandard' \
    -w "$WHEEL_CACHE" --no-deps

# Repackage the pkg-compiled cryptography into a wheel so flavor pack can bundle
# it.  cryptography 45.x requires Rust to build from source (maturin), but
# `pkg install py311-cryptography` gives us a pre-compiled binary.  We zip the
# installed package directory + dist-info into a correctly named .whl archive.
python3.11 - <<'PYEOF'
import base64, hashlib, re, sys, sysconfig, zipfile
from pathlib import Path

site = Path("/usr/local/lib/python3.11/site-packages")
cache = Path("/tmp/freebsd-wheel-cache")

dists = sorted(site.glob("cryptography-*.dist-info"))
if not dists:
    print("ERROR: cryptography dist-info not found in system site-packages", file=sys.stderr)
    sys.exit(1)

dist_info = dists[-1]
version = re.search(r"cryptography-(.+?)\.dist-info", dist_info.name).group(1)
py = f"cp{sys.version_info.major}{sys.version_info.minor}"
# Wheel platform tags must be lowercase (PEP 425 / wheel spec).
# sysconfig.get_platform() may return mixed-case (e.g. "freebsd-14.2-RELEASE-amd64");
# lowercase so uv's sys_tags() comparison matches correctly.
plat = sysconfig.get_platform().replace("-", "_").replace(".", "_").lower()
wheel_name = f"cryptography-{version}-{py}-{py}-{plat}.whl"
out = cache / wheel_name

def sha256_hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

print(f"Packaging pkg cryptography {version} → {wheel_name}")
record_entries: list[str] = []
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as whl:
    pkg_dir = site / "cryptography"
    for p in pkg_dir.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            arcname = str(p.relative_to(site))
            data = p.read_bytes()
            whl.writestr(arcname, data)
            record_entries.append(f"{arcname},{sha256_hash(data)},{len(data)}")
    for p in dist_info.rglob("*"):
        if p.is_file() and p.name not in ("RECORD", "INSTALLER", "direct_url.json"):
            arcname = str(p.relative_to(site))
            data = p.read_bytes()
            whl.writestr(arcname, data)
            record_entries.append(f"{arcname},{sha256_hash(data)},{len(data)}")
    # Ensure a WHEEL metadata file exists
    wheel_file = dist_info / "WHEEL"
    if not wheel_file.exists():
        arcname = f"cryptography-{version}.dist-info/WHEEL"
        data = (
            f"Wheel-Version: 1.0\nGenerator: repackage\n"
            f"Root-Is-Purelib: false\nTag: {py}-{py}-{plat}\n"
        ).encode()
        whl.writestr(arcname, data)
        record_entries.append(f"{arcname},{sha256_hash(data)},{len(data)}")
    # uv requires a RECORD file; generate one with sha256 hashes.
    # The RECORD entry for RECORD itself has no hash/size per PEP 376.
    record_arcname = f"cryptography-{version}.dist-info/RECORD"
    record_content = "\n".join(record_entries) + f"\n{record_arcname},,\n"
    whl.writestr(record_arcname, record_content)
print(f"Created {out}")
PYEOF

# Patch pyproject.toml + remove lock file before flavor pack.
#   1. Relax cffi constraint (>=2.0.0 → >=1.14,<2.0.0): uv 0.9.24 ignores
#      sys_platform markers, so without this it still resolves to cffi 2.0.0.
#   2. Replace provide-foundation[all] with the non-gRPC extras subset so
#      grpcio is not a resolved dependency (no FreeBSD wheel, 20+ min build).
#   3. Delete uv.lock so uv re-resolves from the patched pyproject.toml.
sed -i '' 's/"cffi>=2\.0\.0"/"cffi>=1.14,<2.0.0"/g' pyproject.toml
# Remove the non-FreeBSD cryptography floor (>=46.0.0) — uv 0.9.24 ignores
# sys_platform markers in constraint-dependencies so it applies >=46.0.0
# unconditionally, conflicting with our <46.0.0 FreeBSD cap.
sed -i '' '/"cryptography>=46\.0\.0/d' pyproject.toml
sed -i '' 's/provide-foundation\[all\]/provide-foundation[cli,compression,crypto,transport,platform]/g' pyproject.toml
rm -f uv.lock

mkdir -p _stage/artifacts
FLAVOR_WHEEL_CACHE="$WHEEL_CACHE" flavor pack \
    --manifest pyproject.toml \
    --output "_stage/artifacts/flavor-${VERSION}-${PLATFORM}.psp" \
    --launcher-bin "$LAUNCHER" \
    --key-seed "flavor-${VERSION}"

chmod +x "_stage/artifacts/flavor-${VERSION}-${PLATFORM}.psp"
"./_stage/artifacts/flavor-${VERSION}-${PLATFORM}.psp" --version
echo "✅ FreeBSD Flavor PSP built and verified"
