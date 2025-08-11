# Flavor v0.1 Development Guide

**Document Version**: 1.0  
**Flavor Version**: 0.1  
**Target Audience**: Contributors, Maintainers, Integrators  
**Last Updated**: August 2025

## Table of Contents

1. [Development Environment Setup](#1-development-environment-setup)
2. [Project Structure](#2-project-structure)
3. [Development Workflow](#3-development-workflow)
4. [Testing Strategy](#4-testing-strategy)
5. [Cross-Language Development](#5-cross-language-development)
6. [Contributing Guidelines](#6-contributing-guidelines)
7. [Release Process](#7-release-process)

## 1. Development Environment Setup

### 1.1 Prerequisites

**Required Software:**
- Python 3.13+ with `uv` package manager
- Go 1.22+ with standard toolchain
- Git for version control
- Make for build automation

**Optional but Recommended:**
- Docker for reproducible builds
- IDE with Go and Python support (VS Code, PyCharm, etc.)
- `pre-commit` for automated code quality checks

### 1.2 Environment Setup

#### 1.2.1 Flavor Development Environment

```bash
# Clone the repository
git clone <repository_url>
cd flavor

# Setup Python environment with all dependencies
source env.sh

# Verify installation - should pass 27/27 tests
pytest
```

The `env.sh` script automatically:
- Creates Python virtual environment using `uv`
- Installs all Python dependencies in editable mode
- Installs sibling packages (pyvider, pyvider-cty, etc.) in editable mode
- Configures PYTHONPATH for development
- Sets up Go module path and dependencies

#### 1.2.2 TofuSoup Integration Environment

```bash
# Setup TofuSoup environment
cd ../tofusoup && source env.sh

# Install Flavor in TofuSoup environment
uv pip install -e /path/to/flavor

# Verify integration
.venv_darwin_arm64/bin/python -m tofusoup.cli package --help
```

### 1.3 Development Tools Configuration

#### 1.3.1 Code Quality Tools

```bash
# Python code formatting and linting
ruff check src/                    # Linting
ruff format src/                   # Code formatting  
mypy src/                         # Type checking

# Go code formatting and linting
cd src/flavor/go/
go fmt ./...                      # Code formatting
go vet ./...                      # Static analysis
golangci-lint run                 # Comprehensive linting
```

#### 1.3.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
      - id: ruff-format
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        
  - repo: local
    hooks:
      - id: go-fmt
        name: go-fmt
        entry: gofmt
        language: system
        types: [go]
        args: [-w]
```

## 2. Project Structure

### 2.1 Directory Organization

```
flavor/
├── docs/                           # Comprehensive documentation
│   ├── SPECIFICATION.md            # Flavor v0.1 format specification  
│   ├── ARCHITECTURE.md             # Architecture design document
│   ├── SECURITY.md                 # Security model and implementation
│   ├── DEVELOPMENT.md              # This document
│   ├── INTEGRATION.md              # TofuSoup integration guide
│   ├── DESIGN_TOFUSOUP_INTEGRATION.md  # Legacy integration design
│   └── REFACTOR.md                 # Migration documentation
├── src/
│   └── flavor/                       # Python implementation
│       ├── __init__.py             # Package initialization  
│       ├── api.py                  # Public API interface
│       ├── cli.py                  # Command-line interface
│       ├── models.py               # Flavor data models
│       ├── crypto.py               # Cryptographic operations
│       ├── compiler.py             # Go binary compilation
│       ├── build_backend.py        # PEP 517 build backend
│       ├── packaging/              # Package creation and management
│       │   ├── orchestrator.py     # Build orchestration
│       │   └── reader.py           # Package reading and parsing
│       ├── go/                     # Go implementation
│       │   ├── pkg/flavor/           # Go Flavor library
│       │   │   ├── spec.go         # Format specification
│       │   │   └── footer.go       # Binary footer handling  
│       │   ├── flavor-packager/      # Go CLI tool
│       │   │   ├── main.go         # CLI entry point
│       │   │   └── cmd/            # Cobra commands
│       │   └── flavor-launcher/      # Go runtime launcher
│       │       ├── main.go         # Launcher entry point
│       │       └── runtime.go      # Runtime management
│       └── templates/              # Configuration templates
├── tests/                          # Comprehensive test suite
│   ├── api/                        # API integration tests
│   ├── cli/                        # CLI functionality tests
│   ├── crypto/                     # Cryptographic tests  
│   ├── compiler/                   # Cross-language compatibility tests
│   ├── models/                     # Data model tests
│   └── packaging/                  # Package creation tests
├── scripts/                        # Development and build scripts
├── pyproject.toml                  # Python project configuration
├── BUILD_WORKFLOWS.md              # Build process documentation
├── README.md                       # Project overview and quick start
└── env.sh                          # Development environment setup
```

### 2.2 Code Organization Principles

#### 2.2.1 Separation of Concerns
- **API Layer** (`api.py`): Public interface for external integrations
- **CLI Layer** (`cli.py`): Command-line interface implementation  
- **Core Logic** (`models.py`, `crypto.py`): Business logic and data structures
- **Integration Layer** (`packaging/`, `compiler.py`): External tool integration
- **Cross-Language** (`go/`): Go implementation for performance-critical components

#### 2.2.2 Dependency Management
- **Minimal Dependencies**: Use minimal set of well-maintained dependencies
- **Pinned Versions**: Pin dependency versions for reproducible builds
- **Cross-Language Compatibility**: Ensure Go and Python implementations are compatible

## 3. Development Workflow

### 3.1 Feature Development Process

#### 3.1.1 Branch Strategy
```bash
# Feature development workflow
git checkout main
git pull origin main
git checkout -b feature/feature-name

# Make changes, commit regularly
git add .
git commit -m "feat: add feature description"

# Before pushing, ensure all tests pass
pytest                            # Python tests
cd src/flavor/go && go test ./...   # Go tests

# Push feature branch
git push origin feature/feature-name

# Create pull request for review
```

#### 3.1.2 Code Review Requirements
- **All Changes**: Require peer review for all code changes
- **Cross-Language Changes**: Require review by developers familiar with both Go and Python
- **Security Changes**: Require review by security-focused developers
- **Test Coverage**: Ensure new features have comprehensive test coverage

### 3.2 Testing During Development

#### 3.2.1 Continuous Testing
```bash
# Run tests automatically during development
pytest --cov=flavor --cov-report=term-missing

# Run Go tests
cd src/flavor/go
go test -v -race ./...

# Cross-language compatibility tests
pytest tests/compiler/test_cross_language_compatibility.py
```

#### 3.2.2 Integration Testing
```bash
# Test TofuSoup integration
cd ../tofusoup
.venv_darwin_arm64/bin/python -m pytest tests/package/

# Test end-to-end package creation and verification
cd ../flavor
python -c "
import flavor.api
from pathlib import Path
# Test complete workflow
flavor.api.generate_keys(Path('test-keys'))
flavor.api.build_package_from_manifest(Path('test-project/pyproject.toml'))
"
```

### 3.3 Debugging and Troubleshooting

#### 3.3.1 Debug Configuration
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Flavor-specific debug flags
import flavor.api
flavor.api.DEBUG = True

# Enable Go debug output
export PSPF_DEBUG=true
export PSPF_LOG_LEVEL=debug
```

#### 3.3.2 Common Issues and Solutions

**Issue**: Cross-language test failures
```bash
# Solution: Verify Go and Python produce identical results
cd tests/compiler/
python test_checksum_compatibility.py --verbose
```

**Issue**: Build failures in TofuSoup integration
```bash
# Solution: Ensure Flavor is properly installed in TofuSoup environment
cd ../tofusoup
uv pip install -e /path/to/flavor --force-reinstall
```

**Issue**: Cryptographic test failures
```bash  
# Solution: Verify cryptographic library versions
python -c "import cryptography; print(cryptography.__version__)"
go list -m golang.org/x/crypto
```

## 4. Testing Strategy

### 4.1 Test Categories

#### 4.1.1 Unit Tests
- **Python Units**: Test individual Python functions and classes
- **Go Units**: Test individual Go functions and packages
- **Coverage Target**: >90% code coverage for both languages

```python
# Example Python unit test
def test_pspf_header_creation():
    """Test Flavor header creation and serialization."""
    header = PspfHeader(
        version="0.1",
        format="flavor",
        created=datetime.now(timezone.utc)
    )
    
    # Test serialization
    json_data = header.to_json()
    assert json_data["version"] == "0.1"
    
    # Test deserialization
    reconstructed = PspfHeader.from_json(json_data)
    assert reconstructed.version == header.version
```

#### 4.1.2 Integration Tests
- **API Integration**: Test complete API workflows
- **CLI Integration**: Test command-line interface functionality
- **Cross-Language**: Test Go and Python compatibility

```python
# Example integration test
def test_complete_package_workflow():
    """Test complete package creation and verification workflow."""
    # Setup test environment
    test_dir = Path("test-integration")
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Generate keys
        key_dir = test_dir / "keys"
        flavor.api.generate_keys(key_dir)
        
        # Build package
        manifest = test_dir / "pyproject.toml"
        create_test_manifest(manifest)
        package_path = flavor.api.build_package_from_manifest(manifest)
        
        # Verify package
        is_valid = flavor.api.verify_package(package_path)
        assert is_valid
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
```

#### 4.1.3 Security Tests
- **Cryptographic Validation**: Test cryptographic operations against known vectors
- **Malicious Input**: Test resistance to malformed and malicious inputs  
- **Attack Simulation**: Simulate various attack scenarios

### 4.2 Test Infrastructure

#### 4.2.1 Test Fixtures
```python
# conftest.py - Shared test fixtures
@pytest.fixture
def temp_test_dir():
    """Create temporary directory for tests."""
    test_dir = Path(tempfile.mkdtemp())
    yield test_dir
    shutil.rmtree(test_dir)

@pytest.fixture  
def test_key_pair():
    """Generate test ECDSA key pair."""
    private_key, public_key = flavor.crypto.generate_key_pair()
    return private_key, public_key

@pytest.fixture
def test_manifest(temp_test_dir):
    """Create test pyproject.toml manifest."""
    manifest_path = temp_test_dir / "pyproject.toml"
    manifest_content = """
[project]
name = "test-provider"
version = "1.0.0"
scripts = { "terraform-provider-test" = "test.main:serve" }

[tool.flavor]
provider_name = "test"
entry_point = "test.main:serve"
"""
    manifest_path.write_text(manifest_content)
    return manifest_path
```

#### 4.2.2 Continuous Integration
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: |
          source env.sh
          pytest --cov=flavor
          
  test-go:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
        with:
          go-version: '1.22'
      - run: |
          cd src/flavor/go
          go test -v -race ./...
          
  test-integration:
    runs-on: ubuntu-latest
    needs: [test-python, test-go]  
    steps:
      - uses: actions/checkout@v3
      - run: |
          source env.sh
          pytest tests/compiler/test_cross_language_compatibility.py
```

## 5. Cross-Language Development

### 5.1 Go-Python Compatibility

#### 5.1.1 Data Structure Compatibility
Ensure Go and Python data structures produce identical binary representations:

```python
# Python model
@dataclass
class PspfFooter:
    signature_length: int
    signature: bytes
    public_key_length: int  
    public_key: bytes
    footer_offset: int
    magic: bytes = b"PSPF001\0"
```

```go
// Go equivalent
type PspfFooter struct {
    SignatureLength  uint32
    Signature        []byte
    PublicKeyLength  uint32
    PublicKey        []byte
    FooterOffset     uint64
    Magic           [8]byte // "PSPF001\0"
}
```

#### 5.1.2 Compatibility Testing
```python
def test_go_python_data_compatibility():
    """Ensure Go and Python produce identical binary output."""
    # Create data structure in Python
    python_footer = PspfFooter(
        signature_length=64,
        signature=b"x" * 64,
        public_key_length=64,
        public_key=b"y" * 64,
        footer_offset=12345,
    )
    
    # Serialize to binary
    python_binary = python_footer.to_binary()
    
    # Parse with Go implementation
    go_footer = go_parse_footer(python_binary)
    
    # Verify identical results
    assert go_footer.signature_length == python_footer.signature_length
    assert go_footer.signature == python_footer.signature
```

### 5.2 Build System Integration

#### 5.2.1 Go Binary Compilation
```python
# compiler.py - Go binary compilation
def compile_go_binary(source_path: Path, output_path: Path) -> Path:
    """Compile Go binary with appropriate build flags."""
    cmd = [
        "go", "build",
        "-ldflags", "-s -w",  # Strip debug info
        "-o", str(output_path),
        str(source_path)
    ]
    
    result = subprocess.run(
        cmd,
        cwd=source_path.parent,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise CompilationError(f"Go build failed: {result.stderr}")
        
    return output_path
```

#### 5.2.2 Cross-Platform Builds
```bash
# Build for multiple platforms
for GOOS in linux darwin windows; do
    for GOARCH in amd64 arm64; do
        GOOS=$GOOS GOARCH=$GOARCH go build \
            -ldflags "-s -w" \
            -o "bin/flavor-packager-$GOOS-$GOARCH" \
            ./cmd/flavor-packager
    done
done
```

## 6. Contributing Guidelines

### 6.1 Code Standards

#### 6.1.1 Python Code Standards
- **PEP 8**: Follow Python style guide
- **Type Hints**: Use comprehensive type hints
- **Docstrings**: Document all public functions and classes
- **Error Handling**: Use specific exception types

```python
def build_package_from_manifest(manifest_path: Path) -> Path:
    """Build Flavor package from pyproject.toml manifest.
    
    Args:
        manifest_path: Path to pyproject.toml configuration file
        
    Returns:
        Path to created Flavor package binary
        
    Raises:
        BuildError: If package build fails
        FileNotFoundError: If manifest file not found
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
    try:
        # Implementation here
        pass
    except Exception as e:
        raise BuildError(f"Package build failed: {e}") from e
```

#### 6.1.2 Go Code Standards
- **Go Format**: Use `go fmt` for consistent formatting
- **Go Vet**: Pass `go vet` static analysis
- **Error Handling**: Follow Go error handling conventions  
- **Documentation**: Document all exported functions

```go
// BuildPackage creates a Flavor package from the given configuration.
// Returns the path to the created package or an error if build fails.
func BuildPackage(config BuildConfig) (string, error) {
    if err := config.Validate(); err != nil {
        return "", fmt.Errorf("invalid configuration: %w", err)
    }
    
    // Implementation here
    
    return packagePath, nil
}
```

### 6.2 Commit Guidelines

#### 6.2.1 Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or modifications
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `security`: Security-related changes

**Examples:**
```
feat(crypto): add P-384 curve support

Add support for ECDSA P-384 curve in addition to existing P-256 
support. This provides enhanced security for high-value applications.

Closes #123

fix(parser): handle malformed footer gracefully

Prevent panic when parsing packages with malformed footer data.
Add comprehensive input validation and error handling.

security(verify): add timestamp validation

Add package timestamp validation to prevent replay attacks
with old signed packages.
```

### 6.3 Pull Request Process

1. **Create Feature Branch**: Branch from `main` for new features
2. **Implement Changes**: Follow coding standards and include tests
3. **Run Test Suite**: Ensure all tests pass locally
4. **Update Documentation**: Update relevant documentation
5. **Create Pull Request**: Provide clear description and context
6. **Code Review**: Address reviewer feedback
7. **Merge**: Merge after approval and passing CI

## 7. Release Process

### 7.1 Version Management

#### 7.1.1 Semantic Versioning
Flavor follows semantic versioning (semver):
- **Major** (X.y.z): Breaking changes to format or API
- **Minor** (x.Y.z): New features, backward compatible
- **Patch** (x.y.Z): Bug fixes, backward compatible

#### 7.1.2 Version Update Process
```bash
# Update version in pyproject.toml
sed -i 's/version = "0.1.0"/version = "0.1.1"/' pyproject.toml

# Update version in Go code
sed -i 's/const Version = "0.1.0"/const Version = "0.1.1"/' src/flavor/go/pkg/flavor/version.go

# Commit version update
git add .
git commit -m "release: bump version to 0.1.1"
```

### 7.2 Release Checklist

#### 7.2.1 Pre-Release Testing
- [ ] All unit tests pass (Python and Go)
- [ ] Integration tests pass
- [ ] Cross-language compatibility tests pass
- [ ] Security tests pass
- [ ] TofuSoup integration tests pass
- [ ] Documentation is up-to-date
- [ ] CHANGELOG.md is updated

#### 7.2.2 Release Steps
1. **Version Bump**: Update version numbers in all relevant files
2. **Tag Release**: Create Git tag for release version
3. **Build Artifacts**: Build release artifacts for all platforms
4. **Security Scan**: Run security scans on release artifacts
5. **Documentation**: Ensure documentation matches release
6. **Publish**: Publish release to appropriate channels

```bash
# Create release tag
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin v0.1.1

# Build release artifacts
python -m build
cd src/flavor/go && make build-all

# Publish release
# (Process depends on distribution method)
```

### 7.3 Post-Release

- **Monitor**: Monitor for issues in released version
- **Support**: Provide support for released versions
- **Security**: Monitor for security issues and provide patches
- **Documentation**: Maintain documentation for all supported versions

## Conclusion

This development guide provides the foundation for contributing to Flavor v0.1. The development process emphasizes code quality, comprehensive testing, and cross-language compatibility to ensure the security and reliability of the Progressive Secure Package Format.

For questions or clarifications about the development process, please refer to the project documentation or reach out to the maintainers.