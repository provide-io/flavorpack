# Asynchronous Staged Payload Architecture (SPA) Extension for PSPF

**Abstract**

This document specifies an optional extension to the Progressive Secure Package Format (PSPF/2025). This extension, named the Staged Payload Architecture (SPA), reintroduces the "asynchronous 'start-then-halt' verification model" to improve the perceived startup performance of applications.

The SPA model allows a small, untrusted portion of an application's code, the Pre-Verification Payload (PVP), to execute concurrently with the package's cryptographic verification. The PVP performs non-sensitive startup tasks and then halts at a mandatory "Verification Boundary", awaiting a secure handshake from a trusted Verification Engine. Upon successful verification, the PVP is authorized to proceed with the main application logic. This document defines the architectural model, the protocol of operation, and the necessary extensions to the PSPF/2025 metadata to support this functionality.

## Table of Contents

1.  [Introduction](#1-introduction)
    1.1. [Requirements Language](#11-requirements-language)
    1.2. [Motivation](#12-motivation)
    1.3. [Terminology](#13-terminology)
2.  [Architectural Model](#2-architectural-model)
    2.1. [The Hybrid "Asynchronous Polyglot" Model](#21-the-hybrid-asynchronous-polyglot-model)
    2.2. [Component Roles](#22-component-roles)
3.  [Protocol Operation (The "Dependency Gate")](#3-protocol-operation-the-dependency-gate)
    3.1. [Execution Flow](#31-execution-flow)
4.  [Extensions to the PSPF/2025 Format](#4-extensions-to-the-pspf2025-format)
    4.1. [Launcher Structure](#41-launcher-structure)
    4.2. [Metadata Extensions](#42-metadata-extensions)
    4.3. [Index Block Flag](#43-index-block-flag)
5.  [The Handshake Protocol](#5-the-handshake-protocol)
    5.1. [IPC Mechanism](#51-ipc-mechanism)
    5.2. [Security](#52-security)
6.  [Security Considerations](#6-security-considerations)
    6.1. [PVP Attack Surface](#61-pvp-attack-surface)
    6.2. [Handshake Security](#62-handshake-security)
    6.3. [Timeout and Failure Modes](#63-timeout-and-failure-modes)
7.  [References](#7-references)

## 1. Introduction

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 when, and only when, they appear in all capitals, as shown here.

### 1.2. Motivation

The PSPF/2025 specification prioritizes security and reliability through a strict "verify-then-run" execution model. While this provides the strongest integrity guarantees, the initial verification step introduces unavoidable startup latency.

This extension addresses this latency by adapting the principles of asynchronous authentication, as described in early PSPF drafts, to the modern, self-contained polyglot architecture. The goal is to overlap the productive, non-sensitive work of application startup with the time-consuming cryptographic verification process, thereby improving the perceived performance and user experience without requiring a trusted external host loader.

### 1.3. Terminology

*   **Staged Payload Architecture (SPA)**: The architectural model described in this document, where execution is divided into distinct, sequential stages.
*   **Pre-Verification Payload (PVP)**: The first stage of the SPA. A small, untrusted component of the Launcher that executes immediately to perform preliminary setup tasks. This is the conceptual successor to the Initial Execution Payload (IEP) from earlier drafts.[45]
*   **Verification Engine (VE)**: The trusted component of the Launcher, spawned by the PVP. Its sole responsibility is to perform the full PSPF/2025 package verification.
*   **Verification Boundary**: A mandatory control-flow gate within the PVP where execution MUST halt pending a successful verification signal from the VE.[45]
*   **Handshake Protocol**: The secure IPC mechanism used by the VE to signal a successful verification outcome to the halted PVP.

## 2. Architectural Model

### 2.1. The Hybrid "Asynchronous Polyglot" Model

This extension modifies the monolithic nature of the PSPF Launcher. For an SPA-enabled package, the Native Launcher binary is a polyglot process containing two distinct logical components that operate concurrently. This model preserves the self-contained, daemon-less nature of PSPF/2025 while reintroducing the performance benefits of concurrent verification.

### 2.2. Component Roles

*   **Pre-Verification Payload (PVP)**: The PVP is the untrusted "stager" of the application.[45] It is the first code to run when the user executes the package. Its responsibilities are:
    *   To spawn the Verification Engine (VE) in a separate thread or process.
    *   To pass a one-time secret to the VE for the subsequent handshake.
    *   To perform non-sensitive, resource-intensive startup tasks (e.g., initializing a UI, loading non-critical assets).
    *   To establish an IPC listener (e.g., a local socket) for the handshake.
    *   To halt execution at the Verification Boundary, awaiting the handshake.

*   **Verification Engine (VE)**: The VE is the trusted component. Its responsibilities are:
    *   To perform the complete, multi-layered verification workflow as specified in the PSPF/2025 specification.
    *   Upon successful verification, to connect to the PVP's IPC listener and transmit the one-time secret to complete the handshake.
    *   Upon verification failure, to securely terminate the PVP process and exit.

## 3. Protocol Operation (The "Dependency Gate")

### 3.1. Execution Flow

The execution of an SPA-enabled package MUST follow these steps:
1.  **Start**: The user executes the package. The operating system loads the Launcher, and the PVP component begins execution immediately.
2.  **Spawn Verifier**: As one of its first actions, the PVP spawns the VE as a concurrent process or thread, providing it with the path to the package file and a securely generated, one-time-use secret token.
3.  **Concurrent Work**: The PVP proceeds with its predefined, non-sensitive startup tasks. In parallel, the VE begins the full PSPF/2025 verification process.
4.  **Halt at Boundary**: The PVP completes its initial tasks and reaches the Verification Boundary. It is now in a halted state, listening on its IPC socket for the handshake from the VE.
5.  **Handshake**: The VE completes its verification.
    *   **On Success**: The VE connects to the PVP's IPC socket and sends the correct one-time secret token.
    *   **On Failure**: The VE sends a termination signal (e.g., SIGTERM) to the PVP process and exits with a non-zero status.
6.  **Proceed**: Upon receiving a valid handshake, the PVP is now considered trusted. It crosses the "dependency gate" and proceeds with the main application logic, which typically involves performing the full atomic extraction into the `workenv` and executing the main command as defined in the package metadata.

## 4. Extensions to the PSPF/2025 Format

### 4.1. Launcher Structure

The Native Launcher binary for an SPA-enabled package MUST contain the executable code for both the PVP and the VE components, along with the logic to orchestrate their concurrent execution.

### 4.2. Metadata Extensions

To enable and configure the SPA model, the `execution` object in the JSON metadata is extended with an OPTIONAL `spa` object.

```json
"execution": {
  "command": "...",
  "spa": {
    "enabled": true,
    "verification_boundary": {
      "type": "ipc_handshake",
      "ipc_socket_name": "pspf_verify_{pid}",
      "timeout_seconds": 30
    }
  }
}
```

*   **`spa.enabled`**: A boolean that, if true, instructs the Launcher to use the SPA model. If absent or false, the Launcher MUST default to the standard "verify-then-run" model.
*   **`spa.verification_boundary.type`**: Specifies the halting mechanism. Initially, only "ipc_handshake" is defined.
*   **`spa.verification_boundary.ipc_socket_name`**: A template for the name of the local socket or named pipe. The `{pid}` placeholder SHOULD be substituted with the PVP's process ID.
*   **`spa.verification_boundary.timeout_seconds`**: The maximum time in seconds the PVP will wait for a successful handshake before terminating itself.

### 4.3. Index Block Flag

To allow loaders to quickly identify an SPA-enabled package without parsing the JSON metadata, a new flag is defined for the `flags` field in the 8KB Index Block.
*   **`SPA_ENABLED` (Bit 8): `0x0100`**. If this bit is set, the package supports the Staged Payload Architecture.

## 5. The Handshake Protocol

### 5.1. IPC Mechanism

The RECOMMENDED IPC mechanism is a Unix domain socket or a Windows named pipe, as these are scoped to the local machine and avoid network stack complexities. The socket name MUST be unique per instance, typically by incorporating the PVP's process ID.

### 5.2. Security

The handshake protocol MUST be secured against spoofing from other local processes. This is achieved by using a one-time secret token. The PVP MUST generate a cryptographically secure random token upon startup and pass it to the VE as an argument or via an environment variable. The VE MUST transmit this exact token back to the PVP to complete the handshake. The PVP MUST only accept the handshake if the received token is identical to the one it generated.

## 6. Security Considerations

### 6.1. PVP Attack Surface

The primary security trade-off of the SPA model is that the PVP code runs before the package has been cryptographically verified. Therefore, the PVP represents a potential attack surface.

The PVP's capabilities MUST be strictly limited. It SHOULD NOT perform any sensitive operations, such as accessing the network (other than its local IPC socket), reading sensitive user files, or modifying system state.

Implementations SHOULD consider using OS-level sandboxing mechanisms (e.g., seccomp-bpf on Linux) to enforce these restrictions on the PVP until the verification handshake is complete.

### 6.2. Handshake Security

An attacker could attempt to send a fake handshake to the PVP to bypass verification. The use of a high-entropy, one-time secret token, known only to the parent PVP and child VE processes, mitigates this risk. The IPC socket SHOULD also be created with permissions that restrict access to the current user only.

### 6.3. Timeout and Failure Modes

If the VE fails to send a handshake within the specified timeout (either because verification failed or the VE crashed), the PVP MUST securely terminate itself and perform cleanup of any temporary resources. It MUST NOT proceed to the main application logic.

## 7. References

[45] *TODO: Add reference*
