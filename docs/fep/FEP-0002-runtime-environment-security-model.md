---
fep: 2
title: PSPF/2025 Runtime Environment Security Model
status: Draft
type: Standards Track
author: Claude <code@tim.life>
created: 2025-08-28
---

# FEP-0002: PSPF/2025 Runtime Environment Security Model

**Abstract**

This document specifies the Runtime Environment Security Model for the Progressive Secure Package Format (PSPF/2025). This model provides package authors with granular, declarative control over the execution environment of a packaged application. It defines a four-layer system for processing environment variables and introduces security policies for filesystem and network access. The primary goal is to enable the creation of hermetic, auditable, and secure application packages by default, while providing the necessary flexibility to interact with the host system in a controlled manner.

## Table of Contents

1.  [Introduction](#1-introduction)
    1.1. [Requirements Language](#11-requirements-language)
    1.2. [Motivation](#12-motivation)
2.  [The Layered Environment Model](#2-the-layered-environment-model)
    2.1. [Processing Order](#21-processing-order)
    2.2. [Layer 1: The Runtime Security Layer](#22-layer-1-the-runtime-security-layer)
    2.3. [Layer 2: The Workenv Layer](#23-layer-2-the-workenv-layer)
    2.4. [Layer 3: The Execution Layer](#24-layer-3-the-execution-layer)
    2.5. [Layer 4: The Platform Layer](#25-layer-4-the-platform-layer)
3.  [Metadata Specification](#3-metadata-specification)
    3.1. [The `runtime` Object](#31-the-runtime-object)
    3.2. [The `workenv.env` Object](#32-the-workenv-env-object)
    3.3. [The `execution.env` Object](#33-the-execution-env-object)
4.  [Security Policies](#4-security-policies)
    4.1. [Filesystem Access](#41-filesystem-access)
    4.2. [Network Access](#42-network-access)
5.  [Security Considerations](#5-security-considerations)

## 1. Introduction

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119] when, and only when, they appear in all capitals, as shown here.

### 1.2. Motivation

Modern applications often require careful management of their execution environment to ensure security, reproducibility, and correctness. Environment variables are a primary mechanism for configuring application behavior, but they also present a potential attack surface if not handled correctly. A packaged application inherits the environment of its parent process, which can lead to unintended behavior, information leakage, or security vulnerabilities.

The PSPF/2025 Runtime Environment Security Model is designed to give package authors explicit, declarative control over this environment. By defining a series of ordered layers, it allows for the creation of a well-defined, minimal environment, preventing contamination from the host system while allowing specific variables to be passed through, mapped, or set as needed. This model is critical to fulfilling the PSPF promise of creating secure, self-contained application packages.

## 2. The Layered Environment Model

The core of this specification is a four-layer model for constructing the final environment variable set available to a packaged application. The Launcher MUST process these layers in a specific, sequential order, starting with the host process's environment as the base.

### 2.1. Processing Order

The final environment (`final_env`) is constructed as follows:

1.  Start with `base_env`, a copy of the environment of the host process that invoked the Launcher.
2.  Apply Layer 1 (Runtime Security) to `base_env`, producing `env_1`.
3.  Apply Layer 2 (Workenv) to `env_1`, producing `env_2`.
4.  Apply Layer 3 (Execution) to `env_2`, producing `env_3`.
5.  Apply Layer 4 (Platform) to `env_3`, producing `final_env`.

The `final_env` is the environment that SHALL be passed to the application process when it is executed.

### 2.2. Layer 1: The Runtime Security Layer

This is the most critical layer for establishing a secure environment. It is defined by the `runtime.env` object in the package metadata. This layer gives the package author the power to "clean" the environment inherited from the host. It supports four distinct operations, which MUST be applied in the following order:

1.  **`unset`**: This operation removes variables from the environment. It takes an array of strings, where each string is the name of an environment variable to be removed. This is useful for ensuring that potentially sensitive or conflicting variables from the host (e.g., `LD_LIBRARY_PATH`, `PYTHONPATH`) are not passed to the application.
2.  **`pass`**: This operation acts as a whitelist. If the `pass` array is defined, the environment is completely cleared, and only the variables whose names are explicitly listed in the array are carried over from the host environment. This is the most secure way to build an environment, as it guarantees that no unexpected variables are inherited.
3.  **`map`**: This operation renames environment variables. It is an object where keys are the old variable names and values are the new names. This is useful for adapting a generic host environment to the specific needs of the application without exposing internal variable names.
4.  **`set`**: This operation sets environment variables to specific, static values defined in the package manifest. It is an object where keys are variable names and values are their string values. This is used for defining application-specific settings that are known at build time.

### 2.3. Layer 2: The Workenv Layer

This layer is defined by the `workenv.env` object. Its purpose is to inject environment variables that are specific to the `workenv` itself, typically paths. For example, it can be used to prepend the `workenv`'s `bin` directory to the `PATH` variable. Values in this layer will overwrite any values of the same name from the previous layer.

### 2.4. Layer 3: The Execution Layer

This layer is defined by the `execution.env` object. It represents the final, application-specific environment settings. These are variables that are directly related to the command being executed. Values in this layer will overwrite any values of the same name from previous layers.

### 2.5. Layer 4: The Platform Layer

This is a special, mandatory layer that is applied automatically by the Launcher. It is not user-configurable. Its purpose is to inject a set of standardized `FLAVOR_*` variables that provide the application with reliable information about the platform it is running on. These variables MUST be set by the Launcher and MUST overwrite any pre-existing variables of the same name.

The following variables MUST be set in this layer:
- `FLAVOR_OS`: The normalized operating system name (e.g., `darwin`, `linux`, `windows`).
- `FLAVOR_ARCH`: The normalized CPU architecture (e.g., `amd64`, `arm64`).
- `FLAVOR_PLATFORM`: A combined string of the form `{os}_{arch}`.
- `FLAVOR_OS_VERSION`: (OPTIONAL) The operating system's version string, if available.
- `FLAVOR_CPU_TYPE`: (OPTIONAL) The CPU type or family, if available.

## 3. Metadata Specification

This section defines the JSON schema for the environment-related objects within the PSPF/2025 metadata manifest.

### 3.1. The `runtime` Object

The `runtime` object MAY contain an `env` object that defines the Layer 1 security operations.

```json
"runtime": {
  "env": {
    "unset": ["VAR1", "VAR2"],
    "pass": ["USER", "HOME", "PATH"],
    "map": {
      "OLD_VAR_NAME": "NEW_VAR_NAME"
    },
    "set": {
      "APP_MODE": "production"
    }
  },
  "security": {
    "filesystem": "read-only",
    "network": "disabled"
  }
}
```

### 3.2. The `workenv.env` Object

The `workenv` object MAY contain an `env` object that defines Layer 2 variables.

```json
"workenv": {
  "env": {
    "PATH": "{workenv}/bin:/usr/bin:/bin",
    "VIRTUAL_ENV": "{workenv}"
  }
}
```

### 3.3. The `execution.env` Object

The `execution` object MAY contain an `env` object that defines Layer 3 variables.

```json
"execution": {
  "command": "{workenv}/bin/myapp",
  "args": ["--config", "{workenv}/etc/config.json"],
  "env": {
    "MYAPP_CONFIG_PATH": "{workenv}/etc/config.json"
  }
}
```

## 4. Security Policies

In addition to environment variable management, the `runtime.security` object provides high-level policies to control the application's access to the host system.

### 4.1. Filesystem Access

The `runtime.security.filesystem` field defines the default filesystem access policy for the application.

- **`read-write`** (Default): The application has normal filesystem access, subject to standard OS user permissions.
- **`read-only`**: The Launcher SHOULD attempt to restrict filesystem writes. This may be implemented using platform-specific mechanisms like seccomp, AppArmor, or Seatbelt profiles. This is a "best-effort" policy and does not guarantee complete protection.

### 4.2. Network Access

The `runtime.security.network` field defines the network access policy.

- **`enabled`** (Default): The application has normal network access.
- **`disabled`**: The Launcher SHOULD attempt to block all network access. As with filesystem policies, this is a best-effort approach.

## 5. Security Considerations

- The effectiveness of the `pass` operation depends on the package author providing a comprehensive list of necessary variables. An incomplete list may cause the application to fail.
- The security policies for filesystem and network access are considered a best-effort defense-in-depth mechanism, not a guaranteed sandbox. The primary security boundary remains the cryptographic verification of the package itself.
- Package authors SHOULD prefer the `pass` operation over `unset` to create a "deny-by-default" environment, which is a more secure posture.
- Sensitive data, such as passwords or API keys, SHOULD NOT be stored directly in the `set` block of the package manifest, as the manifest is readable by anyone with access to the package file. These should be passed in from the host environment and whitelisted via the `pass` operation.
