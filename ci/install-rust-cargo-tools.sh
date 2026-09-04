#!/usr/bin/env bash
#
# install-rust-cargo-tools.sh - Install pinned cargo subcommands for a CI job.
#
# Usage: install-rust-cargo-tools.sh <tool> [tool...]
#   e.g. install-rust-cargo-tools.sh cargo-license cargo-deny
#
# Every install is pinned and --locked. Without both, `cargo install` resolves
# each tool's dependency tree afresh on every run, so an upstream break in any
# transitive dependency of any tool turns a job red for reasons that have
# nothing to do with this repository. That is not hypothetical: tinyvec 1.13.0
# was published broken at 21:13 on 2026-09-03 and fixed at 01:26 the next
# morning, and in that window `cargo install cargo-deny` could not build, so
# License Compliance failed on a pull request whose own dependencies were fine.
#
# The same reasoning as ci/install-rust-quality-tools.sh, which pins the one
# tool the code-quality workflow runs. This covers the audit, licence and
# security workflows, which were installing theirs unpinned.

set -euo pipefail

# Bump deliberately: a version change alters what CI enforces.
CARGO_AUDIT_VERSION="${CARGO_AUDIT_VERSION:-0.22.2}"
CARGO_OUTDATED_VERSION="${CARGO_OUTDATED_VERSION:-0.19.0}"
CARGO_LICENSE_VERSION="${CARGO_LICENSE_VERSION:-0.7.0}"
CARGO_DENY_VERSION="${CARGO_DENY_VERSION:-0.20.2}"
CARGO_GEIGER_VERSION="${CARGO_GEIGER_VERSION:-0.13.0}"
CARGO_LLVM_COV_VERSION="${CARGO_LLVM_COV_VERSION:-0.9.0}"
CARGO_MUTANTS_VERSION="${CARGO_MUTANTS_VERSION:-27.1.0}"
CARGO_FUZZ_VERSION="${CARGO_FUZZ_VERSION:-0.13.2}"

if [ "$#" -eq 0 ]; then
    echo "❌ Usage: $0 <tool> [tool...]"
    echo "   Known tools: cargo-audit cargo-outdated cargo-license cargo-deny"
    echo "                cargo-geiger cargo-llvm-cov cargo-mutants cargo-fuzz"
    exit 1
fi

# version_for <tool> — the pin for a tool, or empty when the tool is unknown.
version_for() {
    case "$1" in
        cargo-audit) echo "$CARGO_AUDIT_VERSION" ;;
        cargo-outdated) echo "$CARGO_OUTDATED_VERSION" ;;
        cargo-license) echo "$CARGO_LICENSE_VERSION" ;;
        cargo-deny) echo "$CARGO_DENY_VERSION" ;;
        cargo-geiger) echo "$CARGO_GEIGER_VERSION" ;;
        cargo-llvm-cov) echo "$CARGO_LLVM_COV_VERSION" ;;
        cargo-mutants) echo "$CARGO_MUTANTS_VERSION" ;;
        cargo-fuzz) echo "$CARGO_FUZZ_VERSION" ;;
        *) echo "" ;;
    esac
}

# install_tool <tool> <version>
# binstall pulls a prebuilt binary; building from source is the fallback.
install_tool() {
    local tool="$1"
    local version="$2"

    if command -v cargo-binstall > /dev/null 2>&1; then
        cargo binstall --no-confirm "${tool}@${version}" \
            || cargo install "${tool}@${version}" --locked
    else
        cargo install "${tool}@${version}" --locked
    fi
}

for tool in "$@"; do
    version="$(version_for "$tool")"

    # An unknown tool is a typo in a workflow, and installing whatever that name
    # happens to resolve to on crates.io is the wrong recovery.
    if [ -z "$version" ]; then
        echo "❌ No pinned version for '$tool'."
        echo "   Add one to $(basename "$0") rather than installing it unpinned."
        exit 1
    fi

    # `cargo install --list` is what cargo itself recorded, which is the only
    # uniform way to ask: not every subcommand answers --version. cargo-license
    # 0.7.0 exits 2 on it, so asking the tool would reinstall it every run and
    # then declare the fresh install broken.
    if cargo install --list 2> /dev/null | grep -qE "^${tool} v${version}:"; then
        echo "✅ ${tool} ${version} already installed"
    else
        echo "📦 Installing ${tool} ${version}"
        install_tool "$tool" "$version"
    fi

    # A tool that is absent has to fail here, where the message names the tool,
    # rather than inside the check that needs it, where a missing subcommand
    # reads as a check that found nothing wrong.
    if ! command -v "$tool" > /dev/null 2>&1; then
        echo "❌ ${tool} is not on PATH after installation" >&2
        exit 1
    fi

    # Executing it is the difference between present and working. --version or
    # --help, because which one a tool answers to is its own business.
    if ! "$tool" --version > /dev/null 2>&1 && ! "$tool" --help > /dev/null 2>&1; then
        echo "❌ ${tool} is installed but does not run" >&2
        exit 1
    fi

    echo "✅ Installed: ${tool} ${version}"
done
