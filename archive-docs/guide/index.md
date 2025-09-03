# User Guide

Welcome to the FlavorPack User Guide. This comprehensive guide covers everything from basic concepts to advanced usage patterns.

## What You'll Learn

- **Core Concepts** - Understand the PSPF format and how FlavorPack works
- **Package Creation** - Build and configure packages for your applications  
- **Package Management** - Work with packages, verify integrity, and manage caches
- **Advanced Topics** - Performance optimization, cross-language support, and debugging

## Guide Organization

### 📚 [Core Concepts](concepts/)

Start here to understand the fundamentals:
- [PSPF Format](concepts/pspf-format.md) - The Progressive Secure Package Format explained
- Package Structure - How packages are organized internally
- Security Model - Cryptographic signing and verification
- Work Environments - Smart caching and extraction

### 📦 [Creating Packages](packaging/)

Learn how to package your applications:
- Python Applications - Package Python projects with dependencies
- Configuration - Manifest files and build options
- Signing & Verification - Secure your packages
- Platform Support - Build for different operating systems

### 🚀 [Using Packages](usage/)

Work with packaged applications:
- Running Packages - Execute and manage packaged apps
- CLI Reference - Command-line interface documentation
- Inspection Tools - Examine package contents
- Cache Management - Control the work environment cache

### 🔧 [Advanced Topics](advanced/)

Deep dive into advanced features:
- Cross-Language Support - Using Go and Rust components
- Custom Launchers - Build your own launchers
- Performance Optimization - Make packages smaller and faster
- Debugging - Troubleshoot package issues

## Quick Reference

### Essential Commands

```bash
# Create a package
flavor pack --manifest pyproject.toml --output app.psp

# Run a package
./app.psp

# Verify package integrity
flavor verify app.psp

# Inspect package contents
flavor inspect app.psp

# Extract package
flavor extract app.psp --output extracted/
```

### Configuration Example

```toml
[tool.flavor]
package_name = "my-app"
entry_point = "app:main"

[tool.flavor.build]
include_patterns = ["*.py", "assets/*"]
exclude_patterns = ["tests/*", "__pycache__"]
compression = "gzip"

[tool.flavor.runtime]
python_version = "3.11"
optimization_level = 2
```

## Best Practices

### ✅ DO

- **Sign production packages** - Always use cryptographic signatures
- **Test on target platforms** - Verify compatibility before deployment
- **Optimize package size** - Exclude unnecessary files and use compression
- **Document dependencies** - List all requirements in your manifest
- **Use version tags** - Include versions in package filenames

### ❌ DON'T

- **Include secrets** - Never package API keys or passwords
- **Skip verification** - Always verify packages from untrusted sources
- **Mix environments** - Keep development and production packages separate
- **Ignore errors** - Address warnings during package creation
- **Forget permissions** - Ensure packages have execute permissions

## Getting Help

If you need assistance:

1. Check the [Troubleshooting Guide](../troubleshooting/common.md)
2. Search [GitHub Issues](https://github.com/provide-io/flavorpack/issues)
3. Join the [Community Discussion](https://github.com/provide-io/flavorpack/discussions)
4. Read the [API Reference](../api/)

## Next Steps

Ready to dive in? Start with:

1. **New to FlavorPack?** → [Core Concepts](concepts/pspf-format.md)
2. **Ready to package?** → [Creating Packages](packaging/)
3. **Need examples?** → [Cookbook](../cookbook/)
4. **Having issues?** → [Troubleshooting](../troubleshooting/)