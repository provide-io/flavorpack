# Slots Specification

The PSPF slot system provides flexible data organization within packages.

## Overview

Slots are numbered data containers within a PSPF package. Each slot contains compressed archive data and associated metadata that describes its purpose, lifecycle, and access patterns.

```
Package Structure:
├── Launcher (native executable)
├── Index Block (8192 bytes)
├── Metadata Section (gzipped JSON)
├── Slot Table (array of SlotDescriptor)
└── Data Slots (compressed archives)
    ├── Slot 0: metadata.json
    ├── Slot 1: python-runtime.tar.gz
    ├── Slot 2: application-code.tar.gz
    └── Slot N: additional-data.tar.gz
```

## Slot Descriptor Format

Each slot is described by a fixed-size descriptor:

```c
struct SlotDescriptor {
    uint32_t slot_id;         // Unique slot identifier
    uint64_t offset;          // Byte offset from file start
    uint64_t compressed_size; // Size of compressed data
    uint64_t uncompressed_size; // Size after decompression
    uint8_t  hash[32];        // SHA-256 of uncompressed data
    uint8_t  compression;     // Compression method
    uint8_t  purpose;         // Slot purpose code
    uint8_t  reserved[6];     // Reserved for future use
};
```

## Compression Methods

| ID | Method | Description | Use Case |
|----|--------|-------------|----------|
| 0  | None   | Raw data | Small config files |
| 1  | Gzip   | Standard compression | General purpose |
| 2  | Brotli | High compression | Large text data |
| 3  | Zstd   | Fast compression | Runtime data |

## Purpose Codes

Slots are categorized by purpose to optimize handling:

| Code | Purpose | Description | Lifecycle |
|------|---------|-------------|-----------|
| 0    | metadata | Package metadata | Eager |
| 1    | runtime | Python environment | Eager |
| 2    | application | App code and assets | Lazy |
| 3    | configuration | Config files | Persistent |
| 4    | data | Large datasets | Lazy |
| 5    | cache | Shared resources | Cached |
| 6    | temporary | Temp files | Temporary |

## Lifecycle Management

Slots have different extraction and caching behaviors:

### Eager (Immediate Extraction)
- Extracted when package starts
- Critical for package execution
- Usually small, essential files

```json
{
  "slot_id": 0,
  "purpose": "metadata",
  "lifecycle": "eager",
  "extract_to": "workenv/metadata/"
}
```

### Lazy (On-Demand Extraction)
- Extracted when first accessed
- Large or optional data
- Improves startup performance

```json
{
  "slot_id": 2,
  "purpose": "data",
  "lifecycle": "lazy",
  "extract_to": "workenv/data/"
}
```

### Persistent (Cached Across Runs)
- Extracted once, reused
- Configuration and shared data
- Survives package restarts

```json
{
  "slot_id": 3,
  "purpose": "configuration",
  "lifecycle": "persistent",
  "cache_key": "config-v1.0.0"
}
```

### Temporary (Per-Execution)
- Extracted for each run
- Cleaned up on exit
- Temporary working files

```json
{
  "slot_id": 6,
  "purpose": "temporary",
  "lifecycle": "temporary",
  "cleanup": true
}
```

### Cached (Shared Cache)
- Shared across multiple packages
- Content-addressed storage
- Deduplicated resources

```json
{
  "slot_id": 5,
  "purpose": "cache",
  "lifecycle": "cached",
  "cache_strategy": "content_hash"
}
```

## Slot Naming Conventions

Slots should follow consistent naming patterns:

### Runtime Slots (0-9)
- `metadata.json` - Package metadata
- `python-env.tar.gz` - Python virtual environment
- `launcher-config.json` - Launcher configuration

### Application Slots (10-99)
- `app-code.tar.gz` - Application source code
- `app-assets.tar.gz` - Static assets
- `app-config.json` - Application configuration

### Data Slots (100+)
- `dataset-large.tar.gz` - Large datasets
- `models-ml.tar.gz` - Machine learning models
- `resources-extra.tar.gz` - Optional resources

## Slot Metadata

Each slot can include additional metadata in the package metadata section:

