#!/bin/bash
# Setup Python virtual environment with uv
# Usage: setup-python-workenv.sh [extra-packages]
# Requires: astral-sh/setup-uv action (provides uv + python)

set -e

EXTRA_PACKAGES="${1:-}"

echo "🐍 Setting up Python workenv..."

# Create virtual environment using uv
uv venv workenv

# Activate based on OS
if [[ "$RUNNER_OS" == "Windows" ]]; then
    source workenv/Scripts/activate
else
    source workenv/bin/activate
fi

# Install base testing packages
echo "📦 Installing pytest and dependencies..."
uv pip install pytest pytest-cov pytest-xdist

# Install package in editable mode
if [ -f "pyproject.toml" ]; then
    echo "📦 Installing package in editable mode..."
    uv pip install -e .
fi

# Install extra packages if specified
if [ -n "$EXTRA_PACKAGES" ]; then
    echo "📦 Installing extra packages: $EXTRA_PACKAGES"
    uv pip install $EXTRA_PACKAGES
fi

echo "✅ Python workenv setup complete"
echo "   Python: $(python --version)"
echo "   uv: $(uv --version)"
echo "   Pytest: $(pytest --version)"
