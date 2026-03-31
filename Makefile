# Flavor Makefile
# Root-level build and test orchestration

.PHONY: help docs-setup docs-build docs-serve docs-clean
help: ## Show this help message
	@echo "Flavor Build System"
	@echo "=================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "%-20s %s\n", $$1, $$2}'

.PHONY: check
check: ## Run all quality gates (Python, Go, Rust)
	@echo "=== Python: ruff ==="
	ruff check src/ tests/
	@echo "=== Python: mypy ==="
	uv run mypy src/flavor
	uv run mypy tests/ --exclude 'tests/(taster|pretaster|assets)/'
	@echo "=== Go: fmt + vet + build + test ==="
	@cd src/flavor-go && gofmt -l . | grep . && exit 1 || true
	cd src/flavor-go && go vet ./... && go build ./... && go test ./...
	@echo "=== Rust: fmt + clippy + test ==="
	cd src/flavor-rs && cargo fmt --check && cargo clippy -- -D warnings && cargo test
	@echo "=== Version sync ==="
	python scripts/check_version_sync.py
	@echo "=== ALL GATES PASSED ==="

.PHONY: test
test: ## Run Python tests
	PYTHONUTF8=1 uv run pytest tests/

.PHONY: test-cov
test-cov: ## Run Python tests with coverage
	PYTHONUTF8=1 uv run pytest --cov=flavor --cov-report=term-missing --cov-report=html tests/

.PHONY: test-cov-xml
test-cov-xml: ## Run Python tests with XML coverage for CI
	PYTHONUTF8=1 uv run pytest --cov=flavor --cov-report=xml --cov-report=term tests/

# Mutation Testing (using mutmut directly)
.PHONY: mutation-run
mutation-run: ## Run mutation testing with mutmut
	@echo "🧬 Running mutation testing..."
	@mutmut run

.PHONY: mutation-results
mutation-results: ## Show mutation testing results
	@mutmut results

.PHONY: mutation-browse
mutation-browse: ## Open interactive mutation browser
	@mutmut browse

.PHONY: mutation-clean
mutation-clean: ## Clean mutation testing artifacts
	@rm -rf .mutmut-cache html/
	@echo "🧹 Mutation testing artifacts cleaned"

# ==================== Go Testing ====================

.PHONY: test-go
test-go: ## Run Go unit tests
	@cd src/flavor-go && go test ./... -v

.PHONY: test-go-fuzz-shellparse
test-go-fuzz-shellparse: ## Fuzz shellparse (runs for 30s; override with FUZZTIME=Xs)
	@cd src/flavor-go && go test -fuzz='^FuzzSplit$$' -fuzztime=$${FUZZTIME:-30s} ./pkg/utils/shellparse/
	@cd src/flavor-go && go test -fuzz='^FuzzSplitJoinIdempotent$$' -fuzztime=$${FUZZTIME:-30s} ./pkg/utils/shellparse/

.PHONY: test-go-fuzz-operations
test-go-fuzz-operations: ## Fuzz operation pack/unpack (runs for 30s; override with FUZZTIME=Xs)
	@cd src/flavor-go && go test -fuzz='^FuzzOperationsRoundTrip$$' -fuzztime=$${FUZZTIME:-30s} ./pkg/psp/format_2025/
	@cd src/flavor-go && go test -fuzz='^FuzzUnpackNoPanic$$' -fuzztime=$${FUZZTIME:-30s} ./pkg/psp/format_2025/

.PHONY: test-go-fuzz
test-go-fuzz: test-go-fuzz-shellparse test-go-fuzz-operations ## Fuzz all Go targets (30s each)

.PHONY: mutation-go
mutation-go: ## Run Go mutation testing with gremlins (install: go install github.com/go-gremlins/gremlins/cmd/gremlins@latest)
	@command -v gremlins >/dev/null 2>&1 || { echo "Install gremlins: go install github.com/go-gremlins/gremlins/cmd/gremlins@latest"; exit 1; }
	@cd src/flavor-go && gremlins unleash ./...

# ==================== Rust Testing ====================

.PHONY: test-rust
test-rust: ## Run Rust unit + proptest tests
	@cd src/flavor-rs && cargo test

.PHONY: test-rust-proptest
test-rust-proptest: ## Run Rust proptest property-based tests only
	@cd src/flavor-rs && cargo test prop_

.PHONY: mutation-rust
mutation-rust: ## Run Rust mutation testing with cargo-mutants (install: cargo install cargo-mutants)
	@command -v cargo-mutants >/dev/null 2>&1 || cargo install cargo-mutants
	@cd src/flavor-rs && cargo mutants

# ==================== Security Scanning (local) ====================

.PHONY: security-go
security-go: ## Run Go security scans locally (gosec + govulncheck)
	@echo "🔍 Running gosec..."
	@command -v gosec >/dev/null 2>&1 || go install github.com/securego/gosec/v2/cmd/gosec@latest
	@cd src/flavor-go && gosec ./...
	@echo "🔍 Running govulncheck..."
	@command -v govulncheck >/dev/null 2>&1 || go install golang.org/x/vuln/cmd/govulncheck@latest
	@cd src/flavor-go && govulncheck ./...

.PHONY: security-rust
security-rust: ## Run Rust security scans locally (cargo-audit + cargo-deny)
	@echo "🔍 Running cargo audit..."
	@command -v cargo-audit >/dev/null 2>&1 || cargo install cargo-audit
	@cd src/flavor-rs && cargo audit
	@echo "🔍 Running cargo deny..."
	@command -v cargo-deny >/dev/null 2>&1 || cargo install cargo-deny
	@cd src/flavor-rs && cargo deny check

