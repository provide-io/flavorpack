# Cross-Language Quality Hardening Design

## Goal

Establish a consistent, repo-wide quality engineering framework for Python, Go, and Rust that includes coverage, mutation testing, fuzzing, and parameter/property testing, with all tooling wired into CI and operated in strict mode, but without enabling branch-protection enforcement yet.

## Context

FlavorPack already has uneven quality infrastructure across languages:

- Python has mature coverage, mutation, and property-testing support.
- Go has real fuzzing support and basic coverage generation, but mutation and coverage policy are not normalized at the repo level.
- Rust has property testing, but coverage and fuzzing are not yet established as maintained, first-class workflows.

The project needs a unified quality model that is visible on every PR, reproducible locally, and designed so future enforcement is a configuration step rather than a redesign.

## Non-Goals

- Do not make new quality jobs required for merge in this phase.
- Do not add backward-compatibility shims for old quality flows.
- Do not introduce a custom meta-runner if existing language-native tools can satisfy the need.
- Do not add ad hoc PSPF test harnesses outside pretaster or taster.

## Requirements

### Functional Requirements

1. The root `Makefile` must expose canonical developer and CI entry points for:
   - coverage
   - mutation testing
   - fuzzing
   - parameter/property testing
2. Each language must have an implemented path, not placeholder support, for the applicable domains:
   - Python: coverage, mutation, property/parameter testing
   - Go: coverage, mutation, fuzzing, parameterized/table-driven tests
   - Rust: coverage, mutation, fuzzing, property testing
3. CI must run all of these domains and publish artifacts and summaries where the tool supports them.
4. Tool invocations must run in strict mode where the tool has a meaningful strict mode.
5. CI jobs must be observational in this phase:
   - jobs should still fail if the invocation is invalid, the tool crashes, or the configured run encounters actual failing tests
   - branch protection should not yet require these jobs
6. Repo documentation must explain:
   - what each target does
   - which jobs are observational versus required
   - how to run the same checks locally

### Quality Requirements

1. Local and CI entry points must match; CI should call root-level commands rather than duplicating language-specific shell logic inline.
2. Quality commands must be deterministic enough for CI:
   - explicit tool installation or bootstrap
   - explicit run scopes and time bounds for expensive jobs
3. New defaults must live in shared config or constants, not as inline magic values inside scripts.
4. Rust quality commands must remain compatible with warnings-as-errors expectations.

## Architecture

### Control Surface

The root `Makefile` is the canonical interface for both developers and CI. It should provide stable top-level targets that delegate into language-specific tooling only where necessary.

This keeps three things aligned:

- local usage
- CI usage
- documentation

### Language Ownership

#### Python

Python will continue using the existing `pytest`, coverage, Hypothesis, and `mutmut` stack. The design will tighten and normalize that stack rather than replace it.

Planned state:

- coverage targets produce terminal, XML, and JSON outputs suitable for CI ingestion
- property testing is represented explicitly rather than as an incidental side effect of the whole suite
- mutation testing remains `mutmut`, but invoked through stable root targets and CI jobs

#### Go

Go will use native Go tooling where possible:

- `go test` with race and coverage for coverage reporting
- maintained native fuzz targets for parser and operation-chain risk areas
- `gremlins` for mutation testing

Go parameterization will remain idiomatic table-driven testing. No artificial parameter-test framework should be added.

#### Rust

Rust requires the most expansion in this phase.

Planned state:

- coverage uses `cargo llvm-cov` with structured output
- property testing remains `proptest`, with an explicit CI-visible entry point
- fuzzing uses `cargo-fuzz` with maintained targets under `src/flavor-rs/fuzz/`
- mutation testing uses `cargo-mutants`

Rust placeholder fuzz support in the current `Makefile` is not acceptable as the end state.

## CI Model

### Required vs Observational

The project already has required code quality gates. This design adds a parallel quality-observability layer for deeper signals.

The CI jobs introduced by this work should:

- run on pull requests and relevant pushes
- fail normally if the command is misconfigured or broken
- publish results for developer review
- remain non-required in branch protection during this phase

This means "strict mode" applies to tool behavior, not to merge policy.

### Job Structure

The recommended CI split is:

