# FEP-0004: Staged Payload Architecture Specification

**Status**: Proposed  
**Type**: Standards Track  
**Created**: 2025-08-28  
**Updated**: 2025-09-03  
**Authoritative Schema**: `proto/modules/spa.proto`

## 1. Introduction

This specification defines the Staged Payload Architecture (SPA), an optional extension to PSPF/2025 enabling concurrent execution of untrusted initialization code during cryptographic verification. SPA improves perceived startup performance through asynchronous "start-then-halt" verification while maintaining security guarantees.

## 2. Architecture Overview

### 2.1. Component Structure

A SPA-enabled PSPF package contains:

```
Component               Trust Level    Execution Phase
---------------------   ------------   ---------------
Native Launcher         Trusted        Always
Verification Engine     Trusted        Concurrent
PVP (Slot 0)           Untrusted      Pre-verification
Main Application        Trusted        Post-verification
```

### 2.2. Index Flag

SPA capability SHALL be indicated by bit 5 (value `0x20`) in the index flags field, corresponding to `FLAG_SPA_ENABLED` in `proto/modules/index.proto`.

## 3. Pre-Verification Payload (PVP)

### 3.1. Designation

The PVP SHALL be stored in slot 0 with `LIFECYCLE_INIT` and `PURPOSE_CODE`.

### 3.2. Metadata Configuration

Packages SHALL declare SPA configuration in their metadata, conforming to the `SPASystemConfig` message in `spa.proto`.

### 3.3. Capability Definitions

PVP capabilities are defined by the `Capability` enum in `spa.proto`.

| Capability Enum Name         | Description                 |
|------------------------------|-----------------------------|
| `CAPABILITY_UI_RENDER`       | Display user interface      |
| `CAPABILITY_TEMP_FILES`      | Temporary file access       |
| `CAPABILITY_IPC_SETUP`       | Inter-process communication |
| `CAPABILITY_CACHE_INIT`      | Initialize caches           |
| `CAPABILITY_CONFIG_LOAD`     | Load default configuration  |

## 4. Verification Boundary Protocol

### 4.1. Boundary Definition

The Verification Boundary is a mandatory synchronization point where PVP execution halts until verification completes.

### 4.2. Signaling Mechanism

The IPC mechanism is configured via the `IPCConfig` message in `spa.proto`.

### 4.3. State Structure

The verification state is represented by the `VerificationState` message in `spa.proto`. While it is a protobuf message conceptually, it is typically implemented over a raw IPC mechanism like a shared memory page.

```protobuf
// From proto/modules/spa.proto
message VerificationState {
  fixed32 magic = 1;            // 0x53504156 ('SPAV')
  uint32 version = 2;           // Protocol version
  enum State {
    STATE_PENDING = 0;
    STATE_VERIFIED = 1;
    STATE_FAILED = 2;
  }
  State state = 3;              // Current state
  uint32 error_code = 4;        // Error code if failed
  bytes metadata_hash = 5;      // SHA-256 of metadata
  uint64 timestamp = 6;         // Completion timestamp
}
```

## 5. Sandboxing Requirements

### 5.1. Process Isolation

PVP execution SHALL occur in a separate, sandboxed process.

### 5.2. System Call Filtering

Implementations SHALL block dangerous system call categories like network, process creation, and privilege escalation.

## 6. Implementation Requirements

Launchers implementing SPA SHALL:
1. Check `FLAG_SPA_ENABLED` in the index.
2. Parse `SPASystemConfig` from metadata.
3. Spawn a verification thread/process.
4. Spawn a sandboxed PVP executor.
5. Synchronize at the verification boundary.

## 7. Failure Handling

On PVP failure, implementations SHOULD gracefully degrade by logging the failure, cleaning up resources, and continuing with verification to launch the main application without the SPA performance benefits.

## 8. Security Considerations

The PVP is ALWAYS untrusted before verification completes. The verification engine MUST be completely isolated from the PVP process. Any sandbox escape or violation MUST lead to immediate termination of the entire package execution.

## 9. Platform-Specific Implementation

- **Linux**: `seccomp-bpf`, namespaces, cgroups
- **macOS**: `sandbox-exec` profiles, Mach ports
- **Windows**: `AppContainer`, Job Objects

## 10. References

- RFC 2119: Key words for use in RFCs
- FEP-0001: PSPF Core Specification
- `proto/modules/spa.proto`
- `proto/modules/index.proto`

---
*Version: 2025.1*
