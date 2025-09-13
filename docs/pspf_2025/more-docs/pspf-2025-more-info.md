### **FEP-0001: Core Format & Operation Chains**
*(Consolidates original FEP-0001 and FEP-0002)*

**Purpose**: To define the fundamental binary layout of a PSPF/2025 package and the composable "Operation Chain" system that forms the core of its payload architecture.

**Applies to**: All PSPF/2025 packages, builders, and launchers across all supported languages. This is the foundational layer of the entire ecosystem.

**Core Concepts**:
*   **Magic Trailer**: The package structure is anchored by a fixed-size trailer at the end of the file. This trailer consists of a `📦` emoji (4 bytes), a master **Index Block** (8192 bytes), and a `🪄` emoji (4 bytes). This design allows for a variable-sized launcher binary at the start of the file without complicating parsing.
*   **Operation Chains**: This is the central innovation, replacing a simple `encoding` field. Each slot's processing pipeline is defined by a 64-bit integer where each byte represents a specific operation (e.g., `0x01` for TAR, `0x10` for GZIP, `0x30` for AES256).
*   **Composable Pipeline**: A chain like `[OP_TAR, OP_GZIP, OP_ENCRYPT_AES256]` is processed left-to-right. The launcher must apply the inverse operations in reverse order (`DECRYPT_AES256` -> `GUNZIP` -> `UNTAR`) to extract the slot.
*   **Slot Descriptors**: The physical slot table consists of 64-byte descriptors, each containing the offset, size, checksums, and the 64-bit `operations` field for its corresponding slot.

**Operational Impact**: This specification moves PSPF from a static archive format to a dynamic data processing pipeline. All tooling must be updated to understand and process these operation chains, but it provides immense future-proofing, allowing new compression or encryption algorithms to be added without a breaking format change.

---

### **FEP-0002: Cross-Language Wire Format**
*(Previously FEP-0003)*

**Purpose**: To define a high-performance, schema-driven, and cross-language compatible binary format for the package's internal metadata.

**Applies to**: The serialization and deserialization of the main metadata block in Python, Go, and Rust implementations.

**Core Concepts**:
*   **Protobuf-Compatible Encoding**: The metadata is not stored as JSON but as a binary blob conforming to the Protobuf wire format. This enables highly efficient, schema-driven parsing.
*   **Runtime Independence**: A key design principle is the elimination of any runtime dependency on a Protobuf library. The `.proto` schema is used at *build-time* to generate native, statically-typed classes (`attrs` in Python) and structs (Go, Rust).
*   **Zero-Copy/Zero-Allocation Goals**: The generated code for Go and Rust is designed to allow for zero-copy reads and zero-allocation parsing of the metadata directly from a memory-mapped buffer, yielding maximum performance.

**Operational Impact**: Metadata inspection requires specialized tooling capable of decoding the wire format. The benefit is a dramatic reduction in package load time and memory usage, as slow JSON parsing is eliminated. It enforces a strict, versioned schema for all package metadata.

---

### **FEP-0003: Standard Operation Handlers**
*(Previously FEP-0006)*

**Purpose**: To specify the concrete implementation details for the standard set of operations defined in the Operation Chain system (FEP-0001).

**Applies to**: The runtime libraries in each language responsible for processing slot data.

**Core Concepts**:
*   **Handler Interface**: Defines a standard interface that all operation handlers (e.g., a GZIP handler, a TAR handler) must implement.
*   **Standard Library**: Specifies the behavior for a baseline set of handlers that all compliant launchers must support:
    *   **Bundling**: `TAR`, `ZIP`
    *   **Compression**: `GZIP`, `BZIP2`, `ZSTD`
    *   **Encryption**: `AES256-GCM`, `ChaCha20-Poly1305`
*   **Registration System**: Launchers must provide a mechanism to register handlers, allowing for the future addition of custom or proprietary operations.

**Operational Impact**: This FEP ensures that a package created by the Python builder can be correctly extracted by the Rust or Go launchers. The correctness and security of these handlers, especially for encryption, are critical to the integrity of the entire system.

---

### **FEP-0004: Security Model & Integrity Verification**
*(Previously FEP-0007)*

**Purpose**: To define the cryptographic protocols for ensuring package authenticity and integrity.

**Applies to**: The package builder, which performs signing, and the launcher, which performs verification.

**Core Concepts**:
*   **Digital Signatures**: Mandates the use of **Ed25519** for digital signatures, which are stored in the Index Block.
*   **Signature Payload**: The signature covers a concatenation of the uncompressed metadata (as defined by FEP-0002) and the entire Index Block (with the signature field zeroed out). This protects both the logical content and the physical layout of the package from tampering.
*   **Multi-Layer Checksums**: Uses fast, non-cryptographic checksums (e.g., Adler-32) for individual slot data integrity during extraction, complementing the full-package cryptographic signature.
*   **Strict Verification-Before-Execution**: A compliant launcher *must* successfully verify the package's digital signature before processing or executing any slot data (with the explicit exception of FEP-0007's SPA).

