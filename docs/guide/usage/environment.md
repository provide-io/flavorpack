# Environment Variables

Configure FlavorPack's runtime behavior with environment variables.

## Coming Soon

Complete documentation of all environment variables.

## Key Environment Variables

### FlavorPack Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLAVOR_LOG_LEVEL` | Logging verbosity (debug, info, warn, error) | `info` |
| `FLAVOR_WORKENV` | Work environment cache location | Platform-specific |
| `FLAVOR_VALIDATION` | Validation level (strict, standard, none) | `standard` |

### Build Time

```bash
# Debug build process
FLAVOR_LOG_LEVEL=debug flavor pack

# Custom workenv location
FLAVOR_WORKENV=/tmp/cache flavor pack
```

### Runtime

```bash
# Debug package execution
FLAVOR_LOG_LEVEL=debug ./myapp.psp

# Disable validation (not recommended)
FLAVOR_VALIDATION=none ./myapp.psp
```

## Topics to be Covered

- Complete variable reference
- Build vs runtime variables
- Variable precedence
- Platform-specific variables
- Application-specific variables

---

**See also:** [Running Packages](running.md) | [Cache Management](cache.md)
