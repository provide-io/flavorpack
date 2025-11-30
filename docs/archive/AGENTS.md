# Repository Guidelines

## Project Structure & Modules
- `src/flavor/` hosts the Python orchestrator (CLI, packaging, PSPF tooling), while `src/flavor-go/` and `src/flavor-rs/` hold the launcher/helper implementations; keep helper build artifacts in `dist/bin/`.
- Tests live under `tests/` with subpackages for helpers, security, integration, and Pretaster fixtures (`tests/pretaster`); docs and specs reside in `docs/`.
- Release tooling (`tools/`), automation scripts (`scripts/`), and build glue (`Makefile`, `build.sh`) are top-level; avoid editing generated assets under `site/` or `dist/`.

## Build, Test, and Development Commands
- `uv sync` installs Python dependencies into `.venv`; re-run after `pyproject.toml` changes.
- `make build-helpers` (or `./build.sh`) compiles Go/Rust launchers; required before integration tests.
- `make test`, `make test-cov`, and `uv run pytest -m unit|integration|security` execute the Python suite with or without coverage.
- Static analysis: `ruff format src/ tests/`, `ruff check src/ tests/`, and `mypy src/flavor`; run `gofmt -w . && go test ./...` in `src/flavor-go` and `cargo fmt && cargo clippy && cargo test` in `src/flavor-rs`.
- PSPF validation and cross-language checks live under `tests/pretaster` (`make validate-pspf`, `make combo-test`).

## Coding Style & Naming Conventions
- Python uses 4-space indentation and Ruff’s 111-char line limit; prefer absolute imports (`from flavor.utils import ...`) and fully-typed public APIs.
- Keep CLI modules under `flavor/commands/` prefixed with verbs (`extract.py`, `verify.py`); helper managers belong in `flavor/helpers/`.
- Run `ruff format` before committing; let Ruff, mypy, gofmt, and cargo fmt enforce formatting rather than manual tweaks.

## Testing Guidelines
- Pytest discovers `tests/test_*.py` with markers (`unit`, `integration`, `security`, `requires_helpers`, etc.); include meaningful markers on every new test.
- Maintain ≥60% coverage (`coverage fail_under`); add regression tests for every bugfix and guard new helpers with Pretaster scenarios.
- Integration flows that touch PSPF artifacts must reference fixtures in `tests/pretaster/src/` and validate via `make validate-pspf` before review.

## Commit & Pull Request Guidelines
- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`) in present-tense imperative, mirroring existing history.
- Branch from `develop`, run the full Python + helper test matrices, and update docs when behavior changes.
- Pull requests must describe motivation, list validation commands (`make test`, `make validate-pspf`, etc.), link issues, and attach CLI output or screenshots for UX-facing work.

## Security & Configuration Tips
- Never commit private keys (`keys/flavor-private.key`); use `env.sh`/`env.ps1` to load signing creds locally and restrict distribution to `keys/flavor-public.key`.
- For debugging, prefer environment toggles (`FLAVOR_LOG_LEVEL=debug`, `FOUNDATION_LOG_LEVEL=trace`) over ad-hoc prints, and document any new env var in `docs/`.
