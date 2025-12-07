#!/bin/bash

set -e

python -m venv quality-env
source quality-env/bin/activate
pip install --upgrade pip
pip install \
  ruff \
  mypy \
  bandit[toml] \
  pylint \
  black \
  isort \
  flake8 \
  flake8-docstrings \
  flake8-bugbear \
  flake8-comprehensions \
  flake8-simplify \
  pydocstyle \
  pycodestyle \
  mccabe \
  radon \
  xenon \
  vulture \
  safety \
  pip-audit

# Install project dependencies for better type checking
pip install -e ".[dev,test]"
