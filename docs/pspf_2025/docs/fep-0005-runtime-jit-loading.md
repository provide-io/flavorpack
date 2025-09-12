# FEP-0005: Just-In-Time Loading Specification

**Status**: Future  
**Type**: Standards Track  
**Created**: 2025-09-02  
**Updated**: 2025-09-03  
**Target Version**: v1 or later

**Note**: This feature is deferred from v0 to focus on core functionality. v0 implementations are not required to support JIT loading.  

## 1. Introduction

This specification defines Just-In-Time (JIT) loading mechanisms for PSPF/2025 packages, enabling deferred extraction of slots and on-demand network delivery. JIT loading reduces startup time, memory usage, and bandwidth consumption by loading components only when needed.

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

### 1.2. Design Goals

1. Minimize startup latency through deferred loading
2. Reduce memory footprint via on-demand extraction
3. Enable network-based component delivery
4. Support incremental updates and patches
5. Maintain cryptographic integrity for all content

## 2. JIT Lifecycle Extensions

### 2.1. Extended Lifecycle Types

In addition to FEP-0001 lifecycle types, JIT adds:

```
Value  Name            Description                     Loading
-----  --------------  ------------------------------  -------
11     JIT_LOCAL       Load from package on demand    Deferred
12     JIT_NETWORK     Load from network on demand    Network
13     JIT_HYBRID      Try local, fall back to network Mixed
14     JIT_OPTIONAL    Load only if explicitly used   Manual
15     JIT_BACKGROUND  Load in background after start Async
```

### 2.2. Loading Priority

Slots SHALL be loaded in priority order:

```
Priority  Lifecycle Types           When Loaded
--------  -----------------------   -----------
1         EAGER, STARTUP           Before main execution
2         RUNTIME                  At first access
3         JIT_LOCAL                On demand
4         JIT_BACKGROUND           After startup
5         JIT_NETWORK, JIT_HYBRID  When accessed
6         JIT_OPTIONAL             Explicit request only
```

## 3. Metadata Extensions

### 3.1. JIT Configuration

Packages SHALL declare JIT configuration in metadata:

```json
{
  "jit": {
    "enabled": true,
    "strategy": "aggressive",
    "cache_dir": "{workenv}/.jit_cache",
    "max_cache_size": 1073741824,
    "network_timeout_ms": 30000,
    "background_slots": [4, 5, 6]
  }
}
```

### 3.2. Slot-Level JIT Configuration

Each slot MAY specify JIT parameters:

```json
{
  "slots": [
    {
      "id": 3,
      "name": "large-model",
      "lifecycle": 12,
      "jit": {
        "source": {
          "type": "grpc",
          "endpoint": "api.example.com:443",
          "path": "/slots/model-v2"
        },
        "cache": {
          "strategy": "persistent",
          "ttl": 86400,
          "verify_on_load": true
        },
        "priority": 5
      }
    }
  ]
}
```

## 4. Local JIT Loading

### 4.1. Deferred Extraction

For JIT_LOCAL slots, implementations SHALL:

1. Skip extraction during initial workenv setup
2. Track slot access through filesystem hooks
3. Extract slot on first access
4. Cache extraction for subsequent access

### 4.2. Access Detection Mechanisms

Implementations SHALL use one or more:

1. **Filesystem Hooks**: Intercept file operations
2. **Import Hooks**: Language-specific module loading
3. **Explicit API**: Application requests loading
4. **Memory Mapping**: Trap page faults for access

### 4.3. Extraction Protocol

```
Access Detected → Check Cache → Extract if Missing → Verify Checksum → Grant Access
```

### 4.4. Cache Management

Extracted JIT slots SHALL be cached with:

```
Cache Key: {package_name}_{version}_{slot_id}_{checksum}
Cache Location: {workenv}/.jit_cache/slot_{id}/
Validation: Checksum verification on access
Expiration: LRU when cache_size exceeded
```

## 5. Network Delivery

### 5.1. Network Source Types

Implementations MAY support:

```
Type      Protocol           Use Case
--------  -----------------  ---------
http      HTTP/HTTPS         Simple downloads
grpc      gRPC + Protobuf    Streaming, structured
s3        AWS S3 API         Cloud storage
webdav    WebDAV             Enterprise storage
custom    User-defined       Special requirements
```

### 5.2. Network Configuration

```json
{
  "source": {
    "type": "grpc",
    "endpoint": "slots.example.com:443",
    "tls": true,
    "certificate_pin": "sha256:abcd1234..."
  },
  "auth": {
    "type": "bearer",
    "token": "${PSPF_TOKEN}"
  },
  "retry": {
    "max_attempts": 3,
    "backoff_ms": [1000, 2000, 4000]
  }
}
```

### 5.3. Download Protocol

1. **Request**: Send slot identifier and authentication
2. **Response**: Receive slot size and checksum
3. **Transfer**: Stream data in chunks
4. **Verification**: Validate complete slot checksum
5. **Extraction**: Decompress and extract to cache

### 5.4. Chunk Transfer

