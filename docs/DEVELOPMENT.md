# Contributor Development Guide

This guide provides instructions for setting up the development environment and building the `flavor` project, including its Python, Go, and Rust components.

## 1. Environment Setup

The project uses `uv` for Python package management and `workenv` for coordinating sibling dependencies.

First, set up the Python virtual environment and install all necessary packages. This script handles everything automatically.

```bash
source env.sh
```

This will create a `workenv/` directory containing a platform-specific Python virtual environment and install `flavor` along with its local dependencies.

## 2. Building the Go and Rust Helpers

The Python build orchestrator depends on pre-compiled helper binaries for Go and Rust. These helpers must be built from the source code within this repository.

A single script handles the compilation of both Go and Rust helpers and places them in the cache location (`~/.cache/flavor/bin/`).

```bash
./helpers/build.sh
```

Run this script once after cloning the repository and any time you make changes to the Go or Rust source code in the `helpers/` directory.

The helper binaries will be installed to:
- `~/.cache/flavor/bin/flavor-go-builder` - Go builder
- `~/.cache/flavor/bin/flavor-go-launcher` - Go launcher  
- `~/.cache/flavor/bin/flavor-rs-builder` - Rust builder
- `~/.cache/flavor/bin/flavor-rs-launcher` - Rust launcher

## 3. Development Workflow

After completing the two setup steps above, you can now run all `flavor` commands.

### Running Tests

To run the complete test suite, including cross-language compatibility tests:

```bash
# Activate the environment to get pytest in your PATH
source workenv/flavor_*/bin/activate

# Run all tests
pytest
```

### Building a Package

To build a test package (e.g., the `taster` utility):

```bash
cd helpers/taster
flavor package --manifest pyproject.toml --output dist/taster.psp
```

This command will now reliably find and use the helper binaries you compiled in step 2.

### Summary

1.  `source env.sh` -> Sets up Python environment.
2.  `./helpers/build.sh` -> Compiles and places Go/Rust helpers in `~/.cache/flavor/bin/`.
3.  `flavor ...` -> Use the tool.

This process ensures that the helper binaries are always in sync with the source code of your current branch, providing a reliable and hermetic build environment.
