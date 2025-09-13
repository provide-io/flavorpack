# FEP-0007: Staged Payload Architecture Specification

**Status**: Future  
**Type**: Standards Track  
**Created**: 2025-08-28  
**Updated**: 2025-09-03  
**Target Version**: v1 or later

**Note**: This advanced feature is deferred from v0 due to complexity. v0 implementations are not required to support SPA.  

## 1. Introduction

This specification defines the Staged Payload Architecture (SPA), an optional extension to PSPF/2025 enabling concurrent execution of untrusted initialization code during cryptographic verification. SPA improves perceived startup performance through asynchronous "start-then-halt" verification while maintaining security guarantees.

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

### 1.2. Design Goals

1. Reduce perceived startup latency without compromising security
2. Execute non-sensitive initialization during verification
3. Maintain clear trust boundaries between components
4. Provide platform-agnostic sandboxing mechanisms
5. Enable graceful degradation on failure

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

### 2.2. Execution Timeline

```
Time(ms): 0     50    100   150   200   250   300
          |-----|-----|-----|-----|-----|-----|
Verify:   [====Hashing====][Sig Check][Done]→
PVP:      [Init][UI][Cache]→[Wait----][Main→
                            ↑
                   Verification Boundary
```

### 2.3. Index Flag

SPA capability SHALL be indicated by bit 5 in the index flags field:

```
Bit  Name           Value    Description
---  -------------  -------  -----------
5    SPA_ENABLED    0x20     Package supports SPA
```

## 3. Pre-Verification Payload (PVP)

### 3.1. Designation

The PVP SHALL be stored in slot 0 with lifecycle type 0 (INIT) and purpose type 1 (CODE).

### 3.2. Metadata Configuration

Packages SHALL declare SPA configuration in metadata:

```json
{
  "spa": {
    "enabled": true,
    "pvp_slot": 0,
    "pvp_timeout_ms": 5000,
    "pvp_max_memory": 104857600,
    "pvp_capabilities": ["ui_render", "temp_files"],
    "boundary_type": "synchronous",
    "boundary_timeout_ms": 10000
  }
}
```

### 3.3. Capability Definitions

```
Capability    Description                 Allowed Operations
-----------   -------------------------   ------------------
ui_render     Display user interface      Window creation, drawing
temp_files    Temporary file access       Write to temp directory
ipc_setup     Inter-process communication Create IPC channels
cache_init    Initialize caches           Memory allocation
config_load   Load default configuration  Read embedded config
```

### 3.4. Restricted Operations

PVP code SHALL NOT:
- Access network interfaces
- Read user files
- Write to persistent storage
- Execute external processes
- Load dynamic libraries
- Access cryptographic keys
- Modify system configuration

## 4. Verification Boundary Protocol

### 4.1. Boundary Definition

The Verification Boundary is a mandatory synchronization point where PVP execution halts until verification completes.

### 4.2. Signaling Mechanism

Implementations SHALL provide one of:

1. **Shared Memory**: 4096-byte page with verification state
2. **Unix Socket**: Domain socket at `/tmp/pspf_{pid}.sock`
3. **Named Pipe**: Platform-specific pipe
4. **Semaphore**: System V or POSIX semaphore

### 4.3. State Structure

The verification state SHALL contain:

```
Offset  Size  Type      Field               Description
------  ----  --------  ------------------  -----------
0       4     uint32    magic               0x53504156 ('SPAV')
4       4     uint32    version             Protocol version
8       4     uint32    state               0=pending, 1=verified, 2=failed
12      4     uint32    error_code          Error if failed
16      32    bytes     metadata_hash       SHA-256 of metadata
48      8     uint64    timestamp           Verification completion time
56      4040  bytes     reserved            Zero-filled
```

### 4.4. Handshake Protocol

```
PVP → Engine: READY(pid, nonce)
Engine → PVP: ACK(nonce)
PVP → Engine: AT_BOUNDARY
[Verification occurs]
Engine → PVP: VERIFIED(hash) | FAILED(error)
PVP → Engine: PROCEEDING | TERMINATING
```

## 5. Sandboxing Requirements

### 5.1. Process Isolation

PVP execution SHALL occur in a separate process with:
- Restricted system call access
- Limited file system visibility
- No network capabilities
- Bounded resource consumption

### 5.2. System Call Filtering

Implementations SHALL block at minimum:

```
Category        Blocked Calls
--------------  -------------
Network         socket, connect, bind, listen
Process         fork, execve, clone
Filesystem      mount, chroot, pivot_root
Kernel          module_load, reboot
Privilege       setuid, setgid, capset
```

