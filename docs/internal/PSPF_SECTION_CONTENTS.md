# Flavor Section Contents & Structure

## Section Details

### 1. UV Binary Section
**Purpose**: Package manager for Python dependencies
**Format**: Native binary (optional zstd compression)
**Contents**:
```
- uv executable binary
- Platform-specific (darwin/linux/windows)
- Can be omitted if system uv is available
```

### 2. Python Section
**Purpose**: Complete Python runtime
**Format**: tar.gz archive
**Current Contents**:
```
python/
├── bin/
│   ├── python3.13
│   └── pip
├── lib/
│   └── python3.13/
│       ├── site-packages/
│       └── [standard library]
└── include/
```

**Proposed Improvement**: Could be omitted if target has Python, use flag bit 1

### 3. Metadata Section
**Purpose**: Package information and configuration
**Format**: tar.gz archive
**Current Contents**:
```
metadata/
├── provider_manifest.json
│   {
│     "name": "terraform-provider-example",
│     "version": "1.0.0",
│     "entry_point": "example_provider.main:serve",
│     "python_version": "3.13"
│   }
└── config.json
    {
      "entry_point": "example_provider.main:serve",
      "provider_name": "example"
    }
```

**Proposed Metadata Structure**:
```
metadata/
├── flavor.json           # Flavor package metadata
│   {
│     "format_version": "0.2",
│     "created_at": "2024-01-20T10:30:00Z",
│     "created_by": "flavor v0.1.0",
│     "platform": "darwin_arm64",
│     "python_version": "3.13.0"
│   }
├── package.json        # Package-specific metadata
│   {
│     "name": "terraform-provider-example",
│     "version": "1.0.0",
│     "description": "Example Terraform provider",
│     "author": "Example Corp",
│     "license": "MIT",
│     "homepage": "https://example.com"
│   }
├── runtime.json        # Runtime configuration
│   {
│     "entry_point": "example_provider.main:serve",
│     "environment": {
│       "PYTHONPATH": "/cache/lib/python3.13/site-packages",
│       "PROVIDER_MODE": "production"
│     },
│     "args": ["--grpc"]
│   }
├── dependencies.json   # Dependency manifest
│   {
│     "direct": [
│       "pyvider>=0.7.0",
│       "structlog>=25.0.0"
│     ],
│     "resolved": {
│       "pyvider": "0.7.11",
│       "structlog": "25.4.0",
│       "attrs": "25.3.0"
│     }
│   }
└── checksums.json      # Component checksums
    {
      "python.tar.gz": "sha256:abc123...",
      "payload.tar.gz": "sha256:def456...",
      "uv": "sha256:789012..."
    }
```

### 4. Payload Section
**Purpose**: Actual provider code and dependencies
**Format**: tar.gz archive
**Current Contents**:
```
cache/                          # Virtual environment root
├── bin/
│   └── python -> python3.13
├── lib/
│   └── python3.13/
│       └── site-packages/      # All installed packages
│           ├── pyvider/
│           ├── example_provider/
│           ├── structlog/
│           └── [all dependencies]
└── metadata/                   # Duplicated from metadata section
    ├── provider_manifest.json
    └── config.json
```

**Proposed Payload Structure**:
```
payload/                        # Cleaner structure
├── site-packages/              # Python packages only
│   ├── example_provider/       # Provider code
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── resources/
│   ├── pyvider/               # Framework
│   └── [dependencies]/        # All deps
├── data/                      # Provider data files
│   ├── schemas/
│   └── templates/
└── bin/                       # Scripts/executables
    └── provider-entry
```

### 5. Signature Section
**Purpose**: Cryptographic signature of all previous sections
**Format**: Raw binary
**Contents**:
```
- ECDSA signature (P-256)
- Signs bytes from offset 0 to end of payload
- Verifiable with included public key
```

### 6. Public Key Section
**Purpose**: Key for signature verification
**Format**: PEM encoded text
**Contents**:
```
-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
-----END PUBLIC KEY-----
```

## Improved Metadata Schema

```python
@dataclass
class PSPFMetadata:
    """Core Flavor metadata (flavor.json)"""
    format_version: str = "0.2"
    created_at: datetime
    created_by: str  # Tool name/version
    platform: str    # Target platform
    python_version: str
    
@dataclass
class PackageMetadata:
    """Package information (package.json)"""
    name: str
    version: str
    description: str
    author: str
    license: str
    homepage: Optional[str]
    repository: Optional[str]
    
@dataclass
class RuntimeConfig:
    """Runtime configuration (runtime.json)"""
    entry_point: str
    working_dir: str = "/cache"
    environment: Dict[str, str]
    args: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
```

## Benefits of Structured Metadata

1. **Separation of Concerns**
   - Flavor format metadata
   - Package information  
   - Runtime configuration
   - Dependency tracking

2. **Extensibility**
   - Add new metadata files without changing format
   - JSON allows schema evolution

3. **Debugging**
   - Clear dependency resolution
   - Checksums for integrity
   - Creation timestamp and tool info

4. **Platform Support**
   - Platform-specific metadata
   - Multi-platform packages possible

5. **Security**
   - Capability declarations
   - Environment restrictions
   - Checksum verification