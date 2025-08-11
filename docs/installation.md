# Installation Guide

This guide covers installing Flavor tools on your development machine.

## 🚀 Quick Install

### Option 1: Download Pre-built Binaries (Recommended)

Choose your platform and download the latest release:

#### Linux (x86_64)
```bash
curl -L https://github.com/your-org/flavor/releases/latest/download/flavor-linux-x86_64.tar.gz | tar xz
sudo mv flavor-* /usr/local/bin/
```

#### Linux (ARM64)
```bash
curl -L https://github.com/your-org/flavor/releases/latest/download/flavor-linux-aarch64.tar.gz | tar xz
sudo mv flavor-* /usr/local/bin/
```

#### macOS (Intel)
```bash
curl -L https://github.com/your-org/flavor/releases/latest/download/flavor-darwin-x86_64.tar.gz | tar xz
sudo mv flavor-* /usr/local/bin/
```

#### macOS (Apple Silicon)
```bash
curl -L https://github.com/your-org/flavor/releases/latest/download/flavor-darwin-aarch64.tar.gz | tar xz
sudo mv flavor-* /usr/local/bin/
```

#### Windows
1. Download: [flavor-windows-x86_64.zip](https://github.com/your-org/flavor/releases/latest/download/flavor-windows-x86_64.zip)
2. Extract to a directory in your PATH
3. Open Command Prompt or PowerShell

### Option 2: Package Managers

#### Homebrew (macOS/Linux)
```bash
# Coming soon!
brew install flavor
```

#### Chocolatey (Windows)
```bash
# Coming soon!
choco install flavor
```

#### APT (Debian/Ubuntu)
```bash
# Coming soon!
sudo apt install flavor
```

## 🔧 Verify Installation

After installation, verify Flavor tools are working:

```bash
# Check version and help
flavor-packager --version
flavor-packager --help

flavor-launcher --version
flavor-launcher --help
```

You should see output similar to:
```
Flavor Packager v0.1.0
Usage: flavor-packager <COMMAND>

Commands:
  keygen   Generate ECDSA P256 key pair for Flavor package signing
  build    Build a Flavor package from component parts  
  verify   Verify the integrity and signature of a Flavor file
  help     Print this message or the help of the given subcommand(s)
```

## 🏗️ Build from Source

### Prerequisites

**For Rust Implementation:**
- [Rust](https://rustup.rs/) 1.70+ with Cargo
- Git

**For Go Implementation:**
- [Go](https://golang.org/dl/) 1.21+
- Git

**For Python Development:**
- [Python](https://python.org) 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

### Clone and Build

```bash
# Clone the repository
git clone https://github.com/your-org/flavor.git
cd flavor

# Build Rust implementation (recommended)
cd src/flavor/rust/flavor-launcher
cargo build --release

cd ../flavor-packager  
cargo build --release

# Binaries are in target/release/
ls target/release/flavor-*

# Or build Go implementation
cd ../../go/flavor-launcher
go build -o flavor-go-launcher .

cd ../flavor-packager
go build -o flavor-go-packager .
```

### Install Development Environment

```bash
# Set up Python development environment
./env.sh

# Install in development mode
uv sync --all-extras --dev

# Run tests to verify
uv run pytest
```

## 🐳 Container Usage

### Official Docker Image

```bash
# Pull the official image
docker pull ghcr.io/your-org/flavor:latest

# Use for packaging
docker run --rm -v $(pwd):/workspace ghcr.io/your-org/flavor:latest \
  flavor-packager build --out /workspace/my-provider \
  --payload-dir /workspace/src \
  --package-key /workspace/keys/private.key \
  --public-key /workspace/keys/public.key
```

### Build Your Own Image

```dockerfile
FROM ghcr.io/your-org/flavor:latest as flavor

FROM alpine:latest
COPY --from=flavor /usr/local/bin/flavor-* /usr/local/bin/
WORKDIR /workspace
ENTRYPOINT ["flavor-packager"]
```

## 🔑 Initial Setup

After installation, generate your first signing key pair:

```bash
# Create a directory for your keys
mkdir -p ~/.flavor/keys

# Generate key pair
flavor-packager keygen --out-dir ~/.flavor/keys

# Your keys are now ready
ls ~/.flavor/keys/
# provider-private.key  provider-public.key
```

**⚠️ Security Note**: Keep your private key secure and never commit it to version control!

## ✅ Next Steps

Now that Flavor is installed:

1. **📚 Follow the [Quick Start Guide](./quickstart.md)** to package your first provider
2. **🔍 Explore [Examples](./examples/)** to see real-world usage
3. **🛠️ Check out [CLI Reference](./cli-reference.md)** for detailed command documentation
4. **🚀 Set up [CI/CD Integration](./cicd-integration.md)** to automate packaging

## 🆘 Troubleshooting

### Common Issues

#### "Command not found" after installation
- Ensure the binary location is in your PATH
- On macOS, you may need to allow the binary in Security & Privacy settings
- Try running with `./flavor-packager` if installed locally

#### Permission denied on Linux/macOS
```bash
chmod +x flavor-packager flavor-launcher
```

#### Windows Defender/Antivirus warnings
- Flavor binaries are safe but may trigger false positives
- Add exception for Flavor directory
- Download from official releases only

#### SSL certificate errors during download
```bash
# Use --insecure flag (not recommended for production)
curl -k -L https://github.com/...

# Or update certificates
sudo apt update && sudo apt install ca-certificates  # Ubuntu/Debian
brew install ca-certificates                         # macOS
```

### Getting Help

If you encounter issues:

1. **Check the [FAQ](./faq.md)** for common questions
2. **Review [Troubleshooting Guide](./troubleshooting.md)** for detailed solutions  
3. **Search [GitHub Issues](https://github.com/your-org/flavor/issues)** for known problems
4. **Open a new issue** with your system details and error messages

### System Requirements

**Minimum Requirements:**
- OS: Linux (glibc 2.17+), macOS 10.15+, Windows 10+
- Architecture: x86_64 or ARM64
- RAM: 512MB available
- Disk: 100MB for tools + package size

**Recommended:**
- RAM: 2GB+ for large provider packaging
- Disk: 1GB+ free space
- Fast SSD for better performance

---

**Installation complete?** 👉 [Quick Start Guide](./quickstart.md) | [CLI Reference](./cli-reference.md)