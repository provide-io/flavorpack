# FEP-0004: Staged Payload Architecture (SPA)

**Status**: Proposed  
**Type**: Standards Track  
**Created**: 2025-08-28  
**Updated**: 2025-09-02  
**Implementation**: Not Started ❌

## Abstract

This document specifies the Staged Payload Architecture (SPA), an optional extension to PSPF/2025 that enables asynchronous "start-then-halt" verification. SPA allows a small, untrusted portion of application code (the Pre-Verification Payload or PVP) to execute concurrently with cryptographic verification, performing non-sensitive startup tasks before halting at a mandatory Verification Boundary. This improves perceived startup performance while maintaining security guarantees.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Trust Model](#3-trust-model)
4. [Pre-Verification Payload (PVP)](#4-pre-verification-payload-pvp)
5. [Verification Boundary Protocol](#5-verification-boundary-protocol)
6. [Implementation Design](#6-implementation-design)
7. [Security Considerations](#7-security-considerations)
8. [Relationship to JIT Loading](#8-relationship-to-jit-loading)

## 1. Introduction

### 1.1 Motivation

Package signature verification typically takes 50-500ms depending on:
- Package size (hashing large files)
- CPU performance (Ed25519 operations)
- I/O performance (reading package data)

During this time, traditional PSPF packages cannot execute any code, leading to perceived slow startup. SPA addresses this by allowing limited, safe operations to occur during verification.

### 1.2 Goals

- **Improve perceived performance**: Start UI/initialization during verification
- **Maintain security**: Never execute sensitive operations before verification
- **Simple integration**: Minimal changes to existing PSPF format
- **Clear boundaries**: Explicit separation of trusted/untrusted code

### 1.3 Non-Goals

- **Not a replacement for verification**: All packages must still be verified
- **Not for security-sensitive operations**: PVP is explicitly untrusted
- **Not for small packages**: Overhead may exceed benefits for <10MB packages

## 2. Architecture Overview

### 2.1 Component Model

```
┌─────────────────────────────────────┐
│         PSPF Package File           │
├─────────────────────────────────────┤
│   Native Launcher (Modified)        │
│   ├── Verification Engine           │
│   └── PVP Executor                  │
├─────────────────────────────────────┤
│   8192-byte Index (w/ SPA flag)     │
├─────────────────────────────────────┤
│   Metadata (w/ PVP config)          │
├─────────────────────────────────────┤
│   Slot 0: PVP Code (untrusted)      │
├─────────────────────────────────────┤
│   Slot 1+: Main Application         │
└─────────────────────────────────────┘
```

### 2.2 Execution Flow

```
[Package Launch]
      ↓
[Fork/Thread Split]
      ├─[Thread A: Verification Engine]
      │     ├── Read package
      │     ├── Verify signatures
      │     └── Send "verified" signal
      │
      └─[Thread B: PVP Executor]
            ├── Extract PVP slot
            ├── Execute PVP code
            ├── Hit Verification Boundary
            ├── Wait for "verified" signal
            └── Continue with main app
```

### 2.3 Timing Diagram

```
Time →  0ms          100ms         200ms         300ms
        │             │             │             │
Verify: [====Hashing====][==Sig Check==][Done]→
        │             │             │     ↓
PVP:    [Init][Render UI][Prep Cache]→[Wait][Continue→
        │             │             │     ↑
        └─────────────┴─────────────┴─────┘
                  Verification Boundary
```

## 3. Trust Model

### 3.1 Trust Levels

| Component | Trust Level | Capabilities |
|-----------|------------|--------------|
| Launcher | Trusted | Full system access |
| Verification Engine | Trusted | Read package, verify signatures |
| PVP Code | **Untrusted** | Limited, sandboxed operations |
| Main Application | Trusted (after verification) | Full application privileges |

### 3.2 PVP Restrictions

The Pre-Verification Payload MUST operate under strict limitations:

**Allowed Operations:**
- Render UI elements (splash screen, progress bars)
- Initialize non-sensitive caches
- Prepare temporary directories
- Load configuration defaults
- Establish IPC channels
- Allocate memory buffers

**Forbidden Operations:**
- Network access
- Filesystem writes (except temp)
- Access to sensitive APIs
- Loading user data
- Executing external processes
- Modifying system settings

### 3.3 Enforcement Mechanisms

```python
class PVPSandbox:
    """Sandbox for Pre-Verification Payload execution."""
    
    def __init__(self):
        self.blocked_modules = {
            'socket', 'urllib', 'requests',  # No network
            'subprocess', 'os.system',       # No process spawn
            'ctypes', 'cffi',               # No FFI
        }
        self.allowed_paths = [
            '/tmp/pspf_pvp_*',              # Temp files only
            '/dev/null',                     # Null device
            '/dev/urandom',                  # RNG access
        ]
    
    def execute_pvp(self, pvp_code: bytes) -> None:
        """Execute PVP in restricted environment."""
        
        # Create restricted globals
        restricted_builtins = {
            k: v for k, v in __builtins__.items()
            if k not in ['exec', 'eval', 'compile', '__import__']
        }
        
        # Custom import hook
        original_import = builtins.__import__
        def restricted_import(name, *args, **kwargs):
            if name in self.blocked_modules:
                raise SecurityError(f"Module {name} not allowed in PVP")
            return original_import(name, *args, **kwargs)
        
        # Execute with restrictions
        exec(pvp_code, {
            '__builtins__': restricted_builtins,
            '__import__': restricted_import,
            'VERIFICATION_BOUNDARY': self.verification_boundary,
        })
```

## 4. Pre-Verification Payload (PVP)

### 4.1 PVP Metadata

```json
{
  "spa": {
    "enabled": true,
    "pvp_slot": 0,
    "pvp_timeout_ms": 5000,
    "pvp_max_memory_mb": 100,
    "pvp_capabilities": [
      "ui_render",
      "temp_files",
      "ipc_setup"
    ],
    "verification_boundary": {
      "type": "synchronous",
      "timeout_ms": 10000,
      "fallback": "terminate"
    }
  }
}
```

### 4.2 PVP Code Structure

```python
# Example PVP code (slot_0/pvp_main.py)

import sys
import time
from pathlib import Path

def initialize_ui():
    """Create splash screen (platform-specific)."""
    if sys.platform == "darwin":
        # macOS splash screen
        pass
    elif sys.platform == "linux":
        # X11/Wayland splash
        pass
    elif sys.platform == "win32":
        # Windows splash
        pass

def prepare_cache():
    """Set up cache directories."""
    cache_dir = Path("/tmp/pspf_pvp_cache")
    cache_dir.mkdir(exist_ok=True)
    
    # Pre-allocate buffers
    buffers = []
    for i in range(10):
        buffers.append(bytearray(1024 * 1024))  # 1MB buffers

def pvp_main():
    """PVP entry point."""
    
    # Non-sensitive initialization
    initialize_ui()
    prepare_cache()
    
    # Set up IPC for progress updates
    ipc_socket = create_ipc_channel()
    
    # VERIFICATION BOUNDARY - Mandatory halt point
    VERIFICATION_BOUNDARY()  # Blocks until verified
    
    # Post-verification - now trusted
    load_main_application()

if __name__ == "__main__":
    pvp_main()
```

## 5. Verification Boundary Protocol

### 5.1 Boundary Types

#### Synchronous Boundary
```python
def VERIFICATION_BOUNDARY():
    """Block until verification completes."""
    
    # Wait for signal from Verification Engine
    while not verified_flag.is_set():
        time.sleep(0.001)  # 1ms polling
    
    # Check verification result
    if not verification_result.success:
        raise VerificationError(verification_result.error)
    
    # Continue execution as trusted code
    return verification_result.metadata
```

#### Asynchronous Boundary
```python
async def VERIFICATION_BOUNDARY_ASYNC():
    """Async wait for verification."""
    
    # Await verification completion
    result = await verification_future
    
    if not result.success:
        raise VerificationError(result.error)
    
    return result.metadata
```

### 5.2 IPC Mechanisms

#### Shared Memory (Fastest)
```c
// Launcher creates shared memory segment
typedef struct {
    volatile int verified;
    volatile int success;
    char error_msg[256];
    uint8_t metadata_hash[32];
} verification_state_t;

verification_state_t* state = mmap(NULL, sizeof(verification_state_t),
                                  PROT_READ | PROT_WRITE,
                                  MAP_SHARED | MAP_ANONYMOUS, -1, 0);
```

#### Unix Domain Socket (Portable)
```python
# Verification Engine (server)
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind("/tmp/pspf_verify.sock")
server.listen(1)

# PVP (client)
client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
client.connect("/tmp/pspf_verify.sock")
result = client.recv(1024)
```

#### Named Pipe (Windows)
```python
# Windows named pipe
pipe_name = r'\\.\pipe\pspf_verification'
pipe = win32pipe.CreateNamedPipe(
    pipe_name,
    win32pipe.PIPE_ACCESS_DUPLEX,
    win32pipe.PIPE_TYPE_MESSAGE
)
```

### 5.3 Handshake Protocol

```
PVP                        Verification Engine
 |                                |
 |---> READY (with PID) -------->|
 |                                |
 |<--- ACK (with nonce) <--------|
 |                                |
 |---> WAITING AT BOUNDARY ----->|
 |                                |
 |     [Verification occurs]      |
 |                                |
 |<--- VERIFIED (with proof) <---|
 |                                |
 |---> PROCEEDING -------------->|
 |                                |
```

## 6. Implementation Design

### 6.1 Launcher Modifications

```rust
// Rust launcher with SPA support
pub struct SPALauncher {
    package: PSPFPackage,
    verification_state: Arc<Mutex<VerificationState>>,
}

impl SPALauncher {
    pub fn launch(&self) -> Result<(), Error> {
        // Check if SPA is enabled
        if !self.package.metadata.spa.enabled {
            return self.launch_traditional();
        }
        
        // Create shared state
        let state = Arc::new(Mutex::new(VerificationState::default()));
        
        // Spawn verification thread
        let verify_handle = thread::spawn({
            let package = self.package.clone();
            let state = state.clone();
            move || verify_package(package, state)
        });
        
        // Spawn PVP thread
        let pvp_handle = thread::spawn({
            let package = self.package.clone();
            let state = state.clone();
            move || execute_pvp(package, state)
        });
        
        // Wait for both
        verify_handle.join()?;
        pvp_handle.join()?;
        
        // Continue with main application
        self.execute_main()
    }
}
```

### 6.2 Index Block Extension

Add SPA flag to the index flags field:

```python
# Bit flags for index.flags field
FLAG_SPA_ENABLED = 1 << 0      # Bit 0: SPA enabled
FLAG_PVP_SANDBOXED = 1 << 1    # Bit 1: PVP requires sandbox
FLAG_ASYNC_BOUNDARY = 1 << 2   # Bit 2: Async verification boundary
```

### 6.3 Platform-Specific Sandboxing

#### Linux (seccomp-bpf)
```c
scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_KILL);
seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(read), 0);
seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(write), 1,
                SCMP_A0(SCMP_CMP_EQ, STDOUT_FILENO));
seccomp_load(ctx);
```

#### macOS (Sandbox Profile)
```scheme
(version 1)
(deny default)
(allow file-read* (subpath "/tmp/pspf_pvp"))
(allow file-write* (subpath "/tmp/pspf_pvp"))
(allow mach-lookup (global-name "com.apple.window_server"))
```

#### Windows (AppContainer)
```cpp
PSID container_sid;
CreateAppContainerProfile(L"PSPF_PVP_Container", 
                         L"PVP Sandbox",
                         L"Pre-Verification Payload",
                         nullptr, 0, &container_sid);
```

## 7. Security Considerations

### 7.1 Attack Vectors

| Attack | Mitigation |
|--------|------------|
| PVP escapes sandbox | Process isolation, syscall filtering |
| PVP consumes resources | Memory/CPU limits, timeout |
| PVP leaks information | No access to sensitive data |
| Race conditions | Atomic operations, proper synchronization |
| PVP influences verification | Complete isolation of verification engine |

### 7.2 Defense in Depth

1. **Process Isolation**: Run PVP in separate process
2. **Syscall Filtering**: Block dangerous system calls
3. **Resource Limits**: Cap memory, CPU, file handles
4. **Time Limits**: Kill PVP after timeout
5. **Minimal Privileges**: Drop all unnecessary capabilities
6. **Audit Logging**: Log all PVP operations

### 7.3 Failure Modes

```python
class SPAFailureHandler:
    """Handle SPA-specific failures."""
    
    def handle_pvp_timeout(self):
        """PVP exceeded time limit."""
        # Kill PVP process
        # Continue with traditional launch
        # Log incident
    
    def handle_pvp_crash(self):
        """PVP crashed or terminated."""
        # Clean up resources
        # Continue verification
        # Launch without PVP benefits
    
    def handle_verification_failure(self):
        """Package failed verification."""
        # Terminate PVP immediately
        # Clean up all resources
        # Display error to user
```

## 8. Relationship to JIT Loading

SPA and JIT Loading (FEP-0005) are complementary:

### 8.1 Combined Architecture

```
[Launch] → [SPA: PVP starts] → [SPA: Verify] → [JIT: Load essential]
                ↓                                        ↓
          [UI renders]                           [App runs]
                                                        ↓
                                                 [JIT: Load on-demand]
```

### 8.2 Synergies

1. **SPA Phase** (0-500ms)
   - Initialize UI while verifying
   - Prepare JIT loader infrastructure
   - Set up IPC for progress reporting

2. **JIT Phase** (500ms+)
   - Load only essential slots initially
   - Defer large assets/models
   - Stream from network as needed

### 8.3 Configuration Example

```json
{
  "spa": {
    "enabled": true,
    "pvp_slot": 0,
    "pvp_capabilities": ["ui_render", "jit_prepare"]
  },
  "jit": {
    "enabled": true,
    "essential_slots": [1, 2],
    "deferred_slots": [3, 4, 5],
    "network_slots": [6, 7, 8]
  }
}
```

## Performance Metrics

### Expected Improvements

| Metric | Traditional | SPA Only | SPA + JIT |
|--------|------------|----------|-----------|
| Time to first pixel | 500ms | 50ms | 50ms |
| Time to interactive | 2000ms | 1500ms | 800ms |
| Full load time | 2000ms | 2000ms | 500ms + lazy |
| Memory usage | 500MB | 500MB | 200MB + dynamic |

### Measurement Points

```python
@dataclass
class SPAMetrics:
    launch_time: float
    pvp_start_time: float
    ui_render_time: float
    verification_start: float
    verification_end: float
    boundary_wait_time: float
    main_app_start: float
    fully_loaded_time: float
    
    @property
    def perceived_startup(self) -> float:
        """Time until user sees response."""
        return self.ui_render_time - self.launch_time
    
    @property
    def verification_overhead(self) -> float:
        """Time spent verifying."""
        return self.verification_end - self.verification_start
```

## Future Enhancements

### Phase 1: Basic SPA
- Simple PVP execution
- Synchronous boundary
- Basic sandboxing

### Phase 2: Advanced Sandboxing
- Platform-specific isolation
- Fine-grained capabilities
- Resource accounting

### Phase 3: Optimizations
- Parallel verification
- Incremental verification
- Caching verification results

### Phase 4: Integration
- Combine with JIT loading
- Network verification
- Distributed trust model

## References

- [seccomp-bpf](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html)
- [macOS App Sandbox](https://developer.apple.com/documentation/security/app_sandbox)
- [Windows AppContainer](https://docs.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation)
- [Process Isolation Techniques](https://chromium.googlesource.com/chromium/src/+/master/docs/design/sandbox.md)

---
*Last Updated: 2025-09-02*