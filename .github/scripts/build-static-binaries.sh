#!/bin/bash

set -ex

cd src

# Go builds (static by default with CGO_ENABLED=0)
cd flavor-go
make clean
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 make build
cd ..

# Rust builds (musl for static linking)
cd flavor-rs
make clean
cargo build --release --target x86_64-unknown-linux-musl
cp target/x86_64-unknown-linux-musl/release/flavor-rs-builder ../../dist/bin/flavor-rs-builder-linux_amd64
cp target/x86_64-unknown-linux-musl/release/flavor-rs-launcher ../../dist/bin/flavor-rs-launcher-linux_amd64
cd ..
