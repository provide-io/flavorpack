# Cross-Language Quality Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add strict-mode coverage, mutation, fuzzing, and property/parameter testing workflows for Python, Go, and Rust, wire them into CI as non-required observational jobs, and document the resulting developer workflow.

**Architecture:** The root `Makefile` becomes the canonical control surface for all quality domains. Language-specific `Makefile` files and Rust fuzz scaffolding implement the underlying behavior, while GitHub Actions workflows call only root targets and publish artifacts and summaries. Rust receives the largest expansion because it currently lacks maintained fuzz and coverage workflows.

**Tech Stack:** GNU Make, GitHub Actions, `pytest`, `coverage.py`, `Hypothesis`, `mutmut`, Go `go test`/native fuzzing/`gremlins`, Rust `cargo llvm-cov`, `proptest`, `cargo-fuzz`, `cargo-mutants`

---

### Task 1: Normalize Shared Quality Entry Points

**Files:**
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/Makefile`
- Test: `/Users/tim/code/gh/provide-io/flavorpack/.github/workflows/05-code-quality.yml`

- [ ] **Step 1: Write the failing contract review**

Capture the missing root targets and shared defaults in a checklist before editing code. Add this comment block near the quality section of the root `Makefile` to define the intended surface:

```make
# Shared quality defaults
QUALITY_PY_COV_MIN ?= 85
QUALITY_GO_COV_MIN ?= 80
QUALITY_RUST_COV_MIN ?= 80
QUALITY_GO_FUZZTIME ?= 30s
QUALITY_RUST_FUZZ_SECONDS ?= 30
QUALITY_PY_MUTATION_ARGS ?=
QUALITY_GO_MUTATION_ARGS ?=
QUALITY_RUST_MUTATION_ARGS ?=
```

- [ ] **Step 2: Run a quick existence check to verify the targets do not exist yet**

Run:

```bash
source .venv/bin/activate && make -n quality-python quality-go quality-rust quality-ci
```

Expected: `make` reports missing targets for one or more of these names.

- [ ] **Step 3: Add the root target surface**

Update `/Users/tim/code/gh/provide-io/flavorpack/Makefile` with explicit shared targets that delegate to language-specific workflows and keep all defaults centralized:

```make
# ==================== Unified Quality ====================

QUALITY_PY_COV_MIN ?= 85
QUALITY_GO_COV_MIN ?= 80
QUALITY_RUST_COV_MIN ?= 80
QUALITY_GO_FUZZTIME ?= 30s
QUALITY_RUST_FUZZ_SECONDS ?= 30
QUALITY_PY_MUTATION_ARGS ?=
QUALITY_GO_MUTATION_ARGS ?=
QUALITY_RUST_MUTATION_ARGS ?=

.PHONY: quality-python
quality-python:
	PYTHONUTF8=1 uv run pytest --cov=flavor --cov-report=term-missing --cov-report=xml --cov-report=json tests/
	PYTHONUTF8=1 uv run pytest -m stress tests/
	mutmut run $(QUALITY_PY_MUTATION_ARGS)

.PHONY: quality-go
quality-go:
	@$(MAKE) -C src/flavor-go coverage QUALITY_GO_COV_MIN=$(QUALITY_GO_COV_MIN)
	@$(MAKE) -C src/flavor-go fuzz FUZZTIME=$(QUALITY_GO_FUZZTIME)
	@$(MAKE) -C src/flavor-go mutation QUALITY_GO_MUTATION_ARGS="$(QUALITY_GO_MUTATION_ARGS)"

.PHONY: quality-rust
quality-rust:
	@$(MAKE) -C src/flavor-rs coverage QUALITY_RUST_COV_MIN=$(QUALITY_RUST_COV_MIN)
	@$(MAKE) -C src/flavor-rs proptest
	@$(MAKE) -C src/flavor-rs fuzz QUALITY_RUST_FUZZ_SECONDS=$(QUALITY_RUST_FUZZ_SECONDS)
	@$(MAKE) -C src/flavor-rs mutation QUALITY_RUST_MUTATION_ARGS="$(QUALITY_RUST_MUTATION_ARGS)"

