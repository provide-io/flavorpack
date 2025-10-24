# Inspecting Packages

View package contents, metadata, and verify integrity.

## Coming Soon

This page is under development. In the meantime, see:

- **[CLI Reference](cli.md)** - Inspection commands

## Quick Reference

```bash
# View all package information
flavor inspect myapp.psp

# Verify signature
flavor verify myapp.psp

# Extract to directory
flavor extract myapp.psp --output extracted/

# List slots
flavor inspect myapp.psp --slots

# View metadata only
flavor inspect myapp.psp --metadata
```

## Topics to be Covered

- Package metadata
- Slot information
- Signature verification
- Dependency listing
- Size analysis
- Extraction testing

---

**Need help?** See [CLI Reference](cli.md) or [Troubleshooting](../../troubleshooting/).
