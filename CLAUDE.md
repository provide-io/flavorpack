# Flavorpack

Cross-language packaging system that creates self-contained, portable executables using the Progressive Secure Package Format (PSPF) 2025 Edition. The package name is `flavorpack`, but the CLI tool is `flavor`.

## Architecture

- **Python Orchestrator** (`src/flavor/`): Build process, dependency resolution, CLI (`flavor` command), manifest handling
- **Go Helpers** (`src/flavor-go/`): Builder and launcher binaries (PSPF assembly, extraction, execution)
- **Rust Helpers** (`src/flavor-rs/`): Builder and launcher binaries (alternative implementation)
- Built helper binaries go in `dist/bin/`; for wheel packaging they go in `src/flavor/helpers/bin/`

## Development

```bash
# Setup
uv sync

# Build Go/Rust helpers
make build-helpers  # or ./build.sh

# Run tests
make test           # or: pytest
make test-cov       # with coverage

# Specific test categories
pytest -m unit
pytest -m integration
pytest -m security
pytest -m cross_language

# Code quality
ruff check src/ tests/
mypy src/
```

## Key Conventions

- Python 3.11+ required; source in `src/` layout (`src/flavor/`)
- Line length: 111 (ruff/black)
- Linting: ruff with select rules (E, F, W, I, UP, ANN, B, C90, SIM, PTH, RUF)
- Type checking: mypy strict mode
- Use `uv` for package management, not pip directly
- Coverage threshold: 60% (fail_under)
- Generated/protobuf files excluded from linting (`*pb2*.py`, `**/generated/**`)

## CI Workflows

The stage number lives in the workflow's `name:`, not in its filename — the
files are not prefixed. `gh run list --workflow=<file>` takes the filename.

| Stage | File | Runs on | Does |
|---|---|---|---|
| 01 🥘 Helper Prep | `helper-prep.yml` | dispatch | Builds Go/Rust helpers for all 6 platforms |
| 02a 🔬 Pretaster Validation | `pretaster-pipeline.yml` | after 01, main/develop | Cross-language validation on the full matrix, using 01's artifacts |
| 02b 🧪 Pretaster Validation (PR) | `pr-pretaster.yml` | **pull request** | Same suite, helpers built from the PR's source, Linux + macOS |
| 03a 🌶️ Flavor Pipeline | `flavor-pipeline.yml` | after 01, main/develop | Tests, wheels, Flavor PSP builds (badge workflow) |
| 03b 🧪 Test Suites (PR) | `pr-tests.yml` | **pull request** | `cargo test`, `go test`, `pytest`, helpers built from the PR's source |
| 04 🍰 Taster Pipeline | `taster-pipeline.yml` | after 03a | End-to-end taster tests |
| 05 🎨 Code Quality | `code-quality.yml` | **pull request**, schedule | Linting, type checking, complexity |
| 06 🔒 Security Scanning | `security-scan.yml` | push, schedule | Security scanning |
| 07 📦 Dependency Audit | `dependency-audit.yml` | push, schedule | Dependency auditing |
| 08 ⚖️ License Compliance | `license-compliance.yml` | **pull request**, schedule | License compliance |
| 09 🚀 Release Pipeline | `release.yml` | dispatch | Release builds and publication |

Unnumbered: `build-go.yml`, `build-rust.yml`, `build-tastesh.yml` are reusable
(`workflow_call`); `compatibility-check.yml` and `exp-freebsd.yml` run on their
own schedules.

Four workflows see a pull request: 02b, 03b, 05 and 08. Between them a PR gets
the pretaster end-to-end suite, all three language test suites, linting and
licence checks, on Linux and macOS.

Stage numbers ending in `a` run post-merge against the artifacts 01 publishes;
`b` runs on the pull request and builds its helpers from the PR's own source,
because a PR branch cannot reach those artifacts.

## Cross-Platform

Six target platforms: `linux_amd64`, `linux_arm64`, `darwin_amd64`, `darwin_arm64`, `windows_amd64`, `windows_arm64`.

- Linux builds use musl for static linking
- Both Go and Rust launchers work on Windows (PE32 validated, CLI mode tested in CI)
- Ed25519 signatures for package integrity verification

## Important Files

- `VERSION` - Single source of truth for version
- `pyproject.toml` - Python project config, tool settings
- `src/flavor-go/go.mod` - Go module definition
- `src/flavor-rs/Cargo.toml` - Rust crate definition
- `build.sh` - Helper build script