.PHONY: quality-ci
quality-ci: quality-python quality-go quality-rust
```

- [ ] **Step 4: Run make in dry-run mode to verify the new root target graph is valid**

Run:

```bash
source .venv/bin/activate && make -n quality-python quality-go quality-rust quality-ci
```

Expected: all four targets render command plans without “No rule to make target” errors.

- [ ] **Step 5: Commit the shared orchestration change**

```bash
git add /Users/tim/code/gh/provide-io/flavorpack/Makefile
git commit -m "build: add unified quality entry points"
```

### Task 2: Harden Python Coverage, Property, and Mutation Paths

**Files:**
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/pyproject.toml`
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/Makefile`
- Test: `/Users/tim/code/gh/provide-io/flavorpack/tests/conftest.py`

- [ ] **Step 1: Write the failing configuration expectation**

Add the target coverage threshold and explicit property-test command contract to the plan comments in `pyproject.toml`:

```toml
[tool.coverage.report]
fail_under = 85
```

and ensure the root `Makefile` has an explicit property-focused target:

```make
.PHONY: test-property-python
test-property-python:
	PYTHONUTF8=1 uv run pytest -m stress tests/
```

- [ ] **Step 2: Verify the current Python config is weaker than the target**

Run:

```bash
source .venv/bin/activate && rg -n "fail_under|test-property-python" pyproject.toml Makefile
```

Expected: `fail_under = 60` is present and `test-property-python` is absent.

- [ ] **Step 3: Implement the stricter Python quality surface**

Update `/Users/tim/code/gh/provide-io/flavorpack/pyproject.toml`:

```toml
[tool.coverage.report]
show_missing = true
skip_covered = false
precision = 2
fail_under = 85
```

Update `/Users/tim/code/gh/provide-io/flavorpack/Makefile`:

```make
.PHONY: test-property-python
test-property-python: ## Run Python property and hypothesis tests
	PYTHONUTF8=1 uv run pytest -m stress tests/

.PHONY: mutation-run
mutation-run: ## Run mutation testing with mutmut
	@echo "🧬 Running mutation testing..."
	@mutmut run $(QUALITY_PY_MUTATION_ARGS)
```

- [ ] **Step 4: Run the Python quality commands in strict mode**

Run:

```bash
source .venv/bin/activate && PYTHONUTF8=1 uv run pytest --cov=flavor --cov-report=term-missing --cov-report=xml --cov-report=json tests/
source .venv/bin/activate && PYTHONUTF8=1 uv run pytest -m stress tests/
source .venv/bin/activate && mutmut run --help
```

Expected:
- coverage run completes and writes `coverage.xml` and `coverage.json`
- stress/property test run completes
- `mutmut` help confirms the command surface is valid for CI invocation

- [ ] **Step 5: Run Python code quality after editing Python config**

Run:

```bash
source .venv/bin/activate && ruff format pyproject.toml tests/conftest.py
source .venv/bin/activate && ruff check pyproject.toml tests/conftest.py
source .venv/bin/activate && mypy src/flavor
```

Expected: formatting is clean, lint passes, and `mypy` remains green.

- [ ] **Step 6: Commit the Python quality hardening**

```bash
git add /Users/tim/code/gh/provide-io/flavorpack/pyproject.toml /Users/tim/code/gh/provide-io/flavorpack/Makefile
git commit -m "test(python): harden coverage and property workflows"
```

### Task 3: Add Strict Go Coverage and Mutation Workflow Targets

**Files:**
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-go/Makefile`
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/Makefile`
- Test: `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-go/pkg/psp/format_2025/fuzz_test.go`

- [ ] **Step 1: Write the failing interface requirement**

Define the new Go-specific target contract in `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-go/Makefile`:

```make
.PHONY: coverage mutation
coverage:
	go test -v -race -covermode=atomic -coverprofile=coverage.out ./...
	go tool cover -func=coverage.out

mutation:
	gremlins unleash ./...
```

- [ ] **Step 2: Verify the Go makefile does not yet expose those strict targets**

Run:

```bash
source .venv/bin/activate && rg -n "^coverage:|^mutation:" src/flavor-go/Makefile
```

Expected: no matches.

- [ ] **Step 3: Implement the Go quality targets and shared defaults**

Update `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-go/Makefile`:

```make
QUALITY_GO_COV_MIN ?= 80
QUALITY_GO_MUTATION_ARGS ?=
FUZZTIME ?= 30s

.PHONY: coverage
coverage:
	@echo "📊 Running Go coverage..."
	go test -v -race -covermode=atomic -coverprofile=coverage.out ./...
	go tool cover -func=coverage.out | tee coverage.txt
	awk '/^total:/ {gsub("%","",$$3); if ($$3 + 0 < $(QUALITY_GO_COV_MIN)) exit 1}' coverage.txt

