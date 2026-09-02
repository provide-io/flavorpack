#!/usr/bin/env bash
#
# quality-checks.sh - Run the code quality checks for one language.
#
# Usage: quality-checks.sh <python|go|rust>
#
# Checks are either BLOCKING or ADVISORY. A blocking check that fails makes
# this script exit non-zero; an advisory one is reported and moves on. Every
# check writes to the job summary either way.
#
# Blocking status is decided by what passes on main today, not by how
# important a check feels. golangci-lint (20 issues), staticcheck, gocyclo and
# cargo machete are advisory because they are unmeasured or currently failing;
# promote them once their backlog is clear.
#
# Note on exit codes: checks redirect to a log rather than piping to tee. In a
# pipeline it is tee's status that survives, not the tool's, which is one of
# the ways this workflow used to swallow failures.

set -uo pipefail

LANGUAGE="${1:?usage: quality-checks.sh <python|go|rust>}"
SUMMARY="${GITHUB_STEP_SUMMARY:-/dev/stdout}"
BLOCKING_FAILED=0

# Per-check logs are kept so the workflow can upload them as artifacts.
LOG_DIR="${QUALITY_LOG_DIR:-$(pwd)/quality-logs}"
mkdir -p "$LOG_DIR"

say() { echo "$*" >> "$SUMMARY"; }

# report <blocking|advisory> <label> <logfile> <status>
report() {
  local kind="$1" label="$2" log="$3" status="$4"
  if [ "$status" -eq 0 ]; then
    say "✅ ${label} passed"
    return
  fi
  if [ "$kind" = "blocking" ]; then
    say "❌ ${label} failed"
    BLOCKING_FAILED=1
  else
    say "⚠️ ${label} found issues (advisory)"
  fi
  say '```'
  head -50 "$log" >> "$SUMMARY"
  say '```'
  echo "--- ${label} ---"
  cat "$log"
}

# check <blocking|advisory> <label> <command...>
check() {
  local kind="$1" label="$2"; shift 2
  local slug; slug="$(echo "$label" | tr '[:upper:] ' '[:lower:]-')"
  local log="$LOG_DIR/${slug}.log"
  "$@" > "$log" 2>&1
  report "$kind" "$label" "$log" "$?"
}

case "$LANGUAGE" in
  python)
    say "## 🐍 Python Code Quality"
    say ""
    # ruff is the project's formatter and import sorter -- see [tool.ruff.format]
    # and [tool.ruff.lint.isort] in pyproject.toml. black and isort used to run
    # here too, against a codebase ruff formats, so they always disagreed.
    check blocking "Ruff format"  ruff format --check src/ tests/
    check blocking "Ruff lint"    ruff check src/ tests/
    check blocking "Mypy"         mypy src/flavor
    check blocking "Bandit"       bandit -r src -ll
    check advisory "Xenon complexity" xenon --max-absolute B --max-modules A --max-average A src/
    check advisory "Vulture dead code" vulture src/ --min-confidence 80
    ;;
  go)
    cd src/flavor-go || exit 1
    say "## 🐹 Go Code Quality"
    say ""
    check blocking "Go vet"       go vet ./...
    check advisory "GolangCI-Lint" golangci-lint run
    check advisory "Staticcheck"  staticcheck ./...
    check advisory "Gocyclo"      gocyclo -over 15 .
    ;;
  rust)
    cd src/flavor-rs || exit 1
    say "## 🦀 Rust Code Quality"
    say ""
    check blocking "Clippy"       cargo clippy --all-features --all-targets -- -D warnings
    check blocking "Rustfmt"      cargo fmt -- --check
    check advisory "Cargo machete" cargo machete
    ;;
  *)
    echo "❌ Unknown language: $LANGUAGE" >&2
    exit 2
    ;;
esac

if [ "$BLOCKING_FAILED" -ne 0 ]; then
  say ""
  say "**A blocking check failed.**"
  exit 1
fi
