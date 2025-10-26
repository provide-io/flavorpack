# Design Principles

FlavorPack follows the Provide Foundry's core design principles while adding packaging-specific philosophies.

## Foundry-Wide Principles

### 1. **Composability Over Monoliths**

**Principle**: Build small, focused tools that work well together rather than monolithic frameworks.

**In FlavorPack**:
- FlavorPack handles packaging, not deployment or hosting
- Integrates with `wrknv` for environment management
- Works with `pyvider` for Terraform provider distribution
- Leverages `provide-foundation` for core services

```python
# FlavorPack composes with other tools
from flavor import pack
from wrknv import Environment

env = Environment.create()
env.install_dependencies()
pack(manifest=env.manifest, output="app.psp")
```

### 2. **Developer Experience First**

**Principle**: If it's hard to use, it's wrong. Optimize for clarity, not cleverness.

**In FlavorPack**:
- Clear, predictable CLI commands
- Helpful error messages with suggested fixes
- Sensible defaults that "just work"
- Progressive complexity (simple by default, powerful when needed)

```bash
# Simple: One command packaging
flavor pack

# Powerful: Full control when needed
flavor pack \
  --manifest pyproject.toml \
  --config flavor.toml \
  --launcher-bin dist/bin/flavor-rs-launcher-linux_amd64 \
  --key-seed myseed \
  --output dist/myapp.psp
```

### 3. **Type Safety Without Compromise**

**Principle**: Use Python's type system fully. Types should help, not hinder.

**In FlavorPack**:
- Full type annotations on all public APIs
- Runtime validation for user inputs
- Type-safe configuration with validation
- Clear type errors with helpful messages

```python
from flavor import Packager
from flavor.types import Manifest, Package

def build_package(manifest: Manifest) -> Package:
    packager = Packager(manifest=manifest)
    return packager.build()  # Type-checked!
```

### 4. **Explicit Over Implicit**

**Principle**: Magic is expensive. Be explicit about what's happening.

**In FlavorPack**:
- Explicit helper selection (with smart defaults)
- Clear logging of every step
- Manifest validation with specific errors
- No hidden state or implicit behaviors

```bash
# FlavorPack tells you exactly what it's doing
$ flavor pack
📦 Reading manifest from pyproject.toml
🔍 Selecting helper: flavor-rs-builder-darwin_arm64
🐍 Resolving Python dependencies (found 42 packages)
📂 Creating slot 0: Python runtime
📂 Creating slot 1: Application code
🔐 Signing package with Ed25519
✅ Package created: myapp.psp (2.3 MB)
```

### 5. **Testing at Every Level**

**Principle**: If it's not tested, it's broken.

**In FlavorPack**:
- Unit tests for all core logic
- Integration tests for Go/Rust/Python compatibility
- Cross-language tests with Pretaster
- Property-based tests with Hypothesis
- Security tests for signature verification

## FlavorPack-Specific Principles

### 6. **Security by Default**

**Principle**: Security should be automatic, not optional.

**FlavorPack Implementation**:
- All packages are signed by default
- Signature verification on every execution
- Tamper detection built-in
- No insecure modes in production

```python
# Security is automatic
packager = Packager()
package = packager.build()  # Automatically signed

# Verification is mandatory
launcher.verify(package)  # Always runs before execution
```

### 7. **Progressive Extraction**

**Principle**: Don't extract what you don't need, but cache what you use.

**FlavorPack Implementation**:
- Lazy extraction of slots
- Persistent cache with validation
- Incremental updates when possible
- Smart cache eviction

```python
# Only extracts when needed
workenv = launcher.prepare()  # Checks cache first
if not workenv.valid():
    workenv.extract()  # Only extracts if invalid
```

### 8. **Cross-Language Correctness**

**Principle**: Python orchestrates, native code executes. Both must be correct.

**FlavorPack Implementation**:
- Python defines the format
- Go and Rust implement it identically
- Comprehensive cross-language tests
- Format spec is the source of truth

```python
# Python orchestrator
class Orchestrator:
    def build(self):
        return self.helper.build_package()  # Calls Go/Rust

# Go/Rust helpers implement identical format
```

### 9. **Platform Parity**

**Principle**: Same code, same behavior, everywhere.

**FlavorPack Implementation**:
- Static binaries for maximum portability
- Identical behavior on Linux, macOS, Windows
- Platform-specific binaries, platform-agnostic format
- Comprehensive platform testing

```bash
# Same package runs on all platforms
./myapp.psp  # Works on Linux
./myapp.psp  # Works on macOS
myapp.psp    # Works on Windows
```

### 10. **Zero Installation Requirement**

**Principle**: End users shouldn't need to install anything.

**FlavorPack Implementation**:
- Self-contained executables
- No Python installation required
- No system dependencies
- Runs from any location

```bash
# No setup needed
$ ./myapp.psp --help  # Just works!
```

## Anti-Patterns to Avoid

### ❌ **Hidden Configuration**

```python
# Bad: Hidden magic
packager = Packager()
packager.build()  # Where's the manifest? What launcher?

# Good: Explicit configuration
packager = Packager(manifest="pyproject.toml")
packager.build(launcher="flavor-rs-launcher")
```

### ❌ **Implicit Dependencies**

```python
# Bad: Hidden dependencies
from flavor import pack
pack()  # Requires helper installed, but doesn't say so

# Good: Clear requirements
from flavor import Packager
packager = Packager()
if not packager.has_helper():
    raise MissingHelperError("Run: make build-helpers")
```

### ❌ **Unsafe Defaults**

```python
# Bad: Insecure by default
packager = Packager(verify_signature=False)  # ❌

# Good: Secure by default
packager = Packager()  # Always verifies
packager = Packager(validation="none")  # Explicit override
```

### ❌ **Platform-Specific Behaviors**

```python
# Bad: Different behavior per platform
if platform == "linux":
    extract_with_tar()
else:
    extract_with_zip()

# Good: Platform-agnostic
extract_slot(slot)  # Same API everywhere
```

## Measuring Success

We evaluate FlavorPack against these principles:

### Developer Experience Metrics
- Time from install to first package: **< 5 minutes**
- Lines of code for basic packaging: **< 10 lines**
- Average error resolution time: **< 1 minute**

### Reliability Metrics
- Cross-language test pass rate: **100%**
- Package signature verification rate: **100%**
- Platform parity test coverage: **100%**

### Performance Metrics
- Package build time: **< 10 seconds** for typical app
- Cache hit rate: **> 95%** for unchanged code
- Extraction time: **< 1 second** from cache

## Evolution of Principles

These principles evolve as we learn:

1. **Original**: "Performance above all"
   **Evolved to**: "Correctness first, then performance"
   **Reason**: Security bugs are worse than slow builds

2. **Original**: "One true way to build packages"
   **Evolved to**: "Sensible defaults, full control when needed"
   **Reason**: Different use cases need different options

3. **Original**: "Python-only implementation"
   **Evolved to**: "Cross-language with Python orchestration"
   **Reason**: Native code is faster and more portable

## Learn More

- **[FlavorPack Architecture](architecture.md)** - How principles are implemented
- **[Contributing](../development/contributing.md)** - Help uphold these principles
- **[Provide Foundry](https://foundry.provide.io)** - Ecosystem-wide principles
