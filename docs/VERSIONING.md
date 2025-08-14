# PSPF 2025 Format Versioning Strategy

This document outlines the versioning strategy for the Progressive Secure Package Format (PSPF) 2025 Edition. This strategy is based on Semantic Versioning principles, adapted to ensure clear compatibility guarantees for the binary format and its associated tooling.

The PSPF 2025 format version is embedded within the bundle itself (e.g., `FormatVersion` in the Index Block and `format` field in `psp.json`), allowing verifiers and launchers to identify the format version and adapt their parsing logic accordingly.

---

## Versioning Scheme: MAJOR.MINOR.PATCH

### MAJOR Version (e.g., `PSPF/2025` -> `PSPF/2026` or `1.0.0` -> `2.0.0`)

*   **Purpose:** Indicates **breaking changes** to the fundamental binary format.
*   **Examples of Breaking Changes:**
    *   Alterations to the fixed-size Index Block structure (e.g., adding/removing fields, changing field sizes or types).
    *   Changes to the overall layout of the bundle (e.g., reordering sections, modifying alignment rules).
    *   Mandatory changes to cryptographic primitives or integrity sealing mechanisms.
    *   Any modification that would prevent an older verifier or launcher from correctly parsing or executing a new bundle, or vice-versa.
*   **Impact:** A major version increment signifies that all components (builders, launchers, verifiers) must be updated to support the new format version to ensure compatibility.

### MINOR Version (e.g., `PSPF/2025.1` -> `PSPF/2025.2` or `1.0.0` -> `1.1.0`)

*   **Purpose:** Indicates **backward-compatible additions or changes** to the format.
*   **Examples of Backward-Compatible Changes:**
    *   Adding new, optional fields to the `psp.json` metadata schema.
    *   Introducing new, optional slot types or purposes.
    *   Supporting new compression algorithms (e.g., `zstd`) that older components can gracefully ignore or fall back from.
    *   Refining existing definitions without breaking older parsers.
*   **Impact:** New components can read and utilize these additions, while older components can still successfully process the core of the bundle, potentially ignoring the new features. This ensures forward compatibility for older readers.

### PATCH Version (e.g., `PSPF/2025.1.0` -> `PSPF/2025.1.1` or `1.0.0` -> `1.0.1`)

*   **Purpose:** Indicates **backward-compatible bug fixes or internal improvements** that do not alter the format specification itself.
*   **Examples of Patch-Level Changes:**
    *   A bug fix in how a builder calculates a checksum, without changing the checksum algorithm or its location in the format.
    *   Performance optimizations in a launcher that don't affect its interaction with the bundle structure.
*   **Impact:** No impact on format compatibility; updates are generally transparent to other components.

## Key Considerations for Implementation

1.  **Explicit Versioning in Bundle:** The format version is explicitly embedded within the PSPF bundle (e.g., `FormatVersion` in the Index Block and `format` in `psp.json`). This allows tools to immediately identify the format version and apply appropriate parsing and processing logic.
2.  **Clear Documentation:** Each version increment (especially major and minor) will be accompanied by clear, detailed documentation outlining all changes and their compatibility implications.
3.  **Component Versioning:** The `Flavor` tool itself, and the individual Go/Rust builders and launchers, will also follow a versioning scheme that indicates which PSPF format versions they support. This helps users understand which tool versions are compatible with which bundle versions.
