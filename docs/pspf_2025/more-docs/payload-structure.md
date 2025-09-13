### 1. Payload Structure According to Specifications

The provided specification documents are inconsistent. `fep-0001.md` describes a "Magic Trailer" design, while `binary-layout.md` describes a simpler "Header" design. Both are presented below.

#### A. The "Magic Trailer" Model (from `fep-0001.md`)

This is the more robust and detailed specification. The Index Block is located at a fixed position relative to the end of the file, making it easy to find regardless of the launcher's size.

```ascii
/----------------------------------------------------------------------\
|                      PSPF Package (fep-0001.md)                      |
|======================================================================|
|          Native Launcher Binary          | // Offset: 0              |
|               (Variable Size)            | // Size: L                |
|------------------------------------------|---------------------------|
|              Metadata Block              | // Offset: L              |
|             (gzipped JSON)               | // Padded to 8-byte boundary
|               (Variable Size)            |                           |
|------------------------------------------|---------------------------|
|                 Slot Table               | // Offset: M              |
|               (Variable Size)            |                           |
|------------------------------------------|---------------------------|
|                  Slot Data               | // Offset: S              |
|               (Variable Size)            |                           |
|------------------------------------------|---------------------------|
|                                          |                           |
|                ... (Padding) ...         |                           |
|                                          |                           |
|------------------------------------------|---------------------------|
|              Magic Trailer               | // At EOF - 8200 bytes    |
|              (Fixed: 8200 bytes)         |                           |
|   ┌──────────────────────────────────┐   |                           |
|   │ Package Emoji '📦' (4 bytes)    │   |                           |
|   ├──────────────────────────────────┤   |                           |
|   │      Index Block (8192 bytes)    │   |                           |
|   ├──────────────────────────────────┤   |                           |
|   │ Magic Wand Emoji '🪄' (4 bytes)  │   |                           |
|   └──────────────────────────────────┘   |                           |
\----------------------------------------------------------------------/
```

#### B. The "Header" Model (from `binary-layout.md`)

This conflicting specification places the Index Block directly after the launcher, which is simpler but can be problematic if the launcher size isn't easily determined.

```ascii
/----------------------------------------------------------------------\
|                   PSPF Package (binary-layout.md)                    |
|======================================================================|
|          Native Launcher Binary          | // Offset: 0              |
|               (Variable Size)            |                           |
|------------------------------------------|---------------------------|
|                Index Block               | // Offset: N (Launcher Size)
|              (Fixed: 8192 bytes)         |                           |
|------------------------------------------|---------------------------|
|                  Metadata                | // Offset defined in Index|
|             (gzipped JSON)               |                           |
|               (Variable Size)            |                           |
|------------------------------------------|---------------------------|
|                 Slot Table               | // Offset defined in Index|
|               (Variable Size)            |                           |
|------------------------------------------|---------------------------|
|                  Slot Data               | // Offset defined in Index|
|               (Variable Size)            |                           |
|------------------------------------------|---------------------------|
|                Magic Footer              | // At EOF - 8 bytes       |
|            ('📦🪄', 8 bytes)            |                           |
\----------------------------------------------------------------------/
```

---

### 2. Payload Structure as Implemented in `flavor`

The `flavor` source code resolves the ambiguity in the specifications by **implementing the "Magic Trailer" model from `fep-0001.md`**. The logic in `PSPFReader` and `PSPFBuilder` confirms this choice.

The diagram below details the structure as it is actually built and read by the code.

```ascii
/----------------------------------------------------------------------\
|                Implemented PSPF Package (`flavor` code)              |
|======================================================================|
|         Go or Rust Launcher Binary       | // Written first by PSPFBuilder
|              (Variable Size)             |                           |
|------------------------------------------|---------------------------|
|           gzipped JSON Metadata          | // Written after launcher |
|              (Variable Size)             |                           |
|------------------------------------------|---------------------------|
|                 Slot Table               | // Written after metadata |
|   ┌──────────────────────────────────┐   |                           |
|   │ SlotDescriptor 0 (64 bytes)      │   | // Implements the 64-byte |
|   ├──────────────────────────────────┤   | // descriptor from fep-0001
|   │ SlotDescriptor 1 (64 bytes)      │   |                           |
|   ├──────────────────────────────────┤   |                           |
|   │ ...                              │   |                           |
|   └──────────────────────────────────┘   |                           |
|------------------------------------------|---------------------------|
|       Aligned Slot Data Blocks         | // Slot data is written     |
|              (Variable Size)             | // here, potentially with |
|                                          | // page alignment padding |
|------------------------------------------|---------------------------|
|                                          |                           |
|                ... (Padding) ...         |                           |
|                                          |                           |
|------------------------------------------|---------------------------|
|              Magic Trailer               | // At EOF - 8200 bytes    |
|              (Fixed: 8200 bytes)         | // Read by PSPFReader     |
|   ┌──────────────────────────────────┐   |                           |
|   │ Package Emoji '📦' (4 bytes)    │   |                           |
|   ├──────────────────────────────────┤   |                           |
|   │      Index Block (8192 bytes)    │   | // Matches PSPFIndex class|
|   ├──────────────────────────────────┤   |                           |
|   │ Magic Wand Emoji '🪄' (4 bytes)  │   |                           |
|   └──────────────────────────────────┘   |                           |
\----------------------------------------------------------------------/

