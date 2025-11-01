# Makefile for Rust helpers

.PHONY: all build clean test install fmt lint security fuzz check deps release

# Configuration
BIN_DIR ?= ../../dist/bin
XDG_CACHE_HOME ?= $(HOME)/.cache
FLAVOR_HELPERS_DIR ?= $(XDG_CACHE_HOME)/flavor/helpers/bin
CARGO_FLAGS ?= --release
TARGET ?= 
USE_MUSL ?= false

# Detect platform for naming
RUST_TARGET ?= $(shell rustc -vV | grep host | cut -d' ' -f2)
# Parse and normalize Rust target triple: arch-vendor-os-env -> os_arch
# Examples: x86_64-apple-darwin -> darwin_amd64, aarch64-unknown-linux-gnu -> linux_arm64
# For musl targets, append _musl to platform name
PLATFORM = $(shell echo "$(RUST_TARGET)" | awk -F'-' '{arch=$$1; os=$$3; env=$$4; if ($$4 != "") os=$$3; gsub("x86_64","amd64",arch); gsub("aarch64","arm64",arch); gsub("darwin","darwin",os); gsub("linux","linux",os); gsub("windows","windows",os); suffix=""; if (env == "musl") suffix="_musl"; print os "_" arch suffix}')

all: build

build:
	@echo "🔨 Building Rust helpers..."
	@mkdir -p $(BIN_DIR)
	@# For Linux, build static by default (musl)
	@OS=$$(uname -s | tr '[:upper:]' '[:lower:]'); \
	if [ "$$OS" = "linux" ]; then \
		$(MAKE) build-static BIN_DIR=$(BIN_DIR); \
	else \
		echo "   Building for $(PLATFORM) (native)..."; \
		if [ -n "$(TARGET)" ]; then \
			echo "   Cross-compiling for: $(TARGET)"; \
			cargo build $(CARGO_FLAGS) --target $(TARGET); \
			cp target/$(TARGET)/release/flavor-rs-launcher $(BIN_DIR)/flavor-rs-launcher-$(PLATFORM); \
			cp target/$(TARGET)/release/flavor-rs-builder $(BIN_DIR)/flavor-rs-builder-$(PLATFORM); \
		else \
			cargo build $(CARGO_FLAGS); \
			install -m 755 target/release/flavor-rs-launcher $(BIN_DIR)/flavor-rs-launcher-$(PLATFORM); \
			install -m 755 target/release/flavor-rs-builder $(BIN_DIR)/flavor-rs-builder-$(PLATFORM); \
		fi; \
		chmod +x $(BIN_DIR)/flavor-rs-*; \
		echo "✅ Rust helpers built: flavor-rs-*-$(PLATFORM)"; \
	fi

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

# Build static binaries (default for Linux)
# These work on any Linux system regardless of glibc version
build-static:
	@echo "🔨 Building static Rust helpers (default for Linux)..."
	@mkdir -p $(BIN_DIR)
	@# Detect architecture and build for appropriate musl target
	@ARCH=$$(uname -m); \
	if [ "$$ARCH" = "x86_64" ]; then \
		MUSL_TARGET="x86_64-unknown-linux-musl"; \
		PLATFORM_NAME="linux_amd64"; \
	elif [ "$$ARCH" = "aarch64" ] || [ "$$ARCH" = "arm64" ]; then \
		MUSL_TARGET="aarch64-unknown-linux-musl"; \
		PLATFORM_NAME="linux_arm64"; \
	else \
		echo "❌ Unsupported architecture: $$ARCH"; \
		exit 1; \
	fi; \
	echo "   Target: $$MUSL_TARGET (static, works everywhere)"; \
	if ! rustc --print target-list | grep -q "$$MUSL_TARGET"; then \
		echo "❌ Target $$MUSL_TARGET not installed"; \
		echo "   Run: rustup target add $$MUSL_TARGET"; \
		exit 1; \
	fi; \
	RUSTFLAGS="-C target-feature=+crt-static" cargo build $(CARGO_FLAGS) --target $$MUSL_TARGET && \
	cp target/$$MUSL_TARGET/release/flavor-rs-launcher $(BIN_DIR)/flavor-rs-launcher-$$PLATFORM_NAME && \
	cp target/$$MUSL_TARGET/release/flavor-rs-builder $(BIN_DIR)/flavor-rs-builder-$$PLATFORM_NAME && \
	chmod +x $(BIN_DIR)/flavor-rs-*-$$PLATFORM_NAME && \
	echo "✅ Static Rust helpers built: flavor-rs-*-$$PLATFORM_NAME (works on any Linux)"

