# PSPFBuilder API

Low-level API for building Progressive Secure Package Format (PSPF) packages.

::: flavor.psp.format_2025.builder

## Core Function

### `build_package`

Pure function to build a PSPF package from a complete specification.

```python
def build_package(spec: BuildSpec, output_path: Path) -> BuildResult
```

#### Parameters

- **spec** (`BuildSpec`): Complete build specification including metadata, slots, and keys
- **output_path** (`Path`): Path where the package should be written

#### Returns

`BuildResult`: Result object containing:
- **success** (`bool`): Whether build succeeded
- **errors** (`list[str]`): List of error messages if failed
- **warnings** (`list[str]`): List of warning messages
- **package_size** (`int`): Size of created package in bytes
- **duration** (`float`): Build duration in seconds

#### Example

```python
from pathlib import Path
from flavor.psp.format_2025.builder import build_package
from flavor.psp.format_2025.spec import BuildSpec, SlotSpec, KeyConfig

spec = BuildSpec(
    metadata={
        "name": "myapp",
        "version": "1.0.0",
        "author": "Your Name"
    },
    slots=[
        SlotSpec(
            id="python-runtime",
            source=Path("runtime/"),
            lifecycle="eager",
            codec="tgz"
        ),
        SlotSpec(
            id="application",
            source=Path("app/"),
            lifecycle="lazy"
        )
    ],
    keys=KeyConfig(seed="deterministic-seed"),
    options=BuildOptions(compress=True, strip=True)
)

result = build_package(spec, Path("output.psp"))
if result.success:
    print(f"Package built: {result.package_size} bytes")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

## PSPFBuilder Class

### Overview

The `PSPFBuilder` class provides a fluent interface for incrementally building package specifications.

```python
from flavor.psp.format_2025.pspf_builder import PSPFBuilder

class PSPFBuilder:
    def __init__(self)
    def set_metadata(self, metadata: dict) -> PSPFBuilder
    def add_slot(self, slot: SlotSpec) -> PSPFBuilder
    def set_keys(self, keys: KeyConfig) -> PSPFBuilder
    def set_options(self, options: BuildOptions) -> PSPFBuilder
    def build_spec(self) -> BuildSpec
    def build(self, output_path: Path) -> BuildResult
```

### Methods

#### `__init__()`

Initialize a new builder instance.

```python
builder = PSPFBuilder()
```

#### `set_metadata(metadata: dict) -> PSPFBuilder`

Set package metadata.

##### Parameters

- **metadata** (`dict`): Package metadata dictionary

##### Required Keys

- **name** (`str`): Package name
- **version** (`str`): Package version

##### Optional Keys

- **author** (`str`): Package author
- **description** (`str`): Package description
- **homepage** (`str`): Project homepage URL
- **license** (`str`): License identifier
- **platform** (`str`): Target platform

##### Example

```python
builder.set_metadata({
    "name": "myapp",
    "version": "2.0.0",
    "author": "Jane Doe",
    "description": "My awesome application",
    "homepage": "https://example.com",
    "license": "MIT"
})
```

#### `add_slot(slot: SlotSpec) -> PSPFBuilder`

Add a data slot to the package.

##### Parameters

- **slot** (`SlotSpec`): Slot specification

##### Example

```python
from flavor.psp.format_2025.spec import SlotSpec

builder.add_slot(SlotSpec(
    id="data",
    source=Path("data/"),
    codec="tgz",
    lifecycle="persistent",
    purpose="data-files"
))
```

#### `set_keys(keys: KeyConfig) -> PSPFBuilder`

Set key configuration for package signing.

##### Parameters

- **keys** (`KeyConfig`): Key configuration

##### Example

```python
from flavor.psp.format_2025.spec import KeyConfig

# With explicit keys
builder.set_keys(KeyConfig(
    private_key=Path("private.pem"),
    public_key=Path("public.pem")
))

# With deterministic seed
builder.set_keys(KeyConfig(
    seed="my-deterministic-seed"
))
```

#### `set_options(options: BuildOptions) -> PSPFBuilder`

Set build options.

##### Parameters

- **options** (`BuildOptions`): Build configuration options

##### Example

```python
from flavor.psp.format_2025.spec import BuildOptions

