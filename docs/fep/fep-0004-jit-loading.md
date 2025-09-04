# FEP-0004: Just-In-Time (JIT) Loading and On-Demand Payloads

**Status**: Proposed  
**Type**: Standards Track  
**Created**: 2025-08-28  
**Updated**: 2025-09-02  
**Implementation**: Not Started ❌

## Abstract

This document specifies an optional extension to PSPF/2025 that enables Just-In-Time (JIT) loading of package components and on-demand payload delivery. This allows packages to start faster by deferring extraction of non-critical slots, and enables network-based delivery of package components using modern protocols like gRPC with Protocol Buffers schemas.

## Table of Contents

1. [Introduction](#1-introduction)
2. [JIT Loading Architecture](#2-jit-loading-architecture)
3. [On-Demand Slot Loading](#3-on-demand-slot-loading)
4. [Network Payload Delivery](#4-network-payload-delivery)
5. [Protocol Buffer Integration](#5-protocol-buffer-integration)
6. [Implementation Considerations](#6-implementation-considerations)

## 1. Introduction

### 1.1 Motivation

Large applications face challenges with startup time and distribution:

- **Startup latency**: Extracting all slots before execution is slow
- **Bandwidth waste**: Users may not need all features/assets
- **Storage overhead**: Full extraction requires significant disk space
- **Update efficiency**: Small changes require full re-download

JIT loading addresses these issues by:
- Loading only essential components at startup
- Fetching additional components on-demand
- Supporting network-based component delivery
- Enabling incremental updates

### 1.2 Use Cases

- **Large ML models**: Load models only when needed
- **Multi-language apps**: Load language packs on-demand
- **Plugin systems**: Download plugins when activated
- **Game assets**: Stream levels/textures as needed
- **Documentation**: Fetch help content when accessed

## 2. JIT Loading Architecture

### 2.1 Slot Lifecycle Extensions

Extend the existing lifecycle types with JIT variants:

```python
# Existing lifecycles
LIFECYCLE_RUNTIME = 2      # Extract at startup (current default)
LIFECYCLE_LAZY = 6         # Load on first access (basic JIT)

# New JIT-specific lifecycles
LIFECYCLE_JIT_LOCAL = 11   # JIT from local package
LIFECYCLE_JIT_NETWORK = 12 # JIT from network source
LIFECYCLE_JIT_HYBRID = 13  # Try local, fallback to network
```

### 2.2 Lazy Loading Triggers

```python
class JITLoader:
    """Handles on-demand slot loading."""
    
    def __init__(self, package_path: Path, metadata: dict):
        self.package_path = package_path
        self.metadata = metadata
        self.loaded_slots = set()
        self.slot_locks = {}  # Per-slot locks
    
    def get_slot_path(self, slot_id: int) -> Path:
        """Get slot path, loading if necessary."""
        
        if slot_id in self.loaded_slots:
            return self.workenv_dir / f"slot_{slot_id}"
        
        # Acquire slot-specific lock
        with self.slot_locks.get(slot_id):
            # Double-check after acquiring lock
            if slot_id not in self.loaded_slots:
                self._load_slot(slot_id)
                self.loaded_slots.add(slot_id)
        
        return self.workenv_dir / f"slot_{slot_id}"
    
    def _load_slot(self, slot_id: int) -> None:
        """Load a slot on-demand."""
        
        slot_meta = self._get_slot_metadata(slot_id)
        
        if slot_meta["lifecycle"] == LIFECYCLE_JIT_LOCAL:
            self._extract_local_slot(slot_id)
        elif slot_meta["lifecycle"] == LIFECYCLE_JIT_NETWORK:
            self._download_network_slot(slot_id)
        elif slot_meta["lifecycle"] == LIFECYCLE_JIT_HYBRID:
            if not self._try_extract_local(slot_id):
                self._download_network_slot(slot_id)
```

## 3. On-Demand Slot Loading

### 3.1 File System Hooks

Intercept file access to trigger loading:

```python
class JITFileSystem:
    """Virtual filesystem with JIT loading."""
    
    def open(self, path: str, mode: str = 'r'):
        """Open file, loading slot if needed."""
        
        # Check if path maps to unloaded slot
        slot_id = self._path_to_slot(path)
        if slot_id and slot_id not in self.loaded_slots:
            self.jit_loader.get_slot_path(slot_id)
        
        # Proceed with normal file open
        return open(path, mode)
```

### 3.2 Import Hooks (Python-specific)

```python
import sys
from importlib.abc import MetaPathFinder, Loader

class JITImportFinder(MetaPathFinder):
    """Import hook for JIT module loading."""
    
    def find_spec(self, fullname, path, target=None):
        """Find module spec, loading slot if needed."""
        
        # Map module to slot
        slot_id = self._module_to_slot(fullname)
        if slot_id and slot_id not in self.loaded_slots:
            self.jit_loader.get_slot_path(slot_id)
            # Add to sys.path if needed
            sys.path.insert(0, str(slot_path))
        
        # Continue with normal import
        return None

# Install the import hook
sys.meta_path.insert(0, JITImportFinder())
```

## 4. Network Payload Delivery

### 4.1 Metadata Extensions

```json
{
  "slots": [
    {
      "id": 5,
      "name": "ml-models",
      "lifecycle": 12,
      "jit": {
        "source": "grpc://models.example.com:50051",
        "service": "ModelService",
        "method": "GetSlot",
        "auth": {
          "type": "bearer",
          "token_env": "MODEL_API_TOKEN"
        },
        "cache": {
          "ttl": 3600,
          "validate": "etag"
        }
      }
    }
  ]
}
```

### 4.2 gRPC Client Implementation

```python
import grpc
from concurrent import futures

class GRPCSlotLoader:
    """Load slots via gRPC."""
    
    def __init__(self, config: dict):
        self.config = config
        self.channels = {}  # Connection pool
    
    def download_slot(self, slot_id: int, dest_path: Path) -> None:
        """Download slot via gRPC."""
        
        slot_config = self.config["slots"][slot_id]["jit"]
        
        # Get or create channel
        channel = self._get_channel(slot_config["source"])
        
        # Create stub from protobuf
        stub = self._create_stub(channel, slot_config["service"])
        
        # Prepare request
        request = SlotRequest(
            package_id=self.package_id,
            slot_id=slot_id,
            version=self.package_version
        )
        
        # Add authentication
        metadata = self._get_auth_metadata(slot_config.get("auth"))
        
        # Stream download
        response_stream = stub.GetSlot(request, metadata=metadata)
        
        with open(dest_path, 'wb') as f:
            for chunk in response_stream:
                f.write(chunk.data)
                self._update_progress(chunk.progress)
```

## 5. Protocol Buffer Integration

### 5.1 Schema Definition

```protobuf
syntax = "proto3";

package pspf.v1;

service SlotService {
  // Get slot metadata
  rpc GetSlotInfo(SlotRequest) returns (SlotInfo);
  
  // Stream slot contents
  rpc GetSlot(SlotRequest) returns (stream SlotChunk);
  
  // Check for updates
  rpc CheckUpdate(UpdateRequest) returns (UpdateInfo);
}

message SlotRequest {
  string package_id = 1;
  int32 slot_id = 2;
  string version = 3;
  string etag = 4;  // For caching
}

message SlotChunk {
  bytes data = 1;
  int64 offset = 2;
  int64 total_size = 3;
  float progress = 4;
  string checksum = 5;  // For chunk validation
}

message SlotInfo {
  int32 slot_id = 1;
  string name = 2;
  int64 size = 3;
  string encoding = 4;
  string etag = 5;
  int64 ttl = 6;
}
```

### 5.2 Dynamic Schema Loading

```python
from google.protobuf import descriptor_pb2
from google.protobuf import message_factory

class DynamicProtobufLoader:
    """Load protobuf schemas at runtime."""
    
    def load_schema(self, schema_slot_id: int) -> None:
        """Load protobuf schema from slot."""
        
        # JIT load the schema slot
        schema_path = self.jit_loader.get_slot_path(schema_slot_id)
        
        # Parse the .proto files
        with open(schema_path / "service.proto") as f:
            proto_content = f.read()
        
        # Compile to descriptor
        file_descriptor = self._compile_proto(proto_content)
        
        # Create message classes dynamically
        factory = message_factory.MessageFactory()
        for message_type in file_descriptor.message_type:
            factory.GetPrototype(message_type)
```

## 6. Implementation Considerations

### 6.1 Performance Optimization

```python
class SlotCache:
    """LRU cache for JIT-loaded slots."""
    
    def __init__(self, max_size_gb: float = 10.0):
        self.max_size = max_size_gb * 1024**3
        self.cache = OrderedDict()
        self.sizes = {}
        self.current_size = 0
    
    def get(self, slot_id: int) -> Path | None:
        """Get cached slot, updating LRU order."""
        
        if slot_id in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(slot_id)
            return self.cache[slot_id]
        return None
    
    def put(self, slot_id: int, path: Path, size: int) -> None:
        """Add slot to cache, evicting if necessary."""
        
        # Evict least recently used until space available
        while self.current_size + size > self.max_size:
            if not self.cache:
                raise CacheError("Slot too large for cache")
            self._evict_lru()
        
        self.cache[slot_id] = path
        self.sizes[slot_id] = size
        self.current_size += size
```

### 6.2 Security Considerations

- **Authentication**: Secure token management for network requests
- **Integrity**: Verify checksums for network-delivered slots
- **Encryption**: TLS for all network communications
- **Validation**: Ensure downloaded slots match expected metadata
- **Sandboxing**: JIT code should run with minimal privileges

### 6.3 Error Handling

```python
class JITError(Exception):
    """Base class for JIT loading errors."""

class NetworkSlotError(JITError):
    """Failed to download slot from network."""

class SlotValidationError(JITError):
    """Downloaded slot failed validation."""

class CacheError(JITError):
    """Cache operation failed."""

# Retry logic for network operations
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def download_with_retry(slot_id: int) -> None:
    """Download slot with exponential backoff retry."""
    try:
        download_slot(slot_id)
    except NetworkSlotError as e:
        logger.warning(f"Download failed, retrying: {e}")
        raise
```

### 6.4 Monitoring and Telemetry

```python
class JITMetrics:
    """Track JIT loading performance."""
    
    def __init__(self):
        self.load_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.network_downloads = 0
        self.total_bytes_downloaded = 0
    
    def record_load(self, slot_id: int, duration: float, source: str):
        """Record slot load metrics."""
        
        self.load_times.append({
            "slot_id": slot_id,
            "duration": duration,
            "source": source,  # "cache", "local", "network"
            "timestamp": time.time()
        })
        
        if source == "cache":
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            if source == "network":
                self.network_downloads += 1
```

## Future Enhancements

### Phase 1: Basic JIT (MVP)
- Local package JIT extraction
- Simple lazy loading based on lifecycle
- Basic progress reporting

### Phase 2: Network Delivery
- gRPC-based slot delivery
- Authentication and encryption
- Caching and validation

### Phase 3: Advanced Features
- P2P slot sharing
- Delta updates for slots
- Predictive prefetching
- Multi-CDN support

### Phase 4: Platform Integration
- OS-level virtual filesystem
- Kernel module for transparent JIT
- Container runtime integration

## References

- [gRPC Documentation](https://grpc.io/docs/)
- [Protocol Buffers](https://developers.google.com/protocol-buffers)
- [FUSE Filesystem](https://www.kernel.org/doc/html/latest/filesystems/fuse.html)
- [Python Import Hooks](https://docs.python.org/3/reference/import.html#the-import-system)

---
*Last Updated: 2025-09-02*