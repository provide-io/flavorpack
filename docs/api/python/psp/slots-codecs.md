# Slot Compression Codecs

Compression methods for optimizing slot data in PSPF packages.

## Overview

Codecs determine how slot data is compressed, affecting package size, extraction speed, and memory usage.

## Available Codecs

| Codec | Description | Compression | Best For |
|-------|-------------|-------------|----------|
| `raw` | No compression | None | Small files, pre-compressed data |
| `gzip` | GZIP compression | Single file | Text files, logs |
| `tar` | TAR archive | None (archive only) | Multiple files without compression |
| `tgz` | TAR + GZIP | Archive + compression | Directories, source code |
| `zstd` | Zstandard compression | High ratio | Large binary data |
| `lz4` | LZ4 compression | Fast | Real-time data |

## Codec Constants

```python
from flavor.psp.format_2025.constants import (
    CODEC_RAW,   # = "raw"
    CODEC_GZIP,  # = "gzip"
    CODEC_TAR,   # = "tar"
    CODEC_TGZ,   # = "tgz"
    CODEC_ZSTD,  # = "zstd"
    CODEC_LZ4,   # = "lz4"
)
```

## Raw Codec

No compression applied. Best for already compressed data or small files.

### Use Cases
- Pre-compressed files (images, videos, archives)
- Small configuration files
- Binary executables
- Encrypted data

### Example

```python
from flavor.psp.format_2025.spec import SlotSpec
from flavor.psp.format_2025.constants import CODEC_RAW

SlotSpec(
    id="videos",
    source=Path("videos/"),
    codec=CODEC_RAW  # Already compressed
)
```

### Performance
- **Compression Speed**: Instant (no compression)
- **Decompression Speed**: Instant
- **Compression Ratio**: 0% (no reduction)

## GZIP Codec

Standard GZIP compression for single files.

### Use Cases
- Text files
- Log files
- JSON/XML data
- Source code files

### Example

```python
SlotSpec(
    id="documentation",
    source=Path("docs/README.md"),
    codec=CODEC_GZIP
)
```

### Performance
- **Compression Speed**: Moderate
- **Decompression Speed**: Fast
- **Compression Ratio**: 60-80% for text

## TAR Codec

TAR archive without compression. Bundles multiple files.

### Use Cases
- Grouping files without compression
- Preserving file permissions
- Already compressed file collections

### Example

```python
SlotSpec(
    id="binaries",
    source=Path("bin/"),
    codec=CODEC_TAR  # Archive only
)
```

### Performance
- **Archive Speed**: Fast
- **Extract Speed**: Fast
- **Size Reduction**: None (archive overhead)

## TGZ Codec (TAR + GZIP)

TAR archive with GZIP compression. Best for directories.

### Use Cases
- Source code directories
- Documentation trees
- Configuration directories
- Python packages

### Example

```python
SlotSpec(
    id="source",
    source=Path("src/"),
    codec=CODEC_TGZ  # Archive and compress
)
```

### Performance
- **Compression Speed**: Moderate
- **Decompression Speed**: Moderate
- **Compression Ratio**: 70-85% for mixed content

## Zstandard (ZSTD) Codec

Modern compression with excellent ratio and speed.

### Use Cases
- Large binary data
- Database files
- Virtual environments
- Game assets

### Example

```python
SlotSpec(
    id="assets",
    source=Path("assets/"),
    codec=CODEC_ZSTD  # High compression
)
```

### Performance
- **Compression Speed**: Fast
- **Decompression Speed**: Very fast
- **Compression Ratio**: 75-90% depending on data

## LZ4 Codec

Ultra-fast compression with moderate ratio.

### Use Cases
- Real-time data
- Frequently accessed files
- Stream processing
- Cache data

### Example

```python
SlotSpec(
    id="stream-data",
    source=Path("data/"),
    codec=CODEC_LZ4  # Fast access
)
```

### Performance
- **Compression Speed**: Very fast
- **Decompression Speed**: Ultra-fast
- **Compression Ratio**: 40-60%

## Codec Selection Guide

### By File Type

```python
def select_codec_by_type(file_type: str) -> str:
    """Select codec based on file type."""
    
    codec_map = {
        # Text files
        "text": CODEC_GZIP,
        "source": CODEC_TGZ,
        "docs": CODEC_GZIP,
        
        # Binary files
        "binary": CODEC_ZSTD,
        "executable": CODEC_RAW,
        
        # Media files
        "images": CODEC_RAW,  # Already compressed
        "video": CODEC_RAW,   # Already compressed
        "audio": CODEC_RAW,   # Already compressed
        
        # Data files
        "database": CODEC_ZSTD,
        "cache": CODEC_LZ4,
        "logs": CODEC_GZIP,
        
        # Archives
        "directory": CODEC_TGZ,
        "package": CODEC_TGZ
    }
    
    return codec_map.get(file_type, CODEC_TGZ)
```

### By Size

```python
def select_codec_by_size(size_bytes: int) -> str:
    """Select codec based on data size."""
    
    MB = 1024 * 1024
    
    if size_bytes < 1 * MB:
        return CODEC_RAW  # Small files
    elif size_bytes < 10 * MB:
        return CODEC_GZIP  # Medium files
    elif size_bytes < 100 * MB:
        return CODEC_TGZ  # Large directories
    else:
        return CODEC_ZSTD  # Very large data
```

