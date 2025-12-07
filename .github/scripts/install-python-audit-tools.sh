#!/bin/bash

set -e

python -m venv audit-env
source audit-env/bin/activate
pip install --upgrade pip
pip install \
  pip-audit \
  safety \
  pip-licenses \
  pipdeptree \
  pip-check \
  outdated \
  pipgrip \
  johnnydep \
  pip-autoremove

# Install project dependencies
pip install -e ".[dev,test]"