```json
{
  "slots": [
    {
      "id": 0,
      "name": "metadata.json",
      "purpose": "metadata",
      "lifecycle": "eager",
      "compression": "none",
      "size": 1024,
      "description": "Package metadata and manifest",
      "dependencies": [],
      "optional": false
    },
    {
      "id": 1,
      "name": "python-runtime.tar.gz",
      "purpose": "runtime",
      "lifecycle": "eager",
      "compression": "gzip",
      "size": 45000000,
      "description": "Python 3.11 virtual environment",
      "dependencies": [],
      "optional": false
    },
    {
      "id": 2,
      "name": "application.tar.gz",
      "purpose": "application",
      "lifecycle": "lazy",
      "compression": "gzip",
      "size": 5000000,
      "description": "Application source code",
      "dependencies": [0, 1],
      "optional": false
    }
  ]
}
```

## Slot Dependencies

Slots can declare dependencies on other slots:

```json
{
  "id": 2,
  "dependencies": [0, 1],
  "dependency_strategy": "eager"
}
```

### Dependency Strategies
- **eager**: Extract dependencies immediately
- **lazy**: Extract dependencies when needed
- **optional**: Dependencies are optional

## Slot Validation

Slots are validated during extraction:

1. **Hash Verification**: SHA-256 of uncompressed data
2. **Size Validation**: Compressed and uncompressed sizes
3. **Compression Check**: Verify compression method
4. **Dependency Resolution**: Ensure dependencies are available

## Advanced Features

### Slot Streaming
Large slots can be streamed during extraction:

```json
{
  "id": 100,
  "streaming": true,
  "chunk_size": 1048576,
  "parallel_extraction": true
}
```

### Slot Deduplication
Identical slots across packages can be deduplicated:

```json
{
  "id": 1,
  "content_hash": "sha256:abc123...",
  "deduplication": "content_hash"
}
```

### Slot Encryption
Sensitive slots can be encrypted:

```json
{
  "id": 3,
  "encryption": "aes256-gcm",
  "key_derivation": "pbkdf2"
}
```

## Performance Considerations

### Compression Trade-offs
- **None**: Fastest access, largest size
- **Gzip**: Good balance of speed and size
- **Brotli**: Best compression, slower extraction
- **Zstd**: Fast compression and decompression

### Access Patterns
- **Sequential**: Extract slots in order
- **Random**: Extract specific slots only
- **Parallel**: Extract multiple slots simultaneously

### Caching Strategies
- **Memory**: Keep decompressed data in RAM
- **Disk**: Cache extracted files on disk
- **Hybrid**: Combination of memory and disk caching

## Examples

### Basic Package Structure
```json
{
  "slots": [
    {
      "id": 0,
      "name": "metadata.json",
      "purpose": "metadata",
      "lifecycle": "eager"
    },
    {
      "id": 1,
      "name": "python-env.tar.gz",
      "purpose": "runtime",
      "lifecycle": "eager"
    },
    {
      "id": 2,
      "name": "myapp.tar.gz",
      "purpose": "application",
      "lifecycle": "lazy"
    }
  ]
}
```

### Data Science Package
```json
{
  "slots": [
    {
      "id": 0,
      "name": "metadata.json",
      "purpose": "metadata",
      "lifecycle": "eager"
    },
    {
      "id": 1,
      "name": "python-ml-env.tar.gz",
      "purpose": "runtime",
      "lifecycle": "eager"
    },
    {
      "id": 2,
      "name": "notebook.tar.gz",
      "purpose": "application",
      "lifecycle": "lazy"
    },
    {
      "id": 100,
      "name": "dataset-large.tar.gz",
      "purpose": "data",
      "lifecycle": "lazy",
      "optional": true
    },
    {
      "id": 101,
      "name": "trained-models.tar.gz",
      "purpose": "data",
      "lifecycle": "cached"
    }
  ]
}
```

## Error Handling

Common slot-related errors:

- **Slot not found**: Invalid slot ID referenced
- **Hash mismatch**: Data corruption detected
- **Compression error**: Invalid compressed data
- **Dependency missing**: Required slot unavailable
- **Extraction failed**: Insufficient disk space or permissions

## Related Documentation

- [Binary Layout](binary-layout.md) - Overall package structure
- [Metadata Format](metadata.md) - Package metadata specification
- [Work Environments](../guide/concepts/workenv.md) - Extraction and caching