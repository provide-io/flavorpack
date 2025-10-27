# FEP-0006: Staged Payload Architecture (SPA)

**Status**: Future  
**Type**: Standards Track  
**Created**: 2025-01-11  
**Requires**: FEP-0001, FEP-0004, FEP-0005

## Abstract

This document specifies the Staged Payload Architecture (SPA) for PSPF/2025 packages, enabling progressive loading and execution of package components based on runtime requirements. SPA allows packages to contain multiple execution stages, optional components, and demand-loaded resources while maintaining cryptographic integrity and minimizing initial load times.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architectural Overview](#2-architectural-overview)
3. [Stage Definition Model](#3-stage-definition-model)
4. [Dependency Resolution](#4-dependency-resolution)
5. [Progressive Loading Protocol](#5-progressive-loading-protocol)
6. [Stage Activation Mechanisms](#6-stage-activation-mechanisms)
7. [Caching and Persistence](#7-caching-and-persistence)
8. [Security Model](#8-security-model)
9. [Performance Optimization](#9-performance-optimization)
10. [Platform Integration](#10-platform-integration)
11. [Monitoring and Telemetry](#11-monitoring-and-telemetry)
12. [Implementation Requirements](#12-implementation-requirements)
13. [Test Vectors](#13-test-vectors)
14. [Security Considerations](#14-security-considerations)
15. [IANA Considerations](#15-iana-considerations)
16. [References](#16-references)

## 1. Introduction

### 1.1. Motivation

Modern applications often contain substantial amounts of code and resources that are not required for initial execution. Loading all components at startup increases memory usage, extends launch times, and degrades user experience. The Staged Payload Architecture addresses these challenges by enabling progressive, demand-driven loading of package components.

### 1.2. Design Goals

1. **Minimal Initial Load**: Core functionality available with smallest possible payload
2. **Progressive Enhancement**: Additional features load as needed
3. **Cryptographic Integrity**: All stages verified before execution
4. **Zero-Copy Loading**: Memory-mapped stages for efficient access
5. **Network Awareness**: Support for remote stage fetching
6. **Offline Capability**: Graceful degradation when stages unavailable

### 1.3. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

## 2. Architectural Overview

### 2.1. Stage Hierarchy

```
Package Root
├── Stage 0: Bootstrap (REQUIRED)
│   ├── Core runtime
│   ├── Stage loader
│   └── Verification logic
├── Stage 1: Primary (REQUIRED)
│   ├── Main application logic
│   ├── Essential resources
│   └── Stage manifest
├── Stage 2: Enhanced (OPTIONAL)
│   ├── Advanced features
│   ├── Optimization modules
│   └── Extended libraries
├── Stage 3: Resources (OPTIONAL)
│   ├── Large assets
│   ├── Documentation
│   └── Localization data
└── Stage N: Extensions (OPTIONAL)
    ├── Plugins
    ├── Third-party modules
    └── User customizations
```

### 2.2. Loading Pipeline

```
┌─────────────┐
│  Bootstrap  │ Stage 0 (Always loaded)
└──────┬──────┘
       │
       v
┌─────────────┐
│   Primary   │ Stage 1 (Loaded after verification)
└──────┬──────┘
       │
       v
┌─────────────┐
│  On-Demand  │ Stages 2-N (Loaded as needed)
└─────────────┘
       │
       v
┌─────────────┐
│   Runtime   │ Dynamic stage activation
└─────────────┘
```

### 2.3. Memory Layout

```
Virtual Memory Space
┌────────────────────────────────────┐ 0x0000000000000000
│         Bootstrap Stage            │ Read-Only, Executable
├────────────────────────────────────┤ 0x0000000010000000
│         Primary Stage              │ Read-Only, Executable
├────────────────────────────────────┤ 0x0000000020000000
│         Enhanced Stage             │ Demand-Paged
├────────────────────────────────────┤ 0x0000000030000000
│         Resource Stages            │ Memory-Mapped
├────────────────────────────────────┤ 0x0000000040000000
│         Extension Stages           │ Dynamically Loaded
├────────────────────────────────────┤ 0x0000000050000000
│         Stage Metadata             │ Read-Only
├────────────────────────────────────┤ 0x0000000060000000
│         Runtime Heap               │ Read-Write
└────────────────────────────────────┘ 0x00007FFFFFFFFFFF
```

## 3. Stage Definition Model

### 3.1. Stage Manifest Structure

```json
{
  "version": "2025.1.0",
  "stages": [
    {
      "id": 0,
      "name": "bootstrap",
      "type": "REQUIRED",
      "slots": [0, 1],
      "size": 524288,
      "checksum": "0xABCDEF01",
      "dependencies": [],
      "entry_points": ["_start", "_verify"],
      "capabilities": ["CORE", "VERIFY"]
    },
    {
      "id": 1,
      "name": "primary",
      "type": "REQUIRED",
      "slots": [2, 3, 4],
      "size": 2097152,
      "checksum": "0x12345678",
      "dependencies": [0],
      "entry_points": ["main", "init"],
      "capabilities": ["APPLICATION", "UI"]
    },
    {
      "id": 2,
      "name": "enhanced",
      "type": "OPTIONAL",
      "slots": [5, 6],
      "size": 4194304,
      "checksum": "0x87654321",
      "dependencies": [0, 1],
      "activation": "ON_DEMAND",
      "entry_points": ["enhance_init"],
      "capabilities": ["ADVANCED", "OPTIMIZATION"]
    }
  ],
  "activation_policy": {
    "preload": [0, 1],
    "lazy": [2],
    "remote": [3, 4],
    "cache_policy": "LRU",
    "max_memory": 268435456
  }
}
```

### 3.2. Stage Types

```c
enum StageType {
    STAGE_BOOTSTRAP = 0x00,    // Core loader and verifier
    STAGE_PRIMARY   = 0x01,    // Main application
    STAGE_ENHANCED  = 0x02,    // Advanced features
    STAGE_RESOURCE  = 0x03,    // Large resources
    STAGE_EXTENSION = 0x04,    // Plugins/extensions
    STAGE_DEBUG     = 0x05,    // Debug symbols
    STAGE_PROFILE   = 0x06,    // Profile data
    STAGE_CUSTOM    = 0x80     // User-defined stages
};

enum ActivationTrigger {
    TRIGGER_IMMEDIATE = 0x00,   // Load immediately
    TRIGGER_ON_DEMAND = 0x01,   // Load when accessed
    TRIGGER_EXPLICIT  = 0x02,   // Load via API call
    TRIGGER_SCHEDULED = 0x03,   // Load at specific time
    TRIGGER_MEMORY    = 0x04,   // Load when memory available
    TRIGGER_NETWORK   = 0x05,   // Load when network available
    TRIGGER_USER      = 0x06    // Load on user action
};
```

### 3.3. Stage Descriptor

```c
struct StageDescriptor {
    uint32_t stage_id;          // Unique stage identifier
    uint32_t stage_type;        // Type from StageType enum
    uint64_t offset;            // Offset in package file
    uint64_t compressed_size;   // Compressed size in bytes
    uint64_t uncompressed_size; // Uncompressed size
    uint32_t checksum;          // Adler-32 checksum
    uint32_t flags;             // Stage flags
    uint32_t dependencies[8];   // Required stages
    uint32_t slot_start;        // First slot index
    uint32_t slot_count;        // Number of slots
    uint64_t load_address;      // Preferred load address
    uint64_t entry_point;       // Stage entry point
    uint8_t  signature[64];     // Ed25519 signature
    uint8_t  reserved[32];      // Reserved for future use
};
```

## 4. Dependency Resolution

### 4.1. Dependency Graph

```python
class DependencyGraph:
    def __init__(self):
        self.nodes = {}  # stage_id -> StageNode
        self.edges = {}  # stage_id -> set(dependencies)
        
    def add_stage(self, stage: StageDescriptor):
        """Add stage to dependency graph"""
        self.nodes[stage.id] = stage
        self.edges[stage.id] = set(stage.dependencies)
        
    def resolve_load_order(self, target_stage: int) -> list[int]:
        """Resolve load order using topological sort"""
        visited = set()
        stack = []
        
        def visit(stage_id: int):
            if stage_id in visited:
                return
            visited.add(stage_id)
            
            for dep in self.edges.get(stage_id, []):
                visit(dep)
            stack.append(stage_id)
            
        visit(target_stage)
        return stack
        
    def find_cycles(self) -> list[list[int]]:
        """Detect dependency cycles"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self.nodes}
        cycles = []
        
        def dfs(node: int, path: list[int]):
            color[node] = GRAY
            path.append(node)
            
            for neighbor in self.edges.get(node, []):
                if color[neighbor] == GRAY:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:])
                elif color[neighbor] == WHITE:
                    dfs(neighbor, path[:])
                    
            color[node] = BLACK
            
        for node in self.nodes:
            if color[node] == WHITE:
                dfs(node, [])
                
        return cycles
```

### 4.2. Lazy Resolution Algorithm

```python
class LazyStageLoader:
    def __init__(self, package: Package):
        self.package = package
        self.loaded_stages = {}
        self.loading_stages = set()
        self.stage_cache = LRUCache(max_size=256*1024*1024)
        
    async def load_stage(self, stage_id: int) -> Stage:
        """Load stage with lazy dependency resolution"""
        # Check if already loaded
        if stage_id in self.loaded_stages:
            return self.loaded_stages[stage_id]
            
        # Check if currently loading (prevent cycles)
        if stage_id in self.loading_stages:
            raise CircularDependencyError(f"Stage {stage_id}")
            
        self.loading_stages.add(stage_id)
        
        try:
            # Get stage descriptor
            descriptor = self.package.get_stage_descriptor(stage_id)
            
            # Load dependencies first
            dependencies = []
            for dep_id in descriptor.dependencies:
                dep_stage = await self.load_stage(dep_id)
                dependencies.append(dep_stage)
                
            # Check cache
            cached = self.stage_cache.get(stage_id)
            if cached and self.verify_stage(cached, descriptor):
                stage = cached
            else:
                # Load from package
                stage = await self.load_stage_data(descriptor)
                self.stage_cache.put(stage_id, stage)
                
            # Initialize stage with dependencies
            stage.initialize(dependencies)
            
            self.loaded_stages[stage_id] = stage
            return stage
            
        finally:
            self.loading_stages.remove(stage_id)
```

## 5. Progressive Loading Protocol

### 5.1. Loading State Machine

```
        ┌─────────┐
        │ INITIAL │
        └────┬────┘
             │ open_package()
             v
        ┌─────────┐
        │BOOTSTRAP│
        └────┬────┘
             │ verify_signatures()
             v
        ┌─────────┐
        │ PRIMARY │
        └────┬────┘
             │ application_ready()
             v
        ┌─────────┐
        │ RUNNING │<──────┐
        └────┬────┘       │
             │            │
     request_│            │stage_loaded()
     stage() │            │
             v            │
        ┌─────────┐       │
        │ LOADING │───────┘
        └─────────┘
```

### 5.2. Loading Protocol

```c
// Stage loading protocol
struct LoadRequest {
    uint32_t stage_id;
    uint32_t flags;
    uint64_t timeout_ms;
    void* callback;
    void* user_data;
};

struct LoadResponse {
    uint32_t stage_id;
    uint32_t status;
    uint64_t load_time_us;
    void* stage_ptr;
    uint64_t stage_size;
    char error_msg[256];
};

// Asynchronous loading API
int spa_request_stage(LoadRequest* req);
int spa_wait_stage(uint32_t stage_id, uint64_t timeout_ms);
int spa_cancel_load(uint32_t stage_id);
int spa_query_status(uint32_t stage_id, LoadResponse* resp);
```

### 5.3. Prefetching Strategy

```python
class PrefetchStrategy:
    def __init__(self, telemetry: Telemetry):
        self.telemetry = telemetry
        self.access_patterns = {}
        self.prefetch_queue = PriorityQueue()
        
    def predict_next_stages(self, current_stage: int) -> list[int]:
        """Predict which stages likely needed next"""
        predictions = []
        
        # Historical pattern analysis
        history = self.access_patterns.get(current_stage, [])
        for next_stage, probability in history:
            if probability > 0.7:  # 70% threshold
                predictions.append(next_stage)
                
        # Static analysis from manifest
        manifest = self.get_stage_manifest(current_stage)
        for hint in manifest.prefetch_hints:
            predictions.append(hint.stage_id)
            
        # Resource availability
        if self.has_idle_resources():
            # Add commonly used stages
            predictions.extend(self.get_popular_stages())
            
        return predictions[:5]  # Limit prefetch
        
    def schedule_prefetch(self, stages: list[int]):
        """Schedule background prefetch"""
        for stage_id in stages:
            priority = self.calculate_priority(stage_id)
            self.prefetch_queue.put((priority, stage_id))
            
        # Start prefetch worker if not running
        if not self.prefetch_worker_active:
            self.start_prefetch_worker()
```

## 6. Stage Activation Mechanisms

### 6.1. Activation Triggers

```python
class ActivationTrigger:
    """Base class for stage activation triggers"""
    
    def should_activate(self, context: Context) -> bool:
        raise NotImplementedError
        
class MemoryTrigger(ActivationTrigger):
    """Activate when memory pressure low"""
    
    def __init__(self, threshold_mb: int):
        self.threshold_mb = threshold_mb
        
    def should_activate(self, context: Context) -> bool:
        available_mb = context.get_available_memory() / 1024 / 1024
        return available_mb > self.threshold_mb
        
class NetworkTrigger(ActivationTrigger):
    """Activate when network conditions favorable"""
    
    def __init__(self, min_bandwidth_mbps: float):
        self.min_bandwidth_mbps = min_bandwidth_mbps
        
    def should_activate(self, context: Context) -> bool:
        bandwidth = context.measure_bandwidth()
        return bandwidth > self.min_bandwidth_mbps
        
class TimeTrigger(ActivationTrigger):
    """Activate at scheduled time"""
    
    def __init__(self, schedule: Schedule):
        self.schedule = schedule
        
    def should_activate(self, context: Context) -> bool:
        return self.schedule.is_active(context.current_time)
```

### 6.2. Hot Patching Protocol

```c
// Hot patch a running stage
struct HotPatch {
    uint32_t target_stage;
    uint32_t patch_stage;
    uint64_t patch_offset;
    uint64_t patch_size;
    uint8_t* patch_data;
    uint8_t signature[64];
};

int spa_apply_hot_patch(HotPatch* patch) {
    // Verify patch signature
    if (!verify_signature(patch)) {
        return -EINVAL;
    }
    
    // Pause target stage execution
    pause_stage(patch->target_stage);
    
    // Apply patch atomically
    void* target = get_stage_memory(patch->target_stage);
    
    // Save original for rollback
    void* backup = malloc(patch->patch_size);
    memcpy(backup, target + patch->patch_offset, patch->patch_size);
    
    // Apply patch with memory barriers
    __sync_synchronize();
    memcpy(target + patch->patch_offset, patch->patch_data, patch->patch_size);
    __sync_synchronize();
    
    // Flush instruction cache
    __builtin___clear_cache(target, target + patch->patch_size);
    
    // Resume execution
    resume_stage(patch->target_stage);
    
    return 0;
}
```

### 6.3. Stage Migration

```python
class StageMigration:
    """Migrate stages between versions"""
    
    def migrate_stage(self, 
                     old_stage: Stage,
                     new_descriptor: StageDescriptor) -> Stage:
        """Migrate stage to new version"""
        
        # Check compatibility
        if not self.is_compatible(old_stage, new_descriptor):
            raise IncompatibleStageError()
            
        # Create migration context
        context = MigrationContext(
            old_version=old_stage.version,
            new_version=new_descriptor.version,
            state_mapping=self.get_state_mapping(old_stage, new_descriptor)
        )
        
        # Pause old stage
        old_stage.pause()
        
        # Extract state
        state = old_stage.extract_state()
        
        # Load new stage
        new_stage = self.load_stage(new_descriptor)
        
        # Transform state
        transformed_state = self.transform_state(state, context)
        
        # Inject state into new stage
        new_stage.inject_state(transformed_state)
        
        # Atomic swap
        self.atomic_swap(old_stage, new_stage)
        
        # Cleanup old stage
        old_stage.cleanup()
        
        return new_stage
```

## 7. Caching and Persistence

### 7.1. Multi-Level Cache

```python
class StageCache:
    """Multi-level stage caching system"""
    
    def __init__(self):
        self.l1_cache = {}  # In-memory hot cache
        self.l2_cache = MmapCache("/tmp/spa_cache")  # Memory-mapped
        self.l3_cache = DiskCache("/var/cache/spa")  # Disk cache
        self.remote_cache = RemoteCache("https://cdn.example.com")
        
    async def get_stage(self, stage_id: int) -> Optional[Stage]:
        """Get stage from cache hierarchy"""
        
        # L1: Check memory
        if stage_id in self.l1_cache:
            self.update_lru(stage_id)
            return self.l1_cache[stage_id]
            
        # L2: Check mmap
        stage = self.l2_cache.get(stage_id)
        if stage:
            self.promote_to_l1(stage_id, stage)
            return stage
            
        # L3: Check disk
        stage = await self.l3_cache.get(stage_id)
        if stage:
            self.promote_to_l2(stage_id, stage)
            return stage
            
        # L4: Check remote
        stage = await self.remote_cache.get(stage_id)
        if stage:
            await self.l3_cache.put(stage_id, stage)
            self.promote_to_l2(stage_id, stage)
            return stage
            
        return None
        
    def evict_lru(self):
        """Evict least recently used stages"""
        while self.memory_usage() > self.max_memory:
            stage_id = self.get_lru_stage()
            
            # Demote to lower cache level
            stage = self.l1_cache.pop(stage_id)
            self.l2_cache.put(stage_id, stage)
```

### 7.2. Persistent Stage Storage

```c
// Persistent stage storage format
struct PersistentStage {
    uint32_t magic;              // 0x53544147 ('STAG')
    uint32_t version;
    uint32_t stage_id;
    uint32_t flags;
    uint64_t timestamp;
    uint64_t ttl;               // Time to live
    uint64_t compressed_size;
    uint64_t uncompressed_size;
    uint32_t checksum;
    uint32_t compression_type;
    uint8_t  signature[64];
    uint8_t  data[];            // Compressed stage data
};

// Cache database schema
CREATE TABLE stage_cache (
    stage_id INTEGER PRIMARY KEY,
    package_id TEXT NOT NULL,
    version TEXT NOT NULL,
    data BLOB NOT NULL,
    checksum INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    accessed_at INTEGER NOT NULL,
    access_count INTEGER DEFAULT 0,
    ttl INTEGER,
    size INTEGER NOT NULL,
    INDEX idx_package (package_id, version),
    INDEX idx_lru (accessed_at, size)
);
```

## 8. Security Model

### 8.1. Stage Isolation

```c
// Stage isolation using seccomp-bpf
struct sock_filter stage_filter[] = {
    // Allow essential syscalls
    BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K, __NR_read, 0, 1),
    BPF_STMT(BPF_RET|BPF_K, SECCOMP_RET_ALLOW),
    
    BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K, __NR_write, 0, 1),
    BPF_STMT(BPF_RET|BPF_K, SECCOMP_RET_ALLOW),
    
    BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K, __NR_mmap, 0, 1),
    BPF_STMT(BPF_RET|BPF_K, SECCOMP_RET_ALLOW),
    
    // Deny everything else
    BPF_STMT(BPF_RET|BPF_K, SECCOMP_RET_KILL),
};

int isolate_stage(int stage_id) {
    // Create namespace
    if (unshare(CLONE_NEWNS | CLONE_NEWPID | CLONE_NEWNET) < 0) {
        return -errno;
    }
    
    // Apply seccomp filter
    struct sock_fprog prog = {
        .len = sizeof(stage_filter) / sizeof(stage_filter[0]),
        .filter = stage_filter,
    };
    
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0) {
        return -errno;
    }
    
    if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog) < 0) {
        return -errno;
    }
    
    return 0;
}
```

### 8.2. Capability-Based Access Control

```python
class StageCapabilities:
    """Capability-based access control for stages"""
    
    # Capability flags
    CAP_NETWORK     = 0x00000001
    CAP_FILESYSTEM  = 0x00000002
    CAP_PROCESS     = 0x00000004
    CAP_MEMORY      = 0x00000008
    CAP_HARDWARE    = 0x00000010
    CAP_CRYPTO      = 0x00000020
    CAP_UI          = 0x00000040
    CAP_AUDIO       = 0x00000080
    
    def __init__(self):
        self.stage_caps = {}
        self.cap_tokens = {}
        
    def grant_capability(self, stage_id: int, capability: int) -> str:
        """Grant capability to stage"""
        # Generate capability token
        token = self.generate_token(stage_id, capability)
        
        # Store grant
        if stage_id not in self.stage_caps:
            self.stage_caps[stage_id] = 0
        self.stage_caps[stage_id] |= capability
        
        # Store token
        self.cap_tokens[token] = (stage_id, capability)
        
        return token
        
    def check_capability(self, stage_id: int, capability: int) -> bool:
        """Check if stage has capability"""
        caps = self.stage_caps.get(stage_id, 0)
        return (caps & capability) == capability
        
    def revoke_capability(self, token: str):
        """Revoke capability by token"""
        if token in self.cap_tokens:
            stage_id, capability = self.cap_tokens[token]
            self.stage_caps[stage_id] &= ~capability
            del self.cap_tokens[token]
```

### 8.3. Attestation Protocol

```python
class StageAttestation:
    """Remote attestation for stages"""
    
    def generate_attestation(self, stage: Stage) -> Attestation:
        """Generate stage attestation"""
        
        # Collect measurements
        measurements = {
            'stage_id': stage.id,
            'checksum': stage.calculate_checksum(),
            'load_address': stage.load_address,
            'size': stage.size,
            'timestamp': time.time(),
            'nonce': secrets.token_bytes(32),
        }
        
        # Platform-specific measurements
        if platform.system() == 'Linux':
            measurements['kernel'] = self.get_kernel_version()
            measurements['cpu_flags'] = self.get_cpu_flags()
            
        # Sign attestation
        attestation = Attestation(
            measurements=measurements,
            signature=self.sign_measurements(measurements),
            certificate_chain=self.get_cert_chain()
        )
        
        return attestation
        
    def verify_attestation(self, attestation: Attestation) -> bool:
        """Verify remote attestation"""
        
        # Verify certificate chain
        if not self.verify_cert_chain(attestation.certificate_chain):
            return False
            
        # Verify signature
        if not self.verify_signature(
            attestation.measurements,
            attestation.signature,
            attestation.certificate_chain[0]
        ):
            return False
            
        # Verify measurements against policy
        return self.check_policy(attestation.measurements)
```

## 9. Performance Optimization

### 9.1. Memory Layout Optimization

```c
// Optimize stage memory layout for cache efficiency
struct OptimizedStageLayout {
    // Hot path data (frequently accessed)
    struct {
        void* entry_points[8];   // Function pointers
        uint64_t flags;          // Runtime flags
        void* vtable;            // Virtual table
        uint8_t padding[40];     // Align to cache line
    } hot __attribute__((aligned(64)));
    
    // Warm data (occasionally accessed)
    struct {
        char name[256];
        uint32_t version;
        uint32_t dependencies[16];
        uint8_t padding[224];    // Align to cache line
    } warm __attribute__((aligned(64)));
    
    // Cold data (rarely accessed)
    struct {
        char description[1024];
        uint8_t signature[64];
        uint8_t metadata[4096];
    } cold __attribute__((aligned(64)));
};
```

### 9.2. Parallel Loading

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ParallelStageLoader:
    """Load multiple stages in parallel"""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.io_semaphore = asyncio.Semaphore(2)  # Limit I/O parallelism
        
    async def load_stages_parallel(self, stage_ids: list[int]) -> dict[int, Stage]:
        """Load multiple stages in parallel"""
        
        # Build dependency graph
        graph = self.build_dependency_graph(stage_ids)
        
        # Find independent stages
        levels = graph.get_parallel_levels()
        
        results = {}
        
        # Load each level in parallel
        for level in levels:
            tasks = []
            for stage_id in level:
                task = self.load_stage_async(stage_id)
                tasks.append(task)
                
            # Wait for level to complete
            level_results = await asyncio.gather(*tasks)
            
            for stage_id, stage in zip(level, level_results):
                results[stage_id] = stage
                
        return results
        
    async def load_stage_async(self, stage_id: int) -> Stage:
        """Load single stage asynchronously"""
        
        async with self.io_semaphore:
            # Read stage data from disk
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                self.executor,
                self.read_stage_data,
                stage_id
            )
            
        # Decompress in parallel
        stage = await loop.run_in_executor(
            self.executor,
            self.decompress_stage,
            data
        )
        
        # Verify in parallel
        await loop.run_in_executor(
            self.executor,
            self.verify_stage,
            stage
        )
        
        return stage
```

### 9.3. Predictive Preloading

```python
class PredictivePreloader:
    """Machine learning based stage preloading"""
    
    def __init__(self):
        self.model = self.load_model()
        self.feature_extractor = FeatureExtractor()
        self.history = deque(maxlen=1000)
        
    def predict_next_stages(self, context: Context) -> list[tuple[int, float]]:
        """Predict next stages with confidence scores"""
        
        # Extract features
        features = self.feature_extractor.extract(context)
        
        # Add temporal features
        features['time_of_day'] = context.timestamp.hour
        features['day_of_week'] = context.timestamp.weekday()
        
        # Add usage patterns
        recent_stages = [h.stage_id for h in self.history[-10:]]
        features['recent_stages'] = recent_stages
        
        # Run prediction
        predictions = self.model.predict(features)
        
        # Filter by confidence threshold
        confident_predictions = [
            (stage_id, confidence)
            for stage_id, confidence in predictions
            if confidence > 0.6
        ]
        
        return sorted(confident_predictions, key=lambda x: x[1], reverse=True)
        
    def update_model(self, actual_stage: int):
        """Update model with actual stage access"""
        self.history.append(StageAccess(
            stage_id=actual_stage,
            timestamp=time.time(),
            context=self.get_current_context()
        ))
        
        # Retrain periodically
        if len(self.history) % 100 == 0:
            self.retrain_model()
```

## 10. Platform Integration

### 10.1. Linux Integration

```c
// Linux-specific stage loading using memfd
int load_stage_linux(struct StageDescriptor* desc, void** stage_ptr) {
    // Create anonymous memory file
    int memfd = memfd_create(desc->name, MFD_CLOEXEC | MFD_ALLOW_SEALING);
    if (memfd < 0) {
        return -errno;
    }
    
    // Write stage data
    if (write(memfd, desc->data, desc->size) != desc->size) {
        close(memfd);
        return -EIO;
    }
    
    // Seal the file (make immutable)
    if (fcntl(memfd, F_ADD_SEALS, 
              F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE) < 0) {
        close(memfd);
        return -errno;
    }
    
    // Map as executable
    *stage_ptr = mmap(NULL, desc->size, 
                     PROT_READ | PROT_EXEC,
                     MAP_PRIVATE, memfd, 0);
    
    if (*stage_ptr == MAP_FAILED) {
        close(memfd);
        return -errno;
    }
    
    // Close fd (mapping persists)
    close(memfd);
    
    return 0;
}
```

### 10.2. macOS Integration

```objc
// macOS-specific stage loading with code signing
int load_stage_macos(struct StageDescriptor* desc, void** stage_ptr) {
    // Allocate memory with VM_PROT_COPY
    kern_return_t kr;
    vm_address_t addr = 0;
    vm_size_t size = desc->size;
    
    kr = vm_allocate(mach_task_self(), &addr, size, VM_FLAGS_ANYWHERE);
    if (kr != KERN_SUCCESS) {
        return -ENOMEM;
    }
    
    // Copy stage data
    memcpy((void*)addr, desc->data, desc->size);
    
    // Set protection
    kr = vm_protect(mach_task_self(), addr, size, FALSE,
                   VM_PROT_READ | VM_PROT_EXECUTE);
    if (kr != KERN_SUCCESS) {
        vm_deallocate(mach_task_self(), addr, size);
        return -EPERM;
    }
    
    // Notify dynamic linker
    dyld_register_image_state_change_handler(
        dyld_image_state_bound,
        false,
        stage_image_callback
    );
    
    *stage_ptr = (void*)addr;
    return 0;
}
```

### 10.3. Windows Integration

```c
// Windows-specific stage loading
HRESULT load_stage_windows(StageDescriptor* desc, void** stage_ptr) {
    // Allocate executable memory
    *stage_ptr = VirtualAlloc(NULL, desc->size,
                             MEM_COMMIT | MEM_RESERVE,
                             PAGE_EXECUTE_READWRITE);
    
    if (*stage_ptr == NULL) {
        return HRESULT_FROM_WIN32(GetLastError());
    }
    
    // Copy stage data
    memcpy(*stage_ptr, desc->data, desc->size);
    
    // Change protection to execute-only
    DWORD old_protect;
    if (!VirtualProtect(*stage_ptr, desc->size,
                       PAGE_EXECUTE_READ, &old_protect)) {
        VirtualFree(*stage_ptr, 0, MEM_RELEASE);
        return HRESULT_FROM_WIN32(GetLastError());
    }
    
    // Flush instruction cache
    FlushInstructionCache(GetCurrentProcess(), *stage_ptr, desc->size);
    
    return S_OK;
}
```

## 11. Monitoring and Telemetry

### 11.1. Stage Metrics

```python
@dataclass
class StageMetrics:
    """Runtime metrics for stages"""
    stage_id: int
    load_count: int = 0
    total_load_time_us: int = 0
    average_load_time_us: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage_bytes: int = 0
    cpu_usage_percent: float = 0.0
    last_accessed: float = 0.0
    error_count: int = 0
    
    def update_load_time(self, duration_us: int):
        self.load_count += 1
        self.total_load_time_us += duration_us
        self.average_load_time_us = self.total_load_time_us / self.load_count
        self.last_accessed = time.time()
        
    def update_cache_hit(self, hit: bool):
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            
    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
```

### 11.2. Telemetry Collection

```python
class StageTelemetry:
    """Collect and report stage telemetry"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.metrics = {}
        self.events = deque(maxlen=10000)
        self.upload_interval = 300  # 5 minutes
        
    def record_stage_event(self, event: StageEvent):
        """Record stage lifecycle event"""
        self.events.append({
            'timestamp': time.time(),
            'stage_id': event.stage_id,
            'event_type': event.type,
            'duration_us': event.duration_us,
            'success': event.success,
            'metadata': event.metadata
        })
        
        # Update metrics
        if event.stage_id not in self.metrics:
            self.metrics[event.stage_id] = StageMetrics(stage_id=event.stage_id)
            
        metrics = self.metrics[event.stage_id]
        
        if event.type == 'LOAD':
            metrics.update_load_time(event.duration_us)
        elif event.type == 'CACHE_HIT':
            metrics.update_cache_hit(True)
        elif event.type == 'CACHE_MISS':
            metrics.update_cache_hit(False)
        elif event.type == 'ERROR':
            metrics.error_count += 1
            
    async def upload_telemetry(self):
        """Upload telemetry to endpoint"""
        payload = {
            'version': '2025.1.0',
            'timestamp': time.time(),
            'metrics': [asdict(m) for m in self.metrics.values()],
            'events': list(self.events)
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.endpoint, json=payload) as resp:
                    if resp.status == 200:
                        self.events.clear()
        except Exception as e:
            logger.error(f"Failed to upload telemetry: {e}")
```

## 12. Implementation Requirements

### 12.1. Launcher Requirements

Launchers implementing SPA MUST:

1. Support progressive stage loading
2. Implement dependency resolution
3. Provide stage isolation mechanisms
4. Support hot patching
5. Implement caching strategies
6. Collect telemetry data
7. Handle network failures gracefully
8. Support offline operation

### 12.2. Builder Requirements

Builders creating SPA packages MUST:

1. Generate stage manifests
2. Calculate dependency graphs
3. Optimize stage boundaries
4. Sign individual stages
5. Generate prefetch hints
6. Create activation policies
7. Embed telemetry hooks
8. Support incremental updates

### 12.3. Runtime Requirements

The SPA runtime MUST:

1. Memory-map stages efficiently
2. Implement W^X protection
3. Support atomic stage swaps
4. Handle concurrent loading
5. Implement garbage collection
6. Support debugging interfaces
7. Provide performance counters
8. Enable security auditing

## 13. Test Vectors

### 13.1. Stage Manifest Test Vector

```json
{
  "test_vector": "spa_manifest_v1",
  "input": {
    "stages": [
      {
        "id": 0,
        "name": "bootstrap",
        "slots": [0],
        "size": 65536,
        "checksum": "0x12345678"
      },
      {
        "id": 1,
        "name": "main",
        "slots": [1, 2],
        "size": 131072,
        "checksum": "0x87654321",
        "dependencies": [0]
      }
    ]
  },
  "expected_output": {
    "load_order": [0, 1],
    "total_size": 196608,
    "dependency_depth": 2
  }
}
```

### 13.2. Dependency Resolution Test

```python
def test_dependency_resolution():
    """Test dependency resolution algorithm"""
    
    # Create test stages
    stages = [
        StageDescriptor(id=0, dependencies=[]),
        StageDescriptor(id=1, dependencies=[0]),
        StageDescriptor(id=2, dependencies=[0, 1]),
        StageDescriptor(id=3, dependencies=[1]),
        StageDescriptor(id=4, dependencies=[2, 3])
    ]
    
    # Build graph
    graph = DependencyGraph()
    for stage in stages:
        graph.add_stage(stage)
        
    # Test resolution
    order = graph.resolve_load_order(4)
    assert order == [0, 1, 2, 3, 4]
    
    # Test cycle detection
    stages_with_cycle = [
        StageDescriptor(id=0, dependencies=[2]),
        StageDescriptor(id=1, dependencies=[0]),
        StageDescriptor(id=2, dependencies=[1])
    ]
    
    graph_cycle = DependencyGraph()
    for stage in stages_with_cycle:
        graph_cycle.add_stage(stage)
        
    cycles = graph_cycle.find_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {0, 1, 2}
```

## 14. Security Considerations

### 14.1. Attack Vectors

1. **Stage Injection**: Attacker replaces legitimate stage
   - Mitigation: Cryptographic verification of all stages

2. **Dependency Confusion**: Attacker manipulates dependency graph
   - Mitigation: Signed dependency manifests

3. **Cache Poisoning**: Attacker corrupts cached stages
   - Mitigation: Integrity checks on cache access

4. **Memory Disclosure**: Attacker reads other stage memory
   - Mitigation: Process isolation and ASLR

5. **Timing Attacks**: Attacker infers stage contents via timing
   - Mitigation: Constant-time operations for sensitive paths

### 14.2. Security Requirements

1. All stages MUST be cryptographically signed
2. Stage signatures MUST be verified before execution
3. Stages MUST run with minimal privileges
4. Inter-stage communication MUST be authenticated
5. Cache entries MUST include integrity checks
6. Hot patches MUST be signed by trusted authority
7. Telemetry MUST NOT leak sensitive information
8. Debug interfaces MUST be disabled in production

## 15. IANA Considerations

This document requests IANA registration of:

1. **Media Type**: `application/vnd.pspf.spa+json`
   - For SPA manifest files

2. **URI Scheme**: `spa://`
   - For referencing stages within packages

3. **Well-Known URI**: `/.well-known/spa-manifest`
   - For discovering SPA capabilities

## 16. References

### 16.1. Normative References

- [RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html) Key words for use in RFCs
- [FEP-0001] PSPF Core Format Specification
- [FEP-0004] Supply Chain JIT Compilation
- [FEP-0005] Runtime JIT Loading

### 16.2. Informative References

- [ASLR] Address Space Layout Randomization
- [CFI] Control Flow Integrity
- [W^X] Write XOR Execute Protection
- [SECCOMP] Secure Computing Mode

---

**Document Version**: 2025.1.0  
**Last Updated**: 2025-01-11  
**Status**: Future (Post-v1.0)  
**Implementation Timeline**: 2026+