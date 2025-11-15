**Code Review: `tests/test_pspf_2025_builder.py`**

*   **Purpose:** This file contains tests for the `PSPFBuilder` class, focusing on bundle building, manifest handling, and various build options.
*   **Observations:**
    *   **`manifest_file` fixture:** Creates a simple TOML manifest.
    *   **`test_build_from_manifest`:** Tests building a bundle from a manifest file.
    *   **`test_automatic_launcher_selection_python`:** Tests launcher emoji selection.
    *   **`test_custom_emoji_selection`:** Tests custom emoji selection.
    *   **`test_compression_selection`:** Tests different compression types (gzip, zstd, none). This test *uses* `"zstd"` as a compression type in `SlotMetadata`, implying that the builder *should* handle it, even though `DEVELOPMENT.md` lists it as a "Next Step." This suggests that the builder might be set up to accept `zstd` but the actual compression logic might be a placeholder or incomplete.
    *   **`test_build_validation_missing_file`:** Tests handling of missing files.
    *   **`test_persistent_key_signing`:** This test is highly relevant to our cryptographic discussion.
        *   It defines `metadata` with a `verification` block that includes `integrity_seal` with `"algorithm": "ecdsa-p256"`. This *again* contradicts `SPECIFICATION.md` (Ed25519).
        *   It also includes a `trust_signatures` block with a signer using `"algorithm": "ed25519"`. This suggests a more complex signing model where both ECDSA P-256 and Ed25519 might be involved for different purposes.
        *   The comment "In real implementation, would use actual crypto keys" is interesting, but the test itself doesn't perform actual signature verification.

*   **Relevance to Cryptographic Inconsistency:**
    *   The repeated use of `"ecdsa-p256"` for `integrity_seal` in test metadata (here and in `test_pspf_2025_core.py`) is a strong indicator of a fundamental disconnect between the `SPECIFICATION.md` and the current testing/implementation assumptions. This needs immediate clarification.
    *   The `test_persistent_key_signing` suggests a multi-layered signing approach, which needs to be clearly defined and consistently implemented.

**Next Steps for Code Review:**

This file further emphasizes the cryptographic inconsistencies. I will continue reviewing the test files. I'll move to `tests/test_pspf_2025_compatibility.py` next.