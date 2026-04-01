# Cross-Language Test Taxonomy Design

## Goal

Define a single repo-wide test taxonomy for FlavorPack that improves developer experience, makes security intent explicit, and cleanly supports parameterized testing, fuzzing, mutation testing, adversarial security testing, and cross-language parity testing across Python, Go, and Rust.

## Context

FlavorPack now has a broader quality surface, but the repo still lacks a stable way to classify tests by intent. Developers can run language-native tests, but the selection model is inconsistent:

- Python uses pytest markers in some areas, but the taxonomy is incomplete.
- Go relies on file/package naming and command selection, but there is no shared intent vocabulary.
- Rust has native test, proptest, fuzz, and mutation workflows, but those categories are not yet presented through a common repo model.

This is a DX problem and a security-hardening problem. The repository needs a test model that answers:

- what behavior is being tested
- whether the test is validating normal operation or deliberately trying to break trust boundaries
- how expensive the test is to run
- how to run the same category locally and in CI regardless of implementation language

## Non-Goals

- Do not force Go or Rust to emulate pytest-style markers.
- Do not replace language-native tooling with a custom test runner.
- Do not create a parallel taxonomy for each language with different meanings for similar words.
- Do not classify tests primarily by file location alone.
- Do not hide adversarial/security testing inside generic integration buckets.

## Design Principles

1. One shared vocabulary for test intent.
2. Language-native execution under that shared vocabulary.
3. Security and adversarial behavior are first-class categories.
4. Repo-level commands select by intent, not by language-specific implementation details.
5. Test location follows language norms for unit/module tests and repo norms for cross-language/end-to-end tests.
6. Cost classification and intent classification are separate concerns.

## Shared Taxonomy

### Primary Intent Categories

These categories are the canonical repo-wide meanings. Every test surface in Python, Go, and Rust must map into them.

- `unit`
  - Tests a small unit in isolation, usually within one module/package.
- `integration`
  - Tests interaction between multiple components in one implementation or runtime path.
- `cross_language`
  - Tests interoperability or parity across Python, Go, and Rust implementations.
- `security`
  - Tests trust decisions, verification, integrity, policy enforcement, permissions, provenance, and other intended security behavior.
- `adversarial`
  - Tests malicious, malformed, boundary-violating, or hostile inputs intended to break assumptions or cross trust boundaries.
- `property`
  - Tests invariants across many inputs, usually parameterized or generator-based.
- `fuzz`
  - Uses coverage-guided or randomized malformed input discovery to find crashes, panics, undefined behavior, parser confusion, or extraction failures.
- `mutation`
  - Measures test-suite strength by checking whether intentional code mutations are killed.
- `smoke`
  - Minimal high-signal execution used for quick confidence checks.

### Secondary Cost/Execution Categories

These do not replace the primary intent categories. They are orthogonal selectors.

- `fast`
  - Expected to run in normal local iteration loops.
- `slow`
  - Expensive enough to exclude from default fast feedback.
- `ci`
  - Safe and intended for automated CI runs.
- `manual`
  - Requires special environment, longer runtime, or analyst review; not part of the default CI path.

### Why Intent and Cost Must Be Separate

A test can be both `adversarial` and `fast`, or both `security` and `slow`. If the taxonomy collapses those concepts into one label, developers lose the ability to ask focused questions such as:

- run fast adversarial tests
- run all security tests except slow ones
- run property tests only
- run all cross-language tests in CI

## Security-Focused Classification Rules

### `security` vs `adversarial`

The repo must distinguish between proving intended security behavior and actively attempting to violate boundaries.

Use `security` when the test verifies correct policy or control behavior:

- trusted-key enforcement
- signature verification behavior
- permission application
- operator policy merge/enforcement
- checksum and integrity validation
- launch-mode restrictions
- provenance or attestation handling

Use `adversarial` when the test intentionally tries to break the system:

- path traversal
- tarbomb and symlink escape
- malformed slot descriptors
- corrupted index/trailer structures
- malformed metadata intended to confuse validation
- oversized or truncated payloads
- boundary crossing between workenv and host paths
- environment injection attempts
- command substitution abuse
- malicious launcher/bundle mismatches

Many tests will be both `security` and `adversarial`. That is acceptable and expected.

## Language Mapping

### Python

Python should use pytest markers as the canonical selection mechanism.

Required markers:

- `@pytest.mark.unit`
- `@pytest.mark.integration`
- `@pytest.mark.cross_language`
- `@pytest.mark.security`
- `@pytest.mark.adversarial`
- `@pytest.mark.property`
- `@pytest.mark.fuzz`
- `@pytest.mark.smoke`
- `@pytest.mark.fast`
- `@pytest.mark.slow`
- `@pytest.mark.ci`

Rules:

- Hypothesis tests must always include `property`.
- Tests that intentionally violate PSPF or workenv boundaries must include `adversarial`.
- Pretaster and taster tests that validate builder/launcher interoperability must include `cross_language`.
- Security parity tests should include both `security` and `cross_language` when they compare implementations.

### Go

Go should remain idiomatic. It should not invent a marker framework. Selection should come from a combination of:

- adjacent `_test.go` files for unit/module tests
- targeted package paths
- test naming conventions for intent
- repo-level make targets that group packages and regex selections
- fuzz targets using native Go fuzz support
- mutation via `gremlins`

Naming convention prefixes for discoverability:

- `TestUnit...`
- `TestIntegration...`
- `TestSecurity...`
- `TestAdversarial...`
- `TestProperty...` for generator/table-driven invariant tests
- `Fuzz...` for native fuzz tests

Go intent is enforced at the command layer, not by custom in-language metadata.

### Rust

Rust should use idiomatic unit tests, integration tests, `proptest`, `cargo-fuzz`, and `cargo-mutants`.

