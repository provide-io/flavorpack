# Quick Start Guide

Get your first Flavor package built in under 10 minutes! This guide walks you through creating, verifying, and using a secure Flavor package.

## 🎯 What You'll Build

By the end of this guide, you'll have:
- ✅ Generated cryptographic signing keys
- ✅ Packaged a terraform provider into a single binary
- ✅ Verified the package signature
- ✅ Run the self-contained provider

## 📋 Prerequisites

- Flavor tools installed ([Installation Guide](./installation.md))
- A terraform provider to package (we'll create a sample one)

## 🚀 Step 1: Verify Installation

First, ensure Flavor tools are working:

```bash
flavor-packager --version
flavor-launcher --version
```

You should see version information for both tools.

## 🔑 Step 2: Generate Signing Keys

Every Flavor package must be cryptographically signed. Generate your key pair:

```bash
# Create keys directory
mkdir -p ./demo-keys

# Generate ECDSA P-256 key pair
flavor-packager keygen --out-dir ./demo-keys

# Verify keys were created
ls ./demo-keys/
# provider-private.key  provider-public.key
```

**🔒 Security Note**: The private key is used for signing packages. Keep it secure and never share it!

## 📦 Step 3: Create a Sample Provider

For this demo, let's create a simple terraform provider:

```bash
# Create provider directory structure
mkdir -p ./my-demo-provider/{src,tests}

# Create a simple Python-based provider
cat > ./my-demo-provider/src/main.py << 'EOF'
#!/usr/bin/env python3
"""
Demo Terraform Provider - Flavor Quickstart Example
"""
import sys
import json
from pathlib import Path

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
Demo Terraform Provider (Flavor Package)
=====================================

This is a sample terraform provider packaged with Flavor.

Usage:
  ./my-demo-provider                 - Run as terraform plugin
  ./my-demo-provider --help          - Show this help
  ./my-demo-provider --version       - Show version info

Features:
✅ Self-contained binary with embedded Python runtime  
✅ Cryptographically signed and verified
✅ Cross-platform compatible
✅ Zero external dependencies

Learn more about Flavor: https://github.com/your-org/flavor
        """)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        print("Demo Provider v1.0.0 (Flavor Package)")
        return

    # Simulate terraform provider protocol
    print("🚀 Demo Provider starting...")
    print("📦 Running from Flavor package")
    print("✅ Python runtime embedded and working")
    
    # Create a simple response
    response = {
        "format_version": "1.0",
        "provider_schemas": {
            "demo": {
                "resource_schemas": {
                    "demo_resource": {
                        "block": {
                            "attributes": {
                                "name": {
                                    "type": "string",
                                    "required": True,
                                    "description": "Name of the demo resource"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    print(f"📋 Provider schema: {json.dumps(response, indent=2)}")
    print("🎉 Demo provider executed successfully!")

if __name__ == "__main__":
    main()
EOF

# Create provider metadata
cat > ./my-demo-provider/src/metadata.json << 'EOF'
{
  "name": "demo-provider",
  "version": "1.0.0",
  "description": "Demo terraform provider for Flavor quickstart",
  "author": "Flavor Demo",
  "license": "MIT",
  "pspf_version": "0.1.0"
}
EOF

# Create requirements file (empty for this demo)
touch ./my-demo-provider/src/requirements.txt

# Make main.py executable
chmod +x ./my-demo-provider/src/main.py

echo "✅ Sample provider created!"
```

## 🏗️ Step 4: Build Your Flavor Package

Now package your provider into a secure, self-contained binary:

```bash
# Build the Flavor package
flavor-packager build \
  --out ./my-demo-provider-binary \
  --payload-dir ./my-demo-provider/src \
  --package-key ./demo-keys/provider-private.key \
  --public-key ./demo-keys/provider-public.key \
  --launcher-bin $(which flavor-launcher)

echo "🎉 Package built successfully!"
```

**What just happened?**
- Your provider source was compressed and embedded
- The package was cryptographically signed  
- A native launcher was attached
- Everything was combined into a single binary

Check the result:
```bash
# See the package file
ls -lh ./my-demo-provider-binary

# It's a single executable file (usually 20-60MB)
file ./my-demo-provider-binary
```

## ✅ Step 5: Verify Package Integrity

Always verify packages before use:

```bash
# Verify cryptographic signature and integrity
flavor-packager verify ./my-demo-provider-binary

# You should see:
# ✅ Footer read and checksum verified
# ✅ Public key parsed successfully  
# ✅ Package signature is valid
# ✅ Flavor file is valid and trusted
```

## 🚀 Step 6: Run Your Package

Your provider is now ready to use as a single, self-contained binary:

```bash
# Run the provider
./my-demo-provider-binary --help

# Check version
./my-demo-provider-binary --version

# Run the provider logic
./my-demo-provider-binary
```

You should see output showing your provider running with the embedded Python runtime!

## 🎯 Step 7: Test Integration

Let's test this as a terraform provider:

```bash
# Create a simple terraform configuration
mkdir -p ./terraform-test
cd ./terraform-test

# Copy provider to terraform plugins directory
mkdir -p ./.terraform/providers/local/demo/1.0.0/$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/arm64/aarch64/')
cp ../my-demo-provider-binary ./.terraform/providers/local/demo/1.0.0/$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/arm64/aarch64/')/terraform-provider-demo

# Create terraform config
cat > main.tf << 'EOF'
terraform {
  required_providers {
    demo = {
      source = "local/demo"
      version = "1.0.0"
    }
  }
}

provider "demo" {}

# This would create a demo resource if implemented
# resource "demo_resource" "example" {
#   name = "Flavor is awesome!"
# }

output "message" {
  value = "✅ Flavor provider integration successful!"
}
EOF

# Test terraform can find the provider
terraform init
```

## 🎉 Success!

Congratulations! You've successfully:

✅ **Created a signing key pair**  
✅ **Built your first Flavor package**  
✅ **Verified package integrity**  
✅ **Run a self-contained binary**  
✅ **Integrated with terraform**

## 🚀 What's Next?

Now that you understand the basics:

### **For Real Projects**
- **[Migration Guide](./migration-guide.md)** - Package an existing terraform provider
- **[Security Guide](./security-guide.md)** - Production security best practices
- **[CI/CD Integration](./cicd-integration.md)** - Automate packaging in your pipeline

### **Advanced Features**
- **[CLI Reference](./cli-reference.md)** - Complete command documentation
- **[API Reference](./api-reference.md)** - Use Flavor programmatically
- **[Performance Tuning](./performance-tuning.md)** - Optimize your packages

### **Examples & Community**
- **[Examples Repository](./examples/)** - Real-world examples
- **[GitHub Discussions](https://github.com/your-org/flavor/discussions)** - Ask questions
- **[Contributing](./CONTRIBUTING.md)** - Help improve Flavor

## 🐛 Troubleshooting

### Common Issues

**"Permission denied" when running package:**
```bash
chmod +x ./my-demo-provider-binary
```

**"Package verification failed":**
- Ensure you're using the same key pair for build and verify
- Check that files weren't corrupted during transfer

**"Launcher not found":**
```bash
# Verify flavor-launcher is in PATH
which flavor-launcher

# Or use absolute path
flavor-packager build --launcher-bin /full/path/to/flavor-launcher ...
```

**Package seems too large:**
- This is normal! Packages include the Python runtime (~20-40MB)
- See [Performance Tuning](./performance-tuning.md) for optimization tips

### Getting Help

- **[FAQ](./faq.md)** - Common questions answered
- **[Troubleshooting Guide](./troubleshooting.md)** - Detailed problem solving
- **[GitHub Issues](https://github.com/your-org/flavor/issues)** - Report bugs or get help

---

**Ready for more?** 👉 [Migration Guide](./migration-guide.md) | [Examples](./examples/) | [CLI Reference](./cli-reference.md)