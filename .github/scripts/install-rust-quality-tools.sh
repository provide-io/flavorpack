#!/bin/bash

set -e

# Use cargo-binstall for faster installation when possible
cargo install cargo-binstall --quiet || true

# Try binstall first, fallback to cargo install
cargo binstall --no-confirm cargo-audit || cargo install cargo-audit --quiet
cargo binstall --no-confirm cargo-outdated || cargo install cargo-outdated --quiet
cargo binstall --no-confirm cargo-machete || cargo install cargo-machete --quiet
cargo binstall --no-confirm cargo-deny || cargo install cargo-deny --quiet
cargo binstall --no-confirm cargo-geiger || cargo install cargo-geiger --quiet