builder.set_options(BuildOptions(
    compress=True,
    strip=True,
    deterministic=True,
    page_aligned=True
))
```

#### `build_spec() -> BuildSpec`

Build and return the complete specification.

##### Returns

`BuildSpec`: Complete build specification

##### Raises

- **ValidationError**: If specification is incomplete or invalid

##### Example

```python
spec = builder.build_spec()
# Use spec with build_package() function
```

#### `build(output_path: Path) -> BuildResult`

Build the package directly using the current specification.

##### Parameters

- **output_path** (`Path`): Output path for the package

##### Returns

`BuildResult`: Build result with success status and any errors

##### Example

```python
result = builder.build(Path("myapp.psp"))
if result.success:
    print(f"Package created: {output_path}")
```

### Complete Example

```python
from pathlib import Path
from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.spec import SlotSpec, KeyConfig, BuildOptions

# Create builder
builder = PSPFBuilder()

# Configure package
(builder
    .set_metadata({
        "name": "example-app",
        "version": "1.2.3",
        "author": "Developer",
        "description": "Example application"
    })
    .add_slot(SlotSpec(
        id="runtime",
        source=Path("runtime/"),
        codec="tgz",
        lifecycle="eager"
    ))
    .add_slot(SlotSpec(
        id="app",
        source=Path("src/"),
        lifecycle="lazy"
    ))
    .add_slot(SlotSpec(
        id="config",
        source=Path("config.yaml"),
        lifecycle="persistent",
        purpose="configuration"
    ))
    .set_keys(KeyConfig(seed="build-seed"))
    .set_options(BuildOptions(
        compress=True,
        strip=True
    ))
)

# Build package
result = builder.build(Path("dist/example-app.psp"))

if result.success:
    print(f"✅ Package built successfully")
    print(f"   Size: {result.package_size / 1024 / 1024:.2f} MB")
    print(f"   Time: {result.duration:.2f} seconds")
else:
    print("❌ Build failed:")
    for error in result.errors:
        print(f"   - {error}")
```

## Data Classes

### BuildSpec

Complete specification for building a package.

```python
@attrs.define(frozen=True)
class BuildSpec:
    metadata: dict[str, Any]
    slots: list[SlotSpec]
    keys: KeyConfig | None = None
    options: BuildOptions = BuildOptions()
```

### SlotSpec

Specification for a package slot.

```python
@attrs.define(frozen=True)
class SlotSpec:
    id: str                    # Unique slot identifier
    source: Path               # Source file or directory
    lifecycle: str = "eager"   # Loading lifecycle
    codec: str = "raw"         # Compression codec
    purpose: str = "data"      # Slot purpose
    platform: str | None = None  # Platform-specific
```

#### Lifecycle Values

| Value | Description | Use Case |
|-------|-------------|----------|
| `eager` | Load immediately on startup | Critical components |
| `lazy` | Load on first access | Large optional data |
| `persistent` | Keep in cache between runs | Configuration |
| `temporary` | Extract fresh each run | Temporary files |
| `cached` | Shared between versions | Common resources |
| `init` | Load during initialization | Setup data |
| `shutdown` | Load during shutdown | Cleanup data |

#### Codec Values

| Value | Description | Compression |
|-------|-------------|-------------|
| `raw` | No compression | None |
| `gzip` | GZIP compression | Single file |
| `tar` | TAR archive | Multiple files |
| `tgz` | TAR + GZIP | Multiple files + compression |

### KeyConfig

Configuration for package signing keys.

```python
@attrs.define(frozen=True)
class KeyConfig:
    private_key: Path | None = None  # Path to private key
    public_key: Path | None = None   # Path to public key
    seed: str | None = None          # Deterministic seed
```

### BuildOptions

Build configuration options.

```python
@attrs.define(frozen=True)
class BuildOptions:
    compress: bool = False      # Enable compression
    strip: bool = False         # Strip debug symbols
    deterministic: bool = False # Deterministic build
    page_aligned: bool = False  # Page-align slots
    max_slot_size: int = 100 * 1024 * 1024  # 100MB
```

### BuildResult

Result of a build operation.

```python
@attrs.define(frozen=True)
class BuildResult:
    success: bool
    errors: list[str] = []
    warnings: list[str] = []
    package_size: int = 0
    duration: float = 0.0
