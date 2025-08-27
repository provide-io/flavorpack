# Main Makefile for Flavor Helpers
# Orchestrates building Go and Rust helpers

.PHONY: all go rust rs clean clean-helpers test verify install help

# Configuration
BIN_DIR ?= bin
XDG_CACHE_HOME ?= $(HOME)/.cache
FLAVOR_HELPERS_DIR ?= $(XDG_CACHE_HOME)/flavor/helpers/bin

# Default target
all: go rust verify

# Build Go helpers
go:
	@echo "════════════════════════════════════════════════════════"
	@echo "🐹 Building Go Helpers"
	@echo "════════════════════════════════════════════════════════"
	@$(MAKE) -C flavor-go build BIN_DIR="../$(BIN_DIR)"
	@echo ""

# Build Rust helpers (rs is an alias)
rust rs:
	@echo "════════════════════════════════════════════════════════"
	@echo "🦀 Building Rust Helpers"
	@echo "════════════════════════════════════════════════════════"
	@$(MAKE) -C flavor-rs build BIN_DIR="../$(BIN_DIR)"
	@echo ""

# Verify all built helpers work
verify:
	@echo "════════════════════════════════════════════════════════"
	@echo "🔍 Verifying Helper Binaries"
	@echo "════════════════════════════════════════════════════════"
	@if [ -d "$(BIN_DIR)" ]; then \
		for binary in $(BIN_DIR)/flavor-*; do \
			if [ -f "$$binary" ] && [ -x "$$binary" ]; then \
				echo "Testing: $$(basename $$binary)"; \
				$$binary --version || echo "  ⚠️  No --version flag"; \
				echo ""; \
			fi \
		done; \
		echo "✅ All helpers verified"; \
	else \
		echo "❌ No binaries found in $(BIN_DIR)"; \
		exit 1; \
	fi

# Clean helper binaries
clean-helpers:
	@echo "🧹 Cleaning helper binaries..."
	@rm -rf $(BIN_DIR)
	@mkdir -p $(BIN_DIR)
	@echo "✅ Helper binaries cleaned"

# Deep clean (including build caches)
clean: clean-helpers
	@echo "🧹 Deep cleaning all build artifacts..."
	@$(MAKE) -C flavor-go clean BIN_DIR="../$(BIN_DIR)"
	@$(MAKE) -C flavor-rs clean BIN_DIR="../$(BIN_DIR)"
	@echo "✅ All build artifacts cleaned"

# Run tests for all helpers
test:
	@echo "════════════════════════════════════════════════════════"
	@echo "🧪 Testing All Helpers"
	@echo "════════════════════════════════════════════════════════"
	@echo "Testing Go helpers..."
	@$(MAKE) -C flavor-go test
	@echo ""
	@echo "Testing Rust helpers..."
	@$(MAKE) -C flavor-rs test
	@echo "✅ All tests completed"

# Run code quality checks
check:
	@echo "════════════════════════════════════════════════════════"
	@echo "🔍 Running Code Quality Checks"
	@echo "════════════════════════════════════════════════════════"
	@echo "Checking Go code..."
	@$(MAKE) -C flavor-go check
	@echo ""
	@echo "Checking Rust code..."
	@$(MAKE) -C flavor-rs check
	@echo "✅ All checks passed"

# Install all helpers
install: all
	@echo "════════════════════════════════════════════════════════"
	@echo "📦 Installing All Helpers"
	@echo "════════════════════════════════════════════════════════"
	@$(MAKE) -C flavor-go install BIN_DIR="../$(BIN_DIR)" FLAVOR_HELPERS_DIR="$(FLAVOR_HELPERS_DIR)"
	@$(MAKE) -C flavor-rs install BIN_DIR="../$(BIN_DIR)" FLAVOR_HELPERS_DIR="$(FLAVOR_HELPERS_DIR)"
	@echo ""
	@echo "✅ All helpers installed to $(FLAVOR_HELPERS_DIR)"
	@echo "   Add to PATH with: export PATH=\"$(FLAVOR_HELPERS_DIR):\$$PATH\""

# Install development dependencies
deps:
	@echo "════════════════════════════════════════════════════════"
	@echo "📦 Installing Development Dependencies"
	@echo "════════════════════════════════════════════════════════"
	@$(MAKE) -C flavor-go deps
	@$(MAKE) -C flavor-rs deps
	@echo "✅ All dependencies installed"

# Show help
help:
	@echo "Flavor Helpers - Main Makefile"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Main targets:"
	@echo "  all           Build all helpers (Go and Rust) and verify"
	@echo "  go            Build Go helpers only"
	@echo "  rust, rs      Build Rust helpers only"
	@echo "  verify        Test that all built helpers run correctly"
	@echo "  install       Build and install all helpers"
	@echo ""
	@echo "Maintenance targets:"
	@echo "  clean-helpers Remove helper binaries from bin/"
	@echo "  clean         Deep clean all build artifacts"
	@echo "  test          Run tests for all helpers"
	@echo "  check         Run code quality checks (lint, fmt, security)"
	@echo "  deps          Install development dependencies"
	@echo ""
	@echo "Environment variables:"
	@echo "  BIN_DIR              Build output directory (default: bin)"
	@echo "  FLAVOR_HELPERS_DIR   Install directory (default: \$$XDG_CACHE_HOME/flavor/helpers/bin)"
	@echo "  XDG_CACHE_HOME       XDG cache directory (default: \$$HOME/.cache)"
	@echo ""
	@echo "Examples:"
	@echo "  make                 # Build all helpers and verify"
	@echo "  make go              # Build only Go helpers"
	@echo "  make rs              # Build only Rust helpers"
	@echo "  make clean-helpers   # Remove built binaries"
	@echo "  make install         # Build and install to ~/.cache/flavor/helpers/bin"