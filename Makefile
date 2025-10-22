# Flavor Makefile
# Root-level build and test orchestration

.PHONY: help
help: ## Show this help message
	@echo "Flavor Build System"
	@echo "=================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "%-20s %s\n", $$1, $$2}'

.PHONY: test
test: ## Run Python tests
	source workenv/bin/activate && pytest tests/

.PHONY: test-cov
test-cov: ## Run Python tests with coverage
	source workenv/bin/activate && pytest --cov=flavor --cov-report=term-missing --cov-report=html tests/

.PHONY: test-cov-xml
test-cov-xml: ## Run Python tests with XML coverage for CI
	source workenv/bin/activate && pytest --cov=flavor --cov-report=xml --cov-report=term tests/

# Mutation Testing
.PHONY: test-mutation
test-mutation: ## Run mutation testing quality tests
	@source workenv/bin/activate && pytest -m mutation -v

.PHONY: mutmut
mutmut: ## Run mutation testing with mutmut (legacy)
	@echo "🧬 Running mutation testing..."
	@source workenv/bin/activate && mutmut run

.PHONY: mutmut-results
mutmut-results: ## Show mutation testing results (legacy)
	@source workenv/bin/activate && mutmut results

.PHONY: mutmut-html
mutmut-html: ## Generate HTML mutation testing report (legacy)
	@source workenv/bin/activate && mutmut html
	@echo "📊 HTML report generated in html/"

.PHONY: mutmut-clean
mutmut-clean: ## Clean mutation testing artifacts
	@rm -rf mutants/ .mutmut-cache html/ .mutation-artifacts/
	@echo "🧹 Mutation testing artifacts cleaned"

# Testkit Mutation Testing (Recommended)
.PHONY: mutation-all
mutation-all: ## Run mutation testing on all code (testkit)
	@echo "🧬 Running mutation testing with testkit..."
	@source workenv/bin/activate && testkit quality mutate src/flavor

.PHONY: mutation-security
mutation-security: ## Run mutation testing on security-critical modules
	@echo "🔒 Testing security-critical modules..."
	@source workenv/bin/activate && testkit quality mutate src/flavor --priority critical

.PHONY: mutation-core
mutation-core: ## Run mutation testing on core PSPF modules
	@echo "🎯 Testing core modules..."
	@source workenv/bin/activate && testkit quality mutate src/flavor --priority high

.PHONY: mutation-changed
mutation-changed: ## Run mutation testing on changed files only
	@echo "📝 Testing changed files..."
	@source workenv/bin/activate && testkit quality mutate src/flavor --changed-only

.PHONY: mutation-module
mutation-module: ## Run mutation testing on specific module (usage: make mutation-module MODULE=path/to/module.py)
	@if [ -z "$(MODULE)" ]; then \
		echo "Usage: make mutation-module MODULE=path/to/module.py"; \
		exit 1; \
	fi
	@echo "🎯 Testing module: $(MODULE)..."
	@source workenv/bin/activate && testkit quality mutate src/flavor --module $(MODULE)

.PHONY: mutation-report
mutation-report: ## Generate HTML mutation testing report
	@echo "📊 Generating mutation report..."
	@source workenv/bin/activate && testkit quality mutate src/flavor --format html

.PHONY: build-ingredients
build-ingredients: ## Build all ingredients (Go and Rust)
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
wheel-universal: ## Build universal wheel (no embedded ingredients)
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
	@# Build ingredients first
	@$(MAKE) build-ingredients
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