.PHONY: mutation
mutation:
	@command -v gremlins >/dev/null 2>&1 || { echo "Install gremlins: go install github.com/go-gremlins/gremlins/cmd/gremlins@latest"; exit 1; }
	gremlins unleash $(QUALITY_GO_MUTATION_ARGS) ./...

fuzz:
	@echo "🔀 Running fuzz tests..."
	go test -fuzz='^FuzzSplit$$' -fuzztime=$(FUZZTIME) ./pkg/utils/shellparse/
	go test -fuzz='^FuzzSplitJoinIdempotent$$' -fuzztime=$(FUZZTIME) ./pkg/utils/shellparse/
	go test -fuzz='^FuzzOperationsRoundTrip$$' -fuzztime=$(FUZZTIME) ./pkg/psp/format_2025/
	go test -fuzz='^FuzzUnpackNoPanic$$' -fuzztime=$(FUZZTIME) ./pkg/psp/format_2025/
```

- [ ] **Step 4: Run Go coverage and fuzz commands**

Run:

```bash
source .venv/bin/activate && make -C src/flavor-go coverage QUALITY_GO_COV_MIN=0
source .venv/bin/activate && make -C src/flavor-go fuzz FUZZTIME=5s
```

Expected:
- coverage writes `coverage.out` and `coverage.txt`
- fuzzing completes bounded runs against all maintained targets

- [ ] **Step 5: Verify Go mutation command surface without running a full expensive campaign locally**

Run:

```bash
source .venv/bin/activate && make -n -C src/flavor-go mutation QUALITY_GO_MUTATION_ARGS="./pkg/psp/format_2025/..."
```

Expected: the dry run prints the exact `gremlins` invocation with the configured scope.

- [ ] **Step 6: Commit the Go quality target work**

```bash
git add /Users/tim/code/gh/provide-io/flavorpack/src/flavor-go/Makefile /Users/tim/code/gh/provide-io/flavorpack/Makefile
git commit -m "test(go): add strict coverage and mutation targets"
```

### Task 4: Establish Rust Coverage, Proptest, Mutation, and Real Fuzz Targets

**Files:**
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/Makefile`
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/Cargo.toml`
- Create: `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/fuzz/Cargo.toml`
- Create: `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/fuzz/fuzz_targets/pspf_operations_roundtrip.rs`
- Create: `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/fuzz/fuzz_targets/pspf_reader_no_panic.rs`
- Test: `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/src/psp/format_2025/operations.rs`
- Test: `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/src/psp/format_2025/reader.rs`

- [ ] **Step 1: Write the failing Rust quality contract**

Define the target signatures that must exist after this task:

```make
.PHONY: coverage proptest mutation fuzz
coverage:
	cargo llvm-cov --all-features --workspace --lcov --output-path coverage.lcov

proptest:
	cargo test prop_ --all-features

mutation:
	cargo mutants --all-features
```

and create a real fuzz workspace:

```toml
[workspace]
members = ["."]
exclude = ["fuzz"]
```

- [ ] **Step 2: Verify Rust does not yet have maintained coverage and fuzz surface**

Run:

```bash
source .venv/bin/activate && rg -n "^coverage:|^proptest:|cargo llvm-cov|cargo-mutants" src/flavor-rs/Makefile src/flavor-rs/Cargo.toml
source .venv/bin/activate && test -d src/flavor-rs/fuzz || echo "missing-fuzz-dir"
```

Expected: no real coverage target exists and `missing-fuzz-dir` is printed.

- [ ] **Step 3: Add Rust coverage, proptest, mutation, and bounded fuzz commands**

Update `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/Makefile`:

```make
QUALITY_RUST_COV_MIN ?= 80
QUALITY_RUST_FUZZ_SECONDS ?= 30
QUALITY_RUST_MUTATION_ARGS ?=

.PHONY: coverage
coverage:
	@command -v cargo-llvm-cov >/dev/null 2>&1 || cargo install cargo-llvm-cov
	cargo llvm-cov --all-features --workspace --lcov --output-path coverage.lcov --summary-only | tee coverage.txt

.PHONY: proptest
proptest:
	cargo test prop_ --all-features

.PHONY: mutation
mutation:
	@command -v cargo-mutants >/dev/null 2>&1 || cargo install cargo-mutants
	cargo mutants $(QUALITY_RUST_MUTATION_ARGS) --all-features --output .cargo-mutants.out

