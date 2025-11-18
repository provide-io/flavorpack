# Using Packages

Learn how to run, inspect, and manage FlavorPack packages.

## Quick Start

Running a package is simple:

```bash
# Make executable (if needed)
chmod +x myapp.psp

# Run it!
./myapp.psp
```

No installation, no dependencies, no configuration required!

## Topics

### :material-play: **Running Packages**

Execute packaged applications.

**[Running Packages →](running/)**

- Basic execution
- Command-line arguments
- Environment variables
- Exit codes

### :material-console: **CLI Reference**

Complete command-line interface documentation.

**[CLI Reference →](cli/)**

- `flavor pack` - Create packages
- `flavor verify` - Verify integrity
- `flavor inspect` - View contents
- `flavor extract` - Extract files

### :material-magnify: **Inspecting Packages**

View package contents and metadata.

**[Inspecting Packages →](inspection/)**

- View metadata
- List slots
- Check signatures
- Analyze dependencies

### :material-cached: **Cache Management**

Manage work environment cache.

**[Cache Management →](cache/)**

- Cache location
- Cache cleanup
- Cache validation
- Troubleshooting

### :material-variable: **Environment Variables**

Configure runtime behavior.

**[Environment Variables →](environment/)**

- `FLAVOR_LOG_LEVEL` - Logging verbosity
- `FLAVOR_WORKENV` - Cache location
- `FLAVOR_VALIDATION` - Validation level
- Custom variables

## Common Tasks

### Running with Custom Environment

```bash
# Set log level
FLAVOR_LOG_LEVEL=debug ./myapp.psp

# Custom cache location
FLAVOR_WORKENV=/tmp/cache ./myapp.psp

# Multiple variables
PORT=8000 LOG_LEVEL=info ./myapp.psp
```

### Inspecting Package Contents

```bash
# View metadata
flavor inspect myapp.psp

# Verify signature
flavor verify myapp.psp

# Extract to directory
flavor extract myapp.psp --output extracted/
```

### Managing Cache

```bash
# View cache location
flavor cache info

# Clean cache
flavor cache clean

# Verify cache integrity
flavor cache verify
```

## Next Steps

- **[Running Packages](running/)** - Execution guide
- **[CLI Reference](cli/)** - Complete CLI docs
- **[Troubleshooting](../../troubleshooting/index/)** - Fix issues
