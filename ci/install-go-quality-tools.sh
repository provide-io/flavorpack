#!/usr/bin/env bash
#
# install-go-quality-tools.sh - Install the Go linters ci/quality-checks.sh runs.
#
# Versions are pinned. Installing at @latest means the finding set moves without
# a commit: a check can start failing, or quietly stop reporting, because an
# upstream release shipped. Blocking checks in particular have to be
# reproducible, so a run of this script yields the same linters every time.
#
# Only the tools quality-checks.sh actually invokes are installed. golangci-lint
# already bundles errcheck, ineffassign, unconvert, misspell and gocritic, so
# installing them separately costs CI minutes and reports nothing extra.

set -euo pipefail

# Bump deliberately: a version change alters what CI enforces.
GOLANGCI_LINT_VERSION="${GOLANGCI_LINT_VERSION:-v2.12.2}"
STATICCHECK_VERSION="${STATICCHECK_VERSION:-2026.2.1}"
GOCYCLO_VERSION="${GOCYCLO_VERSION:-v0.6.0}"

echo "📦 Installing Go quality tools"
echo "   golangci-lint ${GOLANGCI_LINT_VERSION}"
go install "github.com/golangci/golangci-lint/v2/cmd/golangci-lint@${GOLANGCI_LINT_VERSION}"
echo "   staticcheck   ${STATICCHECK_VERSION}"
go install "honnef.co/go/tools/cmd/staticcheck@${STATICCHECK_VERSION}"
echo "   gocyclo       ${GOCYCLO_VERSION}"
go install "github.com/fzipp/gocyclo/cmd/gocyclo@${GOCYCLO_VERSION}"

echo "✅ Installed:"
golangci-lint version
staticcheck --version
