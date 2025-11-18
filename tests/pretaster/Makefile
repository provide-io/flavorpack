# Pretaster Makefile
# Comprehensive build and test management for PSPF test suite

# Configuration  
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

# Paths
HELPERS_DIR := ../../dist
BIN_DIR := $(HELPERS_DIR)/bin
DIST_DIR := dist
LOGS_DIR := logs
TESTS_DIR := tests
CONFIGS_DIR := configs

# Platform detection
OS := $(shell uname -s | tr '[:upper:]' '[:lower:]')
ARCH := $(shell uname -m)

# Normalize Windows OS names (MINGW64_NT, MSYS_NT, CYGWIN_NT -> windows)
ifneq ($(findstring mingw,$(OS)),)
    OS := windows
endif
ifneq ($(findstring msys,$(OS)),)
    OS := windows
endif
ifneq ($(findstring cygwin,$(OS)),)
    OS := windows
endif

# On Windows ARM64, uname -m returns x86_64 (emulation layer)
# Check uname -s for ARM64 indicator
ifeq ($(OS),windows)
    UNAME_S := $(shell uname -s)
    ifneq ($(findstring ARM64,$(UNAME_S)),)
        ARCH := arm64
    endif
    ifneq ($(findstring arm64,$(UNAME_S)),)
        ARCH := arm64
    endif
endif

# Normalize architecture names
ifeq ($(ARCH),x86_64)
    ARCH := amd64
endif
ifeq ($(ARCH),aarch64)
    ARCH := arm64
endif
PLATFORM := $(OS)_$(ARCH)

# Windows executable extension
ifeq ($(OS),windows)
    EXE := .exe
else
    EXE :=
endif

# Builders and Launchers with platform suffix and extension
RS_BUILDER := $(BIN_DIR)/flavor-rs-builder-$(PLATFORM)$(EXE)
GO_BUILDER := $(BIN_DIR)/flavor-go-builder-$(PLATFORM)$(EXE)
RS_LAUNCHER := $(BIN_DIR)/flavor-rs-launcher-$(PLATFORM)$(EXE)
GO_LAUNCHER := $(BIN_DIR)/flavor-go-launcher-$(PLATFORM)$(EXE)

# Test packages
ECHO_PSP := $(DIST_DIR)/echo-test.psp
SHELL_PSP := $(DIST_DIR)/shell-test.psp
ENV_PSP := $(DIST_DIR)/env-test.psp
ORCHESTRATE_PSP := $(DIST_DIR)/orchestrate-test.psp
PRETASTER_PSP := $(DIST_DIR)/pretaster.psp

# Combination test packages
COMBO_RS_RS := $(DIST_DIR)/pretaster-rs-rs.psp
COMBO_RS_GO := $(DIST_DIR)/pretaster-rs-go.psp
COMBO_GO_RS := $(DIST_DIR)/pretaster-go-rs.psp
COMBO_GO_GO := $(DIST_DIR)/pretaster-go-go.psp

# All test packages
SIMPLE_PACKAGES := $(ECHO_PSP) $(SHELL_PSP) $(ENV_PSP)
TEST_PACKAGES := $(SIMPLE_PACKAGES) $(ORCHESTRATE_PSP)
COMBO_PACKAGES := $(COMBO_RS_RS) $(COMBO_RS_GO) $(COMBO_GO_RS) $(COMBO_GO_GO)
ALL_PACKAGES := $(TEST_PACKAGES) $(COMBO_PACKAGES) $(PRETASTER_PSP)

# Key seed for reproducible builds
KEY_SEED := test123

# Log level for tests (set to debug for troubleshooting)
LOG_LEVEL ?= error

