# Test Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the cross-language test taxonomy so developers and CI can select tests by intent across Python, Go, and Rust.

**Architecture:** Keep one shared taxonomy at the repo interface while preserving language-native mechanics underneath it. Python uses strict pytest marker registration and reclassification of high-signal tests; Go and Rust remain selected through repo-level `make` targets and CI intent groupings.

**Tech Stack:** pytest markers, root `Makefile`, GitHub Actions workflow YAML, existing quality/fuzz/mutation tooling, repo contract tests.

---

### Task 1: Register Python Taxonomy Markers

**Files:**
- Modify: `pyproject.toml`

- [ ] Add the shared taxonomy markers and descriptions to `tool.pytest.ini_options.markers`.
- [ ] Keep existing useful markers such as `requires_helpers`, `taster`, `packaging`, `memray`, and `mmap`.
- [ ] Preserve `--strict-markers` behavior.

### Task 2: Reclassify High-Signal Python Tests

**Files:**
- Modify: `tests/parity/*.py`
- Modify: `tests/security/*.py`
- Modify: `tests/format_2025/test_hypothesis_invariants.py`
- Modify: `tests/format_2025/test_launcher_security_parity.py`

- [ ] Mark parity tests as `cross_language` and `ci`.
- [ ] Mark hostile-boundary and trust tests as `security` and `adversarial` where applicable.
- [ ] Mark Hypothesis/invariant suites as `property`.
- [ ] Apply `fast` or `slow` where obvious from current behavior.

### Task 3: Add Repo Contract Coverage for Taxonomy

**Files:**
- Modify or create: `tests/test_quality_observability.py`
- Create if needed: `tests/test_test_taxonomy.py`

- [ ] Add assertions that the shared markers are registered.
- [ ] Add assertions that the root `Makefile` exposes intent-oriented test targets.
- [ ] Add assertions that the quality workflow references the intent-oriented surface or summaries.

### Task 4: Add Root Make Intent Targets

**Files:**
- Modify: `Makefile`

- [ ] Add stable targets for `test-unit`, `test-integration`, `test-cross-language`, `test-security`, `test-adversarial`, `test-property`, `test-fuzz`, `test-mutation`, `test-smoke`, `test-fast`, and `test-slow`.
- [ ] Map Python selection through pytest markers.
- [ ] Map Go and Rust intent selection through the existing language-native coverage/fuzz/mutation surfaces without inventing marker systems for them.
- [ ] Avoid breaking existing `quality-*` targets.

### Task 5: Align CI and Docs With Intent Taxonomy

**Files:**
- Modify: `.github/workflows/05-code-quality.yml`
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] Update workflow summaries/naming so intent categories are visible.
- [ ] Document the shared taxonomy, `security` vs `adversarial`, and the root commands for local use.
- [ ] Keep CI non-blocking at the branch-protection level while making the intent model obvious.

### Task 6: Verify the Taxonomy End to End

**Files:**
- No additional file ownership

- [ ] Run focused Python taxonomy tests.
- [ ] Run `ruff` and `mypy` for touched Python files.
- [ ] Run `make -n` or targeted `make` commands for the new root targets.
- [ ] Validate the workflow YAML.
- [ ] Run a fresh repo-level Python suite if taxonomy changes affect selection behavior.