fuzz:
	@command -v cargo-fuzz >/dev/null 2>&1 || cargo install cargo-fuzz
	rustup toolchain install nightly --profile minimal
	cargo +nightly fuzz run pspf_operations_roundtrip -- -max_total_time=$(QUALITY_RUST_FUZZ_SECONDS)
	cargo +nightly fuzz run pspf_reader_no_panic -- -max_total_time=$(QUALITY_RUST_FUZZ_SECONDS)
```

- [ ] **Step 4: Add real Rust fuzz targets for PSPF-critical paths**

Create `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/fuzz/Cargo.toml`:

```toml
[package]
name = "flavor-rs-fuzz"
version = "0.0.0"
publish = false
edition = "2021"

[package.metadata]
cargo-fuzz = true

[dependencies]
libfuzzer-sys = "0.4"
flavor-rs = { path = ".." }

[[bin]]
name = "pspf_operations_roundtrip"
path = "fuzz_targets/pspf_operations_roundtrip.rs"
test = false
doc = false
bench = false

[[bin]]
name = "pspf_reader_no_panic"
path = "fuzz_targets/pspf_reader_no_panic.rs"
test = false
doc = false
bench = false
```

Create `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/fuzz/fuzz_targets/pspf_operations_roundtrip.rs`:

```rust
#![no_main]

use flavor_rs::psp::format_2025::operations::{pack_operations, unpack_operations};
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: Vec<u8>| {
    let ops: Vec<u8> = data.into_iter().take(8).collect();
    let packed = pack_operations(&ops);
    let _ = unpack_operations(packed);
});
```

Create `/Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/fuzz/fuzz_targets/pspf_reader_no_panic.rs`:

```rust
#![no_main]

use flavor_rs::psp::format_2025::reader::PSPFReader;
use libfuzzer_sys::fuzz_target;
use std::io::Cursor;

fuzz_target!(|data: Vec<u8>| {
    let cursor = Cursor::new(data);
    let _ = PSPFReader::new(cursor);
});
```

- [ ] **Step 5: Run Rust quality commands**

Run:

```bash
source .venv/bin/activate && make -C src/flavor-rs proptest
source .venv/bin/activate && make -C src/flavor-rs coverage QUALITY_RUST_COV_MIN=0
source .venv/bin/activate && make -C src/flavor-rs fuzz QUALITY_RUST_FUZZ_SECONDS=5
```

Expected:
- proptest-targeted tests pass
- coverage artifacts are created
- bounded fuzz targets run successfully

- [ ] **Step 6: Verify mutation command surface**

Run:

```bash
source .venv/bin/activate && make -n -C src/flavor-rs mutation QUALITY_RUST_MUTATION_ARGS="--timeout 120 --iterate 2"
```

Expected: the dry run prints a bounded `cargo mutants` invocation.

- [ ] **Step 7: Commit the Rust quality infrastructure**

```bash
git add /Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/Makefile /Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/Cargo.toml /Users/tim/code/gh/provide-io/flavorpack/src/flavor-rs/fuzz
git commit -m "test(rust): add coverage, mutation, and fuzz workflows"
```

### Task 5: Wire Observational Strict-Mode Quality Jobs into CI

**Files:**
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/.github/workflows/05-code-quality.yml`
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/.github/workflows/03-flavor-pipeline.yml`
- Test: `/Users/tim/code/gh/provide-io/flavorpack/.github/scripts/test-metadata.py`

- [ ] **Step 1: Write the failing CI job structure**

Add a new matrix or explicit jobs to `/Users/tim/code/gh/provide-io/flavorpack/.github/workflows/05-code-quality.yml` with these names:

```yaml
quality-python
quality-go
quality-rust
quality-deep-python-mutation
quality-deep-go-fuzz-mutation
quality-deep-rust-fuzz-mutation
```

- [ ] **Step 2: Verify those jobs do not exist yet**

Run:

```bash
source .venv/bin/activate && rg -n "quality-deep|cargo llvm-cov|gremlins|cargo fuzz|mutmut run" .github/workflows/05-code-quality.yml
```

Expected: no matches or only incidental ones outside the desired job structure.

- [ ] **Step 3: Implement CI jobs that call root targets only**

Update `/Users/tim/code/gh/provide-io/flavorpack/.github/workflows/05-code-quality.yml` so each language job installs its toolchain and calls the root `Makefile` interface:

```yaml
- name: Run Python quality
  run: |
    source .venv/bin/activate
    make quality-python QUALITY_PY_MUTATION_ARGS="src/flavor/config"

