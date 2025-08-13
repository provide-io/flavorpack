# Flavor Documentation

Welcome to the Flavor documentation! This directory contains comprehensive documentation for the Flavor packaging system and the Progressive Secure Package Format (PSPF/2025).

## 📚 Core Documentation

### For Users

- **[Quickstart Guide](quickstart.md)** - Get started with Flavor in 5 minutes
- **[Installation](installation.md)** - Detailed installation instructions
- **[CLI Reference](cli-reference.md)** - Complete command-line interface documentation
- **[FAQ](faq.md)** - Frequently asked questions
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

### For Developers

- **[Specification](SPECIFICATION_PSPF_2025.md)** - Complete PSPF/2025 format specification
- **[Architecture](ARCHITECTURE.md)** - System design and architectural decisions
- **[Development](DEVELOPMENT.md)** - Contributing guide and development setup
- **[Security](SECURITY.md)** - Security model and cryptographic design

### Integration & Migration

- **[Integration Guide](INTEGRATION.md)** - Integrating Flavor with other tools
- **[Migration Guide](migration-guide.md)** - Migrating from other packaging systems

## 📁 Examples

The [examples/](examples/) directory contains working examples:

- **[simple-provider](examples/simple-provider/)** - Basic Terraform provider example
- **[aws-resources](examples/aws-resources/)** - Provider with AWS resources
- **[database-provider](examples/database-provider/)** - Database connectivity example
- **[multi-platform](examples/multi-platform/)** - CI/CD automation example

## 🔍 Quick Links

### Getting Started
1. [Install Flavor](installation.md)
2. [Follow the Quickstart](quickstart.md)
3. [Try an Example](examples/simple-provider/)

### Understanding Flavor
- [What is PSPF?](SPECIFICATION.md#overview)
- [Why use Flavor?](index.md)
- [How does it work?](ARCHITECTURE.md#overview)

### Common Tasks
- [Generate signing keys](cli-reference.md#keygen)
- [Build a package](cli-reference.md#package)
- [Verify a package](cli-reference.md#verify)

## 📖 Documentation Structure

```
docs/
├── README.md              # This file
├── index.md              # Documentation home
├── quickstart.md         # Quick start guide
├── installation.md       # Installation instructions
├── cli-reference.md      # CLI documentation
├── faq.md               # Frequently asked questions
├── troubleshooting.md   # Troubleshooting guide
├── migration-guide.md   # Migration from other tools
├── SPECIFICATION_PSPF_2025.md  # PSPF/2025 specification
├── ARCHITECTURE.md      # Architecture documentation
├── DEVELOPMENT.md       # Development guide
├── SECURITY.md         # Security documentation
├── INTEGRATION.md      # Integration guide
├── examples/           # Working examples
│   ├── simple-provider/
│   ├── aws-resources/
│   ├── database-provider/
│   └── multi-platform/
└── internal/           # Internal documentation (not for end users)
```

## 🤝 Contributing

We welcome contributions to the documentation! Please:

1. Follow the existing documentation style
2. Include practical examples where appropriate
3. Keep explanations clear and concise
4. Update the index when adding new documents

See [DEVELOPMENT.md](DEVELOPMENT.md) for more details.

## 📞 Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/provide-io/flavor/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/provide-io/flavor/discussions)
- **Email**: engineering@provide.services

---

*Flavor - Modern packaging for modern applications*