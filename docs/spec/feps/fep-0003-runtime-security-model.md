# FEP-0003: Runtime Security Model Specification

**Status**: Partially Implemented  
**Type**: Standards Track  
**Created**: 2025-08-28  
**Updated**: 2025-09-03  

## 1. Introduction

This specification defines the runtime security model for PSPF/2025 packages, establishing a four-layer environment processing system with declarative security policies for filesystem access, network restrictions, and resource limits.

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

### 1.2. Security Objectives

1. Hermetic execution environment by default
2. Explicit declaration of required host interactions
3. Auditable security policy enforcement
4. Defense against environment manipulation attacks
5. Controlled privilege escalation prevention

## 2. Environment Layer Model

### 2.1. Layer Processing Order

Environment variables SHALL be processed through four sequential layers:

```
Layer  Name        Function                Priority
-----  ----------  ----------------------  --------
0      Host        Inherited environment   Lowest
1      Security    Filter/block/map        Low
2      Workenv     Package-wide settings   Medium
3      Execution   Application-specific    High
4      Platform    System overrides        Highest
```

### 2.2. Layer Precedence Rules

1. Each layer MAY modify the environment from previous layers
2. Later layers SHALL override earlier layers for conflicting keys
3. Platform layer variables SHALL NOT be overridable
4. Security layer SHALL have veto power through blocklists

## 3. Security Layer Specification

### 3.1. Configuration Structure

The security layer configuration in metadata:

```json
{
  "runtime": {
    "inherit_env": false,
    "env_passthrough": ["pattern1", "pattern2"],
    "env_blocklist": ["pattern3", "pattern4"],
    "env_mapping": {"HOST_KEY": "NEW_KEY"}
  }
}
```

### 3.2. Processing Algorithm

Implementations SHALL apply the following algorithm:

1. **Initialize**: Start with empty environment unless `inherit_env` is true
2. **Passthrough**: Add matching host variables from `env_passthrough` patterns
3. **Blocklist**: Remove variables matching `env_blocklist` patterns
4. **Mapping**: Rename variables according to `env_mapping`

### 3.3. Pattern Matching

Patterns SHALL support:
- Literal strings: `HOME` matches exactly `HOME`
- Wildcards: `LC_*` matches `LC_ALL`, `LC_TIME`, etc.
- Character classes: `[A-Z]*` matches variables starting with uppercase

### 3.4. Default Passthrough

If no `env_passthrough` specified, implementations SHOULD default to:

```
PATH, HOME, USER, SHELL, TERM, LANG, LC_*, TZ
```

### 3.5. Mandatory Blocklist

Implementations SHALL always block (regardless of configuration):

```
LD_PRELOAD, LD_LIBRARY_PATH, DYLD_*, __CF_*
```

## 4. Workenv Layer Specification

### 4.1. Configuration Structure

```json
{
  "workenv": {
    "env": {
      "KEY": "value",
      "PATH_VAR": "{workenv}/bin:$PATH"
    }
  }
}
```

### 4.2. Variable Expansion

Values SHALL support:
- Placeholder expansion (see FEP-0002 Section 5)
- Reference to existing variables: `$VAR` or `${VAR}`
- Escape sequences: `\$` for literal dollar sign

### 4.3. Processing Order

1. Expand placeholders
2. Resolve variable references from current environment
3. Set or override variables

## 5. Execution Layer Specification

### 5.1. Configuration Structure

```json
{
  "execution": {
    "env": {
      "APP_KEY": "value"
    }
  }
}
```

### 5.2. Scope

Execution layer variables SHALL:
- Apply only to the primary command execution
- Override workenv layer variables
- Support same expansion as workenv layer

## 6. Platform Layer Specification

### 6.1. Required Variables

Implementations MUST set:

```
Variable                Value Description              Example
----------------------  ----------------------------  -------
FLAVOR_WORKENV         Absolute path to workenv      /home/user/.cache/flavor/workenv/app_1.0
FLAVOR_PACKAGE_NAME    Package name from metadata    myapp
FLAVOR_PACKAGE_VERSION Package version from metadata 1.0.0
FLAVOR_OS              Operating system identifier   linux
FLAVOR_ARCH            Architecture identifier       amd64
```

### 6.2. Optional Variables

Implementations MAY set:

