# Flavor Examples

Real-world examples and templates for packaging Terraform providers with Flavor.

## 📚 Quick Reference

| Example | Description | Complexity |
|---------|-------------|------------|
| [**Simple Provider**](./simple-provider/) | Basic terraform provider with minimal dependencies | 🟢 Beginner |
| [**AWS Resources Provider**](./aws-resources/) | Provider with AWS SDK and multiple resources | 🟡 Intermediate |
| [**Database Provider**](./database-provider/) | Provider with database connectivity | 🟡 Intermediate |
| [**Multi-Platform Build**](./multi-platform/) | CI/CD setup for cross-platform packages | 🔴 Advanced |
| [**Enterprise Security**](./enterprise-security/) | HSM signing and enterprise security features | 🔴 Advanced |

## 🚀 Getting Started Examples

### Hello World Provider

The simplest possible Flavor package - perfect for learning the basics.

```bash
cd examples/simple-provider
./build.sh
./terraform-provider-hello --help
```

**What you'll learn:**
- Basic Flavor packaging workflow
- Key generation and management
- Package verification
- Integration with Terraform

**Files included:**
- `src/main.py` - Minimal provider implementation
- `build.sh` - Build script with all commands
- `terraform-test/` - Sample Terraform configuration
- `README.md` - Step-by-step walkthrough

---

### Production-Ready Provider

A more realistic example with proper error handling, logging, and resource lifecycle management.

```bash
cd examples/aws-resources
./setup.sh      # Install dependencies
./build.sh      # Build Flavor package
./test.sh       # Run integration tests
```

**What you'll learn:**
- Real-world provider architecture
- Dependency management
- Resource CRUD operations
- Error handling and diagnostics
- Performance optimization

**Files included:**
- `src/provider/` - Full provider implementation
- `src/resources/` - Multiple resource types
- `requirements.txt` - Production dependencies
- `tests/` - Unit and integration tests
- `terraform-examples/` - Real Terraform configurations

---

### Database Provider Example

Shows how to handle external dependencies and connection management.

```bash
cd examples/database-provider
docker-compose up -d    # Start test database
./build.sh             # Build provider
./test-integration.sh  # Test with real database
```

**What you'll learn:**
- Database connection handling
- Secrets management
- Resource state management
- Connection pooling
- Transaction handling

**Features demonstrated:**
- PostgreSQL resource management
- Secure credential handling
- Connection lifecycle
- Error recovery patterns

---

## 🏗️ CI/CD Examples

### GitHub Actions Pipeline

Complete CI/CD setup for automated Flavor packaging.

```bash
cd examples/multi-platform
cat .github/workflows/build-flavor.yml
```

**Pipeline features:**
- Multi-platform builds (Linux, macOS, Windows)
- Automated testing
- Security scanning
- Package signing with secrets
- Release automation

**What you'll learn:**
- CI/CD best practices for Flavor
- Secret management in GitHub Actions
- Cross-platform build matrices
- Automated testing strategies

---

### Enterprise Security Example

Advanced example showing enterprise-grade security features.

```bash
cd examples/enterprise-security
```

**Security features:**
- Hardware Security Module (HSM) integration
- Role-based access controls
- Audit logging
- Compliance reporting
- Multi-signature workflows

**What you'll learn:**
- Enterprise security patterns
- HSM integration
- Compliance considerations
- Audit trail implementation

---

## 📁 Example Structure

Each example follows this structure:

```
example-name/
├── README.md              # Detailed walkthrough
├── src/                   # Provider source code
│   ├── main.py           # Provider entry point
│   ├── resources/        # Resource implementations
│   └── requirements.txt  # Python dependencies
├── keys/                 # Signing keys (generated)
├── dist/                 # Built packages (generated)
├── terraform-test/       # Terraform configurations
│   ├── main.tf          # Test configuration
│   └── variables.tf     # Variable definitions
├── build.sh             # Build script
├── test.sh              # Test script
└── docker-compose.yml   # Dependencies (if needed)
```

## 🧪 Testing Examples

Each example includes comprehensive testing:

### Unit Tests
```bash
# Run Python unit tests
cd src && python -m pytest tests/

# Run Go tests (where applicable)
go test ./...
```

### Integration Tests
```bash
# Build and test full workflow
./build.sh && ./test.sh

# Test with real Terraform
cd terraform-test && terraform init && terraform plan
```

### Performance Tests
```bash
# Benchmark build time
time ./build.sh

# Benchmark startup time
time ./dist/terraform-provider-example --help

# Package size analysis
du -h ./dist/terraform-provider-example
```

## 📖 Learning Path

**For beginners:**
1. Start with [Simple Provider](./simple-provider/) to understand basics
2. Try [Hello World Provider](./hello-world/) for hands-on practice
3. Read through build scripts to understand the process

**For intermediate users:**
1. Explore [AWS Resources Provider](./aws-resources/) for real-world patterns
2. Study [Database Provider](./database-provider/) for stateful resources
3. Implement your own provider using these as templates

**For advanced users:**
1. Set up [Multi-Platform Build](./multi-platform/) for your projects
2. Implement [Enterprise Security](./enterprise-security/) features
3. Contribute improvements back to examples

## 🛠️ Development Tools

### Quick Development Setup

```bash
# Clone and set up development environment
git clone https://github.com/your-org/flavor.git
cd flavor/docs/examples

# Install Flavor tools
../scripts/install-dev-tools.sh

# Set up example environment
export PSPF_EXAMPLES_DIR=$(pwd)
export PATH="$PATH:$PSPF_EXAMPLES_DIR/bin"
```

### Helper Scripts

```bash
# Build all examples
./scripts/build-all-examples.sh

# Test all examples
./scripts/test-all-examples.sh

# Clean build artifacts
./scripts/clean-all.sh

# Generate new example template
./scripts/new-example.sh my-new-example
```

## 🤝 Contributing Examples

We welcome new examples! See [Contributing Guide](../CONTRIBUTING.md).

**Good examples to contribute:**
- Providers for specific cloud platforms
- Complex data transformation patterns
- Advanced security implementations
- Performance optimization techniques
- Integration with other tools

**Example contribution process:**
1. Create example following the standard structure
2. Include comprehensive README and documentation
3. Add automated tests and CI integration
4. Submit pull request with example description

## 📞 Getting Help

**Questions about examples:**
- **[GitHub Discussions](https://github.com/your-org/flavor/discussions)** - Ask questions about examples
- **[Issues](https://github.com/your-org/flavor/issues)** - Report problems with examples
- **[Discord/Slack]** - Real-time community help

**Improving examples:**
- **Fork and improve** existing examples
- **Submit pull requests** for fixes and enhancements
- **Suggest new examples** via GitHub issues

---

**Ready to try examples?** 👉 [Simple Provider](./simple-provider/) | [AWS Resources](./aws-resources/) | [Build Your Own](./templates/)