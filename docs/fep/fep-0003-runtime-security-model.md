# FEP-0003: Runtime Environment Security Model

**Status**: Partially Implemented  
**Type**: Standards Track  
**Created**: 2025-08-28  
**Updated**: 2025-09-02  
**Implementation**: Basic Platform Layer Only ⚠️

## Abstract

This document specifies the runtime environment security model for PSPF/2025 packages. The model provides granular control over the execution environment through a layered approach to environment variables, filesystem access policies, and network restrictions. The goal is to create hermetic, auditable, and secure application packages by default while allowing controlled interaction with the host system.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Layered Environment Model](#2-layered-environment-model)
3. [Environment Variable Processing](#3-environment-variable-processing)
4. [Security Policies](#4-security-policies)
5. [Insecure Mode](#5-insecure-mode)
6. [Implementation Status](#6-implementation-status)

## 1. Introduction

### 1.1 Motivation

Modern applications inherit their parent process environment, which can lead to:

- **Information leakage**: Sensitive environment variables exposed
- **Behavioral inconsistency**: Different behavior based on host environment
- **Security vulnerabilities**: Malicious environment manipulation
- **Debugging difficulties**: Hard to reproduce issues across environments

The PSPF security model addresses these issues through declarative, layered environment control.

### 1.2 Security Principles

- **Deny by default**: Start with minimal environment
- **Explicit allowlisting**: Package authors declare what's needed
- **Layered processing**: Clear precedence rules
- **Audit trail**: Log environment modifications

## 2. Layered Environment Model

Environment variables are processed through four ordered layers:

### 2.1 Processing Order

```
Host Environment (inherited)
    ↓
Layer 1: Runtime Security Layer (filter/block)
    ↓
Layer 2: Workenv Layer (package-specific)
    ↓
Layer 3: Execution Layer (application-specific)
    ↓
Layer 4: Platform Layer (system overrides)
    ↓
Final Environment (provided to application)
```

### 2.2 Layer Precedence

Later layers override earlier ones:
- Host < Runtime < Workenv < Execution < Platform

## 3. Environment Variable Processing

### 3.1 Layer 1: Runtime Security Layer

Controls which host variables pass through:

```json
{
  "runtime": {
    "inherit_env": false,
    "env_passthrough": [
      "PATH",
      "HOME",
      "USER",
      "TERM",
      "LANG",
      "LC_*"
    ],
    "env_blocklist": [
      "SECRET_*",
      "API_KEY_*",
      "PASSWORD_*"
    ],
    "env_mapping": {
      "HOST_TMPDIR": "TMPDIR"
    }
  }
}
```

#### Processing Rules:

```python
def apply_runtime_layer(host_env: dict, runtime_config: dict) -> dict:
    """Apply runtime security filtering."""
    
    result = {}
    
    # Start with empty or inherited environment
    if runtime_config.get("inherit_env", False):
        result = host_env.copy()
    
    # Apply passthrough list
    for pattern in runtime_config.get("env_passthrough", []):
        for key, value in host_env.items():
            if fnmatch(key, pattern):
                result[key] = value
    
    # Apply blocklist (removes even if passed through)
    for pattern in runtime_config.get("env_blocklist", []):
        keys_to_remove = [k for k in result if fnmatch(k, pattern)]
        for key in keys_to_remove:
            del result[key]
    
    # Apply mappings
    for host_key, new_key in runtime_config.get("env_mapping", {}).items():
        if host_key in host_env:
            result[new_key] = host_env[host_key]
    
    return result
```

### 3.2 Layer 2: Workenv Layer

Package-wide environment settings:

```json
{
  "workenv": {
    "env": {
      "PACKAGE_HOME": "{workenv}",
      "PACKAGE_VERSION": "{version}",
      "PYTHONPATH": "{workenv}/lib/python3.11/site-packages"
    }
  }
}
```

### 3.3 Layer 3: Execution Layer

Application-specific variables:

```json
{
  "execution": {
    "env": {
      "APP_MODE": "production",
      "APP_CONFIG": "{workenv}/config/app.conf",
      "LOG_LEVEL": "info"
    }
  }
}
```

### 3.4 Layer 4: Platform Layer

System overrides (always applied):

```python
def set_platform_environment(env: dict) -> None:
    """Set platform-specific variables (non-overridable)."""
    
    env["FLAVOR_OS"] = get_os_name()           # darwin, linux, windows
    env["FLAVOR_ARCH"] = get_arch_name()       # amd64, arm64
    env["FLAVOR_PLATFORM"] = get_platform_string()
    env["FLAVOR_WORKENV"] = str(workenv_dir)
    env["FLAVOR_PACKAGE_NAME"] = package_name
    env["FLAVOR_PACKAGE_VERSION"] = package_version
    
    # Optional platform info
    if os_version := get_os_version():
        env["FLAVOR_OS_VERSION"] = os_version
    if cpu_type := get_cpu_type():
        env["FLAVOR_CPU_TYPE"] = cpu_type
```

## 4. Security Policies

### 4.1 Filesystem Access Control

**Note: Not yet implemented**

```json
{
  "security": {
    "filesystem": {
      "read_allowed": [
        "{workenv}/**",
        "/usr/lib/**",
        "/etc/ssl/**"
      ],
      "write_allowed": [
        "{workenv}/tmp/**",
        "{workenv}/var/**"
      ],
      "execute_allowed": [
        "{workenv}/bin/**",
        "/usr/bin/python*"
      ]
    }
  }
}
```

### 4.2 Network Access Control

**Note: Not yet implemented**

```json
{
  "security": {
    "network": {
      "allowed_hosts": [
        "api.example.com",
        "*.cdn.example.com"
      ],
      "allowed_ports": [80, 443],
      "deny_local": true,
      "dns_servers": ["8.8.8.8", "8.8.4.4"]
    }
  }
}
```

### 4.3 Resource Limits

**Note: Partially implemented via performance hints**

```json
{
  "security": {
    "resources": {
      "max_memory": "2GB",
      "max_cpu": "2",
      "max_files": 1024,
      "max_processes": 10
    }
  }
}
```

## 5. Insecure Mode

**Note: Not yet implemented in current version**

For development and debugging, security can be relaxed:

### 5.1 Environment Variable

```bash
# Disable signature verification and security policies
FLAVOR_INSECURE=1 ./myapp.psp  # PLANNED FEATURE
```

### 5.2 Effects of Insecure Mode

- Signature verification skipped
- All environment variables inherited
- No filesystem restrictions
- No network restrictions
- Warning logged to stderr

### 5.3 Implementation

```python
def is_insecure_mode() -> bool:
    """Check if running in insecure mode."""
    return os.environ.get("FLAVOR_INSECURE") == "1"

if is_insecure_mode():
    logger.warning("⚠️ Running in INSECURE mode - signatures not verified!")
    # Skip security checks
else:
    # Apply full security model
```

## 6. Implementation Status

### 6.1 Implemented ✅

- **Platform environment layer**: Full implementation in `environment.py`
- **Basic environment passing**: Workenv and execution layers via metadata
- **Placeholder substitution**: Full support in paths and environment variables

### 6.2 Not Yet Implemented ❌

- **Runtime security layer**: Planned but not implemented
- **Environment filtering/mapping**: Not implemented
- **Insecure mode**: `FLAVOR_INSECURE` variable not checked
- **Resource limits**: Only memory hints in index, not enforced

### 6.3 Not Implemented ❌

- **Filesystem access control**: Planned for future release
- **Network access control**: Planned for future release
- **Process sandboxing**: Requires platform-specific implementation
- **Audit logging**: Security event tracking

### 6.4 Testing

```python
# Test files
tests/psp/format_2025/test_environment.py
tests/security/test_runtime_layer.py
tests/security/test_insecure_mode.py
```

### 6.5 Future Enhancements

- **SELinux/AppArmor profiles**: Linux security modules
- **Windows security descriptors**: Windows-specific ACLs
- **macOS sandbox profiles**: macOS sandboxing
- **Container integration**: Run in Docker/Podman
- **Capability-based security**: Fine-grained permissions

## Security Considerations

### Threat Model

1. **Malicious environment variables**: Filtered by security layer
2. **Path traversal attacks**: Blocked by path validation
3. **Resource exhaustion**: Limited by resource constraints
4. **Network exfiltration**: Restricted by network policies
5. **Privilege escalation**: Prevented by capability restrictions

### Best Practices

1. Always use minimal `env_passthrough` lists
2. Never pass through `*_KEY`, `*_SECRET`, `*_PASSWORD` patterns
3. Use explicit paths rather than PATH-based lookups
4. Validate all user input before environment expansion
5. Log security-relevant events for audit trails

## References

- [POSIX Environment Variables](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap08.html)
- [Linux Capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html)
- [macOS Sandbox](https://developer.apple.com/documentation/security/app_sandbox)
- [Windows AppContainer](https://docs.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation)

---
*Last Updated: 2025-09-02*