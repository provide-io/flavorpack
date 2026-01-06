# Cookbook Examples

Practical examples demonstrating how to use FlavorPack for various packaging scenarios.

## Quick Examples

### Minimal Package

The simplest possible PSPF package.

```toml
# pyproject.toml
[project]
name = "hello-world"
version = "1.0.0"
description = "Minimal FlavorPack example"
requires-python = ">=3.11"

[tool.flavor]
entry_point = "hello:main"
```

```python
# hello.py
def main():
    print("Hello from FlavorPack!")
    
if __name__ == "__main__":
    main()
```

```bash
# Build and run
flavor pack
./dist/hello-world.psp
```

### CLI Application

Package a Click-based CLI application.

```toml
# pyproject.toml
[project]
name = "myapp"
version = "2.0.0"
description = "CLI application example"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
    "rich>=13.0"
]

[tool.flavor]
entry_point = "myapp.cli:main"
```

```python
# myapp/cli.py
import click
from rich.console import Console

console = Console()

@click.command()
@click.option("--name", default="World", help="Name to greet")
@click.option("--color", default="green", help="Text color")
def main(name: str, color: str):
    """A friendly CLI application."""
    console.print(f"Hello, {name}!", style=f"bold {color}")
    
if __name__ == "__main__":
    main()
```

```bash
# Build with progress
flavor pack --progress --strip

# Run with options
./dist/myapp.psp --name "FlavorPack" --color blue
```

### Web Application

Package a FastAPI web application.

```toml
# pyproject.toml
[project]
name = "webapi"
version = "1.0.0"
description = "FastAPI web application"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.100",
    "uvicorn[standard]>=0.23"
]

[tool.flavor]
entry_point = "webapi.app:run"

[tool.flavor.execution.runtime.env]
set = { PORT = "8000", HOST = "0.0.0.0" }
```

```python
# webapi/app.py
import os
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="FlavorPack API")

@app.get("/")
def read_root():
    return {"message": "Hello from FlavorPack!", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

def run():
    """Entry point for packaged application."""
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run()
```

```bash
# Build and run
flavor pack --key-seed "api-key-123"
./dist/webapi.psp

# API is now available at http://localhost:8080
```

### Data Science Package

Package a data science application with NumPy and Pandas.

```toml
# pyproject.toml
[project]
name = "datasci"
version = "1.0.0"
description = "Data science application"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.0",
    "numpy>=1.24",
    "matplotlib>=3.7",
    "scikit-learn>=1.3"
]

[tool.flavor]
entry_point = "datasci.analyze:main"
```

```python
# datasci/analyze.py
import pandas as pd
import numpy as np

def main():
    """Analyze data from package."""
    print("Creating sample data...")
    df = pd.DataFrame({
        "x": np.random.randn(100),
        "y": np.random.randn(100),
    })
    print(f"Generated {len(df)} samples")
    print(df.head())

if __name__ == "__main__":
    main()
```

## Advanced Examples

### Signed Package with Verification

Create cryptographically signed packages.

```bash
# 1. Generate key pair
flavor keygen --out-dir keys/

# 2. Build signed package
flavor pack \
  --private-key keys/private.pem \
  --public-key keys/public.pem \
  --output signed-app.psp

# 3. Distribute public key separately
cp keys/public.pem public-key.pem

# 4. Users verify before running
flavor verify signed-app.psp --public-key public-key.pem
./signed-app.psp
```

### Development vs Production Builds

Different configurations for development and production.

```bash
# Development build (fast, no verification)
flavor pack \
  --no-verify \
  --output dev.psp \
  --key-seed "dev-seed"

# Production build (optimized, signed)
flavor pack \
  --strip \
  --private-key prod-keys/private.pem \
  --public-key prod-keys/public.pem \
  --output prod.psp \
  --progress
```

## Integration Examples

### CI/CD with GitHub Actions

```yaml
# .github/workflows/package.yml
name: Build Package

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install FlavorPack
        run: uv tool install flavorpack
      
{% raw %}
      - name: Build package
        run: |
          flavor pack \
            --strip \
            --key-seed "${{ secrets.PACKAGE_KEY }}" \
            --output dist/app-${{ github.ref_name }}.psp

      - name: Verify package
{% endraw %}
        run: flavor verify dist/app-*.psp
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: package
          path: dist/*.psp
```

### Docker Integration

```dockerfile
# Dockerfile
FROM python:3.11-slim as builder

WORKDIR /app
COPY . .

RUN uv tool install flavorpack
RUN flavor pack --strip --output app.psp

FROM scratch
COPY --from=builder /app/app.psp /app.psp
ENTRYPOINT ["/app.psp"]
```

### Makefile Automation

```makefile
# Makefile
.PHONY: build clean test package

VERSION := $(shell grep version pyproject.toml | cut -d'"' -f2)
PACKAGE := myapp-$(VERSION).psp

build:
	flavor pack --output dist/$(PACKAGE)

clean:
	flavor clean --all --yes
	rm -rf dist/

test:
	pytest tests/
	flavor pack --no-verify --output test.psp
	./test.psp --help

release: clean test
	flavor pack \
		--strip \
		--key-seed "$(RELEASE_KEY)" \
		--output dist/$(PACKAGE)
	flavor verify dist/$(PACKAGE)
```

## Troubleshooting Examples

### Debug Package Contents

```bash
# Inspect package structure
flavor inspect problematic.psp

# Extract all slots for examination
flavor extract-all problematic.psp --output-dir debug/

# Check specific slot
flavor extract problematic.psp metadata.json --output debug-meta.json
cat debug-meta.json | jq '.'
```

### Verbose Logging

```bash
# Maximum verbosity for debugging
flavor --log-level trace pack

# Debug verification issues
flavor --log-level debug verify package.psp
```

### Environment Debugging

```bash
# Check FlavorPack environment
env | grep FLAVOR

# Test with clean environment
env -i HOME=$HOME PATH=$PATH flavor pack

# Override cache location
FLAVOR_CACHE_DIR=/tmp/flavor-cache flavor pack
```

## Performance Examples

### Optimized Builds

```bash
# Strip binaries
flavor pack --strip

# Skip verification for speed
flavor pack --no-verify
```

### Caching Strategies

```bash
# Pre-cache dependencies
UV_CACHE_DIR=uv-cache uv sync

# Use local package index
UV_INDEX_URL=file:///path/to/uv-cache flavor pack
```

## Next Steps

- Review the [API Reference](../../api/index.md) for detailed function documentation
- Check the [CLI Reference](../../guide/usage/cli.md) for all command options
- Read the [Package Format Specification](../../reference/spec/fep-0001-core-format-and-operation-chains.md) for technical details
- See [Troubleshooting Guide](../../troubleshooting/common.md) for common issues
