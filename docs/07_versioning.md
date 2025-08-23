# ##_ Versioning

Flavor and the Progressive Secure Package Format (PSPF) use a versioning strategy based on Semantic Versioning (`MAJOR.MINOR.PATCH`). This applies to both the PSPF format itself and the Flavor tooling. Understanding this will help you manage compatibility between packages and tools.

The format version is embedded directly inside every package, allowing tools to identify and adapt to the specific version of a package.

### Summary

| Version | Change Type                 | Backward Compatible? |
| :------ | :-------------------------- | :------------------- |
| **MAJOR** | Breaking format changes     | No                   |
| **MINOR** | New, optional features      | Yes                  |
| **PATCH** | Bug fixes, internal changes | Yes                  |

### MAJOR Version (`1.0.0` -> `2.0.0`)

A **MAJOR** version change indicates a **breaking change** to the fundamental binary format of a PSPF package.

**When it happens:**
*   The core 8KB Index Block structure is altered.
*   The overall layout of the package file is changed.
*   Fundamental cryptographic methods are changed.

An old launcher will **not** be able to read a package with a new major version. All tools must be updated to support a new major version.

### MINOR Version (`1.0.0` -> `1.1.0`)

A **MINOR** version change indicates a **backward-compatible addition** to the format.

**When it happens:**
*   New, optional fields are added to the `metadata.json`.
*   New slot lifecycles or purposes are introduced.
*   New, optional compression algorithms are supported.

An old launcher **can** still read and execute a package with a new minor version; it will simply ignore the new features it doesn't understand.

### PATCH Version (`1.0.0` -> `1.0.1`)

A **PATCH** version change indicates **internal, backward-compatible bug fixes** or improvements that do not change the format specification.

**When it happens:**
*   A bug is fixed in a builder or launcher that doesn't alter the package format.
*   Performance is optimized without changing behavior.

Patch updates are safe and should not affect compatibility in any way.

### Tool and Component Versioning

The `flavor` tool itself, as well as the Go and Rust helpers, also follow semantic versioning. The version of the tool indicates which PSPF format versions it supports. Always ensure your toolchain is compatible with the format version you intend to produce or consume.

---

**You have now completed the full tour of the Flavor documentation!**
