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

Numbered pipeline stages, each triggering the next:

1. `01-helper-prep.yml` - Build Go/Rust helpers for all 6 platforms
1. `02-pretaster-pipeline.yml` - Cross-language validation with pretaster
1. `03-flavor-pipeline.yml` - Main CI: tests, wheels, Flavor PSP builds (badge workflow)
1. `04-taster-pipeline.yml` - End-to-end taster tests
1. `05-code-quality.yml` - Linting, type checking, complexity
1. `06-security-scan.yml` - Security scanning
1. `07-dependency-audit.yml` - Dependency auditing
1. `08-license-compliance.yml` - License compliance

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