For streaming protocols, chunks SHALL include:

```
Offset  Size  Type      Field         Description
------  ----  --------  ------------  -----------
0       4     uint32    sequence      Chunk number
4       4     uint32    size          Data size
8       4     uint32    checksum      Chunk Adler-32
12      N     bytes     data          Chunk data
```

## 6. Protocol Buffer Integration

### 6.1. Service Definition

For gRPC-based delivery:

```protobuf
syntax = "proto3";

service SlotService {
  rpc GetSlotInfo(SlotRequest) returns (SlotInfo);
  rpc DownloadSlot(SlotRequest) returns (stream SlotChunk);
  rpc CheckUpdate(UpdateRequest) returns (UpdateInfo);
}

message SlotRequest {
  string package_id = 1;
  string package_version = 2;
  uint32 slot_id = 3;
  string auth_token = 4;
}

message SlotChunk {
  uint32 sequence = 1;
  bytes data = 2;
  uint32 checksum = 3;
  float progress = 4;
}
```

### 6.2. Authentication

Network requests SHALL include authentication:

```
Method        Header/Field           Example
-----------   --------------------   -------
HTTP Bearer   Authorization          Bearer {token}
gRPC Meta     authorization          bearer {token}
Custom Auth   X-PSPF-Auth           {signed_request}
```

## 7. Integrity Verification

### 7.1. Slot Verification

All JIT-loaded slots MUST be verified:

1. Compare slot checksum with metadata
2. Verify slot signature if present
3. Validate internal structure
4. Check file permissions

### 7.2. Network Security

Network delivery SHALL:

1. Use TLS for all connections
2. Verify server certificates
3. Support certificate pinning
4. Validate chunk checksums
5. Verify complete slot integrity

### 7.3. Cache Validation

Cached slots SHALL be validated by:

```
On Access: Quick checksum of cache marker
Periodic: Full checksum verification
On Error: Complete re-validation
After Update: Invalidate affected slots
```

## 8. Performance Optimization

### 8.1. Prefetching

Implementations MAY prefetch based on:

- Access patterns from previous runs
- Static dependency analysis
- Explicit prefetch hints
- Background loading priority

### 8.2. Compression

Network transfers SHOULD use:

```
Protocol     Compression          Typical Ratio
----------   ------------------   -------------
HTTP         gzip, brotli         3-5x
gRPC         gzip, snappy         2-4x
Custom       zstd, lz4            2-10x
```

### 8.3. Caching Strategy

```
Strategy      Description                When to Use
-----------   -------------------------  -----------
Persistent    Keep indefinitely          Stable content
Temporal      Time-based expiration      Dynamic content
Size-bound    LRU with size limit        Limited storage
Versioned     Per-version caching        Frequent updates
```

## 9. Error Handling

### 9.1. Local JIT Failures

```
Failure              Recovery Action
------------------   ---------------
Extraction fails     Retry with verification
Checksum mismatch    Re-extract from package
No disk space        Clear cache, retry
Access timeout       Return error to application
```

### 9.2. Network JIT Failures

```
Failure              Recovery Action
------------------   ---------------
Connection failed    Retry with backoff
Server error         Try alternate endpoint
Partial download     Resume from offset
Verification fail    Full re-download
Auth expired         Refresh credentials
```

## 10. Implementation Requirements

### 10.1. Minimum Implementation

A conforming implementation MUST:

- Support JIT_LOCAL lifecycle
- Implement basic cache management
- Verify slot checksums
- Handle extraction failures

### 10.2. Network Implementation

Network-capable implementations MUST:

- Support at least HTTP(S)
- Implement retry logic
- Verify TLS certificates
- Handle partial downloads
- Validate all received data

### 10.3. Advanced Features

Implementations SHOULD support:

- Multiple network protocols
- Background prefetching
- Compression for transfers
- Incremental updates
- Distributed caching

## 11. Relationship to Other FEPs

### 11.1. FEP-0004 (SPA)

JIT Loading complements SPA:
- SPA handles pre-verification UI
- JIT handles post-verification loading
- Combined: Fast perceived and actual startup

### 11.2. FEP-0002 (Workenv)

JIT extends workenv management:
- JIT cache within workenv
- Shared cache across versions
- Coordinated cleanup policies

## 12. Security Considerations

### 12.1. Trust Model

1. Local JIT content is trusted (from verified package)
2. Network content requires verification
3. Cache corruption must be detected
4. Network endpoints must be authenticated

### 12.2. Attack Mitigation

```
Attack                Mitigation
-------------------   -----------
Cache poisoning       Checksum verification
Network tampering     TLS + integrity checks
Denial of service     Timeouts + fallbacks
Path traversal        Sanitize slot paths
Resource exhaustion   Cache size limits
```

## 13. References

- RFC 2119: Key words for use in RFCs
- FEP-0001: PSPF Core Specification
- FEP-0002: Working Environment Management
- FEP-0004: Staged Payload Architecture
- gRPC Protocol Specification
- Protocol Buffers Language Guide

---
*Version: 2025.1*