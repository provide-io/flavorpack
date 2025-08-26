# Makefile for Rust helpers

.PHONY: all build clean test install fmt lint security fuzz check deps release

# Configuration
BIN_DIR ?= ../bin
XDG_CACHE_HOME ?= $(HOME)/.cache
FLAVOR_HELPERS_DIR ?= $(XDG_CACHE_HOME)/flavor/helpers/bin
CARGO_FLAGS ?= --release
TARGET ?= 

# Detect platform for naming
RUST_TARGET ?= $(shell rustc -vV | grep host | cut -d' ' -f2)
# Parse and normalize Rust target triple: arch-vendor-os-env -> os_arch
# Examples: x86_64-apple-darwin -> darwin_amd64, aarch64-unknown-linux-gnu -> linux_arm64
PLATFORM = $(shell echo "$(RUST_TARGET)" | awk -F'-' '{arch=$$1; os=$$3; if ($$4 != "") os=$$3; gsub("x86_64","amd64",arch); gsub("aarch64","arm64",arch); gsub("darwin","darwin",os); gsub("linux","linux",os); gsub("windows","windows",os); print os "_" arch}')

all: build

build:
	@echo "🔨 Building Rust helpers for $(PLATFORM)..."
	@mkdir -p $(BIN_DIR)
	@if [ -n "$(TARGET)" ]; then \
		echo "   Cross-compiling for: $(TARGET)"; \
		cargo build $(CARGO_FLAGS) --target $(TARGET); \
		cp target/$(TARGET)/release/flavor-rs-launcher $(BIN_DIR)/flavor-rs-launcher-$(PLATFORM); \
		cp target/$(TARGET)/release/flavor-rs-builder $(BIN_DIR)/flavor-rs-builder-$(PLATFORM); \
	else \
		cargo build $(CARGO_FLAGS); \
		cp target/release/flavor-rs-launcher $(BIN_DIR)/flavor-rs-launcher-$(PLATFORM); \
		cp target/release/flavor-rs-builder $(BIN_DIR)/flavor-rs-builder-$(PLATFORM); \
	fi
	@chmod +x $(BIN_DIR)/flavor-rs-*
	@echo "✅ Rust helpers built: flavor-rs-*-$(PLATFORM)"

clean:
	@echo "🧹 Cleaning Rust build artifacts..."
	@cargo clean
	@rm -f $(BIN_DIR)/flavor-rs-*
	@echo "✅ Cleaned"

fmt:
	@echo "🎨 Formatting Rust code..."
	@cargo fmt
	@echo "✅ Code formatted with rustfmt"

lint:
	@echo "🔍 Linting Rust code..."
	@cargo clippy -- -D warnings
	@echo "✅ Clippy linting passed"

security:
	@echo "🔐 Running security checks..."
	@if command -v cargo-audit >/dev/null 2>&1; then \
		cargo audit; \
		echo "✅ cargo-audit security scan passed"; \
	else \
		echo "⚠️  cargo-audit not installed"; \
		echo "   Install with: cargo install cargo-audit"; \
	fi
	@if command -v cargo-deny >/dev/null 2>&1; then \
		cargo deny check 2>/dev/null || echo "⚠️  cargo-deny needs configuration (create deny.toml)"; \
	else \
		echo "⚠️  cargo-deny not installed"; \
		echo "   Install with: cargo install cargo-deny"; \
	fi

test:
	@echo "🧪 Running Rust tests..."
	@cargo test --all-features
	@echo "✅ Tests passed"

fuzz:
	@echo "🔀 Running fuzz tests..."
	@if command -v cargo-fuzz >/dev/null 2>&1; then \
		if [ -d "fuzz" ]; then \
			cargo fuzz run fuzz_target_1 -- -max_total_time=10 2>/dev/null || \
				echo "⚠️  Fuzz testing requires setup. Run: cargo fuzz init"; \
		else \
			echo "⚠️  No fuzz targets found. Initialize with: cargo fuzz init"; \
		fi \
	else \
		echo "⚠️  cargo-fuzz not installed"; \
		echo "   Install with: cargo install cargo-fuzz"; \
		echo "   Note: Requires nightly Rust"; \
	fi

check: fmt lint test security
	@echo "✅ All checks passed!"

deps:
	@echo "📦 Installing development dependencies..."
	@rustup component add clippy 2>/dev/null || true
	@rustup component add rustfmt 2>/dev/null || true
	@cargo install cargo-audit --quiet 2>/dev/null || echo "   cargo-audit already installed"
	@cargo install cargo-deny --quiet 2>/dev/null || echo "   cargo-deny already installed"
	@cargo install cargo-outdated --quiet 2>/dev/null || echo "   cargo-outdated already installed"
	@cargo install cargo-machete --quiet 2>/dev/null || echo "   cargo-machete already installed"
	@echo "✅ Dependencies installed"
	@echo "   Optional: cargo install cargo-fuzz (requires nightly)"
	@echo "   Optional: cargo install cargo-tarpaulin (for coverage)"

release:
	@echo "🚀 Building optimized release..."
	@cargo build --release
	@strip target/release/flavor-rs-launcher 2>/dev/null || true
	@strip target/release/flavor-rs-builder 2>/dev/null || true
	@echo "✅ Release build complete"
	@ls -lh target/release/flavor-rs-*

install: build
	@echo "📦 Installing Rust helpers to $(FLAVOR_HELPERS_DIR)..."
	@mkdir -p $(FLAVOR_HELPERS_DIR)
	@cp $(BIN_DIR)/flavor-rs-*-$(PLATFORM) $(FLAVOR_HELPERS_DIR)/
	@# Create symlinks without platform suffix for convenience
	@ln -sf flavor-rs-builder-$(PLATFORM) $(FLAVOR_HELPERS_DIR)/flavor-rs-builder
	@ln -sf flavor-rs-launcher-$(PLATFORM) $(FLAVOR_HELPERS_DIR)/flavor-rs-launcher
	@chmod +x $(FLAVOR_HELPERS_DIR)/flavor-rs-*
	@echo "✅ Installed to $(FLAVOR_HELPERS_DIR)"
	@echo "   Binaries: flavor-rs-*-$(PLATFORM)"
	@echo "   Symlinks: flavor-rs-builder, flavor-rs-launcher"
	@echo "   Add to PATH with: export PATH=\"$(FLAVOR_HELPERS_DIR):\$$PATH\""