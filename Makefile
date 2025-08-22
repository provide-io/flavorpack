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
	source env.sh && pytest tests/

.PHONY: build-helpers
build-helpers: ## Build all helpers (Go and Rust)
	cd helpers && ./build.sh

# PSPF Validation with Pretaster
.PHONY: validate-pspf
validate-pspf: ## Run PSPF compatibility tests with pretaster
	@cd helpers/pretaster && make test

.PHONY: validate-pspf-full
validate-pspf-full: ## Run full PSPF validation suite with pretaster
	@cd helpers/pretaster && make all

.PHONY: validate-pspf-combo
validate-pspf-combo: ## Test all builder/launcher combinations
	@cd helpers/pretaster && make combo-test

.PHONY: validate-package
validate-package: ## Validate a PSPF package (usage: make validate-package PACKAGE=path/to/package.psp)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "Usage: make validate-package PACKAGE=path/to/package.psp"; \
		exit 1; \
	fi
	@.github/scripts/validate-package-with-pretaster.sh "$(PACKAGE)"

.PHONY: pretaster-clean
pretaster-clean: ## Clean pretaster artifacts
	@cd helpers/pretaster && make clean

.PHONY: pretaster-logs
pretaster-logs: ## Show pretaster test logs
	@cd helpers/pretaster && make show-logs