# GEMINI.md: Your AI Assistant for the `flavorpack` Monorepo

This document provides context and instructions for interacting with the `flavorpack` monorepo. It is intended to be used by the Gemini AI assistant to help you with your development tasks.

## Project Overview

`flavorpack` is a cross-language packaging system that creates self-contained, portable executables using the **Progressive Secure Package Format (PSPF) 2025 Edition**. It enables you to ship Python applications as single binaries that "just work" - no installation, no dependencies, no configuration required.

The project is a monorepo containing the Python orchestrator, Go and Rust "ingredients" (builders and launchers), and documentation.

## Core Components

*   **Python Orchestrator (`src/flavor/`)**: The main application that manages the packaging process. It provides the `flavor` command-line interface (CLI).
*   **Go Ingredients (`ingredients/flavor-go/`)**: Go implementation of the PSPF builder and launcher.
*   **Rust Ingredients (`ingredients/flavor-rs/`)**: Rust implementation of the PSPF builder and launcher.
*   **Documentation (`docs/`)**: Contains detailed information about the architecture, user guide, and development process.

## Building and Running

The project uses a combination of `make`, `uv`, `pytest`, and shell scripts for building and testing.

### Prerequisites

*   Python 3.11+
*   Go 1.21+
*   Rust 1.75+
*   `uv` package manager

### Setup

1.  **Install dependencies:**
    ```bash
    source env.sh
    ```

2.  **Build Go and Rust ingredients:**
    ```bash
    make build-ingredients
    ```
    or
    ```bash
    ./ingredients/build.sh
    ```

### Running Tests

*   **Run all tests:**
    ```bash
    make test
    ```
*   **Run tests with coverage:**
    ```bash
    workenv/flavor_*/bin/pytest --cov=src/flavor --cov-report=term-missing
    ```

### CLI Usage

The main entry point is the `flavor` command.

*   **Create a package:**
    ```bash
    flavor pack --manifest pyproject.toml --output myapp.psp
    ```
*   **Verify a package:**
    ```bash
    flavor verify myapp.psp
    ```
*   **Inspect a package:**
    ```bash
    flavor inspect myapp.psp
    ```

## Development Conventions

*   **Coding Style**: The code is formatted with `ruff format` and linted with `ruff check`.
*   **Testing**: The project is tested with `pytest`.
*   **Dependencies**: Dependencies are managed with `uv` and specified in `pyproject.toml`.
