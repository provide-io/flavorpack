#!/bin/bash

set -e

echo "🐍 Installing Python security tools..."
python -m venv security-env
source security-env/bin/activate
pip install --upgrade pip
pip install \
  bandit[toml] \
  safety \
  pip-audit \
  semgrep \
  dlint \
  pyt \
  dodgy \
  vulture

# Install project for dependency scanning
pip install -e ".[dev,test]"

echo "🐹 Installing Go security tools..."
go install github.com/sonatype-nexus-community/nancy@latest

echo "🦀 Installing Rust security tools..."
cargo install cargo-deny
cargo install cargo-geiger

echo "🐳 Installing Container security tools..."
wget -q https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64 -O hadolint
chmod +x hadolint
sudo mv hadolint /usr/local/bin/

echo "🏗️ Installing IaC security tools..."
pip install yamllint
