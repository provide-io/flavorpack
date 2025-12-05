# Flavor Makefile
# Root-level build and test orchestration

.PHONY: help docs-setup docs-build docs-serve docs-clean
help: ## Show this help message
	@echo "Flavor Build System"
	@echo "=================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "%-20s %s\n", $$1, $$2}'

.PHONY: test
test: ## Run Python tests
	uv run pytest tests/

.PHONY: test-cov
test-cov: ## Run Python tests with coverage
	uv run pytest --cov=flavor --cov-report=term-missing --cov-report=html tests/

.PHONY: test-cov-xml
test-cov-xml: ## Run Python tests with XML coverage for CI
	uv run pytest --cov=flavor --cov-report=xml --cov-report=term tests/

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