### 5.3. Resource Limits

```
Resource        Limit           Enforcement
--------------  --------------  -----------
Memory          pvp_max_memory  Process limit
CPU Time        pvp_timeout_ms  Timer signal
File Handles    256             Resource limit
Threads         1               Clone prevention
```

## 6. Implementation Requirements

### 6.1. Launcher Modifications

Launchers implementing SPA SHALL:

1. Check SPA_ENABLED flag in index
2. Parse SPA configuration from metadata
3. Create verification state structure
4. Spawn verification thread/process
5. Spawn PVP executor with sandbox
6. Synchronize at verification boundary
7. Continue with main application or terminate

### 6.2. Verification Engine

The verification engine SHALL:

1. Run independently of PVP execution
2. Complete full cryptographic verification
3. Signal result through agreed mechanism
4. NOT be influenced by PVP execution

### 6.3. PVP Executor

The PVP executor SHALL:

1. Extract and validate PVP slot
2. Configure sandbox environment
3. Execute PVP code with restrictions
4. Block at verification boundary
5. Terminate on timeout or failure

## 7. Failure Handling

### 7.1. Failure Modes

```
Failure              Detection                Action
-------------------  ----------------------   ------
PVP timeout          Timer expiration         Kill PVP, continue verify
PVP crash            Process termination      Log, continue normally
Verification fail    Signature invalid        Kill PVP, terminate
Sandbox breach       Syscall violation        Kill PVP, terminate
Resource exceeded    Limit reached            Kill PVP, continue
```

### 7.2. Graceful Degradation

On PVP failure, implementations SHALL:
1. Log the failure with details
2. Clean up PVP resources
3. Continue verification if not compromised
4. Launch without PVP benefits if verified

## 8. Security Considerations

### 8.1. Trust Model

1. PVP code is ALWAYS untrusted before verification
2. Verification engine MUST be isolated from PVP
3. Sandbox escape SHALL terminate execution
4. Resource exhaustion SHALL NOT affect verification

### 8.2. Attack Mitigation

```
Attack Vector         Mitigation
-------------------   -----------
Sandbox escape        Process isolation, syscall filtering
Resource exhaustion   Hard limits, timeout enforcement
Data exfiltration     No network access, limited I/O
Verification bypass   Complete isolation of verifier
Race conditions       Atomic operations, proper locking
```

### 8.3. Defense Layers

1. **Process Isolation**: Separate address space
2. **Syscall Filtering**: Kernel-level enforcement
3. **Resource Capping**: Hard limits on consumption
4. **Time Bounds**: Mandatory timeout
5. **Capability Dropping**: Minimal privileges
6. **Audit Logging**: Complete operation trail

## 9. Platform-Specific Implementation

### 9.1. Linux

- Sandbox: seccomp-bpf, namespaces
- IPC: Unix domain sockets, shared memory
- Resources: cgroups, rlimits

### 9.2. macOS

- Sandbox: sandbox-exec profiles
- IPC: Mach ports, Unix sockets
- Resources: Sandbox resource limits

### 9.3. Windows

- Sandbox: AppContainer, Job Objects
- IPC: Named pipes, shared memory
- Resources: Job Object limits

## 10. Performance Metrics

### 10.1. Measurement Points

Implementations SHOULD track:

```
Metric                    Description                 Target
----------------------    -------------------------   ------
time_to_first_pixel       PVP UI display              <50ms
verification_duration     Signature verification      <500ms
boundary_wait_time        Time blocked at boundary    <10ms
total_startup_time        Launch to main execution    <600ms
```

### 10.2. Optimization Opportunities

1. Parallel hash computation during PVP execution
2. Incremental signature verification
3. Cached verification results
4. Pre-computed sandbox configuration

## 11. Relationship to Other FEPs

### 11.1. FEP-0005 (JIT Loading)

SPA and JIT Loading are complementary:
- SPA handles pre-verification initialization
- JIT handles post-verification lazy loading
- Combined use reduces both perceived and actual startup time

### 11.2. FEP-0003 (Security Model)

SPA respects the security model:
- PVP runs with minimal environment
- Security policies enforced post-verification
- Insecure mode affects verification, not sandboxing

## 12. References

- RFC 2119: Key words for use in RFCs
- FEP-0001: PSPF Core Specification
- FEP-0003: Runtime Security Model
- FEP-0005: Just-In-Time Loading
- Linux seccomp(2)
- macOS Sandbox Guide
- Windows App Container

---
*Version: 2025.1*