# PSPF/2025 FEP Summary

## Foundation Specifications

### FEP-0001: PSPF/2025 Core Format Specification
**Purpose**: Defines the core binary format, magic trailer structure, and archive operation chain system  
**Applies to**: All PSPF/2025 packages and implementations  
**Key Features**:
- 📦 + 8192-byte index + 🪄 magic trailer structure
- 255 operation types in categories (BUNDLE, COMPRESS, ENCRYPT, etc.)
- 64-bit packed operation chains (up to 8 operations per slot)
- 64-byte slot descriptors with operations field
- Cross-language binary compatibility requirements

### FEP-0002: Operation Chain System
**Purpose**: Specifies the composable archive operation system with 255 operation types  
**Applies to**: Slot processing, archive handlers, chain execution  
**Key Features**:
- Operation categories (0x01-0x0F BUNDLE, 0x10-0x2F COMPRESS, 0x30-0x3F ENCRYPT)
- 64-bit packed chains with left-to-right processing order
- Standard operations: TAR, ZIP, GZIP, BZIP2, ZSTD, AES256, ChaCha20
- Handler interface for operation implementations
- Chain validation and compatibility rules

### FEP-0003: Cross-Language Wire Format
**Purpose**: Defines protobuf-compatible serialization without runtime protobuf dependency  
**Applies to**: Python/Go/Rust implementations, binary compatibility  
**Key Features**:
- Protobuf wire format encoding/decoding
- Python @frozen(slots=True) attrs class generation
- Go zero-allocation struct generation
- Rust zero-copy struct generation
- Build-time proto compilation, runtime independence

## Advanced Features

### FEP-0004: Staged Payload Architecture
**Purpose**: Enables concurrent execution of untrusted code during cryptographic verification  
**Applies to**: Performance optimization, startup latency reduction  
**Key Features**:
- Pre-verification payload (PVP) execution in slot 0
- Sandboxed environment with capability restrictions
- Verification boundary synchronization protocol
- Platform-specific isolation (seccomp, sandbox-exec, AppContainer)
- Graceful degradation on failure

### FEP-0005: Just-In-Time Loading
**Purpose**: Deferred slot extraction and on-demand network delivery  
**Applies to**: Large packages, network-distributed content, memory optimization  
**Key Features**:
- Extended lifecycle types (JIT_LOCAL, JIT_NETWORK, JIT_HYBRID)
- On-demand slot extraction with caching
- Network delivery via HTTP/gRPC/S3 protocols
- Incremental updates and background prefetching
- Cache management and integrity verification

## Implementation Specifications

### FEP-0006: Standard Operation Handlers
**Purpose**: Specifies implementations for core archive operations  
**Applies to**: Operation chain processors, archive format support  
**Key Features**:
- TAR handler (POSIX tar format, preserves permissions)
- ZIP handler (DEFLATE compression, random access)
- GZIP/BZIP2/ZSTD compression handlers
- AES256/ChaCha20 encryption handlers
- Handler interface and registration system
- Error handling and validation protocols

### FEP-0007: Security Model  
**Purpose**: Cryptographic integrity and digital signature verification  
**Applies to**: Package authentication, tamper detection, trust boundaries  
**Key Features**:
- Ed25519 digital signatures (32-byte public key, 64-byte signature)
- Multi-layer checksum validation (Adler-32, SHA-256)
- Signature verification before slot extraction
- Trust boundary enforcement
- Insecure mode handling for development

## Dependencies

```
FEP-0001 (Core Format)
├── FEP-0002 (Operation Chains) → FEP-0006 (Handlers)
├── FEP-0003 (Wire Format)
├── FEP-0004 (SPA) [references 0001, 0002]
├── FEP-0005 (JIT) [references 0001, 0002, 0003]
└── FEP-0007 (Security) [references 0001]
```

## Implementation Priority

1. **FEP-0001** - Core format (required foundation)
2. **FEP-0002** - Operation chains (enables archive system)
3. **FEP-0003** - Wire format (enables cross-language support)
4. **FEP-0006** - Standard handlers (implements basic operations)
5. **FEP-0007** - Security (enables signature verification)
6. **FEP-0004** - SPA (performance optimization)
7. **FEP-0005** - JIT (advanced loading features)

## Archive System Coverage

The archive operation system spans multiple FEPs:

- **FEP-0001**: Defines 255 operation categories and 64-bit packing format
- **FEP-0002**: Specifies chain processing algorithms and operation semantics  
- **FEP-0006**: Implements standard handlers (TAR, GZIP, ZIP, AES, etc.)
- **FEP-0003**: Enables cross-language operation chain compatibility

This provides complete coverage of the composable archive system from specification through implementation across all supported languages (Python/Go/Rust).

---
*Updated: 2025-01-08*