.PHONY: security
security: security-go security-rust ## Run all security scans locally

.PHONY: build-helpers
build-helpers: ## Build all helpers (Go and Rust)
	./build.sh

# PSPF Validation with Pretaster
.PHONY: validate-pspf
validate-pspf: ## Run PSPF compatibility tests with pretaster
	@cd tests/pretaster && make test

.PHONY: validate-pspf-full
validate-pspf-full: ## Run full PSPF validation suite with pretaster
	@cd tests/pretaster && make all

.PHONY: validate-pspf-combo
validate-pspf-combo: ## Test all builder/launcher combinations
	@cd tests/pretaster && make combo-test

.PHONY: validate-package
validate-package: ## Validate a PSPF package (usage: make validate-package PACKAGE=path/to/package.psp)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "Usage: make validate-package PACKAGE=path/to/package.psp"; \
		exit 1; \
	fi
	@.github/scripts/validate-package-with-pretaster.sh "$(PACKAGE)"

.PHONY: clean-cache
clean-cache: ## Clean Flavor workenv cache
	@cd tests/pretaster && make clean-cache

.PHONY: pretaster-logs
pretaster-logs: ## Show pretaster test logs
	@cd tests/pretaster && make show-logs

# ==================== Release Management ====================

.PHONY: wheel
wheel: ## Build platform-specific wheel (usage: make wheel PLATFORM=darwin_arm64)
	@if [ -z "$(PLATFORM)" ]; then \
		echo "Usage: make wheel PLATFORM=darwin_arm64"; \
		echo "Available platforms: darwin_arm64, darwin_amd64, linux_amd64, linux_arm64"; \
		exit 1; \
	fi
	@python3 tools/build_wheel.py --platform $(PLATFORM)

.PHONY: wheel-universal
wheel-universal: ## Build universal wheel (no embedded helpers)
	@python3 tools/build_wheel.py --platform universal

.PHONY: release-all
release-all: ## Build wheels for all platforms
	@echo "🚀 Building release wheels for all platforms..."
	@python3 tools/build_wheel.py --all

.PHONY: release-validate
release-validate: ## Validate all wheels in dist/
	@python3 tools/validate_wheel.py --all

.PHONY: release-validate-full
release-validate-full: ## Full validation of all wheels (includes installation test)
	@python3 tools/validate_wheel.py --all --full

.PHONY: release-test
release-test: ## Test release process locally
	@echo "🧪 Testing release process..."
	@# Build helpers first
	@$(MAKE) build-helpers
	@# Build a test wheel for current platform
	@PLATFORM=$$(python3 -c "import platform; arch = platform.machine().lower(); arch = 'amd64' if arch == 'x86_64' else 'arm64' if arch in ['arm64', 'aarch64'] else arch; os = 'darwin' if platform.system() == 'Darwin' else 'linux' if platform.system() == 'Linux' else 'windows'; print(f'{os}_{arch}')") && \
		echo "Testing with platform: $$PLATFORM" && \
		python3 tools/build_wheel.py --platform $$PLATFORM
	@# Validate the wheel
	@python3 tools/validate_wheel.py --all --full

.PHONY: release-clean
release-clean: ## Clean release artifacts
	@rm -rf dist/ build/ *.egg-info src/flavor.egg-info
	@rm -rf dist/bin
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✨ Release artifacts cleaned"

.PHONY: release-upload
release-upload: ## Upload wheels to PyPI (requires authentication)
	@if [ -z "$$(ls -A dist/*.whl 2>/dev/null)" ]; then \
		echo "❌ No wheels found in dist/"; \
		echo "Run 'make release-all' first"; \
		exit 1; \
	fi
	@echo "📤 Uploading to PyPI..."
	@twine upload dist/*.whl

.PHONY: release-upload-test
release-upload-test: ## Upload wheels to TestPyPI for testing
	@if [ -z "$$(ls -A dist/*.whl 2>/dev/null)" ]; then \
		echo "❌ No wheels found in dist/"; \
		echo "Run 'make release-all' first"; \
		exit 1; \
	fi
	@echo "📤 Uploading to TestPyPI..."
	@twine upload --repository testpypi dist/*.whl
# Documentation targets
docs-setup:
	@python -c "from provide.foundry.config import extract_base_mkdocs; from pathlib import Path; extract_base_mkdocs(Path('.'))"

docs-build: docs-setup
	@mkdocs build

docs-serve: docs-setup
	@mkdocs serve

docs-clean:
	@rm -rf site .provide

# ==================== Memory Profiling ====================

.PHONY: memray
memray: ## Run memray memory stress tests (all subsystems)
	@mkdir -p memray-output
	uv run python scripts/memray/run_memray_stress.py

.PHONY: memray-analyze
memray-analyze: ## Analyze memray results and generate report + flamegraphs
	uv run python scripts/memray/memray_analysis.py

.PHONY: memray-flamegraph
memray-flamegraph: ## Generate flamegraphs from memray binaries
	@for f in memray-output/memray_*.bin; do \
		[ -f "$$f" ] || continue; \
		echo "Processing $$(basename $$f)..."; \
		uv run memray flamegraph "$$f" -o "$${f%.bin}_flamegraph.html" 2>/dev/null || true; \
	done