# Timestamp for logs
TIMESTAMP := $(shell date +"%Y%m%d_%H%M%S")

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
NC := \033[0m # No Color

# Helper function for colored output
define print
	@echo -e "$(2)$(1)$(NC)"
endef

###################
# Primary Targets #
###################

.PHONY: all
all: clean build test ## Clean everything, build helpers, and run all tests
	$(call print,"✅ All tasks completed!",$(GREEN))

.PHONY: help
help: ## Show this help message
	@echo -e "$(CYAN)Pretaster Makefile$(NC)"
	@echo -e "$(CYAN)==================$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo -e "$(PURPLE)Examples:$(NC)"
	@echo "  make build          # Build all helpers"
	@echo "  make test           # Run all tests"
	@echo "  make package-all    # Build all test packages"
	@echo "  make combo-test     # Test all builder/launcher combinations"
	@echo "  make clean          # Remove all built artifacts"

##################
# Build Targets  #
##################

.PHONY: build
build: build-helpers ## Build all helpers (Go and Rust)

.PHONY: build-helpers
build-helpers: ## Build Go and Rust helpers (skipped when in PSP or CI)
ifdef FLAVOR_WORKENV
	$(call print,"📦 Running in PSP - skipping helper build",$(YELLOW))
else ifdef CI
	$(call print,"📦 Running in CI - helpers should be pre-downloaded",$(YELLOW))
else
	$(call print,"🔨 Building helpers...",$(BLUE))
	@cd ../.. && ./build.sh
	$(call print,"✅ Helpers built successfully",$(GREEN))
endif

.PHONY: build-go
build-go: ## Build only Go helpers
	$(call print,"🐹 Building Go helpers...",$(BLUE))
	@cd ../../src/flavor-go && \
		go build -o $(BIN_DIR)/flavor-go-builder-$(PLATFORM) cmd/flavor-go-builder/main.go && \
		go build -o $(BIN_DIR)/flavor-go-launcher-$(PLATFORM) cmd/flavor-go-launcher/main.go
	$(call print,"✅ Go helpers built",$(GREEN))

.PHONY: build-rust
build-rust: ## Build only Rust helpers
	$(call print,"🦀 Building Rust helpers...",$(BLUE))
	@cd ../../src/flavor-rs && \
		cargo build --release && \
		cp target/release/flavor-rs-builder $(BIN_DIR)/flavor-rs-builder-$(PLATFORM) && \
		cp target/release/flavor-rs-launcher $(BIN_DIR)/flavor-rs-launcher-$(PLATFORM)
	$(call print,"✅ Rust helpers built",$(GREEN))

####################
# Package Targets  #
####################

.PHONY: package-all
package-all: $(ALL_PACKAGES) ## Build all test packages

$(DIST_DIR):
	@mkdir -p $(DIST_DIR)

$(LOGS_DIR):
	@mkdir -p $(LOGS_DIR)

# Individual test packages
$(ECHO_PSP): $(DIST_DIR)
	$(call print,"📦 Building echo test package...",$(CYAN))
	@$(GO_BUILDER) \
		--manifest $(CONFIGS_DIR)/test-echo.json \
		--launcher-bin $(RS_LAUNCHER) \
		--output $@ \
		--key-seed $(KEY_SEED)

$(SHELL_PSP): $(DIST_DIR)
	$(call print,"📦 Building shell test package...",$(CYAN))
	@$(RS_BUILDER) \
		--manifest $(CONFIGS_DIR)/test-shell.json \
		--launcher-bin $(GO_LAUNCHER) \
		--output $@ \
		--key-seed $(KEY_SEED)

$(ENV_PSP): $(DIST_DIR)
	$(call print,"📦 Building environment test package...",$(CYAN))
	@$(GO_BUILDER) \
		--manifest $(CONFIGS_DIR)/test-env.json \
		--launcher-bin $(RS_LAUNCHER) \
		--output $@ \
		--key-seed $(KEY_SEED)

$(ORCHESTRATE_PSP): $(DIST_DIR)
	$(call print,"📦 Building orchestration test package...",$(CYAN))
	@$(RS_BUILDER) \
		--manifest $(CONFIGS_DIR)/test-orchestrate.json \
		--launcher-bin $(GO_LAUNCHER) \
		--output $@ \
		--key-seed $(KEY_SEED)

$(PRETASTER_PSP): $(DIST_DIR)
	$(call print,"📦 Building pretaster package...",$(CYAN))
	@$(RS_BUILDER) \
		--manifest $(CONFIGS_DIR)/pretaster.json \
		--launcher-bin $(RS_LAUNCHER) \
		--output $@ \
		--key-seed $(KEY_SEED)

# Combination packages
$(COMBO_RS_RS): $(DIST_DIR)
	@$(RS_BUILDER) \
		--manifest $(CONFIGS_DIR)/test-taster-lite.json \
		--launcher-bin $(RS_LAUNCHER) \
		--output $@ \
		--key-seed $(KEY_SEED)

$(COMBO_RS_GO): $(DIST_DIR)
	@$(RS_BUILDER) \
		--manifest $(CONFIGS_DIR)/test-taster-lite.json \
		--launcher-bin $(GO_LAUNCHER) \
		--output $@ \
		--key-seed $(KEY_SEED)

$(COMBO_GO_RS): $(DIST_DIR)
	@$(GO_BUILDER) \
		--manifest $(CONFIGS_DIR)/test-taster-lite.json \
		--launcher-bin $(RS_LAUNCHER) \
		--output $@ \
		--key-seed $(KEY_SEED)

$(COMBO_GO_GO): $(DIST_DIR)
	@$(GO_BUILDER) \
		--manifest $(CONFIGS_DIR)/test-taster-lite.json \
		--launcher-bin $(GO_LAUNCHER) \
		--output $@ \
		--key-seed $(KEY_SEED)

#################
# Test Targets  #
#################

.PHONY: test
test: test-core test-combo ## Run all tests

.PHONY: test-core
test-core: $(SIMPLE_PACKAGES) $(LOGS_DIR) ## Run core test suite (without orchestration)
	@# Strip extended attributes from built packages (macOS security)
	@xattr -cr $(DIST_DIR) 2>/dev/null || true
	$(call print,"🧪 Running core tests...",$(PURPLE))
	FLAVOR_LOG_LEVEL=$(LOG_LEVEL) $(TESTS_DIR)/test-pretaster.sh || (echo "❌ Core tests failed with exit code $$?"; exit 1)
	$(call print,"✅ Core tests completed",$(GREEN))

.PHONY: test-combo
test-combo: combo-test ## Alias for combo-test

.PHONY: combo-test
combo-test: build-helpers ## Test all builder/launcher combinations
	@mkdir -p $(LOGS_DIR)
	$(call print,"🎯 Testing all builder/launcher combinations...",$(PURPLE))
	@$(TESTS_DIR)/combination-tests.sh || (echo "❌ Combination tests failed with exit code $$?"; exit 1)
	$(call print,"✅ Combination tests completed",$(GREEN))
	$(call print,"📁 Logs saved in $(LOGS_DIR)/",$(CYAN))

.PHONY: test-direct
test-direct: build-helpers ## Test direct PSP execution
	$(call print,"🎯 Testing direct PSP execution...",$(PURPLE))
	@$(TESTS_DIR)/direct-execution-tests.sh || (echo "❌ Direct execution tests failed with exit code $$?"; exit 1)
	$(call print,"✅ Direct execution tests completed",$(GREEN))

.PHONY: test-echo
test-echo: $(ECHO_PSP) ## Test echo package only
	@FLAVOR_LOG_LEVEL=$(LOG_LEVEL) $(ECHO_PSP) "Hello from Makefile test!"

.PHONY: test-shell
test-shell: $(SHELL_PSP) ## Test shell package only
	@FLAVOR_LOG_LEVEL=$(LOG_LEVEL) $(SHELL_PSP)

.PHONY: test-env
test-env: $(ENV_PSP) ## Test environment package only
	@FLAVOR_LOG_LEVEL=$(LOG_LEVEL) $(ENV_PSP)

.PHONY: test-orchestrate
test-orchestrate: $(ORCHESTRATE_PSP) ## Test orchestration package only
	@FLAVOR_LOG_LEVEL=$(LOG_LEVEL) $(ORCHESTRATE_PSP)

.PHONY: test-pretaster
test-pretaster: $(PRETASTER_PSP) ## Test pretaster package interactively
	$(call print,"🍷 Running pretaster...",$(PURPLE))
	@echo "Available commands: info, env, argv, exit, echo, file, signals"
	@$(PRETASTER_PSP) info

########################
# Verification Targets #
########################

.PHONY: verify
verify: verify-structure verify-helpers ## Verify project structure and helpers

.PHONY: verify-structure
verify-structure: ## Verify directory structure is correct
	$(call print,"🔍 Verifying project structure...",$(BLUE))
	@test -d $(CONFIGS_DIR) || (echo "❌ Missing configs/"; exit 1)
	@test -d scripts || (echo "❌ Missing scripts/"; exit 1)
	@test -d slots || (echo "❌ Missing slots/"; exit 1)
	@test -d $(TESTS_DIR) || (echo "❌ Missing tests/"; exit 1)
	@test -d docs || (echo "❌ Missing docs/"; exit 1)
	$(call print,"✅ Structure verified",$(GREEN))

.PHONY: verify-helpers
verify-helpers: ## Verify helpers are built
	$(call print,"🔍 Verifying helpers...",$(BLUE))
	@test -f $(RS_BUILDER) || (echo "❌ Missing Rust builder"; exit 1)
	@test -f $(GO_BUILDER) || (echo "❌ Missing Go builder"; exit 1)
	@test -f $(RS_LAUNCHER) || (echo "❌ Missing Rust launcher"; exit 1)
	@test -f $(GO_LAUNCHER) || (echo "❌ Missing Go launcher"; exit 1)
	$(call print,"✅ Helpers verified",$(GREEN))

####################
# Utility Targets  #
####################

.PHONY: clean
clean: ## Remove all built artifacts and workenv cache
	$(call print,"🧹 Cleaning up...",$(YELLOW))
	@rm -rf $(DIST_DIR)
	@rm -rf $(LOGS_DIR)
	@rm -f *.psp
	@rm -f test-*.txt
	@rm -f .extraction.*
	@rm -f scripts/*.tar.gz
	@rm -f slots/*.tar.gz
	@rm -f test-package.tar.gz
	@# Clean workenv cache including .pspf directories
	@CACHE_DIR=$${XDG_CACHE_HOME:-$$HOME/.cache}; \
	rm -rf $$CACHE_DIR/flavor/workenv/* 2>/dev/null || true; \
	rm -rf $$CACHE_DIR/flavor/workenv/.* 2>/dev/null || true
	$(call print,"✅ Cleanup complete",$(GREEN))

.PHONY: cache-dir
cache-dir: ## Show cache directory location (like uv cache dir)
	@echo "$${XDG_CACHE_HOME:-$$HOME/.cache}/flavor"

.PHONY: clean-cache
clean-cache: ## Clean Flavor workenv cache (respects XDG_CACHE_HOME)
	$(call print,"🧹 Cleaning Flavor cache...",$(YELLOW))
	@# Use XDG_CACHE_HOME if set, otherwise ~/.cache (same as uv)
	@CACHE_DIR=$${XDG_CACHE_HOME:-$$HOME/.cache}; \
	rm -rf $$CACHE_DIR/flavor/workenv/.* 2>/dev/null || true; \
	rm -rf $$CACHE_DIR/flavor/workenv/* 2>/dev/null || true
	$(call print,"✅ Cache cleaned from $${XDG_CACHE_HOME:-$$HOME/.cache}/flavor",$(GREEN))

.PHONY: clean-logs
clean-logs: ## Remove only log files
	$(call print,"🧹 Cleaning logs...",$(YELLOW))
	@rm -rf $(LOGS_DIR)
	$(call print,"✅ Logs cleaned",$(GREEN))

.PHONY: clean-dist
clean-dist: ## Remove only built packages
	$(call print,"🧹 Cleaning dist...",$(YELLOW))
	@rm -rf $(DIST_DIR)
	$(call print,"✅ Dist cleaned",$(GREEN))

.PHONY: info
info: ## Show current configuration
	@echo -e "$(CYAN)Pretaster Configuration$(NC)"
	@echo -e "$(CYAN)=======================$(NC)"
	@echo ""
	@echo -e "$(YELLOW)Paths:$(NC)"
	@echo "  Helpers: $(HELPERS_DIR)"
	@echo "  Binaries:   $(BIN_DIR)"
	@echo "  Dist:       $(DIST_DIR)"
	@echo "  Logs:       $(LOGS_DIR)"
	@echo "  Tests:      $(TESTS_DIR)"
	@echo "  Configs:    $(CONFIGS_DIR)"
	@echo ""
	@echo -e "$(YELLOW)Builders:$(NC)"
	@echo "  Rust:       $(RS_BUILDER)"
	@echo "  Go:         $(GO_BUILDER)"
	@echo ""
	@echo -e "$(YELLOW)Launchers:$(NC)"
	@echo "  Rust:       $(RS_LAUNCHER)"
	@echo "  Go:         $(GO_LAUNCHER)"
	@echo ""
	@echo -e "$(YELLOW)Settings:$(NC)"
	@echo "  Key Seed:   $(KEY_SEED)"
	@echo "  Log Level:  $(LOG_LEVEL)"

.PHONY: show-logs
show-logs: ## Show recent log files
	$(call print,"📄 Recent log files:",$(CYAN))
	@ls -lat $(LOGS_DIR) 2>/dev/null | head -10 || echo "No logs found"

.PHONY: watch
watch: ## Watch for changes and rebuild (requires fswatch)
	$(call print,"👁️ Watching for changes...",$(BLUE))
	@which fswatch > /dev/null || (echo "❌ fswatch not installed. Run: brew install fswatch"; exit 1)
	@fswatch -o scripts/ configs/ | xargs -n1 -I{} make package-all

#######################
# Development Targets #
#######################

.PHONY: dev
dev: clean build package-all test ## Full development cycle

.PHONY: quick
quick: $(PRETASTER_PSP) ## Quick build of pretaster for testing
	$(call print,"🚀 Pretaster ready at $(PRETASTER_PSP)",$(GREEN))

.PHONY: debug
debug: ## Run tests with debug logging
	@$(MAKE) test LOG_LEVEL=debug

.PHONY: trace
trace: ## Run tests with trace logging
	@$(MAKE) test LOG_LEVEL=trace

# Prevent make from treating existing files as intermediate
.PRECIOUS: $(ALL_PACKAGES)

# Silent by default, use VERBOSE=1 for detailed output
ifndef VERBOSE
.SILENT:
endif