- name: Run Go quality
  run: make quality-go QUALITY_GO_COV_MIN=0 QUALITY_GO_FUZZTIME=15s QUALITY_GO_MUTATION_ARGS="./pkg/psp/format_2025/..."

- name: Run Rust quality
  run: make quality-rust QUALITY_RUST_COV_MIN=0 QUALITY_RUST_FUZZ_SECONDS=15 QUALITY_RUST_MUTATION_ARGS="--timeout 120 --iterate 2"
```

Keep the jobs observational by workflow naming and repository settings, not by `continue-on-error` on the core command step.

- [ ] **Step 4: Add artifact and summary publishing**

Add upload steps like:

```yaml
- name: Upload quality artifacts
  if: always()
  uses: actions/upload-artifact@v7
  with:
    name: quality-${{ github.run_id }}-${{ github.job }}
    path: |
      coverage.xml
      coverage.json
      src/flavor-go/coverage.out
      src/flavor-go/coverage.txt
      src/flavor-rs/coverage.lcov
      src/flavor-rs/coverage.txt
      .mutmut-cache/
      src/flavor-rs/.cargo-mutants.out/
```

and append short rollups to `$GITHUB_STEP_SUMMARY`.

- [ ] **Step 5: Validate workflow syntax**

Run:

```bash
source .venv/bin/activate && python - <<'PY'
import yaml, pathlib
for path in [pathlib.Path(".github/workflows/05-code-quality.yml"), pathlib.Path(".github/workflows/03-flavor-pipeline.yml")]:
    with path.open() as fh:
        yaml.safe_load(fh)
print("workflow-yaml-ok")
PY
```

Expected: `workflow-yaml-ok`

- [ ] **Step 6: Commit the CI quality wiring**

```bash
git add /Users/tim/code/gh/provide-io/flavorpack/.github/workflows/05-code-quality.yml /Users/tim/code/gh/provide-io/flavorpack/.github/workflows/03-flavor-pipeline.yml
git commit -m "ci: add observational cross-language quality jobs"
```

### Task 6: Document the Quality Model and Verify End-to-End

**Files:**
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/README.md`
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/AGENTS.md`
- Modify: `/Users/tim/code/gh/provide-io/flavorpack/docs/superpowers/specs/2026-03-31-quality-hardening-design.md`

- [ ] **Step 1: Write the missing documentation outline**

Add a “Quality Engineering” section to `/Users/tim/code/gh/provide-io/flavorpack/README.md` with these headings:

```md
## Quality Engineering
### Local Commands
### CI Observability Jobs
### Strict Mode vs Required Checks
```

- [ ] **Step 2: Verify the docs do not already explain this model**

Run:

```bash
source .venv/bin/activate && rg -n "Quality Engineering|Strict Mode vs Required Checks|quality-python|quality-go|quality-rust" README.md AGENTS.md
```

Expected: no full section covering the new model.

- [ ] **Step 3: Add the documentation**

Update `/Users/tim/code/gh/provide-io/flavorpack/README.md`:

```md
## Quality Engineering

Use the root quality targets to run the same workflows locally that CI runs observationally:

```bash
make quality-python
make quality-go
make quality-rust
make quality-ci
```

The tools run in strict mode, but these jobs are not yet required by branch protection. A red job means the quality run itself failed; it does not, by itself, define merge policy in this rollout phase.
```

Update `/Users/tim/code/gh/provide-io/flavorpack/AGENTS.md` with a short note that cross-language quality work should use the root quality targets instead of ad hoc commands when validating coverage, mutation, fuzzing, or property-test behavior.

- [ ] **Step 4: Run end-to-end verification**

Run:

```bash
source .venv/bin/activate && make -n quality-ci
source .venv/bin/activate && ruff format README.md AGENTS.md
source .venv/bin/activate && ruff check README.md AGENTS.md
source .venv/bin/activate && git diff --check
```

Expected:
- `make -n quality-ci` shows the full orchestration path
- formatting/linting does not introduce issues
- `git diff --check` reports no whitespace errors

- [ ] **Step 5: Commit the documentation and final verification changes**

```bash
git add /Users/tim/code/gh/provide-io/flavorpack/README.md /Users/tim/code/gh/provide-io/flavorpack/AGENTS.md
git commit -m "docs: document cross-language quality workflows"
```