```
Variable                Value Description              Example
----------------------  ----------------------------  -------
FLAVOR_PLATFORM        Combined OS and arch          linux_amd64
FLAVOR_OS_VERSION      OS version string             5.15.0-91-generic
FLAVOR_CPU_TYPE        CPU type identifier           x86_64
FLAVOR_SLOT_{N}_PATH   Path to extracted slot N      /home/user/.cache/flavor/workenv/app_1.0/slot_0
```

### 6.3. Override Protection

Platform variables SHALL NOT be modifiable by:
- Package metadata
- User environment
- Application code

## 7. Security Policies

### 7.1. Filesystem Access Control (Future)

When implemented, filesystem policies SHALL use:

```json
{
  "security": {
    "filesystem": {
      "read_allowed": ["path_pattern"],
      "write_allowed": ["path_pattern"],
      "execute_allowed": ["path_pattern"]
    }
  }
}
```

### 7.2. Network Access Control (Future)

When implemented, network policies SHALL use:

```json
{
  "security": {
    "network": {
      "allowed_hosts": ["hostname_pattern"],
      "allowed_ports": [port_numbers],
      "deny_local": boolean,
      "dns_servers": ["ip_addresses"]
    }
  }
}
```

### 7.3. Resource Limits (Future)

When implemented, resource limits SHALL use:

```json
{
  "security": {
    "resources": {
      "max_memory": bytes,
      "max_cpu": cores,
      "max_files": count,
      "max_processes": count
    }
  }
}
```

## 8. Insecure Mode

### 8.1. Activation

Insecure mode SHALL be activated when environment variable `FLAVOR_INSECURE` equals `1`.

### 8.2. Effects

In insecure mode, implementations SHALL:

1. Skip signature verification (see FEP-0001)
2. Inherit full host environment
3. Disable filesystem restrictions
4. Disable network restrictions
5. Log warning to stderr

### 8.3. Warning Format

The warning MUST be visible and include:
```
WARNING: Running in INSECURE mode - signatures not verified, security policies disabled
```

## 9. Audit Logging

### 9.1. Security Events

Implementations SHOULD log:

- Environment variable filtering
- Blocked filesystem operations
- Blocked network connections
- Resource limit violations
- Insecure mode activation

### 9.2. Log Format

Security logs SHALL include:

```json
{
  "timestamp": "ISO-8601",
  "level": "security",
  "event": "event_type",
  "details": {
    "action": "blocked|allowed|modified",
    "target": "resource_identifier",
    "policy": "policy_name"
  }
}
```

## 10. Implementation Status

### 10.1. Currently Implemented

- Platform layer environment variables
- Basic workenv/execution layer variables
- Placeholder expansion in variables

### 10.2. Not Yet Implemented

- Security layer filtering/mapping
- Environment blocklist enforcement
- Insecure mode detection
- Filesystem access control
- Network access control
- Resource limits enforcement
- Audit logging

## 11. Security Considerations

### 11.1. Attack Vectors

Implementations MUST defend against:

1. **Environment injection**: Malicious variables from host
2. **Path manipulation**: Altered PATH leading to wrong executables
3. **Library injection**: LD_PRELOAD attacks
4. **Information disclosure**: Leaking sensitive environment data
5. **Resource exhaustion**: Unbounded resource consumption

### 11.2. Mitigation Strategies

1. Default deny for environment inheritance
2. Explicit allowlisting required
3. Mandatory blocklist for dangerous variables
4. Platform variables non-overridable
5. Audit trail for security events

### 11.3. Best Practices

1. Use minimal `env_passthrough` lists
2. Never pass through credential patterns
3. Validate all user input before expansion
4. Log security-relevant events
5. Regular security policy review

## 12. Platform-Specific Considerations

### 12.1. Linux

- Consider SELinux/AppArmor profiles
- Use seccomp for syscall filtering
- Leverage cgroups for resource limits

### 12.2. macOS

- Use sandbox-exec for sandboxing
- Consider Hardened Runtime
- Leverage Endpoint Security framework

### 12.3. Windows

- Use AppContainer for isolation
- Consider Windows Defender Application Control
- Leverage Job Objects for resource limits

## 13. References

- RFC 2119: Key words for use in RFCs
- FEP-0001: PSPF Core Specification
- FEP-0002: Working Environment Management
- POSIX.1-2017: Environment variables
- Linux capabilities(7)
- Windows Security Model

---
*Version: 2025.1*