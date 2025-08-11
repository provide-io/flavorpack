# Flavor Runtime Execution Flow

## How a Flavor Package Executes

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Flavor Package File                              │
│                    terraform-provider-example                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          1. Read Footer                               │
│  - Seek to -128 bytes from EOF                                       │
│  - Verify !PSP📦 marker                                              │
│  - Check Flavor version and magic                                      │
│  - Extract section offsets                                           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       2. Verify Signature                             │
│  - Read public key from public_key section                           │
│  - Read signature from signature section                             │
│  - Verify all content up to signature offset                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    3. Extract to Cache Directory                      │
│                                                                       │
│  Cache Location: ~/.cache/flavor/[package-hash]/                       │
│  ├── uv                    (if flags & 0x01, decompress first)      │
│  ├── python/               (extract python.tar.gz)                   │
│  ├── metadata/             (extract metadata.tar.gz)                 │
│  └── payload/              (extract payload.tar.gz)                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    4. Read Runtime Configuration                      │
│                                                                       │
│  metadata/runtime.json:                                               │
│  {                                                                    │
│    "entry_point": "example_provider.main:serve",                     │
│    "environment": {                                                   │
│      "PYTHONPATH": "./payload/site-packages",                        │
│      "GRPC_VERBOSITY": "ERROR"                                       │
│    }                                                                  │
│  }                                                                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      5. Launch Python Process                         │
│                                                                       │
│  Command:                                                             │
│  ./python/bin/python3.13 \                                           │
│    -c "import sys; sys.path.insert(0, './payload/site-packages'); \  │
│        from example_provider.main import serve; serve()"             │
│                                                                       │
│  Environment:                                                         │
│  - PYTHONPATH=./payload/site-packages                                │
│  - TF_PLUGIN_MAGIC_COOKIE=...                                        │
│  - PLUGIN_PROTOCOL_VERSIONS=6                                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    6. Provider Serves gRPC                            │
│  - Terraform communicates via gRPC                                   │
│  - Provider handles GetProviderSchema, ValidateConfig, etc.          │
│  - All file access restricted to cache directory                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Directory Structure After Extraction

```
~/.cache/flavor/abc123def456/         # Hash of package for uniqueness
├── uv*                             # Package manager (executable)
├── python/                         # Python runtime
│   ├── bin/
│   │   ├── python3.13*
│   │   └── pip*
│   └── lib/
│       └── python3.13/
├── metadata/                       # Package metadata
│   ├── flavor.json                  # Format metadata
│   ├── package.json               # Package info
│   ├── runtime.json               # Runtime config
│   ├── dependencies.json          # Dependency manifest
│   └── checksums.json             # Integrity checks
└── payload/                        # Provider code
    ├── site-packages/              # All Python packages
    │   ├── example_provider/
    │   ├── pyvider/
    │   └── [dependencies]/
    ├── data/                       # Provider data
    └── bin/                        # Scripts

Permissions:
- Directories: 0o700 (rwx------)
- Files: 0o600 (rw-------)
- Executables: 0o700 (rwx------)
```

## Metadata Usage During Runtime

### flavor.json - Format & Platform Info
```json
{
  "format_version": "0.2",
  "created_at": "2024-01-20T10:30:00Z",
  "created_by": "flavor v0.1.0",
  "platform": "darwin_arm64",
  "python_version": "3.13.0",
  "flags_interpretation": {
    "uv_compressed": true,
    "python_included": true,
    "archive_format": "tar.gz"
  }
}
```

### package.json - What's in the Package
```json
{
  "name": "terraform-provider-example",
  "version": "1.0.0",
  "description": "Example provider for demo",
  "author": "Example Corp",
  "license": "MIT",
  "terraform": {
    "protocol_version": 6,
    "provider_name": "example"
  }
}
```

### runtime.json - How to Run It
```json
{
  "entry_point": "example_provider.main:serve",
  "working_dir": ".",
  "python_args": ["-u", "-W", "ignore"],
  "environment": {
    "PYTHONPATH": "./payload/site-packages",
    "PYTHONDONTWRITEBYTECODE": "1",
    "GRPC_VERBOSITY": "ERROR"
  },
  "capabilities": ["network", "filesystem"],
  "timeout_seconds": 300
}
```

### dependencies.json - What's Required
```json
{
  "direct": [
    "pyvider>=0.7.0",
    "structlog>=25.0.0"
  ],
  "resolved": {
    "pyvider": {
      "version": "0.7.11",
      "hash": "sha256:abc123..."
    },
    "structlog": {
      "version": "25.4.0", 
      "hash": "sha256:def456..."
    }
  },
  "python_requires": ">=3.9",
  "platform_tags": ["py3-none-any"]
}
```

## Benefits of This Structure

1. **Self-Contained**: Everything needed in one file
2. **Cacheable**: Extract once, run many times
3. **Verifiable**: Signatures and checksums ensure integrity
4. **Debuggable**: Clear metadata about contents
5. **Portable**: Platform info included
6. **Secure**: Restricted permissions and capabilities