1. Fast quality jobs
   - Python coverage + property tests
   - Go coverage
   - Rust coverage + proptest
2. Deep quality jobs
   - Python mutation
   - Go mutation
   - Rust mutation
   - Go fuzz
   - Rust fuzz

This preserves fast feedback while still exercising the deeper toolchain on every PR or on a defined PR/push schedule.

### Artifact Strategy

Each job should produce machine-readable artifacts where available:

- Python coverage XML/JSON
- Go coverage profile and text summary
- Rust coverage report artifacts
- mutation result outputs or summaries
- fuzzing logs and crash artifacts when generated

GitHub job summaries should provide high-signal rollups so developers do not need to inspect raw logs first.

## Tooling Decisions

### Python

Use the existing configured tools:

- `pytest`
- `coverage.py`
- `Hypothesis`
- `mutmut`

Changes to make:

- add explicit root targets for property-focused runs
- ensure coverage jobs emit CI-consumable artifacts consistently
- review and raise coverage configuration toward a credible threshold, while keeping the resulting job observational in branch policy

### Go

Use:

- `go test -race -coverprofile=...`
- native Go fuzzing
- `gremlins`

Changes to make:

- add root-level coverage targets that expose artifacts and summaries
- make fuzz targets explicit and bounded
- make mutation invocation reproducible in CI, including installation/bootstrap and scoped runtime behavior

### Rust

Use:

- `cargo llvm-cov`
- `proptest` via targeted `cargo test` runs
- `cargo-fuzz`
- `cargo-mutants`

Changes to make:

- add real fuzz target scaffolding for PSPF-critical code paths
- add root-level and language-level coverage commands using `cargo llvm-cov`
- make mutation and fuzz invocations bounded and CI-friendly

## Scope of Test Content

This design is not just CI plumbing. Some maintained test surface must be added where the framework is currently incomplete.

Expected additions:

- at least one Rust fuzz target for PSPF parsing or operation processing
- any small supporting tests needed to make new strict quality commands meaningful and stable
- no standalone PSPF ad hoc test harnesses; PSPF execution validation continues to use pretaster or taster

## Error Handling and Operational Policy

### CI Failure Semantics

Jobs should fail when:

- the tool cannot be installed or invoked
- the test run fails
- the fuzz or mutation command is configured incorrectly
- strict lint/compile prerequisites for the toolchain fail

Jobs should not be marked as required merge gates during this phase. That distinction lives in repository settings and workflow naming/documentation, not in weakened command behavior.

### Time Bounding

Mutation and fuzzing must be bounded for CI practicality.

The implementation should define shared defaults for:

- Go fuzz time budgets
- Rust fuzz time budgets
- Python mutation scope or runtime strategy
- Go mutation scope or runtime strategy
- Rust mutation scope or runtime strategy

These defaults must live in shared config locations such as `Makefile` variables or dedicated config files, not as inline shell literals scattered across workflows.

## Rollout Strategy

### Phase 1

- normalize root and per-language commands
- add missing Rust coverage and fuzzing support
- add CI jobs and artifacts
- document the model

### Phase 2

- tune runtimes and scopes based on CI observations
- improve summaries and triage ergonomics
- decide which jobs should become required

## Risks

### CI Runtime Growth

Adding mutation and fuzz jobs across three languages will increase workflow duration.

Mitigation:

- separate fast and deep jobs
- bound execution windows
- scope mutation runs carefully at first

### Toolchain Friction

Rust coverage and fuzzing require more setup than the current repo provides.

Mitigation:

- bootstrap tools explicitly in CI
- make local commands install or clearly fail with actionable guidance

### False Confidence

Developers may confuse "strict tooling in CI" with "fully enforced quality gate."

Mitigation:

- name jobs clearly
- document observational status
- summarize results prominently

## Acceptance Criteria

This design is complete when:

1. The root `Makefile` exposes stable quality targets for all requested domains.
2. Python, Go, and Rust each have documented and runnable quality workflows appropriate to their ecosystems.
3. Rust has real maintained fuzz targets and coverage execution.
4. CI runs all quality domains and publishes artifacts/summaries.
5. The repo documents how to run and interpret these checks.
6. The jobs are wired into CI but not yet required by branch protection.
