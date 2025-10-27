# FEP-0004: PSPF/2025 Supply Chain Just-In-Time Compilation

**Status**: Experimental  
**Type**: Standards Track  
**Created**: 2025-01-08  
**Version**: v0.1  
**Category**: Future Enhancement  
**Target**: PSPF/2025 v1.0

## Abstract

This document specifies the Supply Chain Just-In-Time (JIT) compilation system for PSPF/2025 packages. Supply Chain JIT enables edge-based compilation services to dynamically generate optimized packages for specific target platforms, reducing distribution size while maximizing runtime performance. The system operates at package distribution time rather than execution time, allowing for aggressive optimization and caching strategies.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Compilation Service Protocol](#3-compilation-service-protocol)
4. [Package Manifest Extensions](#4-package-manifest-extensions)
5. [Platform Detection and Targeting](#5-platform-detection-and-targeting)
6. [Optimization Strategies](#6-optimization-strategies)
7. [Caching and Distribution](#7-caching-and-distribution)
8. [Security Model](#8-security-model)
9. [Implementation Requirements](#9-implementation-requirements)
10. [Performance Considerations](#10-performance-considerations)
11. [Deployment Scenarios](#11-deployment-scenarios)
12. [Migration Path](#12-migration-path)
13. [Security Considerations](#13-security-considerations)
14. [References](#14-references)

## 1. Introduction

### 1.1 Motivation

Traditional software distribution faces a fundamental trade-off:
- **Universal packages** work everywhere but are suboptimal everywhere
- **Platform-specific packages** are optimal but require maintaining multiple variants
- **Source distribution** enables optimization but requires build tools on target systems

Supply Chain JIT resolves this trade-off by performing compilation at distribution edges:
- Single source package maintained by developers
- Platform-optimized binaries generated on-demand
- Transparent caching for repeated requests
- No build tools required on target systems

### 1.2 Design Principles

1. **Separation of Concerns**: Developers ship source, edges compile, users run binaries
2. **Progressive Enhancement**: Systems work without JIT, perform better with it
3. **Transparent Operation**: No changes to existing PSPF package structure
4. **Security by Default**: Cryptographic verification throughout pipeline
5. **Edge Computing**: Leverage CDN and edge infrastructure for compilation

### 1.3 Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html) [RFC8174](https://www.rfc-editor.org/rfc/rfc8174.html) when, and only when, they appear in all capitals, as shown here.

## 2. Architecture Overview

### 2.1 System Components

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Package   │      │     Edge     │      │   Client    │
│  Repository │◄────►│   Compiler   │◄────►│   System    │
└─────────────┘      └──────────────┘      └─────────────┘
       │                     │                     │
       │                     ▼                     │
       │              ┌──────────────┐            │
       └─────────────►│    Cache     │◄───────────┘
                      └──────────────┘

Package Repository: Stores source packages and metadata
Edge Compiler: JIT compilation service at CDN edge
Cache: Compiled package cache (distributed)
Client System: End-user requesting packages
```

### 2.2 Compilation Pipeline

```
Source Package → Platform Detection → Dependency Resolution →
Compilation → Optimization → Packaging → Signing → Caching → Delivery
```

### 2.3 Package Types

| Type               | Description                          | Use Case                    |
|--------------------|--------------------------------------|-----------------------------|
| SOURCE_ONLY        | Source code, requires compilation   | Libraries, interpreted code |
| UNIVERSAL_BINARY   | Pre-compiled for common platforms   | Fallback when JIT unavailable |
| JIT_ELIGIBLE       | Source + universal binary           | Optimal: JIT with fallback |
| PLATFORM_SPECIFIC  | Pre-compiled for single platform    | Embedded systems           |

## 3. Compilation Service Protocol

### 3.1 Service Discovery

Clients discover JIT services via:

```http
GET /.well-known/pspf-jit HTTP/1.1
Host: packages.example.com

HTTP/1.1 200 OK
Content-Type: application/json

{
  "version": "1.0",
  "endpoints": {
    "compile": "https://jit.example.com/v1/compile",
    "status": "https://jit.example.com/v1/status",
    "cache": "https://cache.example.com/v1/packages"
  },
  "capabilities": {
    "platforms": ["linux_x86_64", "linux_arm64", "darwin_arm64"],
    "languages": ["c", "cpp", "rust", "go", "python"],
    "optimizations": ["native", "size", "speed", "balanced"]
  },
  "limits": {
    "max_source_size": 1073741824,  // 1GB
    "max_compile_time": 300,         // 5 minutes
    "cache_duration": 86400          // 24 hours
  }
}
```

### 3.2 Compilation Request

```http
POST /v1/compile HTTP/1.1
Host: jit.example.com
Content-Type: application/json
Authorization: Bearer <token>

{
  "package": {
    "name": "example-app",
    "version": "1.2.3",
    "source_url": "https://packages.example.com/example-app-1.2.3.src.pspf"
  },
  "target": {
    "platform": "linux_x86_64",
    "cpu_features": ["avx2", "aes", "sse4.2"],
    "optimization": "native",
    "libc": "glibc-2.31"
  },
  "options": {
    "strip_symbols": true,
    "static_linking": false,
    "lto": true,
    "pgo_data": "https://telemetry.example.com/pgo/example-app"
  },
  "signature": {
    "key_id": "ABC123",
    "algorithm": "ed25519",
    "value": "base64-signature"
  }
}
```

### 3.3 Compilation Response

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
Location: /v1/status/job-12345

{
  "job_id": "job-12345",
  "status": "queued",
  "estimated_time": 60,
  "status_url": "/v1/status/job-12345",
  "webhook_url": "https://callback.example.com/notify"
}
```

### 3.4 Status Polling

```http
GET /v1/status/job-12345 HTTP/1.1
Host: jit.example.com

HTTP/1.1 200 OK
Content-Type: application/json

{
  "job_id": "job-12345",
  "status": "completed",
  "result": {
    "package_url": "https://cache.example.com/compiled/abc123.pspf",
    "checksum": "sha256:abcdef...",
    "size": 10485760,
    "metadata": {
      "compile_time": 45.2,
      "optimizations_applied": ["lto", "native-cpu", "strip"],
      "compiler_version": "gcc-11.2.0",
      "cache_key": "linux_x86_64_avx2_native_abc123"
    }
  },
  "signature": {
    "signer": "jit.example.com",
    "timestamp": "2025-01-08T12:00:00Z",
    "value": "base64-signature"
  }
}
```

## 4. Package Manifest Extensions

### 4.1 JIT Metadata in package.json

```json
{
  "format_version": "2025.1.0",
  "package": {
    "name": "example-app",
    "version": "1.2.3"
  },
  "jit": {
    "enabled": true,
    "source_slots": [
      {
        "id": 100,
        "name": "source-code",
        "path": "src/",
        "language": "rust",
        "build_system": "cargo"
      }
    ],
    "build_requirements": {
      "min_memory": 2147483648,  // 2GB
      "min_cores": 2,
      "timeout": 300,
      "tools": ["rustc>=1.70", "cargo", "llvm>=15"]
    },
    "optimization_hints": {
      "hot_functions": ["process_data", "calculate_hash"],
      "likely_features": ["simd", "crypto"],
      "profile_guided": true
    },
    "platform_overrides": {
      "linux_arm64": {
        "flags": ["-march=armv8.2-a+crypto"]
      },
      "darwin_*": {
        "flags": ["-framework", "Accelerate"]
      }
    }
  }
}
```

### 4.2 Build Recipe Specification

```yaml
# build-recipe.yaml (embedded in package)
version: "1.0"
language: rust
source_dir: src/

steps:
  - name: configure
    command: cargo build --release
    environment:
      RUSTFLAGS: "-C target-cpu=native"
      
  - name: optimize
    command: strip target/release/example-app
    
  - name: package
    outputs:
      - source: target/release/example-app
        slot: 0
        purpose: code
        permissions: "755"

variants:
  size_optimized:
    steps:
      - name: configure
        command: cargo build --release
        environment:
          RUSTFLAGS: "-C opt-level=z"
          
  debug:
    steps:
      - name: configure
        command: cargo build
        outputs:
          - source: target/debug/example-app
```

## 5. Platform Detection and Targeting

### 5.1 Platform Identification

```c
struct PlatformInfo {
    // Operating System
    char os[32];              // "linux", "darwin", "windows"
    char os_version[32];      // "5.15.0", "13.0", "10.0.22000"
    
    // Architecture
    char arch[32];            // "x86_64", "arm64", "riscv64"
    char cpu_vendor[32];      // "GenuineIntel", "AuthenticAMD"
    char cpu_model[64];       // "Intel Core i7-12700K"
    
    // CPU Features (bitmask)
    uint64_t cpu_features;    // SSE4.2, AVX2, AVX512, AES, etc.
    
    // Runtime Environment
    char libc[32];            // "glibc", "musl", "msvcrt"
    char libc_version[32];    // "2.35", "1.2.3"
    
    // Container/VM Detection
    bool virtualized;         // Running in VM
    bool containerized;       // Running in container
    char container_runtime[32]; // "docker", "podman", "none"
};
```

### 5.2 Feature Detection Protocol

```http
GET /v1/detect HTTP/1.1
Host: jit.example.com
User-Agent: PSPF/1.0

HTTP/1.1 200 OK
Content-Type: application/json

{
  "client_ip": "203.0.113.42",
  "detected_platform": {
    "os": "linux",
    "arch": "x86_64", 
    "cpu_features": ["sse4.2", "avx2", "aes"],
    "libc": "glibc-2.35"
  },
  "recommended_target": "linux_x86_64_avx2",
  "available_variants": [
    "linux_x86_64_generic",
    "linux_x86_64_avx2",
    "linux_x86_64_avx512"
  ]
}
```

### 5.3 Target Specification Grammar

```abnf
target = os "-" arch [ "-" variant ]

os = "linux" / "darwin" / "windows" / "freebsd" / "android"

arch = "x86_64" / "x86" / "arm64" / "armv7" / "riscv64" / 
       "ppc64le" / "s390x" / "mips64"

variant = cpu-variant / abi-variant / custom-variant

cpu-variant = "generic" / "v2" / "v3" / "v4" /  ; x86-64 levels
              "avx2" / "avx512" / "znver3"      ; specific CPUs

abi-variant = "musl" / "gnu" / "android" / "msvc"

custom-variant = 1*( ALPHA / DIGIT / "_" )
```

## 6. Optimization Strategies

### 6.1 Optimization Levels

| Level       | Focus                | Compile Time | Binary Size | Performance |
|-------------|----------------------|--------------|-------------|-------------|
| DEBUG       | Debuggability        | Fast         | Large       | Slow        |
| RELEASE     | Balanced             | Moderate     | Medium      | Good        |
| SIZE        | Minimal size         | Moderate     | Small       | Moderate    |
| SPEED       | Maximum performance  | Slow         | Large       | Fast        |
| NATIVE      | CPU-specific         | Slow         | Medium      | Fastest     |

### 6.2 Profile-Guided Optimization (PGO)

```json
{
  "pgo": {
    "enabled": true,
    "profile_data": {
      "source": "https://telemetry.example.com/profiles/app-1.2.3.profdata",
      "format": "llvm",
      "coverage": 0.87,
      "samples": 1000000
    },
    "hot_paths": [
      "main.rs:process_request:42-187",
      "crypto.rs:hash_data:15-33"
    ],
    "cold_paths": [
      "error.rs:*",
      "debug.rs:*"
    ]
  }
}
```

### 6.3 Link-Time Optimization (LTO)

```yaml
lto_config:
  mode: "full"          # full|thin|off
  cross_language: true  # Enable cross-language LTO
  internalize: true     # Internalize symbols
  devirtualize: true    # Devirtualize function calls
  inline_threshold: 325 # Inlining threshold
  
  # Preserved symbols (not optimized away)
  preserve:
    - "plugin_*"
    - "ffi_*"
```

### 6.4 Architecture-Specific Optimizations

```c
// x86-64 Optimization Flags
#ifdef __x86_64__
  #if HAS_AVX512
    #define VECTOR_WIDTH 512
    #define USE_AVX512_INTRINSICS
  #elif HAS_AVX2
    #define VECTOR_WIDTH 256
    #define USE_AVX2_INTRINSICS
  #else
    #define VECTOR_WIDTH 128
    #define USE_SSE_INTRINSICS
  #endif
#endif

// ARM64 Optimization Flags  
#ifdef __aarch64__
  #if HAS_SVE2
    #define USE_SVE2_INTRINSICS
  #elif HAS_NEON
    #define USE_NEON_INTRINSICS
  #endif
  
  #if HAS_CRYPTO
    #define USE_ARM_CRYPTO
  #endif
#endif
```

## 7. Caching and Distribution

### 7.1 Cache Key Generation

```python
def generate_cache_key(request):
    """Generate deterministic cache key for compiled package."""
    components = [
        request.package.name,
        request.package.version,
        request.target.platform,
        request.target.cpu_features.sorted().join(","),
        request.options.optimization,
        hash(request.options.flags),
        request.options.lto,
        request.options.static_linking
    ]
    
    data = "|".join(str(c) for c in components)
    return hashlib.sha256(data.encode()).hexdigest()[:16]
```

### 7.2 Cache Hierarchy

```
┌─────────────────┐
│   Origin Cache  │  Long-term storage (S3, GCS)
└────────┬────────┘  TTL: 30 days
         │
┌────────▼────────┐
│   Edge Cache    │  CDN edge locations
└────────┬────────┘  TTL: 24 hours
         │
┌────────▼────────┐
│  Local Cache    │  Client-side cache
└─────────────────┘  TTL: 7 days
```

### 7.3 Cache Control Headers

```http
HTTP/1.1 200 OK
Content-Type: application/pspf
Cache-Control: public, max-age=86400, stale-while-revalidate=3600
ETag: "abc123def456"
X-PSPF-Cache-Key: "linux_x86_64_avx2_speed_abc123"
X-PSPF-Compile-Date: "2025-01-08T12:00:00Z"
X-PSPF-Compiler: "rustc-1.75.0"
Vary: X-PSPF-Target-Platform, X-PSPF-CPU-Features
```

### 7.4 Cache Invalidation

```json
{
  "invalidation": {
    "reason": "security_update",
    "packages": [
      {"name": "example-app", "version": "1.2.3"},
      {"name": "example-lib", "version": "2.*"}
    ],
    "platforms": ["linux_x86_64_*"],
    "compiled_before": "2025-01-07T00:00:00Z",
    "action": "recompile"
  }
}
```

## 8. Security Model

### 8.1 Trust Chain

```
Developer → Source Package → Edge Compiler → Compiled Package → Client

1. Developer signs source package with private key
2. Edge compiler verifies source signature
3. Edge compiler signs compiled package
4. Client verifies both signatures
```

### 8.2 Compilation Attestation

```json
{
  "attestation": {
    "version": "1.0",
    "compiler": {
      "identity": "jit.example.com",
      "certificate": "base64-cert",
      "environment": {
        "os": "linux",
        "kernel": "5.15.0",
        "compiler": "gcc-11.2.0",
        "isolation": "container"
      }
    },
    "source": {
      "package": "example-app-1.2.3",
      "checksum": "sha256:source-hash",
      "signature_verified": true
    },
    "compilation": {
      "timestamp": "2025-01-08T12:00:00Z",
      "duration": 45.2,
      "flags": ["-O3", "-march=native"],
      "deterministic": true
    },
    "output": {
      "checksum": "sha256:output-hash",
      "size": 10485760,
      "reproducible": true
    },
    "signature": {
      "algorithm": "ed25519",
      "key_id": "compiler-key-2025",
      "value": "base64-signature"
    }
  }
}
```

### 8.3 Secure Compilation Environment

```yaml
compilation_environment:
  isolation:
    type: "container"  # container|vm|bare-metal
    runtime: "gvisor"  # Additional sandboxing
    
  resource_limits:
    cpu: "4"
    memory: "8Gi"
    disk: "20Gi"
    network: "none"  # No network during compilation
    
  security:
    readonly_source: true
    no_execute_source: true
    syscall_filter: true
    seccomp_profile: "compilation.json"
    
  audit:
    log_commands: true
    record_filesystem: true
    capture_network: true
```

## 9. Implementation Requirements

### 9.1 Edge Compiler Requirements

Edge compilers MUST:
1. Support all PSPF v0 required operations
2. Verify source package signatures
3. Generate reproducible builds when possible
4. Provide compilation attestation
5. Implement resource limits and timeouts
6. Support incremental compilation
7. Cache intermediate artifacts

### 9.2 Client Requirements

Clients SHOULD:
1. Detect platform capabilities accurately
2. Prefer JIT-compiled packages when available
3. Fall back to universal binaries gracefully
4. Cache compiled packages locally
5. Verify compilation attestations
6. Report telemetry for PGO

### 9.3 Language Support Matrix

| Language | Build System | JIT Support | Notes                        |
|----------|--------------|-------------|------------------------------|
| C/C++    | CMake, Make  | FULL        | GCC, Clang, MSVC            |
| Rust     | Cargo        | FULL        | rustc with LLVM backend      |
| Go       | go build     | FULL        | Official Go compiler         |
| Python   | setuptools   | PARTIAL     | C extensions only            |
| Java     | Maven, Gradle| PARTIAL     | Native components via GraalVM |
| .NET     | dotnet       | PARTIAL     | NativeAOT compilation        |

## 10. Performance Considerations

### 10.1 Compilation Performance Metrics

```json
{
  "metrics": {
    "queue_time": 2.3,        // Seconds waiting in queue
    "compile_time": 45.2,      // Actual compilation time
    "optimization_time": 12.1, // LTO/PGO time
    "package_time": 3.4,       // Package assembly time
    "total_time": 63.0,        // Total end-to-end time
    
    "cpu_usage": 387,          // CPU-seconds used
    "peak_memory": 2147483648, // Peak memory in bytes
    "disk_io": 524288000,      // Disk I/O in bytes
    
    "cache_hit_rate": 0.73,    // Cache effectiveness
    "recompilation_rate": 0.12 // Forced recompiles
  }
}
```

### 10.2 Optimization Impact

| Optimization      | Compile Time | Size Impact | Performance Gain |
|-------------------|--------------|-------------|------------------|
| Basic (-O2)       | 1.0x         | 1.0x        | Baseline         |
| Full (-O3)        | 1.5x         | 1.1x        | +15-20%          |
| LTO               | 2.0x         | 0.9x        | +5-10%           |
| PGO               | 2.5x         | 1.0x        | +10-30%          |
| Native CPU        | 1.2x         | 1.0x        | +5-15%           |
| Size (-Os)        | 1.1x         | 0.7x        | -5-10%           |

### 10.3 Caching Effectiveness

```python
# Cache hit ratio by platform specificity
cache_hit_rates = {
    "generic": 0.95,      # linux_x86_64
    "cpu_variant": 0.75,  # linux_x86_64_avx2  
    "fully_native": 0.15, # linux_x86_64_znver3_native
    "custom_flags": 0.05  # User-specified optimization flags
}

# Compilation cost vs cache benefit analysis
def should_compile_jit(request):
    cache_probability = cache_hit_rates.get(request.specificity, 0.5)
    compilation_cost = request.estimated_compile_time
    download_savings = request.universal_size - request.jit_size
    
    expected_benefit = (
        cache_probability * download_savings +
        request.performance_gain * request.expected_runs
    )
    
    return expected_benefit > compilation_cost
```

## 11. Deployment Scenarios

### 11.1 CDN Edge Deployment

```yaml
deployment:
  type: cdn_edge
  locations:
    - region: us-east-1
      compilers: 10
      cache_size: 1TB
      platforms: ["linux_x86_64", "linux_arm64"]
      
    - region: eu-west-1
      compilers: 8
      cache_size: 750GB
      platforms: ["linux_x86_64", "darwin_arm64"]
      
  routing:
    strategy: geo_proximity
    fallback: origin_compiler
    
  scaling:
    min_compilers: 2
    max_compilers: 50
    scale_up_threshold: 0.8   # CPU utilization
    scale_down_threshold: 0.3
```

### 11.2 Enterprise Deployment

```yaml
deployment:
  type: on_premise
  infrastructure:
    compiler_nodes: 4
    cache_nodes: 2
    storage: "nfs"
    
  configuration:
    allowed_packages:
      - "internal/*"
      - "approved/*"
    
    custom_flags:
      global: ["-fstack-protector-strong"]
      debug: ["-g3", "-fsanitize=address"]
    
    compliance:
      log_retention: 90  # days
      audit_trail: true
      sbom_generation: true
```

### 11.3 Hybrid Cloud Deployment

```yaml
deployment:
  type: hybrid
  
  public_cloud:
    provider: "aws"
    service: "lambda"
    regions: ["us-east-1", "us-west-2"]
    
  private_cloud:
    type: "kubernetes"
    namespace: "pspf-jit"
    
  routing_rules:
    - match: {package: "proprietary/*"}
      route: private_cloud
      
    - match: {optimization: "debug"}
      route: private_cloud
      
    - default:
      route: public_cloud
```

## 12. Migration Path

### 12.1 Adoption Phases

#### Phase 1: Metadata Addition (v0.5)
- Add JIT metadata to packages
- No behavioral changes
- Collect platform telemetry

#### Phase 2: Opt-in JIT (v1.0)
- Enable JIT for specific packages
- Manual compilation triggering
- Limited platform support

#### Phase 3: Automatic JIT (v1.5)
- Automatic compilation for popular packages
- Expanded platform coverage
- PGO data collection

#### Phase 4: Universal JIT (v2.0)
- JIT by default for all eligible packages
- Full optimization pipeline
- Advanced caching strategies

### 12.2 Backward Compatibility

```python
def get_package(name, version, platform=None):
    """Get package with JIT fallback logic."""
    
    # Try JIT-compiled version first
    if platform and jit_enabled():
        compiled = try_get_jit_compiled(name, version, platform)
        if compiled:
            return compiled
    
    # Fall back to universal binary
    universal = get_universal_package(name, version)
    if universal:
        return universal
    
    # Last resort: source package for local compilation
    return get_source_package(name, version)
```

### 12.3 Feature Detection

```c
// Runtime JIT capability detection
struct JITCapabilities {
    bool available;
    char endpoint[256];
    char version[32];
    uint32_t max_compile_time;
    uint64_t max_package_size;
};

bool detect_jit_support(struct JITCapabilities *caps) {
    // Check environment variable
    char *jit_endpoint = getenv("PSPF_JIT_ENDPOINT");
    if (!jit_endpoint) {
        return false;
    }
    
    // Probe endpoint
    if (!probe_jit_service(jit_endpoint, caps)) {
        return false;
    }
    
    // Verify compatibility
    return strcmp(caps->version, REQUIRED_JIT_VERSION) >= 0;
}
```

## 13. Security Considerations

### 13.1 Supply Chain Attacks

**Threat**: Malicious code injection during compilation
**Mitigation**: 
- Reproducible builds with multiple compilers
- Source package signature verification
- Compilation attestation chain
- Binary transparency logs

### 13.2 Resource Exhaustion

**Threat**: DoS through expensive compilation requests
**Mitigation**:
- Rate limiting per client
- Compilation cost estimation
- Resource quotas
- Request authentication

### 13.3 Cache Poisoning

**Threat**: Serving malicious compiled packages from cache
**Mitigation**:
- Cryptographic cache keys
- Cache entry signatures
- Periodic cache validation
- Immutable cache entries

### 13.4 Platform Fingerprinting

**Threat**: Information disclosure through platform detection
**Mitigation**:
- Generic platform options
- Optional platform detection
- Minimal information collection
- Privacy-preserving telemetry

### 13.5 Compiler Vulnerabilities

**Threat**: Exploiting compiler bugs to generate malicious code
**Mitigation**:
- Compiler diversity
- Regular compiler updates
- Sandboxed compilation
- Output validation

## 14. References

### 14.1 Normative References

[RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html) Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.

[RFC8174](https://www.rfc-editor.org/rfc/rfc8174.html) Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.

[FEP-0001] "PSPF/2025 Core Format & Operation Chains Specification", FEP-0001, January 2025.

[FEP-0002] "PSPF/2025 JSON Metadata Format Specification", FEP-0002, January 2025.

[FEP-0003] "PSPF/2025 Operation Registry and Allocation Policy", FEP-0003, January 2025.

### 14.2 Informative References

[REPRO-BUILDS] "Reproducible Builds: Increasing the Integrity of Software Supply Chains", https://reproducible-builds.org/

[SLSA] "Supply-chain Levels for Software Artifacts", https://slsa.dev/

[CDN-EDGE] "Edge Computing: A Survey", IEEE Internet Computing, 2019.

[PGO] "Profile-Guided Optimization", GCC Documentation, https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html

[LTO] "Link Time Optimization", LLVM Documentation, https://llvm.org/docs/LinkTimeOptimization.html

---

**Authors' Addresses**

[Author contact information]

**Status Note**

This specification is EXPERIMENTAL and subject to change. Implementation should be considered prototype-quality until standardization in PSPF/2025 v1.0.

**Copyright Notice**

Copyright (c) 2025 IETF Trust and the persons identified as the document authors. All rights reserved.