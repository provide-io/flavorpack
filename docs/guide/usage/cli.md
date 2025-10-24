# CLI Reference

Complete command-line interface documentation for FlavorPack.

## Coming Soon

This page is under development with complete CLI documentation.

## Quick Reference

### Main Commands

```bash
# Package an application
flavor pack --manifest pyproject.toml --output myapp.psp

# Verify package integrity
flavor verify myapp.psp

# Inspect package contents
flavor inspect myapp.psp

# Extract package
flavor extract myapp.psp --output extracted/

# Generate signing keys
flavor keygen --output keys/
```

### Common Options

- `--manifest PATH` - Path to manifest file
- `--output PATH` - Output file path
- `--log-level LEVEL` - Set logging level (debug, info, warn, error)
- `--help` - Show help message

---

**For full documentation, run:** `flavor --help` or `flavor COMMAND --help`

**See also:** [Inspection](inspection.md) | [Cache Management](cache.md)
