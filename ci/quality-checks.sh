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
# important a check feels. golangci-lint and staticcheck report nothing on main
# and are enforced, as is cargo machete once it could actually run.
#
# The two complexity checks are enforced as ratchets: the blocking threshold is
# what the tree holds today, so nothing may get worse, and an advisory check
# beside it reports the distance to the target. Tighten the blocking one as the
# advisory one clears.
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
#
# A tool that is not installed exits 127, and reporting that as "found issues"
# describes a lint failure that never happened. Worse, on an advisory check it
# reads as a known backlog, which is how `cargo machete` sat in this file
# reporting "no such command" without anyone noticing. A missing tool fails the
# run whatever the check's status is.
check() {
  local kind="$1" label="$2"; shift 2
  local slug; slug="$(echo "$label" | tr '[:upper:] ' '[:lower:]-')"
  local log="$LOG_DIR/${slug}.log"

  if ! command -v "$1" > /dev/null 2>&1; then
    say "❌ ${label} could not run: '$1' is not installed"
    say ""
    say "This is a setup failure, not a lint result. The check reported nothing"
    say "because it never ran."
    echo "--- ${label} ---" >&2
    echo "'$1' is not installed; ${label} never ran." >&2
    BLOCKING_FAILED=1
    return
  fi

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
    # Two thresholds. The blocking one is a ratchet: it is set to what the tree
    # holds today, so nothing may get worse, and it is meant to be tightened as
    # the advisory one is cleared. The advisory one is the target -- B absolute,
    # A modules and average -- and reports the 16 B-rank and 22 C-rank blocks
    # still between here and there.
    check blocking "Xenon complexity" xenon --max-absolute C --max-modules C --max-average B src/
    check advisory "Xenon complexity (target)" xenon --max-absolute B --max-modules A --max-average A src/
    check blocking "Vulture dead code" vulture
    ;;
  go)
    cd src/flavor-go || exit 1
    say "## 🐹 Go Code Quality"
    say ""
    check blocking "Go vet"       go vet ./...
    check blocking "GolangCI-Lint" golangci-lint run
    check blocking "Staticcheck"  staticcheck ./...
    # Ratchet, as for xenon above: 32 is the worst function in the tree today
    # (runBundleWithCwd), so this fails on anything worse. 15 is the target and
    # lists what is still between the two.
    check blocking "Gocyclo"      gocyclo -over 32 .
    check advisory "Gocyclo (target)" gocyclo -over 15 .
    ;;
  rust)
    cd src/flavor-rs || exit 1
    say "## 🦀 Rust Code Quality"
    say ""
    check blocking "Clippy"       cargo clippy --all-features --all-targets -- -D warnings
    check blocking "Rustfmt"      cargo fmt -- --check
    check blocking "Cargo machete" cargo machete
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