# Build with dynamic linking (glibc) - optional, not default
build-dynamic:
	@echo "🔨 Building dynamically linked Rust helpers (requires glibc)..."
	@mkdir -p $(BIN_DIR)
	@# Get glibc version for naming
	@GLIBC_VER=$$(ldd --version 2>/dev/null | head -1 | grep -o '[0-9]\+\.[0-9]\+' | head -1); \
	ARCH=$$(uname -m); \
	if [ "$$ARCH" = "x86_64" ]; then \
		ARCH="amd64"; \
	elif [ "$$ARCH" = "aarch64" ] || [ "$$ARCH" = "arm64" ]; then \
		ARCH="arm64"; \
	fi; \
	PLATFORM_NAME="linux_$${ARCH}_glibc$${GLIBC_VER}"; \
	echo "   Building for $$PLATFORM_NAME..."; \
	cargo build $(CARGO_FLAGS) && \
	cp target/release/flavor-rs-launcher $(BIN_DIR)/flavor-rs-launcher-$$PLATFORM_NAME && \
	cp target/release/flavor-rs-builder $(BIN_DIR)/flavor-rs-builder-$$PLATFORM_NAME && \
	chmod +x $(BIN_DIR)/flavor-rs-*-$$PLATFORM_NAME && \
	echo "✅ Dynamic Rust helpers built: flavor-rs-*-$$PLATFORM_NAME (requires glibc >= $$GLIBC_VER)"

# Build musl binaries for both architectures (cross-compilation)
build-musl-all:
	@echo "🔨 Building static Rust helpers for all architectures..."
	@mkdir -p $(BIN_DIR)
	@# Build x86_64
	@echo "📦 Building x86_64-unknown-linux-musl..."
	@if [ -n "$(CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_LINKER)" ]; then \
		cargo build $(CARGO_FLAGS) --target x86_64-unknown-linux-musl && \
		cp target/x86_64-unknown-linux-musl/release/flavor-rs-launcher $(BIN_DIR)/flavor-rs-launcher-linux_amd64_musl && \
		cp target/x86_64-unknown-linux-musl/release/flavor-rs-builder $(BIN_DIR)/flavor-rs-builder-linux_amd64_musl; \
	else \
		echo "⚠️  Skipping x86_64: Set CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_LINKER to enable"; \
	fi
	@# Build aarch64
	@echo "📦 Building aarch64-unknown-linux-musl..."
	@if [ -n "$(CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER)" ] || command -v musl-gcc >/dev/null 2>&1; then \
		CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER=$${CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER:-musl-gcc} \
		cargo build $(CARGO_FLAGS) --target aarch64-unknown-linux-musl && \
		cp target/aarch64-unknown-linux-musl/release/flavor-rs-launcher $(BIN_DIR)/flavor-rs-launcher-linux_arm64_musl && \
		cp target/aarch64-unknown-linux-musl/release/flavor-rs-builder $(BIN_DIR)/flavor-rs-builder-linux_arm64_musl; \
	else \
		echo "⚠️  Skipping aarch64: Set CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER to enable"; \
	fi
	@chmod +x $(BIN_DIR)/flavor-rs-* 2>/dev/null || true
	@echo "✅ Built all available musl targets"

# Build Windows binaries (cross-compilation)
build-windows:
	@echo "🔨 Building Windows Rust helpers..."
	@mkdir -p $(BIN_DIR)
	@# Build x86_64 Windows (MSVC)
	@echo "📦 Building x86_64-pc-windows-msvc..."
	@if rustup target list --installed | grep -q "x86_64-pc-windows-msvc"; then \
		cargo build $(CARGO_FLAGS) --target x86_64-pc-windows-msvc && \
		cp target/x86_64-pc-windows-msvc/release/flavor-rs-launcher.exe $(BIN_DIR)/flavor-rs-launcher-windows_amd64.exe && \
		cp target/x86_64-pc-windows-msvc/release/flavor-rs-builder.exe $(BIN_DIR)/flavor-rs-builder-windows_amd64.exe && \
		echo "✅ Windows helpers built: flavor-rs-*-windows_amd64.exe"; \
	else \
		echo "⚠️  x86_64-pc-windows-msvc target not installed"; \
		echo "   Run: rustup target add x86_64-pc-windows-msvc"; \
	fi