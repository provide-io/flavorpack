# FEP-0006: Supply Chain JIT Assembly Specification

**Status**: Future  
**Type**: Standards Track  
**Target Version**: v2 or later

**Note**: This server-side feature is deferred from v0 and v1. It requires mature v1 implementations before considering dynamic assembly.

This document provides a crucial clarification of the architectural vision for the Progressive Secure Packaging Format. It correctly distinguishes between two orthogonal, yet complementary, Just-In-Time (JIT) mechanisms: one focused on **runtime performance** (FEP-0005) and the other on **supply chain logistics** (this FEP-0006).

This separation of concerns is a hallmark of a robust, scalable system. I have integrated this distinction into my analysis. Below is a formalized summary, a process flow diagram illustrating the combined architecture, and the key operational considerations that arise from this powerful model.

### Formal Comparison: Runtime JIT vs. Supply Chain JIT

| Dimension | FEP-0005: Runtime JIT Loading | FEP-0006 (Proposed): Supply Chain JIT Assembly |
| :--- | :--- | :--- |
| **Name** | Runtime JIT Loading | Supply Chain JIT Assembly |
| **Domain** | Client-Side Runtime | Server-Side Distribution |
| **Granularity** | **Slot** (A single component within a package) | **Package** (The entire executable bundle) |
| **Trigger** | User action or API call during execution | Client request to download the application |
| **Primary Goal** | Minimize startup latency and memory footprint | Minimize storage costs and enable mass customization |
| **Core Tech** | Launcher with filesystem hooks, lazy extraction | Dynamic packager service, component repository |

### Combined Architectural Process Flow

The true power of this model lies in composing both JIT mechanisms. A package that was assembled Just-in-Time can itself contain slots that are loaded Just-in-Time. The following diagram illustrates this complete workflow.

```ascii
+--------------------------------------------------------------------------------------------------+
|                                     PSPF Combined JIT Workflow                                   |
+--------------------------------------------------------------------------------------------------+

  +-----------------+                                +---------------------------+     +-------------------+
  |     Client      |                                | Dynamic Assembly Service  |     | Component Storage |
  | (e.g., Updater) |                                |        (FEP-0006)         |     |   (e.g., S3)      |
  +-----------------+                                +---------------------------+     +-------------------+
          |                                                       |                           |
          | 1. Request Package                                    |                           |
          |    (platform=linux_amd64, features=core)              |                           |
          |------------------------------------------------------>|                           |
          |                                                       | 2. Fetch required         |
          |                                                       |    components             |
          |                                                       |-------------------------->|
          |                                                       |                           | (Launcher, Core Slots)
          |                                                       |                           |
          |                                                       | <-------------------------|
          |                                                       | 3. Assemble minimal .psp  |
          |                                                       |    - Injects JIT metadata |
          |                                                       |      for optional slots   |
          |                                                       |                           |
          | 4. Return tailored .psp package                       |                           |
          | <-----------------------------------------------------|                           |
          |                                                       |                           |
  +-----------------+                                             |                           |
  |  User launches  |                                             |                           |
  | minimal package |                                             |                           |
  +-----------------+                                             |                           |
          |                                                       |                           |
          | 5. User action triggers need for optional feature     |                           |
          |    (Launcher initiates FEP-0005 JIT Load)             |                           |
          |                                                       |                           |
          | 6. Request Slot                                       |                           |
          |    (component=plugin_x.slot)                          |                           |
          |------------------------------------------------------>|                           |
          |                                                       | 7. Fetch requested slot   |
          |                                                       |-------------------------->|
          |                                                       |                           | (plugin_x.slot data)
          |                                                       |                           |
          |                                                       | <-------------------------|
          |                                                       |                           |
          | 8. Return raw, compressed slot data                   |                           |
          | <-----------------------------------------------------|                           |
          |                                                       |                           |
          | 9. Launcher verifies and integrates slot              |                           |
          |                                                       |                           |
          V                                                       V                           V
      Time                                                                                    
```

### Operational & Engineering Considerations

As a Distinguished Engineer, this two-tiered JIT architecture introduces several critical operational challenges that must be addressed for a production system:

1.  **Security of the Assembly Service**: The FEP-0006 service becomes a high-value target. Since it assembles and signs packages on the fly, it must have access to signing keys. This necessitates the use of a Hardware Security Module (HSM) or equivalent secure key management system to protect the private keys from compromise. The service itself must be hardened against attacks.

2.  **Cache Coherency and Invalidation**: This is the most complex problem. If a core component (e.g., a shared library slot) is updated in Component Storage, how are clients with partially JIT-loaded packages notified? A robust mechanism for cache invalidation or version pinning is required to prevent clients from JIT-loading a new, incompatible slot into an older application shell.

3.  **Component Versioning and Dependency Management**: The Assembly Service must maintain a "bill of materials" for every package version. It needs a dependency graph to understand that `App v2.1` requires `SharedLib v1.4` and `PluginX v3.0`. Assembling a package with incompatible components would lead to runtime failures. This requires a rigorous component versioning and compatibility matrix.

4.  **Performance and Scalability**: The Assembly Service must be highly performant to avoid becoming a bottleneck. Assembling and signing a package, even a small one, is a non-trivial operation. Caching frequently requested package configurations (e.g., the default `linux_amd64` build) at the edge (CDN) would be essential to handle load.

5.  **State Management**: The service is inherently stateful, as it needs to manage component metadata, version information, and signing keys. This state must be managed reliably and consistently, especially in a distributed environment.
