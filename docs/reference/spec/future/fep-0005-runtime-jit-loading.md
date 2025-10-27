# FEP-0005: PSPF/2025 Runtime Just-In-Time Loading

**Status**: Experimental  
**Type**: Standards Track  
**Created**: 2025-01-08  
**Version**: v0.1  
**Category**: Future Enhancement  
**Target**: PSPF/2025 v1.5

## Abstract

This document specifies the Runtime Just-In-Time (JIT) loading system for PSPF/2025 packages. Runtime JIT enables dynamic loading, compilation, and optimization of package components during execution, reducing startup time and memory usage while enabling adaptive optimization based on runtime behavior. Unlike Supply Chain JIT which operates at distribution time, Runtime JIT operates within the executing process to provide fine-grained, adaptive code loading and optimization.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Lazy Loading Mechanisms](#3-lazy-loading-mechanisms)
4. [Runtime Compilation Pipeline](#4-runtime-compilation-pipeline)
5. [Memory Management](#5-memory-management)
6. [Profile-Guided Runtime Optimization](#6-profile-guided-runtime-optimization)
7. [Slot Loading Strategies](#7-slot-loading-strategies)
8. [Native Code Cache](#8-native-code-cache)
9. [Security Model](#9-security-model)
10. [Performance Monitoring](#10-performance-monitoring)
11. [Implementation Requirements](#11-implementation-requirements)
12. [Platform Integration](#12-platform-integration)
13. [Debugging and Diagnostics](#13-debugging-and-diagnostics)
14. [References](#14-references)

## 1. Introduction

### 1.1 Motivation

Modern applications face conflicting requirements:
- **Fast Startup**: Users expect immediate responsiveness
- **Low Memory**: Devices have limited RAM, especially mobile/embedded
- **High Performance**: CPU-intensive operations need optimization
- **Large Codebases**: Applications include extensive functionality

Runtime JIT resolves these conflicts through:
- **Lazy Loading**: Load code only when needed
- **Tiered Compilation**: Start with interpreter, compile hot code
- **Adaptive Optimization**: Optimize based on actual usage patterns
- **Memory Pressure Response**: Unload cold code under memory pressure

### 1.2 Design Principles

1. **Pay-As-You-Go**: Only load and compile what's actually used
2. **Progressive Performance**: Start fast, get faster over time
3. **Adaptive Behavior**: Optimize based on runtime profiling
4. **Graceful Degradation**: Function correctly under resource constraints
5. **Transparent Operation**: No changes to application logic required

### 1.3 Compilation Tiers

```
Tier 0: Bytecode Interpreter     (Instant startup, slow execution)
  ↓
Tier 1: Baseline JIT              (Fast compilation, moderate speed)
  ↓
Tier 2: Optimizing JIT            (Slow compilation, fast execution)
  ↓
Tier 3: Profile-Guided Recompile  (Adaptive optimization)
```

## 2. Architecture Overview

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        PSPF Package                          │
├─────────────────────────────────────────────────────────────┤
│                     Native Launcher                          │
├─────────────────────────────────────────────────────────────┤
│                    Runtime JIT Engine                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Loader  │  │ Compiler │  │ Profiler │  │  Cache   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
├─────────────────────────────────────────────────────────────┤
│                      Slot Manager                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Slot 0  │  │  Slot 1  │  │  Slot 2  │  │  Slot N  │  │
│  │  LOADED  │  │  LAZY    │  │  LAZY    │  │  LAZY    │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Loading State Machine

```
         ┌─────────┐
         │ DORMANT │ Package not yet accessed
         └────┬────┘
              │ First access
         ┌────▼────┐
         │ LOADING │ Reading from disk/network
         └────┬────┘
              │ Loaded to memory
         ┌────▼────┐
         │ STAGED  │ In memory, not compiled
         └────┬────┘
              │ First execution
         ┌────▼────┐
         │TIER_0   │ Interpreted/Baseline
         └────┬────┘
              │ Hot threshold reached
         ┌────▼────┐
         │TIER_1   │ Optimized JIT
         └────┬────┘
              │ Profile data collected
         ┌────▼────┐
         │TIER_2   │ Profile-guided optimized
         └─────────┘
```

### 2.3 Memory Layout

```c
struct RuntimeSlot {
    // Slot Metadata
    uint32_t slot_id;
    uint32_t state;           // DORMANT|LOADING|STAGED|TIER_0|TIER_1|TIER_2
    
    // Memory Pointers
    void *compressed_data;    // Original compressed slot data
    void *staged_data;        // Decompressed but not compiled
    void *compiled_code;      // JIT compiled native code
    
    // Profiling Data
    uint64_t access_count;    // Number of times accessed
    uint64_t exec_count;      // Number of times executed
    uint64_t total_time;      // Total execution time
    uint8_t *heat_map;        // Per-function heat map
    
    // Memory Management
    size_t compressed_size;
    size_t staged_size;
    size_t compiled_size;
    uint64_t last_access;     // For LRU eviction
    
    // JIT Metadata
    void *jit_context;        // Language-specific JIT context
    void *profile_data;       // Collected profile information
    uint32_t tier;            // Current compilation tier
    uint32_t flags;           // Loading/compilation flags
};
```

## 3. Lazy Loading Mechanisms

### 3.1 Slot Access Hooks

```c
// Lazy loading through access hooks
void* get_slot_function(uint32_t slot_id, const char *symbol) {
    RuntimeSlot *slot = &slots[slot_id];
    
    // Check if slot needs loading
    if (slot->state == DORMANT) {
        load_slot(slot);
    }
    
    // Check if compilation needed
    if (slot->state == STAGED) {
        compile_tier_0(slot);
    }
    
    // Check if optimization warranted
    if (should_optimize(slot)) {
        schedule_optimization(slot);
    }
    
    // Return function pointer
    return resolve_symbol(slot, symbol);
}
```

### 3.2 Import Resolution

```python
# Python lazy import mechanism
class LazySlotImporter:
    def __init__(self, package):
        self.package = package
        self.loaded_slots = {}
        
    def find_module(self, fullname):
        if self.package.has_slot(fullname):
            return self
        return None
        
    def load_module(self, fullname):
        if fullname in self.loaded_slots:
            return self.loaded_slots[fullname]
            
        # Trigger JIT loading
        slot_data = self.package.load_slot_jit(fullname)
        module = self.compile_module(slot_data)
        
        self.loaded_slots[fullname] = module
        return module
```

### 3.3 Memory-Mapped Loading

```c
// Memory-mapped lazy loading for large slots
struct MMapSlot {
    int fd;                   // File descriptor
    off_t offset;            // Offset in package file
    size_t size;             // Slot size
    void *base;              // mmap base address
    
    // Page fault tracking
    uint8_t *page_bitmap;    // Which pages have been faulted in
    size_t pages_loaded;     // Number of pages in memory
    size_t total_pages;      // Total pages in slot
};

void* mmap_slot_lazy(uint32_t slot_id) {
    MMapSlot *slot = &mmap_slots[slot_id];
    
    // Map with PROT_NONE initially
    slot->base = mmap(NULL, slot->size, 
                      PROT_NONE, MAP_PRIVATE,
                      slot->fd, slot->offset);
    
    // Install SIGSEGV handler for page faults
    install_page_fault_handler(slot);
    
    return slot->base;
}

void page_fault_handler(int sig, siginfo_t *info, void *context) {
    void *fault_addr = info->si_addr;
    MMapSlot *slot = find_slot_for_address(fault_addr);
    
    if (slot) {
        // Make page readable on first access
        size_t page_num = ((char*)fault_addr - (char*)slot->base) / PAGE_SIZE;
        mprotect(fault_addr, PAGE_SIZE, PROT_READ);
        
        // Track page access for profiling
        slot->page_bitmap[page_num] = 1;
        slot->pages_loaded++;
        
        // Consider JIT compilation if hot
        if (is_hot_page(slot, page_num)) {
            schedule_jit_compile(slot, page_num);
        }
    }
}
```

## 4. Runtime Compilation Pipeline

### 4.1 Tiered Compilation Strategy

```c
enum CompilationTier {
    TIER_INTERPRETER = 0,  // Bytecode interpreter
    TIER_BASELINE = 1,      // Quick baseline JIT
    TIER_OPTIMIZED = 2,     // Full optimization
    TIER_PROFILE_GUIDED = 3 // PGO recompilation
};

struct TierThresholds {
    uint32_t baseline_threshold;      // Calls before baseline JIT
    uint32_t optimize_threshold;      // Calls before optimization
    uint32_t profile_threshold;       // Calls before profiling
    uint32_t recompile_threshold;     // Profile samples before recompile
};

// Default thresholds
const struct TierThresholds default_thresholds = {
    .baseline_threshold = 10,         // Compile after 10 calls
    .optimize_threshold = 100,        // Optimize after 100 calls
    .profile_threshold = 1000,        // Profile after 1000 calls
    .recompile_threshold = 10000      // Recompile after 10K samples
};
```

### 4.2 JIT Compilation Request

```c
struct JITRequest {
    // Source Information
    uint32_t slot_id;
    void *bytecode;
    size_t bytecode_size;
    
    // Compilation Options
    enum CompilationTier tier;
    uint32_t optimization_level;
    bool generate_debug_info;
    
    // Profile Data (if available)
    void *profile_data;
    size_t profile_size;
    
    // Output
    void *native_code;
    size_t native_size;
    void *debug_info;
    
    // Timing
    uint64_t queued_time;
    uint64_t start_time;
    uint64_t end_time;
};

void* compile_jit(struct JITRequest *req) {
    switch (req->tier) {
        case TIER_BASELINE:
            return compile_baseline(req);
            
        case TIER_OPTIMIZED:
            return compile_optimized(req);
            
        case TIER_PROFILE_GUIDED:
            return compile_with_profile(req);
            
        default:
            return NULL;
    }
}
```

### 4.3 Inline Caching

```c
// Inline cache for dynamic dispatch
struct InlineCache {
    void *cached_target;      // Cached function pointer
    uint32_t cached_class;    // Cached object class/type
    uint32_t hit_count;       // Cache hit counter
    uint32_t miss_count;      // Cache miss counter
};

void* ic_dispatch(void *object, uint32_t method_id, struct InlineCache *ic) {
    uint32_t object_class = get_object_class(object);
    
    // Fast path: cache hit
    if (ic->cached_class == object_class) {
        ic->hit_count++;
        return ic->cached_target;
    }
    
    // Slow path: cache miss
    ic->miss_count++;
    void *target = lookup_method(object_class, method_id);
    
    // Update cache if stable
    if (ic->miss_count < 5) {  // Megamorphic threshold
        ic->cached_class = object_class;
        ic->cached_target = target;
    }
    
    return target;
}
```

### 4.4 Deoptimization

```c
// Deoptimization when assumptions are violated
struct DeoptimizationPoint {
    void *native_pc;          // Native code location
    void *bytecode_pc;        // Corresponding bytecode location
    void *frame_state;        // Saved frame state
    char *reason;             // Deopt reason for debugging
};

void deoptimize(struct DeoptimizationPoint *deopt) {
    // Log deoptimization for profiling
    log_deopt(deopt->reason, deopt->native_pc);
    
    // Restore interpreter state
    restore_frame_state(deopt->frame_state);
    
    // Mark code for recompilation
    mark_for_recompilation(deopt->native_pc);
    
    // Continue in interpreter
    interpret_from(deopt->bytecode_pc);
}
```

## 5. Memory Management

### 5.1 Memory Pressure Response

```c
struct MemoryManager {
    size_t total_memory;      // Total available memory
    size_t used_memory;       // Currently used memory
    size_t jit_cache_size;    // Size of JIT code cache
    size_t pressure_threshold; // Memory pressure threshold
    
    // LRU tracking
    struct SlotLRU {
        uint32_t slot_id;
        uint64_t last_access;
        struct SlotLRU *next;
        struct SlotLRU *prev;
    } *lru_head, *lru_tail;
};

void handle_memory_pressure(struct MemoryManager *mm) {
    // Level 1: Evict cold compiled code
    if (mm->used_memory > mm->pressure_threshold * 0.7) {
        evict_cold_code(mm, mm->jit_cache_size * 0.3);
    }
    
    // Level 2: Evict staged data
    if (mm->used_memory > mm->pressure_threshold * 0.85) {
        evict_staged_slots(mm, mm->used_memory * 0.2);
    }
    
    // Level 3: Disable JIT compilation
    if (mm->used_memory > mm->pressure_threshold * 0.95) {
        disable_jit_compilation();
        force_interpreter_mode();
    }
    
    // Level 4: Emergency GC
    if (mm->used_memory > mm->pressure_threshold) {
        emergency_garbage_collection();
    }
}
```

### 5.2 Code Cache Management

```c
struct CodeCache {
    // Memory regions
    void *executable_base;    // Base of executable memory
    size_t total_size;       // Total cache size
    size_t used_size;        // Currently used
    
    // Allocation tracking
    struct CodeBlock {
        void *address;
        size_t size;
        uint32_t slot_id;
        uint32_t tier;
        uint64_t last_exec;
        struct CodeBlock *next;
    } *blocks;
    
    // Statistics
    uint64_t allocations;
    uint64_t deallocations;
    uint64_t compactions;
};

void* allocate_code(struct CodeCache *cache, size_t size) {
    // Try simple allocation
    if (cache->used_size + size <= cache->total_size) {
        void *result = cache->executable_base + cache->used_size;
        cache->used_size += size;
        return result;
    }
    
    // Try compaction
    compact_code_cache(cache);
    if (cache->used_size + size <= cache->total_size) {
        void *result = cache->executable_base + cache->used_size;
        cache->used_size += size;
        return result;
    }
    
    // Evict cold code
    evict_cold_code_blocks(cache, size);
    return allocate_code(cache, size);  // Retry
}
```

### 5.3 Garbage Collection Integration

```python
# Integration with Python GC
import gc
import weakref

class JITCodeManager:
    def __init__(self):
        self.code_cache = {}
        self.weak_refs = {}
        
        # Register with GC
        gc.callbacks.append(self.gc_callback)
        
    def compile_function(self, func):
        # Compile and cache
        native_code = self.jit_compile(func)
        self.code_cache[func] = native_code
        
        # Track with weak reference
        def cleanup(ref):
            del self.code_cache[func]
            self.free_native_code(native_code)
            
        self.weak_refs[func] = weakref.ref(func, cleanup)
        
    def gc_callback(self, phase):
        if phase == 'start':
            # Prepare for GC
            self.flush_inline_caches()
        elif phase == 'stop':
            # Compact after GC
            self.compact_code_cache()
```

## 6. Profile-Guided Runtime Optimization

### 6.1 Profiling Infrastructure

```c
struct ProfileData {
    // Basic block profiling
    struct BasicBlockProfile {
        uint32_t block_id;
        uint64_t exec_count;
        uint64_t total_cycles;
        uint32_t branch_taken;
        uint32_t branch_not_taken;
    } *blocks;
    size_t num_blocks;
    
    // Call profiling
    struct CallProfile {
        uint32_t caller_id;
        uint32_t callee_id;
        uint64_t call_count;
        uint32_t inline_benefit;  // Estimated benefit of inlining
    } *calls;
    size_t num_calls;
    
    // Type profiling
    struct TypeProfile {
        uint32_t site_id;
        uint32_t observed_types[8];
        uint32_t type_counts[8];
        uint32_t num_types;
    } *types;
    size_t num_types;
};

void collect_profile(void *code, struct ProfileData *profile) {
    // Instrument code with profiling callbacks
    instrument_basic_blocks(code, profile);
    instrument_call_sites(code, profile);
    instrument_type_checks(code, profile);
}
```

### 6.2 Optimization Decisions

```c
struct OptimizationPlan {
    // Inlining decisions
    struct InlineDecision {
        uint32_t call_site;
        uint32_t callee;
        float benefit_ratio;
        bool should_inline;
    } *inlining;
    
    // Specialization decisions
    struct SpecializationDecision {
        uint32_t function;
        uint32_t parameter;
        uint32_t specialized_type;
        bool should_specialize;
    } *specialization;
    
    // Layout decisions
    struct LayoutDecision {
        uint32_t *hot_blocks;
        uint32_t *cold_blocks;
        size_t num_hot;
        size_t num_cold;
    } layout;
};

struct OptimizationPlan* analyze_profile(struct ProfileData *profile) {
    struct OptimizationPlan *plan = allocate_plan();
    
    // Analyze inlining opportunities
    for (int i = 0; i < profile->num_calls; i++) {
        struct CallProfile *call = &profile->calls[i];
        float benefit = estimate_inline_benefit(call);
        
        if (benefit > INLINE_THRESHOLD) {
            add_inline_decision(plan, call->caller_id, 
                              call->callee_id, benefit);
        }
    }
    
    // Analyze type specialization
    for (int i = 0; i < profile->num_types; i++) {
        struct TypeProfile *type = &profile->types[i];
        
        if (type->num_types == 1) {  // Monomorphic
            add_specialization(plan, type->site_id, 
                             type->observed_types[0]);
        }
    }
    
    // Analyze code layout
    identify_hot_cold_split(profile, plan);
    
    return plan;
}
```

### 6.3 Speculative Optimization

```c
// Speculative optimization with guards
struct SpeculativeOpt {
    enum OptType {
        TYPE_GUARD,      // Type specialization
        NULL_CHECK,      // Null check elimination
        BOUNDS_CHECK,    // Array bounds check
        OVERFLOW_CHECK   // Integer overflow check
    } type;
    
    void *guard_address;     // Location of guard check
    void *slow_path;        // Deopt/slow path target
    uint32_t success_count;  // Successful speculations
    uint32_t failure_count;  // Failed speculations
};

void* generate_speculative_code(struct SpeculativeOpt *opt) {
    void *code = allocate_code();
    
    // Generate guard
    emit_guard(code, opt);
    
    // Generate fast path (assuming guard passes)
    emit_fast_path(code);
    
    // Generate slow path stub
    emit_slow_path_stub(code, opt->slow_path);
    
    return code;
}

void update_speculation_stats(struct SpeculativeOpt *opt, bool success) {
    if (success) {
        opt->success_count++;
    } else {
        opt->failure_count++;
        
        // Deoptimize if speculation failing too often
        if (opt->failure_count > opt->success_count * 0.1) {
            deoptimize_speculation(opt);
        }
    }
}
```

## 7. Slot Loading Strategies

### 7.1 Loading Priority Matrix

```c
enum LoadPriority {
    PRIORITY_CRITICAL = 0,   // Load immediately
    PRIORITY_HIGH = 1,       // Load on startup
    PRIORITY_NORMAL = 2,     // Load on first use
    PRIORITY_LOW = 3,        // Load lazily
    PRIORITY_OPTIONAL = 4    // May never load
};

struct SlotLoadStrategy {
    uint32_t slot_id;
    enum LoadPriority priority;
    
    // Loading triggers
    bool load_on_startup;
    bool load_on_import;
    bool load_on_access;
    bool load_on_memory_available;
    
    // Compilation strategy
    bool compile_immediately;
    bool compile_on_first_call;
    uint32_t compile_threshold;
    
    // Memory strategy
    bool keep_staged;
    bool keep_compiled;
    bool allow_eviction;
};

// Determine loading strategy based on metadata
struct SlotLoadStrategy determine_strategy(struct SlotMetadata *meta) {
    struct SlotLoadStrategy strategy = {0};
    
    // Critical slots (main entry points)
    if (meta->lifecycle == LIFECYCLE_STARTUP) {
        strategy.priority = PRIORITY_CRITICAL;
        strategy.load_on_startup = true;
        strategy.compile_immediately = true;
        strategy.keep_compiled = true;
    }
    // Hot path slots (frequently used)
    else if (meta->access_frequency > HOT_THRESHOLD) {
        strategy.priority = PRIORITY_HIGH;
        strategy.load_on_startup = true;
        strategy.compile_on_first_call = true;
        strategy.compile_threshold = 1;
    }
    // Normal slots (on-demand)
    else if (meta->lifecycle == LIFECYCLE_RUNTIME) {
        strategy.priority = PRIORITY_NORMAL;
        strategy.load_on_access = true;
        strategy.compile_threshold = 10;
        strategy.allow_eviction = true;
    }
    // Cold slots (rarely used)
    else {
        strategy.priority = PRIORITY_LOW;
        strategy.load_on_access = true;
        strategy.compile_threshold = 100;
        strategy.allow_eviction = true;
    }
    
    return strategy;
}
```

### 7.2 Predictive Preloading

```python
# Machine learning based preloading
import numpy as np
from sklearn.ensemble import RandomForestClassifier

class PredictiveLoader:
    def __init__(self):
        self.model = RandomForestClassifier()
        self.access_history = []
        
    def record_access(self, slot_id, context):
        """Record slot access for training."""
        self.access_history.append({
            'slot_id': slot_id,
            'time': time.time(),
            'prev_slot': context.get('prev_slot'),
            'call_stack_depth': len(context.get('stack', [])),
            'memory_pressure': context.get('memory_pressure', 0),
        })
        
    def train_model(self):
        """Train prediction model on access history."""
        if len(self.access_history) < 1000:
            return
            
        # Prepare training data
        X, y = self.prepare_training_data()
        self.model.fit(X, y)
        
    def predict_next_slots(self, current_slot, context, n=3):
        """Predict next N slots likely to be accessed."""
        features = self.extract_features(current_slot, context)
        probabilities = self.model.predict_proba([features])[0]
        
        # Get top N predictions
        top_slots = np.argsort(probabilities)[-n:]
        return top_slots[probabilities[top_slots] > 0.5]
        
    def preload_predicted(self, predictions):
        """Asynchronously preload predicted slots."""
        for slot_id in predictions:
            if not is_loaded(slot_id):
                schedule_async_load(slot_id, priority=PRIORITY_LOW)
```

### 7.3 Dependency Graph Loading

```c
// Load slots based on dependency graph
struct SlotDependency {
    uint32_t slot_id;
    uint32_t *dependencies;
    size_t num_deps;
    uint32_t *dependents;
    size_t num_dependents;
};

void load_with_dependencies(uint32_t slot_id) {
    struct SlotDependency *dep = get_dependencies(slot_id);
    
    // Build loading order (topological sort)
    uint32_t *load_order = topological_sort(dep);
    
    // Load dependencies first
    for (int i = 0; i < dep->num_deps; i++) {
        if (!is_loaded(dep->dependencies[i])) {
            load_slot(dep->dependencies[i]);
        }
    }
    
    // Load target slot
    load_slot(slot_id);
    
    // Optionally preload likely dependents
    for (int i = 0; i < dep->num_dependents; i++) {
        if (should_preload(dep->dependents[i])) {
            schedule_async_load(dep->dependents[i]);
        }
    }
}
```

## 8. Native Code Cache

### 8.1 Persistent Code Cache

```c
struct PersistentCache {
    char cache_dir[PATH_MAX];
    int cache_fd;
    
    // Cache index
    struct CacheEntry {
        uint8_t key[32];      // SHA-256 of source
        off_t offset;         // Offset in cache file
        size_t size;          // Size of cached code
        uint32_t version;     // Compiler version
        uint32_t flags;       // Compilation flags
        time_t timestamp;     // Creation time
    } *entries;
    size_t num_entries;
};

void* load_from_cache(struct PersistentCache *cache, 
                      const uint8_t *source_hash) {
    // Look up in cache index
    struct CacheEntry *entry = find_cache_entry(cache, source_hash);
    if (!entry) {
        return NULL;
    }
    
    // Validate cache entry
    if (!validate_cache_entry(entry)) {
        invalidate_cache_entry(cache, entry);
        return NULL;
    }
    
    // Memory map cached code
    void *code = mmap(NULL, entry->size, 
                     PROT_READ | PROT_EXEC, MAP_PRIVATE,
                     cache->cache_fd, entry->offset);
    
    // Relocate if necessary
    relocate_cached_code(code, entry);
    
    return code;
}

void save_to_cache(struct PersistentCache *cache,
                  const uint8_t *source_hash,
                  const void *code, size_t size) {
    // Allocate cache space
    off_t offset = allocate_cache_space(cache, size);
    
    // Write code to cache
    pwrite(cache->cache_fd, code, size, offset);
    
    // Update cache index
    add_cache_entry(cache, source_hash, offset, size);
    
    // Persist index
    sync_cache_index(cache);
}
```

### 8.2 Cache Validation

```c
struct CacheValidation {
    uint32_t magic;           // Cache file magic number
    uint32_t version;         // Cache format version
    uint8_t compiler_hash[32]; // Hash of compiler binary
    uint8_t flags_hash[32];   // Hash of compilation flags
    uint8_t source_hash[32];  // Hash of source code
    uint8_t code_hash[32];    // Hash of compiled code
};

bool validate_cached_code(const void *code, size_t size,
                         struct CacheValidation *validation) {
    // Check magic and version
    if (validation->magic != CACHE_MAGIC ||
        validation->version != CACHE_VERSION) {
        return false;
    }
    
    // Verify compiler hasn't changed
    uint8_t current_compiler_hash[32];
    hash_compiler(current_compiler_hash);
    if (memcmp(validation->compiler_hash, 
               current_compiler_hash, 32) != 0) {
        return false;
    }
    
    // Verify code integrity
    uint8_t computed_hash[32];
    sha256(code, size, computed_hash);
    if (memcmp(validation->code_hash, computed_hash, 32) != 0) {
        return false;
    }
    
    return true;
}
```

### 8.3 Cross-Process Code Sharing

```c
// Shared memory code cache for multiple processes
struct SharedCodeCache {
    // Shared memory segment
    int shm_fd;
    void *shm_base;
    size_t shm_size;
    
    // Synchronization
    pthread_mutex_t *mutex;
    pthread_cond_t *cond;
    
    // Reference counting
    struct RefCount {
        uint32_t slot_id;
        uint32_t process_count;
        uint32_t thread_count;
    } *refcounts;
};

void* get_shared_code(struct SharedCodeCache *cache, uint32_t slot_id) {
    pthread_mutex_lock(cache->mutex);
    
    // Check if already compiled by another process
    void *code = find_shared_code(cache, slot_id);
    if (code) {
        increment_refcount(cache, slot_id);
        pthread_mutex_unlock(cache->mutex);
        return code;
    }
    
    // Compile and add to shared cache
    code = compile_slot(slot_id);
    add_to_shared_cache(cache, slot_id, code);
    
    pthread_mutex_unlock(cache->mutex);
    return code;
}
```

## 9. Security Model

### 9.1 JIT Security Hardening

```c
struct JITSecurity {
    // W^X enforcement
    bool enforce_wx_exclusive;    // Never W+X simultaneously
    
    // Control Flow Integrity
    bool enable_cfi;              // Control flow integrity
    bool enable_cet;              // Intel CET support
    
    // Address Space Layout
    bool randomize_jit_base;      // ASLR for JIT code
    size_t guard_page_size;       // Guard pages around JIT code
    
    // Code Signing
    bool require_signed_code;     // Only execute signed code
    uint8_t trusted_keys[10][32]; // Trusted signing keys
};

void* secure_jit_allocate(size_t size, struct JITSecurity *sec) {
    // Allocate with guard pages
    size_t total_size = size + (2 * sec->guard_page_size);
    void *region = mmap(NULL, total_size, PROT_NONE, 
                       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    
    // Randomize within allocated region if requested
    void *code_base = region + sec->guard_page_size;
    if (sec->randomize_jit_base) {
        size_t offset = random() % sec->guard_page_size;
        code_base += offset & ~0xF;  // Align to 16 bytes
    }
    
    // Initially writable for compilation
    mprotect(code_base, size, PROT_READ | PROT_WRITE);
    
    return code_base;
}

void secure_jit_finalize(void *code, size_t size, struct JITSecurity *sec) {
    // Sign code if required
    if (sec->require_signed_code) {
        sign_jit_code(code, size);
    }
    
    // Add CFI markers
    if (sec->enable_cfi) {
        add_cfi_checks(code, size);
    }
    
    // Make executable, remove write
    mprotect(code, size, PROT_READ | PROT_EXEC);
    
    // Flush instruction cache
    __builtin___clear_cache(code, code + size);
}
```

### 9.2 Sandboxed JIT Compilation

```c
// Sandbox JIT compiler for untrusted code
struct JITSandbox {
    // Process isolation
    pid_t compiler_pid;
    int stdin_pipe[2];
    int stdout_pipe[2];
    
    // Resource limits
    struct rlimit cpu_limit;
    struct rlimit memory_limit;
    struct rlimit file_limit;
    
    // Seccomp filter
    struct sock_fprog *seccomp_filter;
};

void* sandboxed_compile(const void *bytecode, size_t size,
                       struct JITSandbox *sandbox) {
    // Fork compiler process
    sandbox->compiler_pid = fork();
    
    if (sandbox->compiler_pid == 0) {
        // Child: Set up sandbox
        setup_sandbox(sandbox);
        
        // Read bytecode from pipe
        void *input = read_from_pipe(sandbox->stdin_pipe[0], size);
        
        // Compile
        void *output = compile_bytecode(input, size);
        
        // Write result to pipe
        write_to_pipe(sandbox->stdout_pipe[1], output);
        
        exit(0);
    }
    
    // Parent: Send bytecode
    write(sandbox->stdin_pipe[1], bytecode, size);
    
    // Wait for result with timeout
    void *result = read_with_timeout(sandbox->stdout_pipe[0], 
                                    COMPILE_TIMEOUT);
    
    // Clean up compiler process
    kill(sandbox->compiler_pid, SIGTERM);
    waitpid(sandbox->compiler_pid, NULL, 0);
    
    return result;
}
```

### 9.3 JIT Spray Mitigation

```c
// Prevent JIT spray attacks
struct JITSprayDefense {
    // Constant blinding
    bool blind_constants;         // Randomize embedded constants
    uint32_t blinding_key;        // XOR key for constants
    
    // Code diversity
    bool randomize_register_allocation;
    bool insert_nop_sleds;
    bool shuffle_basic_blocks;
    
    // Allocation limits
    size_t max_jit_size;          // Maximum JIT allocation
    size_t max_allocations;       // Maximum concurrent allocations
    time_t allocation_rate_limit; // Minimum time between allocations
};

void apply_jit_spray_defense(void *code, size_t size,
                            struct JITSprayDefense *defense) {
    if (defense->blind_constants) {
        // XOR all constants with random key
        blind_constants_in_code(code, size, defense->blinding_key);
    }
    
    if (defense->insert_nop_sleds) {
        // Insert random NOP sequences
        insert_random_nops(code, size);
    }
    
    if (defense->shuffle_basic_blocks) {
        // Randomize basic block order
        shuffle_blocks(code, size);
    }
}
```

## 10. Performance Monitoring

### 10.1 JIT Performance Metrics

```c
struct JITMetrics {
    // Compilation metrics
    uint64_t compilations_total;
    uint64_t compilation_time_total;
    uint64_t compilation_bytes_total;
    
    // Tier transitions
    uint64_t tier0_to_tier1;
    uint64_t tier1_to_tier2;
    uint64_t deoptimizations;
    
    // Cache metrics
    uint64_t cache_hits;
    uint64_t cache_misses;
    uint64_t cache_evictions;
    
    // Memory metrics
    size_t code_cache_size;
    size_t peak_memory_usage;
    uint64_t gc_collections;
    
    // Performance impact
    double speedup_ratio;         // JIT vs interpreted
    double startup_overhead;      // JIT compilation overhead
    double memory_overhead;       // JIT memory overhead
};

void collect_jit_metrics(struct JITMetrics *metrics) {
    // Update compilation metrics
    metrics->compilation_time_total += last_compilation_time();
    metrics->compilations_total++;
    
    // Calculate speedup
    uint64_t jit_cycles = measure_jit_performance();
    uint64_t interp_cycles = measure_interpreter_performance();
    metrics->speedup_ratio = (double)interp_cycles / jit_cycles;
    
    // Memory tracking
    metrics->code_cache_size = get_code_cache_size();
    metrics->peak_memory_usage = max(metrics->peak_memory_usage,
                                    get_current_memory());
}
```

### 10.2 Adaptive Tuning

```python
# Adaptive JIT parameter tuning
class AdaptiveJITTuner:
    def __init__(self):
        self.parameters = {
            'tier1_threshold': 10,
            'tier2_threshold': 100,
            'inline_threshold': 50,
            'unroll_threshold': 4,
            'cache_size': 50 * 1024 * 1024,  # 50MB
        }
        
        self.history = []
        self.best_config = None
        self.best_score = 0
        
    def tune(self, workload):
        """Tune JIT parameters for workload."""
        for iteration in range(10):
            # Try different configurations
            config = self.generate_config(iteration)
            self.apply_config(config)
            
            # Measure performance
            score = self.benchmark(workload)
            self.history.append((config, score))
            
            # Update best
            if score > self.best_score:
                self.best_score = score
                self.best_config = config
                
        # Apply best configuration
        self.apply_config(self.best_config)
        
    def generate_config(self, iteration):
        """Generate parameter configuration."""
        if iteration == 0:
            return self.parameters  # Baseline
            
        # Vary parameters
        config = self.parameters.copy()
        if iteration % 2 == 0:
            # Adjust thresholds
            config['tier1_threshold'] *= 1.5
            config['tier2_threshold'] *= 1.5
        if iteration % 3 == 0:
            # Adjust inlining
            config['inline_threshold'] *= 0.8
        if iteration % 5 == 0:
            # Adjust cache size
            config['cache_size'] *= 1.2
            
        return config
```

## 11. Implementation Requirements

### 11.1 Language Runtime Integration

Each language runtime MUST:

1. **Provide Bytecode**: Supply bytecode or IR for JIT compilation
2. **Support Deoptimization**: Enable fallback to interpreter
3. **Expose Type Information**: Provide type feedback for optimization
4. **Handle GC Integration**: Coordinate with garbage collector
5. **Implement Guards**: Support speculative optimization guards

### 11.2 Platform Requirements

Platforms supporting Runtime JIT MUST provide:

1. **Executable Memory**: Ability to allocate executable pages
2. **Memory Protection**: mprotect() or equivalent
3. **Cache Coherency**: Instruction cache flushing
4. **Signal Handling**: For deoptimization triggers
5. **High-Resolution Timers**: For profiling

### 11.3 Fallback Behavior

When JIT is unavailable:

1. **Interpreter Mode**: Fall back to pure interpretation
2. **AOT Compilation**: Use ahead-of-time compiled code if available
3. **Cached Code**: Use persistent code cache if present
4. **Degraded Mode**: Disable optional features requiring JIT

## 12. Platform Integration

### 12.1 Operating System Support

```c
// Linux-specific JIT support
#ifdef __linux__
void* allocate_jit_memory_linux(size_t size) {
    // Use memfd for W^X compliance
    int fd = memfd_create("jit-code", MFD_CLOEXEC);
    ftruncate(fd, size);
    
    // Map twice: once for writing, once for execution
    void *write_addr = mmap(NULL, size, PROT_READ | PROT_WRITE,
                          MAP_SHARED, fd, 0);
    void *exec_addr = mmap(NULL, size, PROT_READ | PROT_EXEC,
                         MAP_SHARED, fd, 0);
    
    close(fd);
    return write_addr;  // Return write address for compilation
}
#endif

// macOS-specific JIT support
#ifdef __APPLE__
void* allocate_jit_memory_macos(size_t size) {
    // Use MAP_JIT flag for macOS 10.14+
    void *mem = mmap(NULL, size, PROT_READ | PROT_WRITE | PROT_EXEC,
                    MAP_PRIVATE | MAP_ANONYMOUS | MAP_JIT, -1, 0);
    
    // Toggle W^X using pthread_jit_write_protect_np
    pthread_jit_write_protect_np(0);  // Make writable
    
    return mem;
}
#endif
```

### 12.2 Hardware Acceleration

```c
// ARM64 pointer authentication for JIT code
#ifdef __aarch64__
void sign_jit_pointers(void *code, size_t size) {
    // Enable pointer authentication
    uint64_t *ptr = (uint64_t*)code;
    uint64_t *end = ptr + (size / 8);
    
    while (ptr < end) {
        if (is_return_address(ptr)) {
            // Sign return address with PAC
            *ptr = __builtin_arm_pacia(*ptr, 0);
        }
        ptr++;
    }
}
#endif

// Intel CET shadow stack for JIT
#ifdef __CET__
void setup_shadow_stack(void *jit_code, size_t size) {
    // Allocate shadow stack
    void *shadow = mmap(NULL, size, PROT_READ | PROT_WRITE,
                       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    
    // Configure CET for JIT region
    syscall(SYS_arch_prctl, ARCH_CET_LEGACY_BITMAP, jit_code);
}
#endif
```

## 13. Debugging and Diagnostics

### 13.1 JIT Debug Interface

```c
struct JITDebugInfo {
    // Source mapping
    struct SourceMap {
        void *native_pc;
        uint32_t bytecode_offset;
        uint32_t source_line;
        const char *source_file;
    } *mappings;
    size_t num_mappings;
    
    // Symbol table
    struct Symbol {
        const char *name;
        void *address;
        size_t size;
        uint32_t flags;
    } *symbols;
    size_t num_symbols;
    
    // Inline information
    struct InlineInfo {
        void *pc;
        const char *inlined_function;
        uint32_t call_site;
    } *inlines;
    size_t num_inlines;
};

// GDB JIT interface
struct jit_code_entry {
    struct jit_code_entry *next_entry;
    struct jit_code_entry *prev_entry;
    const char *symfile_addr;
    uint64_t symfile_size;
};

void register_jit_code_with_gdb(void *code, size_t size,
                               struct JITDebugInfo *debug_info) {
    // Generate DWARF debug info
    void *dwarf = generate_dwarf(code, size, debug_info);
    
    // Register with GDB
    struct jit_code_entry *entry = malloc(sizeof(*entry));
    entry->symfile_addr = dwarf;
    entry->symfile_size = dwarf_size;
    
    __jit_debug_register_code(entry);
}
```

### 13.2 Diagnostic Commands

```python
# Runtime JIT diagnostics
class JITDiagnostics:
    def show_compilation_stats(self):
        """Display JIT compilation statistics."""
        print(f"Total compilations: {self.metrics.compilations}")
        print(f"Average compile time: {self.metrics.avg_compile_time}ms")
        print(f"Code cache size: {self.metrics.cache_size / 1024}KB")
        print(f"Cache hit rate: {self.metrics.cache_hit_rate:.1%}")
        
    def dump_compiled_code(self, function):
        """Dump native code for function."""
        code = self.get_compiled_code(function)
        if code:
            disasm = self.disassemble(code)
            print(f"Compiled code for {function.__name__}:")
            print(disasm)
            
    def profile_jit_overhead(self):
        """Profile JIT compilation overhead."""
        with self.jit_disabled():
            baseline = self.benchmark()
            
        with self.jit_enabled():
            jit_time = self.benchmark()
            
        overhead = (jit_time - baseline) / baseline
        print(f"JIT overhead: {overhead:.1%}")
```

## 14. References

### 14.1 Normative References

[RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html) Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.

[RFC8174](https://www.rfc-editor.org/rfc/rfc8174.html) Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.

[FEP-0001] "PSPF/2025 Core Format & Operation Chains Specification", FEP-0001, January 2025.

[FEP-0004] "PSPF/2025 Supply Chain Just-In-Time Compilation", FEP-0004, January 2025.

### 14.2 Informative References

[V8-TURBOFAN] "TurboFan: V8's Optimizing Compiler", https://v8.dev/docs/turbofan

[PYPY-JIT] "PyPy's Tracing JIT Compiler", https://doc.pypy.org/en/latest/jit.html

[GRAAL] "GraalVM: High-Performance Polyglot VM", https://www.graalvm.org/

[LLVM-JIT] "LLVM's JIT Compilation Infrastructure", https://llvm.org/docs/MCJITDesignAndImplementation.html

[CET] "Intel Control-flow Enforcement Technology", Intel SDM, 2020.

[PAC] "ARM Pointer Authentication", ARM Architecture Reference Manual, 2018.

---

**Authors' Addresses**

[Author contact information]

**Status Note**

This specification is EXPERIMENTAL and represents advanced functionality planned for PSPF/2025 v1.5. Implementation complexity is high and requires significant runtime support.

**Copyright Notice**

Copyright (c) 2025 IETF Trust and the persons identified as the document authors. All rights reserved.