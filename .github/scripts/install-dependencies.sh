#!/bin/bash

set -e

# Create virtual environment
uv venv workenv
source workenv/bin/activate

# Install project with dev dependency group
uv pip install --group dev -e .

# Install sibling packages if needed
if [ -f "../pyvider-telemetry/pyproject.toml" ]; then
  uv pip install -e "../pyvider-telemetry"
fi
