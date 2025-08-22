# ##_ Core Concepts: Understanding the Magic

In the Quick Start, you saw Flavor turn a simple Python project into a single, executable file. But how does that actually work? Understanding the core concepts of the Progressive Secure Package Format (PSPF) will help you master Flavor.

At its heart, a Flavor package is a cleverly constructed file that is two things at once:
1.  A **native executable** that your operating system can run directly.
2.  A **structured archive**, like a zip file, that contains all your application's parts.

Let's break down its structure.

```
┌──────────────────────────────┐
│                              │
│      Launcher Binary         │
│      (Go or Rust)            │
│                              │
├──────────────────────────────┤
│      Index Block (8KB)       │
├──────────────────────────────┤
│      Metadata (JSON)         │
├──────────────────────────────┤
│      Slot Table              │
├──────────────────────────────┤
│      Slot 0 (e.g., Python)   │
├──────────────────────────────┤
│      Slot 1 (e.g., app code) │
├──────────────────────────────┤
│      ...                     │
├──────────────────────────────┤
│      📦🪄 (Magic Footer)      │
└──────────────────────────────┘
```

### The Launcher: The Engine

The very beginning of the file is a standard executable program, called the **Launcher**. This is typically built in a high-performance, low-dependency language like Go or Rust. When you run your package, the operating system starts this launcher.

The launcher's job is to:
1.  Find the other parts of the file (the index, metadata, and slots).
2.  Verify the package integrity to make sure it hasn't been tampered with.
3.  Set up a temporary, isolated environment for your application to run in.
4.  Extract only the necessary components (this is the "progressive extraction" part).
5.  Execute your application's entry point.

### The Index: The Table of Contents

Immediately after the launcher binary, there is a fixed-size (8 kilobyte) block of data called the **Index**. This is the package's brain or table of contents. It contains critical information, including:
*   Where the other sections (metadata, slots) are located within the file.
*   The package's cryptographic signature and the public key needed to verify it.
*   The total number of "slots" in the package.

By reading this small, fixed-size block, the launcher instantly knows everything it needs to know about the package structure.

### Slots: The Building Blocks

Following the index and metadata, the rest of the file is composed of **Slots**. A slot is just a chunk of data. It can be anything:
*   A Python runtime.
*   Your application's code (e.g., a Python wheel).
*   A dependency library.
*   A configuration file (like a `config.json`).
*   An asset (like an image or a machine learning model).
*   Another binary executable.

Each slot has a defined purpose and lifecycle, telling the launcher what it is and how to handle it (e.g., "this is a temporary config file" or "this is a runtime that should be cached").

### Metadata: The Instruction Manual

The **Metadata** is a simple JSON file that describes your package in detail. It's the instruction manual that the launcher follows. It contains information like:
*   The package name and version.
*   A list of all the slots, what they are, and where to find them.
*   The command to execute to start your application (e.g., run the `hello` function from your `main` module).
*   Environment variables to set for your application.

This metadata is what you implicitly created when you wrote the `[tool.flavor]` section in your `pyproject.toml`.

### Security: Built-in Trust

Every Flavor package is cryptographically sealed.
*   When the package is built, Flavor generates a new key pair.
*   It signs the package's metadata with the private key.
*   It embeds the **public key** and the **signature** into the Index.
*   The private key is then discarded.

Every time the launcher starts, it performs a verification check: it uses the public key (from the index) to verify the signature against the package's metadata. If a single byte has been changed, the verification fails, and the application will not run. This provides powerful, built-in tamper-proofing without the complexity of traditional code-signing certificates.

### The Magic Footer: 📦🪄

No, really. Every valid PSPF file ends with the exact same 8 bytes: the "package" and "magic wand" emojis. This isn't just for fun—it serves as a unique, instantly identifiable "magic number" that confirms the file is a complete and valid Flavor package.

---

**Now that you understand the components, let's look at the tools that build them.**

➡️ **Next: [The Flavor Ecosystem](./03_ecosystem.md)**