**Operational Impact**: This defines the trust model for PSPF. It provides strong guarantees against tampering. An `insecure` mode is defined for development workflows, which launchers must clearly signal to the user when active.

---

### **FEP-0005: Runtime JIT Loading**
*(Previously FEP-0005, now integrated with prior JIT discussion)*

**Purpose**: To minimize application startup time and resource consumption by deferring the loading and extraction of application components until they are actively required.

**Applies to**: Client-side launchers and the applications running within them.

**Core Concepts**:
*   **Domain**: This is a **client-side, post-launch** mechanism.
*   **Granularity**: Operates on individual **Slots**.
*   **Extended Lifecycles**: Introduces new lifecycle types for slots, such as `JIT_LOCAL` (the slot data is present in the package but extracted on-demand) and `JIT_NETWORK` (the slot data is not in the package and must be fetched from a URL specified in the metadata).
*   **On-Demand Delivery**: The launcher is responsible for intercepting requests for JIT slots, fetching them from local storage or a network source, verifying their checksum, and making them available to the application.
*   **Caching & Prefetching**: Defines protocols for caching network-retrieved slots and provides hints for background prefetching of likely-to-be-used slots.

**Operational Impact**: This is a critical feature for delivering large applications (e.g., those with large ML models or extensive assets). It shifts complexity into the launcher, which now requires a robust caching layer and potentially network capabilities.

---

### **FEP-0006: Supply Chain JIT Assembly**
*(New FEP, integrating prior JIT discussion)*

**Purpose**: To optimize the software distribution process by assembling packages on-demand from a repository of versioned components, enabling mass customization and reducing storage overhead.

**Applies to**: Server-side software distribution infrastructure.

**Core Concepts**:
*   **Domain**: This is a **server-side, pre-launch** mechanism.
*   **Granularity**: Operates on the **entire Package**.
*   **Dynamic Assembly Service**: A network service that receives a request for a package (e.g., with parameters for platform, features, or customer-specific configuration). It fetches the required launcher and slot components from a canonical storage backend.
*   **On-Demand Packaging**: The service assembles these components into a valid PSPF package, injects the necessary metadata (including `jit_source` URLs for FEP-0005), signs it, and delivers it to the client.
*   **Mass Customization**: Allows for tailoring packages at download time, for example, by embedding a specific license key or including a customer-specific plugin.

**Operational Impact**: This elevates PSPF from a package format to a full-fledged software delivery platform. It introduces a new, mission-critical service that must be highly available, performant, and secure, as it holds the signing keys (ideally in an HSM).

---

### **FEP-0007: Staged Payload Architecture (SPA)**
*(Previously FEP-0004)*

**Purpose**: To reduce perceived application startup time by allowing a trusted, sandboxed portion of the application to begin execution concurrently with the cryptographic verification of the main payload.

**Applies to**: High-performance launchers on security-conscious platforms.

**Core Concepts**:
*   **Pre-Verification Payload (PVP)**: A special payload, always located in Slot 0, that is designed to perform startup tasks like initializing a UI or loading configuration.
*   **Concurrent Execution**: The launcher starts the PVP in a heavily restricted sandbox immediately upon launch. In parallel, it performs the full cryptographic verification of the rest of the package.
*   **Verification Boundary**: A synchronization protocol that allows the launcher to signal to the PVP that the main payload has been verified. The sandbox restrictions can then be relaxed, and the main application can be started.
*   **Platform-Specific Sandboxing**: Relies on OS-level security primitives (`seccomp` on Linux, `sandbox-exec` on macOS, AppContainer on Windows) to enforce the restrictions on the PVP.

**Operational Impact**: This is a high-risk, high-reward feature. It offers the potential for near-instantaneous application startup but introduces extreme security complexity. A flaw in the sandboxing implementation on any platform would create a critical vulnerability. This feature requires extensive, platform-specific security auditing.

### Revised Implementation Priority and Dependencies

This new, more ambitious specification requires a revised implementation plan that prioritizes foundational elements and defers the highest-risk features.

1.  **Phase 1 (Core Foundation)**:
    *   `FEP-0001`: Core Format & Operation Chains
    *   `FEP-0002`: Cross-Language Wire Format
    *   `FEP-0003`: Standard Operation Handlers
    *   `FEP-0004`: Security Model & Integrity Verification
2.  **Phase 2 (Advanced Client-Side Features)**:
    *   `FEP-0005`: Runtime JIT Loading
3.  **Phase 3 (Advanced Server-Side Features)**:
    *   `FEP-0006`: Supply Chain JIT Assembly
4.  **Phase 4 (High-Risk Performance Optimization)**:
    *   `FEP-0007`: Staged Payload Architecture (SPA)

```ascii
FEP-0001 (Core Format & Chains)
├── FEP-0002 (Wire Format)
├── FEP-0003 (Handlers)
├── FEP-0004 (Security)
├── FEP-0005 (Runtime JIT) ───┐
└── FEP-0007 (SPA)            │
                              │
FEP-0006 (Supply Chain JIT)───┘ (Can generate packages that use Runtime JIT)