Conventions:

- in-module unit tests for `unit`
- crate integration tests for public-API `integration`
- `proptest` suites represent `property`
- `cargo-fuzz` targets represent `fuzz`
- mutation remains external via `cargo-mutants`
- test names should include intent where useful, especially `security` and `adversarial`

Rust intent is expressed through module placement, target selection, and repo-level commands rather than a fake marker system.

## Test Placement Strategy

### Adjacent by Default

Default placement:

- Go unit/module tests next to the code in `*_test.go`
- Rust unit tests in-file or adjacent module tests
- Python unit/module tests in existing repo test layout consistent with current project patterns

Adjacent tests are the default because they:

- improve local comprehension
- keep unit coverage close to implementation
- reduce drift between code and tests
- match Go and Rust norms

### Centralized Only for Cross-Cutting Flows

Use centralized test trees for:

- cross-language parity tests
- end-to-end builder/launcher validation
- pretaster/taster execution flows
- broad security campaigns spanning multiple implementations

PSPF package-execution validation should continue to use `pretaster` or `taster`, not ad hoc standalone harnesses.

## Repo-Level Developer Experience

### Canonical Intent Commands

The root `Makefile` should expose stable test-intent commands:

- `make test-unit`
- `make test-integration`
- `make test-cross-language`
- `make test-security`
- `make test-adversarial`
- `make test-property`
- `make test-fuzz`
- `make test-mutation`
- `make test-smoke`

And cost-filtered variants where useful:

- `make test-fast`
- `make test-slow`
- `make test-security-fast`
- `make test-adversarial-fast`

Developers should not need to know whether a category runs pytest markers, Go package selections, Rust test filters, proptest, cargo-fuzz, or mutation tooling. The root command should own that mapping.

### CI Reporting Model

CI should report by intent category, not only by language:

- Unit
- Integration
- Cross-Language
- Security
- Adversarial
- Property
- Fuzz
- Mutation

Each job summary should state:

- what intent category ran
- which language implementations participated
- whether the run is fast or deep
- where artifacts can be found

## Parameterized and Property Testing Strategy

Parameterized and property testing should be expanded deliberately around the highest-risk behavior:

- path normalization and placeholder substitution
- slot extraction and operation application
- trailer/index parsing
- verification and launch policy decisions
- workenv path safety
- trust store and key parsing behavior
- CLI argument/flag handling
- operation-chain packing and unpacking

Rules:

- Python: use `pytest.mark.parametrize` for discrete matrix coverage and Hypothesis for invariant discovery.
- Go: use idiomatic table-driven tests for parameterized behavior and native fuzzing where input-space explosion matters.
- Rust: use `proptest` for invariants and standard unit tests for discrete cases.

Parameterized tests should not be a substitute for adversarial tests. A matrix of happy paths is not enough.

## Fuzzing Strategy

Fuzzing must focus on parser and boundary surfaces that can fail catastrophically:

- PSPF trailer/index parsing
- slot descriptor decoding
- metadata decoding and validation
- tar/gzip extraction
- launcher command parsing
- path normalization and workenv substitution
- operation-chain parsing/packing

Rules:

- Go native fuzzers remain first-class for parser/extraction logic.
- Rust `cargo-fuzz` targets must cover maintained PSPF-critical surfaces.
- Python fuzz-like/property coverage can supplement but does not replace native fuzzing in Go and Rust.

Fuzz targets should be explicitly marked and documented as `fuzz`, and any corpus/crash artifacts should stay owned by the relevant language subtree.

## Adversarial Security Test Strategy

The repo needs an intentional hostile-input layer, not just defensive happy-path tests.

Required adversarial themes:

- symlink and hardlink extraction escape attempts
- path traversal in targets and setup commands
- malformed or truncated PSPF structures
- corrupted checksums and signature material
- untrusted-key execution attempts under strict policy
- environment poisoning and placeholder abuse
- launcher/builder type confusion
- oversized values and integer-boundary conditions
- malformed tar/PE metadata and debug directory content

These tests should exist at multiple layers:

- Python orchestration/runtime layer
- Go native parser/launcher layer
- Rust native parser/launcher layer
- cross-language parity layer where the same malicious bundle should produce the same accept/reject behavior

## Mutation Testing Role

Mutation testing is not a behavior category. It is a test-suite quality category.

Meaning:

- `mutation` answers whether the tests are strong enough to detect behavioral change.
- It should focus first on security-critical and parsing-heavy code paths.
- Mutation failures should inform where more unit/property/adversarial tests are needed.

The repo should treat mutation as a feedback loop for test quality, not as the only evidence of correctness.

## Documentation Requirements

The repo documentation must include:

- the canonical meanings of each category
- how Python, Go, and Rust map into those categories
- which commands run each category locally
- which CI jobs correspond to each category
- when to add `security`, `adversarial`, or both
- where to place new tests by default

## Rollout Plan

### Phase 1

- Document the taxonomy.
- Register/normalize pytest markers.
- Add root `Makefile` intent targets.
- Map existing quality jobs and commands to the taxonomy.

### Phase 2

- Reclassify existing tests, especially security and cross-language tests.
- Add adversarial categories where current tests are only implicitly hostile.
- Add missing property/fuzz coverage to the highest-risk native surfaces.

### Phase 3

- Publish CI summaries by intent category.
- Use mutation/fuzz/adversarial results to drive coverage expansion in security-critical areas.

## Recommended End State

The best DX is:

- one shared vocabulary across the repo
- native tools in each language
- repo-level commands by intent
- adversarial security testing as a first-class category
- cost labels that are separate from intent

That gives developers a stable mental model:

- decide what you want to prove
- run the matching intent target
- let the repo choose the correct language-native implementation details
