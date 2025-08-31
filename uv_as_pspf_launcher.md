# `uv` as a `pspf` Compliant Launcher

> **Status: PROPOSAL - Not Implemented**  
> This document describes a proposed enhancement that has not been implemented.
> Last Updated: August 31, 2025

This document outlines a proposal for `uv` to become a native launcher for the Progressive Secure Package Format (PSPF). This would be achieved by embedding latent launcher capabilities within the standard `uv` binary, which can be activated by a `pspf` builder.

The core of this proposal is a "feature flag byte" within the `uv` executable. This allows a single, standard `uv` binary to be dynamically configured as a launcher by a third-party tool, without requiring a separate build of `uv`.

## How It Works: The "Feature Flag Byte"

1.  **Latent Launcher Code:** The standard `uv` binary will contain all the necessary code to function as a `pspf` launcher, including the `flavor-rs` library. However, this code will remain dormant by default.

2.  **The Feature Flag Byte:** A specific byte at a known, fixed offset within the `uv` executable will act as a switch.
    *   **Default State (e.g., `0x00`):** In a standard `uv` binary, this byte will have a default value.
    *   **Activated State (e.g., `0x01`):** A `pspf` builder will "activate" the launcher mode by overwriting this single byte.

3.  **Startup and Mode Detection:** When the `uv` binary is executed, its `main` function will perform a self-check:
    *   It will read the feature flag byte from its own binary.
    *   **If the byte is in the "Activated State"**, it will immediately switch to "Launcher Mode," handing off control to the `flavor-rs` launcher logic.
    *   **If the byte is in the "Default State"**, it will proceed with its normal command-line operations.

This approach is powerful because it decouples the `uv` build process from the `pspf` packaging process. `uv` can be developed and released as usual, and any `pspf`-compliant builder can independently turn it into a launcher.

## Implementation Checklist

This plan simplifies the required changes to the `uv` project, placing more responsibility on the `pspf` builder.

### Phase 1: `uv` Project Modifications

-   [ ] **Add `flavor-rs` Dependency:**
    -   [ ] Add the `flavor-rs` crate as a *non-optional* library dependency in `uv`'s `Cargo.toml`.

-   [ ] **Implement the "Feature Flag Byte":**
    -   [ ] In the `uv` source code, define a `const` or `static` byte variable at a fixed, well-documented location. This will be the feature flag.
    -   [ ] A common technique for this is to use an assembly file or a linker script to place the variable at a predictable offset in the final binary.

-   [ ] **Update `uv`'s `main` Function:**
    -   [ ] At the very beginning of `main`, implement the self-check logic to read the feature flag byte from its own binary.
    -   [ ] Based on the value of the byte, either hand off execution to the `flavor-rs` launcher logic or proceed with the normal `uv` CLI logic.

-   [ ] **No Build Process Changes:**
    -   [ ] The standard `cargo build --release` for `uv` will produce a binary with the latent launcher capability. No special build flags are needed.

### Phase 2: `pspf` Builder Modifications (`flavorpack` or other)

-   [ ] **Implement the "Activation" Step:**
    -   [ ] The `pspf` builder (e.g., the `flavor` CLI) will be updated with a new function to "activate" a `uv` binary.
    -   [ ] This function will:
        1.  Take a standard `uv` binary as input.
        2.  Create a copy of it.
        3.  Open the copy in binary write mode.
        4.  Seek to the known offset of the feature flag byte.
        5.  Overwrite the byte with the "activated" value.
        6.  This new, activated `uv` binary is now ready to be used as a launcher.

-   [ ] **Update the Packaging Logic:**
    -   [ ] The builder will use the newly activated `uv` binary as the base for the `pspf` package.
    -   [ ] It will append the `pspf` archive data and the magic number, as before.
    -   [ ] The builder must be configured to *not* include `uv` as a separate slot in the package payload.

### Phase 3: Testing and Validation

-   [ ] **Test the Activation Process:**
    -   [ ] Add tests to the `pspf` builder to ensure that it can correctly and reliably "activate" a `uv` binary.
    -   [ ] Verify that a standard `uv` binary is not affected and continues to function as expected.

-   [ ] **Comprehensive Integration Tests:**
    -   [ ] Create a full end-to-end test that:
        1.  Takes a standard `uv` release binary.
        2.  Uses the `pspf` builder to activate it and create a package.
        3.  Runs the package and verifies that it launches correctly.
        4.  Verifies that the packaged application can successfully use the launcher's internal `uv` functionality.

-   [ ] **Robustness and Stability:**
    -   [ ] Investigate methods to ensure the offset of the feature flag byte remains stable across `uv` versions. This might involve using linker scripts or other advanced toolchain features.
    -   [ ] Document the offset and the activation process clearly for other `pspf`-compliant tool developers.
