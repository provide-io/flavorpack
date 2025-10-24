# Running Packages

Execute FlavorPack packages (.psp files).

## Coming Soon

This page is under development. In the meantime, see:

- **[Quick Start](../../getting-started/quickstart.md)** - Basic execution
- **[CLI Tools Example](../../cookbook/examples/cli-tool.md)** - Real examples

## Topics to be Covered

- Basic execution
- Command-line arguments
- Environment variables
- Exit codes and error handling
- Signal handling
- Process management
- Debugging execution issues

## Quick Reference

```bash
# Make executable
chmod +x myapp.psp

# Run it
./myapp.psp

# With arguments
./myapp.psp --arg value

# With environment variables
ENV_VAR=value ./myapp.psp

# Debug mode
FLAVOR_LOG_LEVEL=debug ./myapp.psp
```

---

**Need help?** Check [Environment Variables](environment.md) or [Troubleshooting](../../troubleshooting/).
