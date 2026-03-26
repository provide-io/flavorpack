#!/bin/bash
set -euo pipefail

# Install Flavor from a pre-built wheel using uv tool install.
#
# On windows_arm64, the flavorpack wheel is win_arm64 (native ARM64 tool).
# UV resolves dependencies for the native ARM64 platform; cryptography 46.0.4+
# dropped win_arm64 binary wheels so we pin to 46.0.3 (last version with
# win_arm64 wheel) via --with to avoid a source build that requires OpenSSL.
#
# Usage: install-flavor-wheel.sh <wheel-dir> [platform]
#   wheel-dir  Directory containing flavorpack-*.whl
#   platform   Optional: target platform string (e.g. windows_arm64)

WHEEL_DIR="${1}"
PLATFORM="${2:-}"

WHEEL=$(find "${WHEEL_DIR}" -name "flavorpack-*.whl" | head -1)

if [ -z "${WHEEL}" ]; then
  echo "❌ Flavor wheel not found in ${WHEEL_DIR}"
  ls -la "${WHEEL_DIR}/" || true
  exit 1
fi

echo "Installing Flavor from wheel: ${WHEEL}"

if [[ "${PLATFORM}" == "windows_arm64" ]]; then
  # cryptography 46.0.4+ has no win_arm64 binary wheel and cannot be built from
  # source on GHA (no OpenSSL). Pin to 46.0.3 which ships a win_arm64 wheel.
  #
  # grpcio (OTLP gRPC exporter) is excluded on windows_arm64 via a platform
  # marker in flavorpack's pyproject.toml — the wheel metadata handles this.
  echo "Platform windows_arm64: pinning cryptography==46.0.3 for binary wheel"
  uv tool install "${WHEEL}" --with "cryptography==46.0.3"
else
  uv tool install "${WHEEL}"
fi

# Add uv tools to PATH and verify
export PATH="${HOME}/.local/bin:${PATH}"
which flavor
flavor --version

echo "✅ Flavor installed successfully"