```

## Helper Functions

### `prepare_slots`

Prepare slots for packaging by compressing and calculating checksums.

```python
def prepare_slots(
    slots: list[SlotSpec],
    options: BuildOptions
) -> list[PreparedSlot]
```

#### Parameters

- **slots** (`list[SlotSpec]`): List of slot specifications
- **options** (`BuildOptions`): Build options

#### Returns

`list[PreparedSlot]`: List of prepared slots with data and checksums

#### Example

```python
from flavor.psp.format_2025.builder import prepare_slots

prepared = prepare_slots(spec.slots, spec.options)
for slot in prepared:
    print(f"Slot {slot.id}: {slot.size} bytes, checksum: {slot.checksum}")
```

## Constants

The builder module uses constants from `flavor.psp.format_2025.constants`:

```python
# Format version
FORMAT_VERSION = 0x20250001

# Size limits
MAX_METADATA_SIZE = 1024 * 1024  # 1MB
MAX_SLOT_SIZE = 100 * 1024 * 1024  # 100MB
SLOT_ALIGNMENT = 4096  # 4KB page alignment

# Magic bytes
PACKAGE_EMOJI_BYTES = b'\xf0\x9f\x93\xa6'  # 📦
MAGIC_WAND_EMOJI_BYTES = b'\xf0\x9f\xaa\x84'  # 🪄
```

## Error Handling

The builder performs extensive validation and may raise:

- **ValidationError**: Invalid specification or metadata
- **BuildError**: Build process failed
- **CryptoError**: Key or signing error
- **IOError**: File system errors

```python
from flavor.exceptions import ValidationError, BuildError

try:
    result = build_package(spec, output_path)
except ValidationError as e:
    print(f"Invalid specification: {e}")
except BuildError as e:
    print(f"Build failed: {e}")
```

## Best Practices

### 1. Validate Early

```python
def validate_spec(spec: BuildSpec) -> list[str]:
    """Validate specification before building."""
    errors = []
    
    if not spec.metadata.get("name"):
        errors.append("Missing package name")
    if not spec.metadata.get("version"):
        errors.append("Missing package version")
    if not spec.slots:
        errors.append("No slots defined")
    
    return errors

# Check before building
errors = validate_spec(spec)
if errors:
    raise ValidationError(f"Invalid spec: {errors}")
```

### 2. Use Deterministic Builds

```python
# For reproducible builds
builder.set_keys(KeyConfig(seed="stable-seed"))
builder.set_options(BuildOptions(deterministic=True))
```

### 3. Optimize Slot Configuration

```python
# Large data: use lazy loading and compression
builder.add_slot(SlotSpec(
    id="large-data",
    source=Path("data/"),
    lifecycle="lazy",
    codec="tgz"
))

# Small config: eager loading, no compression
builder.add_slot(SlotSpec(
    id="config",
    source=Path("config.yaml"),
    lifecycle="eager",
    codec="raw"
))
```

### 4. Handle Platform-Specific Slots

```python
from flavor.utils.platform import get_current_platform

platform = get_current_platform()

builder.add_slot(SlotSpec(
    id=f"binary-{platform}",
    source=Path(f"bin/{platform}/"),
    platform=platform,
    lifecycle="eager"
))
```

## Performance Considerations

- **Compression**: Reduces package size but increases build time
- **Page alignment**: Improves runtime performance but increases size
- **Slot size**: Keep individual slots under 100MB for optimal performance
- **Parallel compression**: Slots are compressed in parallel when possible

## Thread Safety

The `PSPFBuilder` class is not thread-safe. Create separate instances for concurrent builds:

```python
import concurrent.futures

def build_variant(variant: str) -> Path:
    builder = PSPFBuilder()
    # Configure for variant...
    return builder.build(Path(f"{variant}.psp"))

with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(build_variant, v) for v in ["lite", "full", "pro"]]
    results = [f.result() for f in futures]
```

## Related Documentation

- [PSPFReader](reader.md) - Reading and extracting packages
- [Slot Management](slots.md) - Detailed slot documentation
- [Metadata](metadata.md) - Metadata assembly and validation
- [Format Specification](../../../spec/pspf-2025.md) - PSPF format details
- [Core API](../index.md) - High-level API functions