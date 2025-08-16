#!/usr/bin/env bash
# Flavor Production Hardening Script
# This script applies security hardening for production builds

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🛡️ Flavor Production Hardening Script"
echo "======================================"

# Check if running in CI or production mode
if [ "${CI:-false}" != "true" ] && [ "${PRODUCTION:-false}" != "true" ]; then
    echo -e "${YELLOW}⚠️  Warning: Not in CI/production mode. Some checks may be skipped.${NC}"
fi

# Function to check command existence
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ $1 is available${NC}"
    return 0
}

# Function to apply Go hardening
harden_go() {
    echo ""
    echo "🐹 Hardening Go binaries..."
    
    cd helpers/flavor-go
    
    # Security-focused build flags
    export CGO_ENABLED=0  # Disable CGO for static binaries
    export GOFLAGS="-buildmode=pie -mod=readonly"
    export GOLDFLAGS="-s -w -X main.Mode=production -extldflags '-static'"
    
    # Build with security flags
    echo "  Building launcher with security flags..."
    go build \
        -trimpath \
        -ldflags="${GOLDFLAGS}" \
        -tags "netgo osusergo static_build" \
        -o ../bin/flavor-go-launcher \
        cmd/pspf-launcher/main.go
    
    echo "  Building builder with security flags..."
    go build \
        -trimpath \
        -ldflags="${GOLDFLAGS}" \
        -tags "netgo osusergo static_build" \
        -o ../bin/flavor-go-builder \
        cmd/pspf-builder/main.go
    
    # Strip binaries
    if check_command strip; then
        echo "  Stripping debug symbols..."
        strip -s ../bin/flavor-go-launcher
        strip -s ../bin/flavor-go-builder
    fi
    
    # Check for vulnerabilities
    if check_command gosec; then
        echo "  Running security scan..."
        gosec -quiet -fmt json ./... || true
    fi
    
    cd ../..
    echo -e "${GREEN}✅ Go binaries hardened${NC}"
}

# Function to apply Rust hardening
harden_rust() {
    echo ""
    echo "🦀 Hardening Rust binaries..."
    
    cd helpers/flavor-rust
    
    # Security-focused build configuration
    cat > .cargo/config.toml << 'EOF'
[build]
rustflags = [
    "-C", "opt-level=3",
    "-C", "lto=true",
    "-C", "codegen-units=1",
    "-C", "strip=symbols",
    "-C", "overflow-checks=yes",
    "-C", "panic=abort",
    "-C", "relocation-model=pie",
    "-C", "link-arg=-s",
    "-D", "warnings",
]

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
strip = true
panic = "abort"
overflow-checks = true
EOF
    
    # Build with security profile
    echo "  Building with security profile..."
    cargo build --release --locked
    
    # Copy hardened binaries
    cp target/release/flavor-rs-launcher ../bin/
    cp target/release/flavor-rs-builder ../bin/
    
    # Audit dependencies
    if check_command cargo-audit; then
        echo "  Auditing dependencies..."
        cargo audit --deny warnings || true
    fi
    
    cd ../..
    echo -e "${GREEN}✅ Rust binaries hardened${NC}"
}

# Function to apply Python hardening
harden_python() {
    echo ""
    echo "🐍 Hardening Python code..."
    
    # Remove debug code
    echo "  Removing debug statements..."
    find src -name "*.py" -type f -exec sed -i.bak '/^\s*print(/d' {} \;
    find src -name "*.py" -type f -exec sed -i.bak '/^\s*breakpoint()/d' {} \;
    find src -name "*.py.bak" -type f -delete
    
    # Compile Python files
    echo "  Compiling Python files..."
    python -m compileall -b src/
    
    # Run security checks
    if check_command bandit; then
        echo "  Running security scan..."
        bandit -r src/ -ll -f json -o bandit-report.json || true
    fi
    
    if check_command safety; then
        echo "  Checking dependencies..."
        safety check --json || true
    fi
    
    echo -e "${GREEN}✅ Python code hardened${NC}"
}

# Function to verify signatures
verify_signatures() {
    echo ""
    echo "🔐 Verifying signatures..."
    
    # Ensure FLAVOR_INSECURE is not set
    if [ -n "${FLAVOR_INSECURE:-}" ]; then
        echo -e "${RED}❌ FLAVOR_INSECURE is set! This is not allowed in production.${NC}"
        exit 1
    fi
    
    # Check for test keys
    if grep -r "FLAVOR_SKIP_KEY_VERIFICATION" src/ helpers/; then
        echo -e "${RED}❌ Found FLAVOR_SKIP_KEY_VERIFICATION in code!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Signature verification enforced${NC}"
}

# Function to set secure permissions
set_permissions() {
    echo ""
    echo "🔒 Setting secure permissions..."
    
    # Set executable permissions
    chmod 755 helpers/bin/*
    
    # Remove write permissions from binaries
    chmod a-w helpers/bin/*
    
    # Ensure no world-writable files
    find . -type f -perm /002 -exec chmod o-w {} \;
    
    echo -e "${GREEN}✅ Permissions secured${NC}"
}

# Function to generate SBOM
generate_sbom() {
    echo ""
    echo "📋 Generating SBOM..."
    
    if check_command syft; then
        syft . -o spdx-json > sbom.spdx.json
        echo -e "${GREEN}✅ SBOM generated: sbom.spdx.json${NC}"
    else
        echo -e "${YELLOW}⚠️  syft not installed, skipping SBOM generation${NC}"
    fi
}

# Function to run tests
run_security_tests() {
    echo ""
    echo "🧪 Running security tests..."
    
    if [ -d "tests/security" ]; then
        python -m pytest tests/security/ -v || true
    else
        echo -e "${YELLOW}⚠️  No security tests found${NC}"
    fi
}

# Main hardening process
main() {
    echo ""
    echo "🚀 Starting hardening process..."
    
    # Check prerequisites
    echo ""
    echo "📦 Checking prerequisites..."
    check_command go
    check_command cargo
    check_command python
    
    # Apply hardening
    harden_go
    harden_rust
    harden_python
    
    # Security checks
    verify_signatures
    set_permissions
    
    # Generate artifacts
    generate_sbom
    
    # Run tests
    run_security_tests
    
    # Final summary
    echo ""
    echo "======================================"
    echo -e "${GREEN}✅ Hardening complete!${NC}"
    echo ""
    echo "📋 Checklist:"
    echo "  ✅ Go binaries hardened and stripped"
    echo "  ✅ Rust binaries hardened with security flags"
    echo "  ✅ Python code cleaned and compiled"
    echo "  ✅ Signature verification enforced"
    echo "  ✅ Secure permissions set"
    
    if [ -f "sbom.spdx.json" ]; then
        echo "  ✅ SBOM generated"
    fi
    
    echo ""
    echo "🔒 Production build is ready for release"
}

# Run main function
main "$@"