### By Performance Priority

```python
def select_codec_by_priority(priority: str) -> str:
    """Select codec based on priority."""
    
    if priority == "size":
        return CODEC_ZSTD  # Best compression
    elif priority == "speed":
        return CODEC_LZ4  # Fastest
    elif priority == "compatibility":
        return CODEC_GZIP  # Most compatible
    else:
        return CODEC_TGZ  # Balanced
```

## Compression Utilities

### Compress Data

```python
def compress_data(data: bytes, codec: str) -> bytes:
    """Compress data using specified codec."""
    
    if codec == CODEC_RAW:
        return data
    elif codec == CODEC_GZIP:
        import gzip
        return gzip.compress(data)
    elif codec == CODEC_ZSTD:
        import zstandard
        compressor = zstandard.ZstdCompressor()
        return compressor.compress(data)
    elif codec == CODEC_LZ4:
        import lz4.frame
        return lz4.frame.compress(data)
    # ... handle other codecs
```

### Decompress Data

```python
def decompress_data(data: bytes, codec: str) -> bytes:
    """Decompress data using specified codec."""
    
    if codec == CODEC_RAW:
        return data
    elif codec == CODEC_GZIP:
        import gzip
        return gzip.decompress(data)
    elif codec == CODEC_ZSTD:
        import zstandard
        decompressor = zstandard.ZstdDecompressor()
        return decompressor.decompress(data)
    elif codec == CODEC_LZ4:
        import lz4.frame
        return lz4.frame.decompress(data)
    # ... handle other codecs
```

## Compression Levels

### Configuring Compression Level

```python
def compress_with_level(
    data: bytes,
    codec: str,
    level: int = 6
) -> bytes:
    """Compress with specific level (1-9)."""
    
    if codec == CODEC_GZIP:
        import gzip
        return gzip.compress(data, compresslevel=level)
    elif codec == CODEC_ZSTD:
        import zstandard
        compressor = zstandard.ZstdCompressor(level=level)
        return compressor.compress(data)
    # ... handle other codecs
```

### Level Guidelines

| Level | Speed | Ratio | Use Case |
|-------|-------|-------|----------|
| 1-3 | Fast | Low | Real-time, streaming |
| 4-6 | Moderate | Medium | Default, balanced |
| 7-9 | Slow | High | Archival, distribution |

## Benchmarks

### Compression Ratio Comparison

```python
# Typical compression ratios for 10MB of source code
benchmarks = {
    "raw": {"size": 10.0, "ratio": 0},
    "gzip": {"size": 2.5, "ratio": 75},
    "tgz": {"size": 2.3, "ratio": 77},
    "zstd": {"size": 2.0, "ratio": 80},
    "lz4": {"size": 4.0, "ratio": 60}
}
```

### Speed Comparison

```python
# Compression/decompression speed (MB/s)
speed_benchmarks = {
    "raw": {"compress": "∞", "decompress": "∞"},
    "gzip": {"compress": 50, "decompress": 150},
    "tgz": {"compress": 45, "decompress": 140},
    "zstd": {"compress": 350, "decompress": 1000},
    "lz4": {"compress": 500, "decompress": 2000}
}
```

## Advanced Usage

### Multi-Codec Strategy

```python
class MultiCodecStrategy:
    """Use different codecs for different parts."""
    
    def prepare_slots(self, slots: list[SlotSpec]) -> list[SlotSpec]:
        """Optimize codec selection per slot."""
        
        optimized = []
        for slot in slots:
            # Runtime: fast decompression
            if slot.purpose == "runtime":
                slot = attrs.evolve(slot, codec=CODEC_LZ4)
            
            # Data: high compression
            elif slot.purpose == "data":
                slot = attrs.evolve(slot, codec=CODEC_ZSTD)
            
            # Config: standard compression
            elif slot.purpose == "configuration":
                slot = attrs.evolve(slot, codec=CODEC_GZIP)
            
            optimized.append(slot)
        
        return optimized
```

### Adaptive Compression

```python
def adaptive_compress(
    data: bytes,
    target_ratio: float = 0.5
) -> tuple[bytes, str]:
    """Try codecs until target ratio achieved."""
    
    original_size = len(data)
    target_size = original_size * target_ratio
    
    # Try codecs in order of compression ratio
    for codec in [CODEC_ZSTD, CODEC_GZIP, CODEC_LZ4, CODEC_RAW]:
        compressed = compress_data(data, codec)
        if len(compressed) <= target_size:
            return compressed, codec
    
    # Fallback to best compression
    return compress_data(data, CODEC_ZSTD), CODEC_ZSTD
```

## Next Steps

- [Slot Purposes](slots-purposes.md) - Semantic slot types
- [Slot Core API](slots-core.md) - Core classes and functions
- [Slot Lifecycles](slots-lifecycles.md) - Loading behaviors

## Related Documentation

- [Performance Guide](../../../guide/performance.md) - Optimization strategies
- [Compression Guide](../../../guide/compression.md) - Detailed compression guide