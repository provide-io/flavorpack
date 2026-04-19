# Contributing to flavorpack

Thanks for contributing to flavorpack — the provide.io packaging format and toolchain. This guide covers day-to-day development, testing, and submission expectations.

See `CLAUDE.md` and `AGENTS.md` for the detailed architectural rules that govern code review.

## Prerequisites

- Python 3.11+
- `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Go 1.22+ (for `src/flavor-go/`)
- Rust stable (for `src/flavor-rs/`)

## Development Setup

```bash
git clone https://github.com/provide-io/flavorpack
cd flavorpack
uv sync
```

## Quality Gates

Before opening a PR:

```bash
make quality         # ruff lint + format, mypy strict, tests with 100% coverage gate
make test            # Python tests
make test-go         # Go tests (src/flavor-go)
make test-rust       # Rust tests (src/flavor-rs)
```

Requirements:

- **100% branch coverage** on `src/flavor/**` (enforced).
- **mypy strict mode**. No `type: ignore` without an inline justification.
- **ruff** lint + format must pass.
- Files ≤ 500 lines.

## Commits

- Conventional prefixes: `feat(pack): …`, `fix(manifest): …`, `test(parity): …`, `refactor(runner): …`, `docs: …`, `chore: …`.
- Subject ≤ 72 chars.
- Do not mention AI assistance. No `Co-Authored-By:` trailers.
- Canonical email: `code@tim.life` or `code@provide.io`.
- SPDX headers required on every source/config file.

## Pull Requests

1. Run `make quality` (must pass).
1. For parity-sensitive changes, run `tests/parity/` explicitly.
1. Pretaster fixtures updated where applicable.
1. PR description notes any PSPF spec impact.
