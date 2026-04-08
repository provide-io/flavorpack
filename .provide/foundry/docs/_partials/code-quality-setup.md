### Code Quality Tools

Standard code quality commands:

#### Formatting

```bash
# Format code with ruff
uv run ruff format src/ tests/

# Check formatting without changing files
uv run ruff format --check src/ tests/
```

#### Linting

```bash
# Run linter
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check --fix src/ tests/

# Fix with unsafe fixes
uv run ruff check --fix --unsafe-fixes src/ tests/
```

#### Type Checking

```bash
# Run mypy
uv run mypy src/

# Run pyright (if available)
uv run pyright

# Type check with strict mode
uv run mypy --strict src/
```

#### Security Scanning

```bash
# Run bandit security scanner
uv run bandit -r src/

# With detailed output
uv run bandit -r src/ -v
```

#### All Quality Checks

```bash
# Run all checks in sequence
uv run ruff format src/ tests/ && \
uv run ruff check src/ tests/ && \
uv run mypy src/ && \
uv run pytest
```
