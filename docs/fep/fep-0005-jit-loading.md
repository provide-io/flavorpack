# FEP-0005: Just-In-Time (JIT) Loading and On-Demand Delivery

**Status**: Proposed  
**Type**: Standards Track  
**Created**: 2025-09-02  
**Updated**: 2025-09-02  
**Implementation**: Not Started ❌

## Abstract

This document specifies Just-In-Time (JIT) loading and on-demand delivery mechanisms for PSPF/2025 packages. JIT loading allows packages to defer extraction of non-critical slots until needed, reducing startup time and memory usage. The specification includes support for network-based slot delivery using modern protocols like gRPC with Protocol Buffers, enabling streaming of package components from remote servers or CDNs.

## Table of Contents

1. [Introduction](#1-introduction)
2. [JIT Loading Architecture](#2-jit-loading-architecture)
3. [Slot Lifecycle Extensions](#3-slot-lifecycle-extensions)
4. [Local JIT Extraction](#4-local-jit-extraction)
5. [Network Delivery](#5-network-delivery)
6. [Protocol Buffer Integration](#6-protocol-buffer-integration)
7. [Implementation Design](#7-implementation-design)
8. [Performance Optimization](#8-performance-optimization)
9. [Security Considerations](#9-security-considerations)
10. [Relationship to SPA](#10-relationship-to-spa)

## 1. Introduction

### 1.1 Motivation

Modern applications face distribution and performance challenges:

- **Large package sizes**: ML models, game assets, documentation can be gigabytes
- **Slow startup**: Extracting all slots before execution causes delays
- **Bandwidth waste**: Users download features they never use
- **Storage overhead**: Full extraction requires significant disk space
- **Update inefficiency**: Small changes require full re-download

JIT loading addresses these by:
- Starting with minimal essential components
- Loading additional components on-demand
- Supporting network-based streaming
- Enabling incremental updates

### 1.2 Use Cases

| Use Case | Traditional | JIT Local | JIT Network |
|----------|------------|-----------|-------------|
| ML Application | Extract 5GB model at startup | Load model when needed | Stream model from CDN |
| Multi-language App | Extract all language packs | Load user's language | Download languages on selection |
| Game | Extract all levels/assets | Load current level | Stream levels as player progresses |
| IDE/Editor | Extract all plugins | Load active plugins | Download plugins from marketplace |
| Documentation | Extract full docs | Load viewed sections | Fetch docs from server |

### 1.3 Design Principles

- **Transparent**: Applications shouldn't need modification
- **Efficient**: Minimize latency and bandwidth
- **Reliable**: Handle network failures gracefully
- **Secure**: Verify integrity of JIT-loaded content
- **Flexible**: Support various loading strategies

## 2. JIT Loading Architecture

### 2.1 System Overview

```
┌─────────────────────────────────────────┐
│           PSPF Package                   │
├─────────────────────────────────────────┤
│  Launcher (with JIT support)             │
├─────────────────────────────────────────┤
│  Index (with JIT flags)                  │
├─────────────────────────────────────────┤
│  Metadata (with JIT config)              │
├─────────────────────────────────────────┤
│  Slot 0: Runtime (EAGER)                 │
│  Slot 1: Core App (EAGER)                │
│  Slot 2: Optional Feature (JIT_LOCAL)    │
│  Slot 3: Large Model (JIT_NETWORK)       │
│  Slot 4: Documentation (JIT_HYBRID)      │
└─────────────────────────────────────────┘
                    ↓
         ┌──────────────────┐
         │   JIT Loader      │
         ├──────────────────┤
         │  Load Manager     │
         │  Cache Manager    │
         │  Network Client   │
         └──────────────────┘
                    ↓
         ┌──────────────────┐
         │  Remote Server    │
         ├──────────────────┤
         │  gRPC Service     │
         │  CDN Storage      │
         │  Update Service   │
         └──────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **JIT Loader** | Coordinates on-demand loading |
| **Load Manager** | Tracks loaded/pending slots |
| **Cache Manager** | LRU cache for loaded slots |
| **Network Client** | Downloads remote slots |
| **gRPC Service** | Serves slot data via RPC |
| **CDN Storage** | Distributed content delivery |

## 3. Slot Lifecycle Extensions

### 3.1 Extended Lifecycle Types

```python
# Existing lifecycles (FEP-0001)
LIFECYCLE_INIT = 0          # First run only
LIFECYCLE_STARTUP = 1       # Every startup
LIFECYCLE_RUNTIME = 2       # Extract at startup (default)
LIFECYCLE_SHUTDOWN = 3      # At exit
LIFECYCLE_CACHE = 4         # Cacheable
LIFECYCLE_TEMPORARY = 5     # Session only
LIFECYCLE_LAZY = 6          # Basic JIT (load on first access)
LIFECYCLE_EAGER = 7         # Load immediately

# New JIT-specific lifecycles
LIFECYCLE_JIT_LOCAL = 11    # JIT from local package file
LIFECYCLE_JIT_NETWORK = 12  # JIT from network only
LIFECYCLE_JIT_HYBRID = 13   # Try local, fallback to network
LIFECYCLE_JIT_STREAMED = 14 # Stream progressively
LIFECYCLE_JIT_CACHED = 15   # Network with persistent cache
```

### 3.2 Lifecycle Behavior

| Lifecycle | Extraction | Source | Caching |
|-----------|-----------|--------|---------|
| `RUNTIME` | At startup | Local | Persistent |
| `LAZY` | On first access | Local | Persistent |
| `JIT_LOCAL` | On demand | Local package | Memory + Disk |
| `JIT_NETWORK` | On demand | Network only | Memory only |
| `JIT_HYBRID` | On demand | Local → Network | Memory + Disk |
| `JIT_STREAMED` | Progressive | Network chunks | Incremental |
| `JIT_CACHED` | On demand | Network | Persistent |

## 4. Local JIT Extraction

### 4.1 Lazy Loading Mechanism

```python
class LocalJITLoader:
    """Handles JIT extraction from local package."""
    
    def __init__(self, package_path: Path, workenv_dir: Path):
        self.package_path = package_path
        self.workenv_dir = workenv_dir
        self.reader = PSPFReader(package_path)
        self.loaded_slots: set[int] = set()
        self.loading_locks: dict[int, threading.Lock] = {}
        
    def get_slot_path(self, slot_id: int) -> Path:
        """Get slot path, extracting if necessary."""
        
        # Fast path - already loaded
        if slot_id in self.loaded_slots:
            return self.workenv_dir / f"slot_{slot_id}"
        
        # Acquire per-slot lock
        if slot_id not in self.loading_locks:
            self.loading_locks[slot_id] = threading.Lock()
        
        with self.loading_locks[slot_id]:
            # Double-check after acquiring lock
            if slot_id in self.loaded_slots:
                return self.workenv_dir / f"slot_{slot_id}"
            
            # Extract slot
            self._extract_slot(slot_id)
            self.loaded_slots.add(slot_id)
            
        return self.workenv_dir / f"slot_{slot_id}"
    
    def _extract_slot(self, slot_id: int) -> None:
        """Extract a single slot from package."""
        
        logger.info(f"JIT: Extracting slot {slot_id}")
        
        # Read slot data
        slot_data = self.reader.read_slot(slot_id)
        slot_meta = self.reader.get_slot_metadata(slot_id)
        
        # Verify checksum
        if not self._verify_slot_checksum(slot_data, slot_meta):
            raise SlotVerificationError(f"Slot {slot_id} checksum mismatch")
        
        # Extract based on encoding
        dest_path = self.workenv_dir / f"slot_{slot_id}"
        if slot_meta.encoding == ENCODING_TGZ:
            self._extract_tar_gz(slot_data, dest_path)
        elif slot_meta.encoding == ENCODING_GZIP:
            self._extract_gzip(slot_data, dest_path)
        else:
            self._extract_raw(slot_data, dest_path)
```

### 4.2 File System Hooks

```python
class JITFileSystem:
    """Virtual filesystem with transparent JIT loading."""
    
    def __init__(self, jit_loader: LocalJITLoader):
        self.jit_loader = jit_loader
        self.slot_mapping = self._build_slot_mapping()
    
    def _build_slot_mapping(self) -> dict[str, int]:
        """Map file paths to slot IDs."""
        mapping = {}
        for slot_id, slot_meta in enumerate(self.jit_loader.metadata.slots):
            if slot_meta.lifecycle in JIT_LIFECYCLES:
                # Map all files in slot to slot ID
                for file_path in slot_meta.files:
                    mapping[file_path] = slot_id
        return mapping
    
    def open(self, path: str, mode: str = 'r') -> IO:
        """Open file, triggering JIT load if needed."""
        
        # Check if path requires JIT loading
        if path in self.slot_mapping:
            slot_id = self.slot_mapping[path]
            slot_path = self.jit_loader.get_slot_path(slot_id)
            actual_path = slot_path / Path(path).name
        else:
            actual_path = Path(path)
        
        return open(actual_path, mode)
    
    def exists(self, path: str) -> bool:
        """Check existence, considering JIT slots."""
        
        # Virtual existence for JIT slots
        if path in self.slot_mapping:
            return True
        return Path(path).exists()
```

### 4.3 Import Hooks (Python)

```python
import sys
from importlib.abc import MetaPathFinder, ModuleSpec
from importlib.machinery import ModuleSpec, SourceFileLoader

class JITImportFinder(MetaPathFinder):
    """Python import hook for JIT module loading."""
    
    def __init__(self, jit_loader: LocalJITLoader):
        self.jit_loader = jit_loader
        self.module_to_slot = self._build_module_mapping()
    
    def find_spec(self, fullname: str, path=None, target=None) -> ModuleSpec | None:
        """Find module, loading JIT slot if needed."""
        
        if fullname not in self.module_to_slot:
            return None
        
        slot_id = self.module_to_slot[fullname]
        slot_path = self.jit_loader.get_slot_path(slot_id)
        
        # Build module spec
        module_path = slot_path / fullname.replace('.', '/') / '__init__.py'
        if not module_path.exists():
            module_path = slot_path / (fullname.replace('.', '/') + '.py')
        
        if module_path.exists():
            return ModuleSpec(
                fullname,
                SourceFileLoader(fullname, str(module_path)),
                origin=str(module_path)
            )
        
        return None

# Install the import hook
sys.meta_path.insert(0, JITImportFinder(jit_loader))
```

## 5. Network Delivery

### 5.1 Network Configuration

```json
{
  "slots": [
    {
      "id": 5,
      "name": "large-model",
      "lifecycle": 12,
      "jit": {
        "source": {
          "type": "grpc",
          "endpoint": "models.example.com:50051",
          "service": "SlotService",
          "tls": true
        },
        "auth": {
          "type": "bearer",
          "token_env": "PSPF_API_TOKEN"
        },
        "cache": {
          "strategy": "persistent",
          "ttl_seconds": 3600,
          "max_size_mb": 1000
        },
        "fallback": {
          "retry_count": 3,
          "retry_delay_ms": 1000,
          "offline_mode": true
        }
      }
    }
  ]
}
```

### 5.2 Network JIT Loader

```python
class NetworkJITLoader:
    """Downloads slots from network sources."""
    
    def __init__(self, config: dict, cache_dir: Path):
        self.config = config
        self.cache_dir = cache_dir
        self.clients: dict[str, Any] = {}  # Connection pool
        self.download_progress: dict[int, float] = {}
        
    async def download_slot(self, slot_id: int) -> Path:
        """Download slot from network."""
        
        slot_config = self.config.slots[slot_id]
        jit_config = slot_config.jit
        
        # Check cache first
        cached_path = self._check_cache(slot_id)
        if cached_path and self._validate_cache(cached_path, slot_config):
            logger.info(f"JIT: Using cached slot {slot_id}")
            return cached_path
        
        # Download from network
        logger.info(f"JIT: Downloading slot {slot_id} from {jit_config.source.endpoint}")
        
        if jit_config.source.type == "grpc":
            return await self._download_grpc(slot_id, jit_config)
        elif jit_config.source.type == "http":
            return await self._download_http(slot_id, jit_config)
        elif jit_config.source.type == "s3":
            return await self._download_s3(slot_id, jit_config)
        else:
            raise ValueError(f"Unknown source type: {jit_config.source.type}")
    
    async def _download_grpc(self, slot_id: int, config: dict) -> Path:
        """Download via gRPC streaming."""
        
        # Get or create gRPC channel
        channel = self._get_grpc_channel(config.source.endpoint)
        
        # Create stub from service definition
        stub = self._create_stub(channel, config.source.service)
        
        # Prepare request
        request = SlotRequest(
            package_id=self.config.package.id,
            package_version=self.config.package.version,
            slot_id=slot_id,
            auth_token=self._get_auth_token(config.auth)
        )
        
        # Stream download
        dest_path = self.cache_dir / f"slot_{slot_id}.tmp"
        total_size = 0
        
        async with aiofiles.open(dest_path, 'wb') as f:
            async for chunk in stub.DownloadSlot(request):
                await f.write(chunk.data)
                total_size += len(chunk.data)
                self.download_progress[slot_id] = chunk.progress
                
                # Verify chunk checksum
                if not self._verify_chunk(chunk):
                    raise DownloadError(f"Chunk checksum mismatch at {total_size}")
        
        # Verify complete slot
        if not self._verify_slot(dest_path, config):
            raise DownloadError(f"Slot {slot_id} verification failed")
        
        # Move to final location
        final_path = self.cache_dir / f"slot_{slot_id}"
        dest_path.rename(final_path)
        
        return final_path
```

### 5.3 CDN Integration

```python
class CDNSlotLoader:
    """Load slots from CDN with geographic distribution."""
    
    def __init__(self, cdn_config: dict):
        self.cdn_endpoints = cdn_config.endpoints
        self.edge_locations = self._discover_edges()
    
    async def download_slot(self, slot_id: int) -> Path:
        """Download from nearest CDN edge."""
        
        # Find nearest edge location
        edge = self._find_nearest_edge()
        
        # Build CDN URL
        url = f"{edge.url}/packages/{self.package_id}/slots/{slot_id}"
        
        # Download with resume support
        return await self._download_with_resume(url)
    
    async def _download_with_resume(self, url: str) -> Path:
        """Download with resume capability."""
        
        headers = {}
        dest_path = self.cache_dir / Path(url).name
        
        # Check for partial download
        if dest_path.exists():
            size = dest_path.stat().st_size
            headers['Range'] = f'bytes={size}-'
            mode = 'ab'
        else:
            mode = 'wb'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                
                async with aiofiles.open(dest_path, mode) as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
        
        return dest_path
```

## 6. Protocol Buffer Integration

### 6.1 Service Definition

```protobuf
syntax = "proto3";

package pspf.jit.v1;

import "google/protobuf/timestamp.proto";

service SlotService {
  // Get slot metadata
  rpc GetSlotInfo(SlotInfoRequest) returns (SlotInfo);
  
  // Download complete slot
  rpc DownloadSlot(SlotRequest) returns (stream SlotChunk);
  
  // Download slot range (for resume)
  rpc DownloadSlotRange(SlotRangeRequest) returns (stream SlotChunk);
  
  // Check for slot updates
  rpc CheckSlotUpdate(SlotUpdateRequest) returns (SlotUpdateInfo);
  
  // Get slot manifest (list of files)
  rpc GetSlotManifest(SlotManifestRequest) returns (SlotManifest);
}

message SlotRequest {
  string package_id = 1;
  string package_version = 2;
  int32 slot_id = 3;
  string auth_token = 4;
  string client_id = 5;
}

message SlotChunk {
  bytes data = 1;
  int64 offset = 2;
  int64 total_size = 3;
  float progress = 4;
  string chunk_hash = 5;
  bool is_final = 6;
}

message SlotInfo {
  int32 slot_id = 1;
  string name = 2;
  int64 compressed_size = 3;
  int64 uncompressed_size = 4;
  string encoding = 5;
  string checksum = 6;
  google.protobuf.Timestamp last_modified = 7;
  map<string, string> metadata = 8;
}

message SlotManifest {
  int32 slot_id = 1;
  repeated FileEntry files = 2;
  
  message FileEntry {
    string path = 1;
    int64 size = 2;
    string mode = 3;
    string checksum = 4;
  }
}
```

### 6.2 Dynamic Schema Loading

```python
from google.protobuf import descriptor_pool, message_factory
from google.protobuf.descriptor_pb2 import FileDescriptorSet

class DynamicProtobufLoader:
    """Load Protocol Buffer schemas at runtime."""
    
    def __init__(self, jit_loader: LocalJITLoader):
        self.jit_loader = jit_loader
        self.pool = descriptor_pool.DescriptorPool()
        self.factory = message_factory.MessageFactory(self.pool)
        
    def load_schema_from_slot(self, schema_slot_id: int) -> None:
        """Load protobuf schema from JIT slot."""
        
        # JIT load the schema slot
        schema_path = self.jit_loader.get_slot_path(schema_slot_id)
        
        # Load compiled descriptor set
        descriptor_path = schema_path / "descriptors.pb"
        with open(descriptor_path, 'rb') as f:
            descriptor_set = FileDescriptorSet()
            descriptor_set.ParseFromString(f.read())
        
        # Add to descriptor pool
        for file_descriptor in descriptor_set.file:
            self.pool.Add(file_descriptor)
    
    def create_message(self, message_type: str) -> Any:
        """Create message instance by type name."""
        
        descriptor = self.pool.FindMessageTypeByName(message_type)
        return self.factory.GetPrototype(descriptor)()
    
    def serialize_to_slot(self, message: Any, slot_id: int) -> None:
        """Serialize protobuf message to slot."""
        
        slot_path = self.cache_dir / f"slot_{slot_id}"
        slot_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(slot_path, 'wb') as f:
            f.write(message.SerializeToString())
```

## 7. Implementation Design

### 7.1 JIT Manager Architecture

```python
@dataclass
class JITConfig:
    """JIT loading configuration."""
    
    enable_local_jit: bool = True
    enable_network_jit: bool = False
    cache_dir: Path = Path.home() / ".cache" / "pspf" / "jit"
    max_cache_size_gb: float = 10.0
    network_timeout_seconds: int = 30
    max_concurrent_downloads: int = 3
    prefetch_slots: list[int] = field(default_factory=list)

class JITManager:
    """Central JIT loading coordinator."""
    
    def __init__(self, package: PSPFPackage, config: JITConfig):
        self.package = package
        self.config = config
        
        # Initialize loaders
        self.local_loader = LocalJITLoader(package.path, package.workenv_dir)
        self.network_loader = NetworkJITLoader(package.metadata, config.cache_dir)
        
        # Slot tracking
        self.slot_status: dict[int, SlotStatus] = {}
        self.load_queue: asyncio.Queue = asyncio.Queue()
        
        # Cache management
        self.cache = SlotCache(config.max_cache_size_gb)
        
        # Start background workers
        self._start_workers()
    
    async def get_slot(self, slot_id: int) -> Path:
        """Get slot, loading if necessary."""
        
        # Check status
        status = self.slot_status.get(slot_id, SlotStatus.NOT_LOADED)
        
        if status == SlotStatus.LOADED:
            return self._get_slot_path(slot_id)
        
        if status == SlotStatus.LOADING:
            return await self._wait_for_slot(slot_id)
        
        # Start loading
        return await self._load_slot(slot_id)
    
    async def _load_slot(self, slot_id: int) -> Path:
        """Load slot based on lifecycle type."""
        
        self.slot_status[slot_id] = SlotStatus.LOADING
        
        try:
            slot_meta = self.package.get_slot_metadata(slot_id)
            
            if slot_meta.lifecycle == LIFECYCLE_JIT_LOCAL:
                path = await self._load_local(slot_id)
            elif slot_meta.lifecycle == LIFECYCLE_JIT_NETWORK:
                path = await self._load_network(slot_id)
            elif slot_meta.lifecycle == LIFECYCLE_JIT_HYBRID:
                path = await self._load_hybrid(slot_id)
            else:
                raise ValueError(f"Unknown JIT lifecycle: {slot_meta.lifecycle}")
            
            self.slot_status[slot_id] = SlotStatus.LOADED
            return path
            
        except Exception as e:
            self.slot_status[slot_id] = SlotStatus.FAILED
            raise JITLoadError(f"Failed to load slot {slot_id}: {e}")
```

### 7.2 Prefetching Strategy

```python
class PrefetchStrategy:
    """Intelligent slot prefetching."""
    
    def __init__(self, jit_manager: JITManager):
        self.jit_manager = jit_manager
        self.access_history: list[int] = []
        self.predictive_model = self._build_model()
    
    def record_access(self, slot_id: int) -> None:
        """Record slot access for prediction."""
        
        self.access_history.append(slot_id)
        
        # Predict next slots
        predicted = self.predict_next_slots(slot_id)
        
        # Queue for prefetching
        for next_slot_id in predicted:
            if not self.jit_manager.is_loaded(next_slot_id):
                asyncio.create_task(
                    self.jit_manager.prefetch_slot(next_slot_id)
                )
    
    def predict_next_slots(self, current_slot: int) -> list[int]:
        """Predict which slots will be needed next."""
        
        # Simple Markov chain prediction
        predictions = []
        
        # Find previous occurrences
        for i, slot_id in enumerate(self.access_history[:-1]):
            if slot_id == current_slot:
                next_slot = self.access_history[i + 1]
                predictions.append(next_slot)
        
        # Return most common predictions
        from collections import Counter
        counter = Counter(predictions)
        return [slot_id for slot_id, _ in counter.most_common(3)]
```

## 8. Performance Optimization

### 8.1 Memory-Mapped JIT

```python
class MemoryMappedJIT:
    """Direct memory mapping for JIT slots."""
    
    def __init__(self, package_path: Path):
        self.package_fd = os.open(package_path, os.O_RDONLY)
        self.slot_mappings: dict[int, mmap.mmap] = {}
    
    def map_slot(self, slot_id: int, offset: int, size: int) -> mmap.mmap:
        """Memory-map a slot directly from package."""
        
        if slot_id in self.slot_mappings:
            return self.slot_mappings[slot_id]
        
        # Create memory mapping
        mapping = mmap.mmap(
            self.package_fd,
            length=size,
            offset=offset,
            access=mmap.ACCESS_READ
        )
        
        self.slot_mappings[slot_id] = mapping
        return mapping
    
    def read_slot_data(self, slot_id: int, offset: int, size: int) -> bytes:
        """Read data from memory-mapped slot."""
        
        mapping = self.slot_mappings[slot_id]
        mapping.seek(offset)
        return mapping.read(size)
```

### 8.2 Parallel Loading

```python
class ParallelJITLoader:
    """Load multiple slots concurrently."""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures: dict[int, Future] = {}
    
    def load_slots_parallel(self, slot_ids: list[int]) -> dict[int, Path]:
        """Load multiple slots in parallel."""
        
        futures = {}
        for slot_id in slot_ids:
            if slot_id not in self.futures:
                future = self.executor.submit(self._load_slot, slot_id)
                self.futures[slot_id] = future
                futures[slot_id] = future
        
        # Wait for completion
        results = {}
        for slot_id, future in futures.items():
            try:
                results[slot_id] = future.result(timeout=30)
            except TimeoutError:
                logger.error(f"Timeout loading slot {slot_id}")
        
        return results
```

### 8.3 Compression-Aware Loading

```python
class CompressionAwareJIT:
    """Optimize loading based on compression."""
    
    def should_decompress(self, slot_meta: SlotMetadata) -> bool:
        """Decide whether to decompress slot."""
        
        # Keep compressed if:
        # 1. Slot is large and rarely accessed
        # 2. Compression ratio is high
        # 3. Memory is constrained
        
        compression_ratio = slot_meta.uncompressed_size / slot_meta.compressed_size
        
        if compression_ratio > 10 and slot_meta.access_frequency < 0.1:
            return False  # Keep compressed, decompress on demand
        
        if self.available_memory() < slot_meta.uncompressed_size * 2:
            return False  # Not enough memory
        
        return True  # Decompress for performance
```

## 9. Security Considerations

### 9.1 Integrity Verification

```python
class SecureJITLoader:
    """JIT loading with integrity verification."""
    
    def __init__(self, public_key: bytes):
        self.public_key = public_key
        self.verified_slots: set[int] = set()
    
    def verify_slot(self, slot_id: int, data: bytes, signature: bytes) -> bool:
        """Verify slot integrity."""
        
        if slot_id in self.verified_slots:
            return True
        
        # Verify Ed25519 signature
        try:
            verify_key = VerifyKey(self.public_key)
            verify_key.verify(data, signature)
            self.verified_slots.add(slot_id)
            return True
        except BadSignatureError:
            logger.error(f"Slot {slot_id} signature verification failed")
            return False
    
    def verify_network_slot(self, slot_id: int, chunks: list[bytes]) -> bool:
        """Verify downloaded slot chunks."""
        
        # Reconstruct full slot
        full_data = b''.join(chunks)
        
        # Verify against manifest
        expected_hash = self.manifest.slots[slot_id].checksum
        actual_hash = hashlib.sha256(full_data).hexdigest()
        
        if actual_hash != expected_hash:
            logger.error(f"Slot {slot_id} checksum mismatch")
            return False
        
        return True
```

### 9.2 Network Security

```python
class SecureNetworkJIT:
    """Secure network slot delivery."""
    
    def __init__(self, tls_config: dict):
        self.tls_context = self._create_tls_context(tls_config)
        self.pinned_certs = tls_config.get('pinned_certs', [])
    
    def _create_tls_context(self, config: dict) -> ssl.SSLContext:
        """Create TLS context with security settings."""
        
        context = ssl.create_default_context()
        
        # Certificate pinning
        if config.get('pin_certificates'):
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_verify_locations(config['ca_bundle'])
        
        # Minimum TLS version
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        
        # Client certificate authentication
        if config.get('client_cert'):
            context.load_cert_chain(
                config['client_cert'],
                config['client_key']
            )
        
        return context
```

### 9.3 Access Control

```python
class JITAccessControl:
    """Control access to JIT slots."""
    
    def __init__(self, policy: dict):
        self.policy = policy
        self.access_log = []
    
    def check_access(self, slot_id: int, context: dict) -> bool:
        """Check if slot access is allowed."""
        
        slot_policy = self.policy.get(f"slot_{slot_id}", {})
        
        # Check time-based access
        if 'time_window' in slot_policy:
            if not self._in_time_window(slot_policy['time_window']):
                return False
        
        # Check user permissions
        if 'required_permission' in slot_policy:
            if not context.get(slot_policy['required_permission']):
                return False
        
        # Check rate limiting
        if 'rate_limit' in slot_policy:
            if not self._check_rate_limit(slot_id, slot_policy['rate_limit']):
                return False
        
        # Log access
        self.access_log.append({
            'slot_id': slot_id,
            'timestamp': time.time(),
            'context': context
        })
        
        return True
```

## 10. Relationship to SPA

JIT Loading and SPA (FEP-0004) work together synergistically:

### 10.1 Combined Execution Flow

```
[Launch]
    ↓
[SPA: Start PVP]──────────→[PVP: Initialize UI]
    ↓                              ↓
[SPA: Verify Package]         [PVP: Prepare JIT]
    ↓                              ↓
[SPA: Signal Verified]←──────[PVP: Wait at Boundary]
    ↓
[JIT: Load Essential Slots]
    ↓
[Main App Starts]
    ↓
[JIT: Load Additional Slots On-Demand]
```

### 10.2 Integration Points

1. **PVP Prepares JIT Infrastructure**
   ```python
   # In PVP code (runs during verification)
   def prepare_jit_system():
       # Set up cache directories
       cache_dir = Path("/tmp/pspf_jit_cache")
       cache_dir.mkdir(exist_ok=True)
       
       # Pre-connect to network sources
       grpc_channel = grpc.aio.insecure_channel('slots.example.com:50051')
       
       # Build slot dependency graph
       dependency_graph = analyze_slot_dependencies()
       
       # Ready for immediate use after verification
   ```

2. **Coordinated Loading Strategy**
   ```python
   class SPAJITCoordinator:
       """Coordinate SPA and JIT loading."""
       
       def __init__(self):
           self.spa_manager = SPAManager()
           self.jit_manager = JITManager()
       
       async def launch(self):
           # Start PVP and verification in parallel
           pvp_task = asyncio.create_task(self.spa_manager.run_pvp())
           verify_task = asyncio.create_task(self.spa_manager.verify())
           
           # PVP can prepare JIT system
           await pvp_task
           
           # Wait for verification
           await verify_task
           
           # Now use JIT for fast startup
           essential_slots = await self.jit_manager.load_essential()
           
           # Start main app with minimal slots
           await self.start_application(essential_slots)
   ```

### 10.3 Performance Benefits

| Metric | Traditional | SPA Only | JIT Only | SPA + JIT |
|--------|------------|----------|----------|-----------|
| First pixel | 500ms | 50ms | 400ms | 50ms |
| Interactive | 3000ms | 2500ms | 1000ms | 500ms |
| Full load | 3000ms | 3000ms | 500ms+lazy | 500ms+lazy |
| Memory | 1GB | 1GB | 300MB+dynamic | 300MB+dynamic |
| Network | 0 | 0 | On-demand | On-demand |

### 10.4 Configuration Example

```json
{
  "spa": {
    "enabled": true,
    "pvp_slot": 0,
    "pvp_capabilities": ["ui_render", "jit_prepare"]
  },
  "jit": {
    "enabled": true,
    "strategy": "progressive",
    "essential_slots": [1, 2],
    "prefetch_slots": [3, 4],
    "lazy_slots": [5, 6, 7],
    "network_slots": [8, 9, 10]
  }
}
```

## Testing Strategy

### Unit Tests
```python
# tests/jit/test_local_loader.py
def test_lazy_slot_extraction():
    """Test lazy extraction of local slots."""
    
def test_concurrent_slot_loading():
    """Test thread-safe concurrent loading."""

# tests/jit/test_network_loader.py
def test_grpc_slot_download():
    """Test gRPC-based slot download."""
    
def test_download_resume():
    """Test resumable downloads."""
```

### Integration Tests
```python
# tests/jit/test_spa_jit_integration.py
def test_spa_prepares_jit():
    """Test PVP preparing JIT infrastructure."""
    
def test_combined_performance():
    """Measure combined SPA+JIT performance."""
```

### Performance Tests
```python
# tests/jit/test_performance.py
def test_startup_time_reduction():
    """Measure startup time improvements."""
    
def test_memory_usage_reduction():
    """Measure memory usage with JIT."""
```

## Future Enhancements

### Phase 1: Local JIT (MVP)
- Basic lazy extraction from package
- Simple slot lifecycle management
- File system hooks

### Phase 2: Network JIT
- gRPC-based slot delivery
- CDN integration
- Resume support

### Phase 3: Advanced Features
- Predictive prefetching
- P2P slot sharing
- Delta updates
- Compression-aware loading

### Phase 4: Platform Integration
- OS-level virtual filesystem (FUSE)
- Transparent JIT via kernel module
- Container runtime integration

## References

- [gRPC Streaming](https://grpc.io/docs/what-is-grpc/core-concepts/#server-streaming-rpc)
- [Protocol Buffers](https://developers.google.com/protocol-buffers/docs/pythontutorial)
- [Python Import Hooks](https://docs.python.org/3/reference/import.html#the-import-system)
- [FUSE Filesystem](https://github.com/libfuse/libfuse)
- [Memory-Mapped I/O](https://docs.python.org/3/library/mmap.html)

---
*Last Updated: 2025-09-02*