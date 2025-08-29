---
fep: 3
title: PSPF/2025 Workenv Directory Management
status: Draft
type: Standards Track
author: Claude <claude@anthropic.com>
created: 2025-08-28
---

# FEP-0003: PSPF/2025 Workenv Directory Management

**Abstract**

This document specifies the system for declarative management of the Working Environment (`workenv`) directory structure within a PSPF/2025 package. It defines a metadata schema for specifying directories to be created at extraction time, including support for Unix-style permissions, process umask handling, and a flexible placeholder substitution system. This allows package authors to precisely define the required directory layout for their application, ensuring a consistent and correct environment on any host system.

## Table of Contents

1.  [Introduction](#1-introduction)
    1.1. [Requirements Language](#11-requirements-language)
    1.2. [Motivation](#12-motivation)
2.  [Directory Management Model](#2-directory-management-model)
    2.1. [The `workenv.directories` Array](#21-the-workenvdirectories-array)
    2.2. [Directory Creation Process](#22-directory-creation-process)
3.  [Metadata Specification](#3-metadata-specification)
    3.1. [The Directory Object](#31-the-directory-object)
    3.2. [The `workenv.umask` Field](#32-the-workenvumask-field)
4.  [Placeholder Substitution](#4-placeholder-substitution)
    4.1. [Supported Placeholders](#41-supported-placeholders)
    4.2. [Expansion at Runtime](#42-expansion-at-runtime)
5.  [Security Considerations](#5-security-considerations)

## 1. Introduction

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119] when, and only when, they appear in all capitals, as shown here.

### 1.2. Motivation

Many applications require a specific directory structure to function correctly. This may include empty directories for temporary files, logs, or user-generated content. Traditionally, ensuring the existence of these directories has been the responsibility of installation scripts or the application's own startup logic. This can lead to inconsistencies and runtime errors if the setup is not performed correctly.

PSPF/2025 aims to create fully self-contained packages. Therefore, the PSPF Launcher MUST be responsible for preparing the entire `workenv` before the application is executed. This FEP defines a declarative mechanism for package authors to specify the required directory structure within the package manifest, delegating the creation and permission-setting to the Launcher.

## 2. Directory Management Model

### 2.1. The `workenv.directories` Array

The core of this specification is the `directories` array within the `workenv` object of the package manifest. This array contains a list of Directory Objects, each one specifying a directory that the Launcher MUST create within the `workenv`.

### 2.2. Directory Creation Process

During the atomic extraction process described in FEP-0001, after extracting all package slots but before executing the application, the Launcher MUST perform the following steps:

1.  **Set Umask**: If the `workenv.umask` field is present in the metadata, the Launcher MUST apply this umask to the current process. The original umask SHOULD be restored after the directory creation process is complete.
2.  **Iterate and Create**: The Launcher SHALL iterate through the `workenv.directories` array. For each Directory Object:
    a.  It MUST substitute any placeholders in the `path` string (see Section 4).
    b.  It MUST create the specified directory, including any necessary parent directories (equivalent to `mkdir -p`).
    c.  If a `mode` is specified, the Launcher MUST apply the specified file permissions to the directory. If the directory already existed, its permissions MUST be updated to match the specified mode.
    d.  If no `mode` is specified, the permissions of a newly created directory will be determined by the standard interaction of the system's default mode (e.g., `0777`) and the active umask.

## 3. Metadata Specification

This section defines the JSON schema for the directory management objects within the PSPF/2025 metadata manifest.

### 3.1. The Directory Object

Each entry in the `workenv.directories` array is an object with the following fields:

- **`path`** (string, REQUIRED): The path of the directory to create, relative to the `workenv` root. This path MUST use the `{workenv}` placeholder as its root (e.g., `{workenv}/logs`).
- **`mode`** (string, OPTIONAL): A Unix-style octal permission string (e.g., `"0755"`, `"1777"`). If provided, the Launcher MUST apply these permissions to the directory.

**Example:**

```json
"workenv": {
  "umask": "0022",
  "directories": [
    {
      "path": "{workenv}/tmp",
      "mode": "1777" 
    },
    {
      "path": "{workenv}/logs",
      "mode": "0750"
    },
    {
      "path": "{workenv}/data/cache"
    }
  ]
}
```

In this example:
- A sticky temporary directory (`/tmp`) is created with world-writable permissions.
- A logging directory (`/logs`) is created with group-writable permissions.
- A data cache directory (`/data/cache`) is created, and its permissions will be determined by the `0022` umask (resulting in `0755`).

### 3.2. The `workenv.umask` Field

The `workenv` object MAY contain a `umask` field.

- **`umask`** (string, OPTIONAL): A Unix-style octal umask string (e.g., `"0022"`, `"0077"`). If provided, the Launcher MUST apply this umask before creating any directories defined in the `directories` array.

## 4. Placeholder Substitution

To create dynamic, platform-aware directory structures, the `path` field in a Directory Object supports placeholder substitution.

### 4.1. Supported Placeholders

The following placeholders MUST be supported by the Launcher:

- **`{workenv}`**: The absolute path to the root of the current `workenv` directory.
- **`{os}`**: The normalized operating system name (e.g., `darwin`, `linux`, `windows`).
- **`{arch}`**: The normalized CPU architecture (e.g., `amd64`, `arm64`).
- **`{platform}`**: A combined string of the form `{os}_{arch}`.

### 4.2. Expansion at Runtime

Before creating a directory, the Launcher MUST expand these placeholders in the `path` string. This allows for the creation of platform-specific directories.

**Example:**

```json
"directories": [
  {
    "path": "{workenv}/platform_libs/{platform}"
  }
]
```

On a 64-bit ARM macOS system, the Launcher would expand this path to `{workenv}/platform_libs/darwin_arm64` before creating it.

## 5. Security Considerations

- The `path` field MUST be validated by the Launcher to prevent directory traversal attacks. Paths should be normalized, and any attempts to reference paths outside of the `{workenv}` (e.g., using `..`) MUST be rejected.
- The `mode` field allows for the creation of world-writable directories (e.g., `"0777"` or `"1777"`). Package authors should use permissive modes with caution, as they can create security risks if the directory is used to store sensitive data or executables.
- The Launcher process itself runs with the privileges of the user who executed it. Therefore, it cannot create directories or set permissions that the user would not normally have access to.
