# Metadata Structure

The metadata section contains JSON-encoded information about the package, its slots, and execution configuration.

## Overview

Metadata is stored as gzipped JSON at the offset specified in the index block. It provides all necessary information for package execution and slot management.

## Structure

```json
{
  "package": {
    "name": "string",
    "version": "string",
    "description": "string (optional)",
    "author": "string (optional)",
    "license": "string (optional)"
  },
  "slots": [
    {
      "id": "string",
      "purpose": "string",
      "lifecycle": "string",
      "extract_to": "string (optional)",
      "platform": "string (optional)",
      "checksum": "string",
      "size": "number",
      "codec": "string",
      "type": "string (optional)",
      "permissions": "string (optional)"
    }
  ],
  "execution": {
    "command": "string",
    "args": ["string"],
    "env": {"key": "value"},
    "primary_slot": "number",
    "entry_point": "string (optional)"
  },
  "workenv": {
    "directories": [
      {"path": "string", "mode": "string"}
    ],
    "env": {"key": "value"},
    "cache_key": "string (optional)"
  },
  "runtime": {
    "set": {"key": "value"},
    "unset": ["string"],
    "pass": ["string"],
    "map": {"old": "new"}
  },
  "build": {
    "timestamp": "string",
    "builder_version": "string",
    "launcher_type": "string",
    "platform": "string"
  }
}
```

## Field Descriptions

### Package Section

Basic package identification and metadata.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Package name (alphanumeric + hyphens) |
| version | string | Yes | Semantic version (e.g., "1.0.0") |
| description | string | No | Human-readable description |
| author | string | No | Author name or organization |
| license | string | No | SPDX license identifier |

### Slots Array

Describes each slot in the package. Array index corresponds to slot table entry.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | Unique slot identifier |
| purpose | string | Yes | Slot purpose (see below) |
| lifecycle | string | Yes | Slot lifecycle (see below) |
| extract_to | string | No | Custom extraction path |
| platform | string | No | Platform restriction |
| checksum | string | Yes | SHA256 hash of slot data |
| size | number | Yes | Uncompressed size in bytes |
| codec | string | Yes | Compression codec used |
| type | string | No | MIME type or file type |
| permissions | string | No | Unix permissions (e.g., "0755") |

#### Slot Purposes

| Purpose | Description | Example |
|---------|-------------|---------|
| `package-metadata` | Package metadata | metadata.json |
| `python-environment` | Python virtual environment | venv.tar.gz |
| `application-code` | Application source code | app.tar.gz |
| `configuration` | Configuration files | config.json |
| `static-resources` | Static assets | assets.tar.gz |
| `native-binary` | Native executables | bin.tar.gz |
| `data-files` | Data files | data.tar.gz |
| `documentation` | Documentation | docs.tar.gz |

#### Slot Lifecycles

| Lifecycle | Description | Cleanup |
|-----------|-------------|---------|
| `persistent` | Kept for entire execution | Never |
| `volatile` | Deleted after initialization | After setup |
| `temporary` | Deleted after session | On exit |
| `cached` | Can be regenerated | On cache clear |
| `init-only` | First run only | After first run |
| `lazy` | Load on demand | When needed |
| `eager` | Load immediately | At startup |

### Execution Section

Defines how to execute the package.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| command | string | Yes | Command to execute |
| args | array | No | Default command arguments |
| env | object | No | Environment variables to set |
| primary_slot | number | No | Index of primary slot (default: 0) |
| entry_point | string | No | Python entry point (module:function) |

### Workenv Section

Configures the work environment.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| directories | array | No | Directories to create |
| env | object | No | Environment variables |
| cache_key | string | No | Cache key for reuse |

#### Directory Entry

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| path | string | Yes | Relative path to create |
| mode | string | No | Unix permissions (default: "0755") |

### Runtime Section

Runtime environment configuration.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| set | object | No | Variables to set |
| unset | array | No | Variables to unset |
| pass | array | No | Variables to pass through |
| map | object | No | Variable name mappings |

