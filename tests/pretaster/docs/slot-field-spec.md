# Slot Field Specification Update

## Overview

The `slot` field has been added to PSPF/2025 manifest slot definitions as an optional well-formedness check to ensure manifest integrity and prevent slot ordering errors.

## Field Definition

```json
{
  "slots": [
    {
      "slot": 0,  // Optional: Expected position in slots array
      "name": "example.sh",
      "path": "scripts/example.sh",
      "purpose": "payload",
      "lifecycle": "cached",
      "encoding": "none",
      "extract_to": "{workenv}/scripts"
    }
  ]
}
```

## Field Properties

- **Type**: Integer (`int` in Go, `i32` in Rust)
- **Required**: No (optional field)
- **Default**: Unset/null
- **Purpose**: Validate slot ordering in manifest

## Validation Rules

1. **Optional Field**: If not provided, no validation is performed
2. **Zero-Based Indexing**: Slot numbers start at 0
3. **Critical Error on Mismatch**: If `slot` field is present and doesn't match the actual array position, the builder MUST exit with a non-zero status
4. **Error Message Format**: `❌ Critical: Slot number mismatch - expected {position}, declared {slot} for slot '{name}'`

## Implementation

### Go Builder (flavor-go)
```go
type Slot struct {
    Slot      *int   `json:"slot,omitempty"`  // Pointer to distinguish unset from 0
    // ... other fields
}

// Validation
if slot.Slot != nil && *slot.Slot != i {
    logger.Error("❌ Critical: Slot number mismatch", "expected", i, "declared", *slot.Slot, "name", slot.Name)
    os.Exit(1)
}
```

### Rust Builder (flavor-rs)
```rust
struct ManifestSlot {
    #[serde(skip_serializing_if = "Option::is_none")]
    slot: Option<i32>,  // Option to distinguish unset from 0
    // ... other fields
}

// Validation
if let Some(declared_slot) = slot.slot {
    if declared_slot as usize != i {
        error!("❌ Critical: Slot number mismatch - expected {}, declared {} for slot '{}'", i, declared_slot, slot.name);
        std::process::exit(1);
    }
}
```

## Rationale

### Why Add the Slot Field?

1. **Well-Formedness Check**: Provides an explicit declaration of expected slot position, catching manifest errors early in the build process

2. **Prevents Silent Reordering**: Without this field, slots could be accidentally reordered in the manifest without detection, potentially breaking assumptions about slot positions

3. **Documentation**: Makes slot ordering explicit and self-documenting in the manifest

4. **Debugging Aid**: When troubleshooting multi-slot packages, explicit slot numbers make it easier to track which slot is which

5. **Safety for Critical Slots**: Some packages may have dependencies between slots (e.g., slot 0 bootstraps other slots). The slot field ensures these relationships are preserved

### Why Make It Optional?

1. **Backward Compatibility**: Existing manifests without the field continue to work
2. **Simplicity for Basic Cases**: Single-slot packages don't need the extra validation
3. **Progressive Enhancement**: Teams can adopt the field gradually as needed

### Why Make Mismatches Critical Errors?

1. **Fail Fast**: Catches configuration errors at build time rather than runtime
2. **Prevents Subtle Bugs**: Slot ordering errors can cause hard-to-debug runtime failures
3. **Clear Intent**: A declared slot number represents explicit intent that should be honored
4. **Security**: Prevents potential attacks where slot ordering could be manipulated

## Examples

### Valid Manifest
```json
{
  "slots": [
    { "slot": 0, "name": "bootstrap.sh", ... },
    { "slot": 1, "name": "utilities.tar.gz", ... },
    { "slot": 2, "name": "binary.gz", ... }
  ]
}
```

### Invalid Manifest (Will Fail)
```json
{
  "slots": [
    { "slot": 1, "name": "bootstrap.sh", ... },  // Error: Expected 0, declared 1
    { "slot": 0, "name": "utilities.tar.gz", ... }  // Error: Expected 1, declared 0
  ]
}
```

### Mixed Usage (Valid)
```json
{
  "slots": [
    { "slot": 0, "name": "critical.sh", ... },  // Validated
    { "name": "optional.txt", ... },            // No validation
    { "slot": 2, "name": "important.bin", ... } // Validated
  ]
}
```

## Testing

All four builder/launcher combinations have been tested and validated:
- ✅ Go Builder + Go Launcher
- ✅ Go Builder + Rust Launcher  
- ✅ Rust Builder + Go Launcher
- ✅ Rust Builder + Rust Launcher

Test cases include:
1. Correct slot numbering (passes)
2. Missing slot field (passes - optional)
3. Incorrect slot numbering (fails with critical error)
4. Mixed presence/absence of slot field (passes where correct)