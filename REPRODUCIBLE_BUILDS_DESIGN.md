# Reproducible Builds Design for Flavor

## Current State

### What's Implemented
- Builders (Go and Rust) have a `--reproducible` flag
- When set, uses deterministic values:
  - Fixed seed: "reproducible-build-seed" for ephemeral keys
  - Fixed timestamp: "2025-01-01T00:00:00Z"
  - Fixed host: "{OS}/{ARCH} reproducible"

### The Problem
- `--reproducible` flag is a blunt instrument
- Doesn't allow using specific keys for signing
- Python CLI doesn't expose the flag
- Real reproducibility should come from controlling inputs, not a special mode

## Proposed Design

### CLI Interface
Instead of `--reproducible`, provide fine-grained control:

```bash
flavor package \
  --manifest pyproject.toml \
  --private-key path/to/signing.key \    # Use specific signing key
  --public-key path/to/verify.key \       # Use specific public key
  --timestamp "2025-01-01T00:00:00Z" \    # Fixed build timestamp
  --output package.pspf
```

### Key Handling Hierarchy
1. **Explicit keys provided**: Use `--private-key` and `--public-key`
2. **Keys in manifest directory**: Look for `keys/flavor-{private,public}.key`
3. **Generate ephemeral**: Create new keys for this build only (current default)

### Implementation Changes Needed

#### 1. Python CLI (`src/flavor/cli.py`)
Add options to package command:
- `--private-key`: Path to Ed25519 private key for signing
- `--public-key`: Path to corresponding public key
- `--timestamp`: Fixed build timestamp (ISO format)
- `--build-host`: Fixed build host identifier

#### 2. Python API (`src/flavor/api.py`)
Update `build_package_from_manifest()` to accept:
- `private_key_path: Optional[Path]`
- `public_key_path: Optional[Path]`
- `build_timestamp: Optional[str]`
- `build_host: Optional[str]`

#### 3. Orchestrator (`src/flavor/packaging/orchestrator.py`)
The manifest already includes signature paths:
```json
"signature": {
    "private_key": "/path/to/private.key",
    "public_key": "/path/to/public.key"
}
```
But builders ignore these fields currently.

#### 4. Builders (Go and Rust)
Update to accept and use key paths from manifest:
- If `signature.private_key` exists in manifest, read and use it
- If not provided, generate ephemeral keys (current behavior)
- Remove `--reproducible` flag (deprecated)

#### 5. Build Metadata
Add to metadata to track build reproducibility:
```json
"build_info": {
    "timestamp": "2025-01-01T00:00:00Z",
    "host": "linux/amd64",
    "key_type": "provided" | "ephemeral",
    "deterministic": true | false
}
```

## Benefits of This Approach

1. **True Reproducibility**: Using the same keys and timestamp produces identical output
2. **Flexibility**: Can use CI/CD keys, developer keys, or ephemeral keys
3. **Auditability**: Metadata shows whether build used provided or generated keys
4. **No Special Mode**: Reproducibility comes from controlling inputs, not a flag

## Migration Path

1. Keep `--reproducible` flag temporarily (deprecated warning)
2. When `--reproducible` is used, internally set:
   - Use deterministic ephemeral keys (current behavior)
   - Fixed timestamp and host
3. Eventually remove `--reproducible` in favor of explicit control

## Security Considerations

- Private keys should never be included in packages
- Public keys can be embedded for verification
- Consider supporting key URIs (e.g., `vault://keys/signing`) for secure key storage
- Warn if using well-known test keys in production builds

## Testing

Create test vectors with:
- Known private/public key pair
- Fixed timestamp
- Fixed host
- Expected output hash

This ensures reproducibility across:
- Different machines
- Different times
- Different OS/architectures (for same target)