### Build Section

Build-time metadata (automatically generated).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| timestamp | string | Yes | ISO 8601 build timestamp |
| builder_version | string | Yes | Builder version used |
| launcher_type | string | Yes | Launcher type (go/rust) |
| platform | string | Yes | Build platform |

## Compression

The metadata JSON is compressed using gzip with compression level 9 (maximum).

```python
import gzip
import json

# Compress metadata
metadata_json = json.dumps(metadata, separators=(',', ':'))
compressed = gzip.compress(metadata_json.encode('utf-8'), compresslevel=9)

# Decompress metadata
decompressed = gzip.decompress(compressed)
metadata = json.loads(decompressed.decode('utf-8'))
```

## Size Limits

- Maximum uncompressed size: 50 MB
- Maximum compressed size: 10 MB
- Maximum slot count: 1000
- Maximum environment variables: 1000

## Validation Rules

1. **Package name**: Must match `^[a-zA-Z0-9][a-zA-Z0-9-_]*$`
2. **Version**: Should follow semantic versioning
3. **Slot IDs**: Must be unique within package
4. **Checksums**: Must be valid SHA256 hashes
5. **Paths**: Must not contain `..` or absolute paths
6. **Environment keys**: Must be valid shell variable names

## Examples

### Minimal Metadata

```json
{
  "package": {
    "name": "hello-world",
    "version": "1.0.0"
  },
  "slots": [
    {
      "id": "main",
      "purpose": "application-code",
      "lifecycle": "persistent",
      "checksum": "abc123...",
      "size": 1024,
      "codec": "raw"
    }
  ],
  "execution": {
    "command": "python",
    "args": ["hello.py"]
  }
}
```

### Complex Metadata

```json
{
  "package": {
    "name": "web-app",
    "version": "2.1.0",
    "description": "FastAPI web application",
    "author": "Example Corp",
    "license": "MIT"
  },
  "slots": [
    {
      "id": "metadata.json",
      "purpose": "package-metadata",
      "lifecycle": "persistent",
      "checksum": "sha256...",
      "size": 1024,
      "codec": "raw"
    },
    {
      "id": "python-venv",
      "purpose": "python-environment",
      "lifecycle": "persistent",
      "extract_to": "venv",
      "checksum": "sha256...",
      "size": 50000000,
      "codec": "tgz"
    },
    {
      "id": "app-code",
      "purpose": "application-code",
      "lifecycle": "persistent",
      "extract_to": "app",
      "checksum": "sha256...",
      "size": 100000,
      "codec": "tar"
    },
    {
      "id": "static-assets",
      "purpose": "static-resources",
      "lifecycle": "lazy",
      "extract_to": "static",
      "checksum": "sha256...",
      "size": 5000000,
      "codec": "tgz"
    }
  ],
  "execution": {
    "command": "python",
    "args": ["-m", "uvicorn"],
    "env": {
      "PYTHONPATH": "app",
      "PORT": "8000"
    },
    "entry_point": "app.main:app"
  },
  "workenv": {
    "directories": [
      {"path": "logs", "mode": "0755"},
      {"path": "tmp", "mode": "0700"}
    ],
    "env": {
      "TMPDIR": "tmp",
      "LOG_DIR": "logs"
    }
  },
  "runtime": {
    "set": {
      "FLAVOR_APP": "web-app",
      "FLAVOR_VERSION": "2.1.0"
    },
    "pass": ["HOME", "USER", "PATH"],
    "unset": ["DEBUG"]
  },
  "build": {
    "timestamp": "2025-01-15T10:30:00Z",
    "builder_version": "flavor-go-builder-0.3.0",
    "launcher_type": "flavor-rs-launcher",
    "platform": "darwin_arm64"
  }
}
```

## Related Documentation

- [Binary Layout](binary-layout.md)
- [Slot Specifications](slots.md)
- [Package Format](pspf-2025.md)
- [API Reference](../api/index.md)