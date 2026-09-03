#!/usr/bin/env bash
#
# pr-tests.sh - Run the Rust, Go and Python test suites for a pull request.
#
# Until this existed, no workflow ran a test suite on a PR. 03a holds them, and
# it is workflow_run-gated to main behind 01 Helper Prep, which is
# workflow_dispatch-only -- so the suites ran when somebody manually kicked off
# a helper build, roughly four times in a fortnight, and never on a PR. A pull
# request could add or break a test and merge green.
#
# Like 02b, this builds the helpers it needs from the PR's own source instead
# of downloading artifacts a PR branch has no way to reach.
#
# Usage: pr-tests.sh [all|rust|go|python]

set -uo pipefail

SUITE="${1:-all}"
SUMMARY="${GITHUB_STEP_SUMMARY:-/dev/stdout}"
FAILED=0

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# set -e is deliberately not enabled here (checks are meant to run to
# completion), so a failed cd would otherwise run every suite from whatever
# directory the runner happened to be in.
cd "$REPO_ROOT" || exit 1

LOG_DIR="${PR_TESTS_LOG_DIR:-$REPO_ROOT/test-logs}"
mkdir -p "$LOG_DIR"

say() { echo "$*" >> "$SUMMARY"; }

# run <label> <command...>
#
# Output goes through tee so a long suite shows progress in the job log rather
# than sitting silent for minutes. The status comes from PIPESTATUS[0], never
# from the pipeline: a bare `cmd | tee` reports tee's status, which is how this
# repository's checks used to swallow failures. See ci/quality-checks.sh, which
# avoids the same trap by redirecting instead.
run() {
  local label="$1"; shift
  local slug; slug="$(echo "$label" | tr '[:upper:] ' '[:lower:]-')"
  local log="$LOG_DIR/${slug}.log"
  local status

  echo "::group::${label}"
  "$@" 2>&1 | tee "$log"
  status=${PIPESTATUS[0]}
  echo "::endgroup::"

  if [ "$status" -eq 0 ]; then
    say "✅ ${label} passed"
  else
    say "❌ ${label} failed (exit ${status})"
    FAILED=1
  fi
}

say "## 🧪 Test Suites"
say ""

# The Python suite needs real launcher binaries; Rust and Go do not. Build
# regardless -- a PR that breaks the build should fail here rather than in a
# later job with a more confusing message.
echo "🔨 Building Go and Rust helpers from source..."
if ! ./build.sh; then
  say "❌ Helper build failed — no suite could run"
  exit 1
fi
ls -la dist/bin/

if [ "$SUITE" = "all" ] || [ "$SUITE" = "rust" ]; then
  run "Rust tests" cargo test --manifest-path src/flavor-rs/Cargo.toml
fi

if [ "$SUITE" = "all" ] || [ "$SUITE" = "go" ]; then
  run "Go tests" make -C src/flavor-go test
fi

if [ "$SUITE" = "all" ] || [ "$SUITE" = "python" ]; then
  # FLAVOR_REQUIRE_HELPERS turns a missing launcher into an error instead of a
  # silent skip. Every prerequisite exists in this job, so a skip would mean a
  # setup bug -- and a suite that skips its integration tests reports success
  # having checked nothing.
  export FLAVOR_REQUIRE_HELPERS=1
  run "Python tests" uv run ci/run-tests.sh
fi

say ""
if [ "$FAILED" -ne 0 ]; then
  say "One or more suites failed."
  exit 1
fi
say "All suites passed."
