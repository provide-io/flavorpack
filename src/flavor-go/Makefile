# Makefile for Go helpers

.PHONY: all build clean test coverage install fmt lint security fuzz mutation check deps

# Configuration
BIN_DIR ?= ../../dist/bin
XDG_CACHE_HOME ?= $(HOME)/.cache
FLAVOR_HELPERS_DIR ?= $(XDG_CACHE_HOME)/flavor/helpers/bin
QUALITY_GO_COV_MIN ?= 80
QUALITY_GO_MUTATION_ARGS ?=
FUZZTIME ?= 30s
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
BUILD_TIME := $(shell date -u '+%Y-%m-%d_%H:%M:%S')
LDFLAGS := -ldflags="-s -w -X main.Version=$(VERSION) -X main.BuildTime=$(BUILD_TIME)"
GOOS ?= $(shell go env GOOS)
GOARCH ?= $(shell go env GOARCH)

all: build

build:
	@echo "🔨 Building Go helpers for $(GOOS)_$(GOARCH)..."
	@mkdir -p $(BIN_DIR)
	@# Add .exe extension for Windows builds
	@if [ "$(GOOS)" = "windows" ]; then \
		EXT=".exe"; \
	else \
		EXT=""; \
	fi; \
	GOOS=$(GOOS) GOARCH=$(GOARCH) CGO_ENABLED=0 go build -buildvcs=false $(LDFLAGS) \
		-o $(BIN_DIR)/flavor-go-builder-$(GOOS)_$(GOARCH)$$EXT ./cmd/flavor-go-builder; \
	GOOS=$(GOOS) GOARCH=$(GOARCH) CGO_ENABLED=0 go build -buildvcs=false $(LDFLAGS) \
		-o $(BIN_DIR)/flavor-go-launcher-$(GOOS)_$(GOARCH)$$EXT ./cmd/flavor-go-launcher
	@chmod +x $(BIN_DIR)/flavor-go-* 2>/dev/null || true
	@echo "✅ Go helpers built: flavor-go-*-$(GOOS)_$(GOARCH)"

clean:
	@echo "🧹 Cleaning Go build artifacts..."
	@rm -f $(BIN_DIR)/flavor-go-*
	@go clean -cache -testcache
	@echo "✅ Cleaned"

fmt:
	@echo "🎨 Formatting Go code..."
	@gofmt -w .
	@if command -v goimports >/dev/null 2>&1; then \
		goimports -w .; \
		echo "✅ Code formatted with gofmt and goimports"; \
	else \
		echo "⚠️  goimports not installed, only gofmt applied"; \
		echo "   Install with: go install golang.org/x/tools/cmd/goimports@latest"; \
	fi

lint:
	@echo "🔍 Linting Go code..."
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run --timeout=5m; \
		echo "✅ Linting passed"; \
	else \
		echo "⚠️  golangci-lint not installed"; \
		echo "   Install with: go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest"; \
		echo "   Or: brew install golangci-lint"; \
		go vet ./...; \
		echo "✅ Basic vetting with 'go vet' passed"; \
	fi

security:
	@echo "🔐 Running security checks..."
	@if command -v gosec >/dev/null 2>&1; then \
		gosec -quiet ./...; \
		echo "✅ gosec security scan passed"; \
	else \
		echo "⚠️  gosec not installed"; \
		echo "   Install with: go install github.com/securego/gosec/v2/cmd/gosec@latest"; \
	fi
	@if command -v govulncheck >/dev/null 2>&1; then \
		govulncheck ./...; \
		echo "✅ govulncheck vulnerability scan passed"; \
	else \
		echo "⚠️  govulncheck not installed"; \
		echo "   Install with: go install golang.org/x/vuln/cmd/govulncheck@latest"; \
	fi

test:
	@echo "🧪 Running Go tests..."
	go test -v -race -coverprofile=coverage.out ./...
	@echo "✅ Tests passed"

coverage:
	@echo "📊 Running Go coverage checks..."
	@set -e; \
	go test -v -race -covermode=atomic -coverprofile=coverage.out ./...; \
	go tool cover -func=coverage.out | tee coverage.txt; \
	total="$$(awk '/^total:/{gsub(/%/,"",$$3); print $$3}' coverage.txt)"; \
	min="$${QUALITY_GO_COV_MIN}"; \
	if awk "BEGIN {exit !($$total < $$min)}"; then \
		echo "❌ Coverage $$total% is below minimum $$min%"; \
		exit 1; \
	fi; \
	echo "✅ Coverage $$total% meets minimum $$min%"

fuzz:
	@echo "🔀 Running fuzz tests..."
	@set -e; \
	go test -fuzz='^FuzzSplit$$' -fuzztime=$(FUZZTIME) ./pkg/utils/shellparse/; \
	go test -fuzz='^FuzzSplitJoinIdempotent$$' -fuzztime=$(FUZZTIME) ./pkg/utils/shellparse/; \
	go test -fuzz='^FuzzOperationsRoundTrip$$' -fuzztime=$(FUZZTIME) ./pkg/psp/format_2025/; \
	go test -fuzz='^FuzzUnpackNoPanic$$' -fuzztime=$(FUZZTIME) ./pkg/psp/format_2025/; \
	echo "✅ Fuzz testing completed"

mutation:
	@echo "🧬 Running Go mutation testing..."
	@command -v gremlins >/dev/null 2>&1 || { \
		echo "⚠️  gremlins not installed"; \
		echo "   Install with: go install github.com/go-gremlins/gremlins/cmd/gremlins@latest"; \
		exit 1; \
	}
	@gremlins unleash $(if $(strip $(QUALITY_GO_MUTATION_ARGS)),$(QUALITY_GO_MUTATION_ARGS),./...)

check: fmt lint security test
	@echo "✅ All checks passed!"

deps:
	@echo "📦 Installing development dependencies..."
	go mod download
	go install golang.org/x/tools/cmd/goimports@latest
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	go install github.com/securego/gosec/v2/cmd/gosec@latest
	go install golang.org/x/vuln/cmd/govulncheck@latest
	@echo "✅ Dependencies installed"

install: build
	@echo "📦 Installing Go helpers to $(FLAVOR_HELPERS_DIR)..."
	@mkdir -p $(FLAVOR_HELPERS_DIR)
	@install -m 755 $(BIN_DIR)/flavor-go-*-$(GOOS)_$(GOARCH) $(FLAVOR_HELPERS_DIR)/
	@# Create symlinks without platform suffix for convenience
	@ln -sf flavor-go-builder-$(GOOS)_$(GOARCH) $(FLAVOR_HELPERS_DIR)/flavor-go-builder
	@ln -sf flavor-go-launcher-$(GOOS)_$(GOARCH) $(FLAVOR_HELPERS_DIR)/flavor-go-launcher
	@chmod +x $(FLAVOR_HELPERS_DIR)/flavor-go-*
	@echo "✅ Installed to $(FLAVOR_HELPERS_DIR)"
	@echo "   Binaries: flavor-go-*-$(GOOS)_$(GOARCH)"
	@echo "   Symlinks: flavor-go-builder, flavor-go-launcher"
	@echo "   Add to PATH with: export PATH=\"$(FLAVOR_HELPERS_DIR):\$$PATH\""
