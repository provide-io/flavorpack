# Advanced Topics

Deep dive into FlavorPack's advanced features and customization options.

## Overview

These topics are for users who want to:
- Customize launchers and builders
- Optimize performance
- Debug complex issues
- Extend FlavorPack functionality

## Topics

### :material-language-go: **Cross-Language Support**

Understand Go and Rust helper integration.

**[Cross-Language Support →](cross-language/)**

- Go builder and launcher
- Rust builder and launcher
- Cross-compatibility testing
- Format specification

### :material-rocket-launch: **Custom Launchers**

Build custom launchers for specific use cases.

**[Custom Launchers →](launchers/)**

- Launcher architecture
- Building custom launchers
- Platform-specific features
- Integration with builders

### :material-hammer-wrench: **Custom Builders**

Extend the build system.

**[Custom Builders →](builders/)**

- Builder architecture
- Plugin system
- Custom slot handlers
- Build hooks

### :material-speedometer: **Performance Tuning**

Optimize package size and execution speed.

**[Performance Tuning →](performance/)**

- Reduce package size
- Optimize extraction
- Improve startup time
- Caching strategies

### :material-bug: **Debugging**

Troubleshoot complex issues.

**[Debugging →](debugging/)**

- Enable debug logging
- Trace execution
- Diagnose build failures
- Debug runtime issues

## When to Use Advanced Features

### Custom Launchers
- Need platform-specific behavior
- Require specialized extraction logic
- Want custom security checks
- Building domain-specific tools

### Custom Builders
- Package non-Python applications
- Need custom compression
- Require specialized slot types
- Extending format capabilities

### Performance Tuning
- Packages are too large
- Startup time is slow
- Cache misses are frequent
- Running in constrained environments

### Debugging
- Build failures
- Runtime errors
- Integration issues
- Performance problems

## Prerequisites

Before diving into advanced topics, you should:

1. ✅ Understand [Core Concepts](../concepts/index/)
2. ✅ Be comfortable with [Building Packages](../packaging/index/)
3. ✅ Have experience [Using Packages](../usage/index/)
4. ✅ Know Go or Rust (for helper development)

## Next Steps

Choose your path:

- **Customization** → [Custom Launchers](launchers/)
- **Optimization** → [Performance Tuning](performance/)
- **Problems** → [Debugging](debugging/)
- **Integration** → [Cross-Language Support](cross-language/)

---

**Need help?** Join the discussion on [GitHub](https://github.com/provide-io/flavorpack/discussions) or check [Troubleshooting](../../troubleshooting/index/).
