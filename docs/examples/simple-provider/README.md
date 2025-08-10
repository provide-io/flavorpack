# Simple Provider Example

A minimal terraform provider packaged with Flavor to demonstrate the basic workflow.

## 🎯 What This Example Shows

- ✅ Basic provider structure and entry point
- ✅ Flavor packaging workflow from start to finish  
- ✅ Key generation and package signing
- ✅ Package verification and execution
- ✅ Terraform integration testing

**Perfect for:** First-time Flavor users learning the fundamentals

## 📁 Project Structure

```
simple-provider/
├── README.md              # This file
├── src/                   # Provider source code
│   ├── main.py           # Provider entry point
│   ├── provider.py       # Provider implementation
│   ├── resources.py      # Resource definitions
│   └── requirements.txt  # Dependencies (minimal)
├── keys/                 # Generated signing keys
├── dist/                 # Built Flavor packages
├── terraform-test/       # Terraform test configuration
│   ├── main.tf          # Test terraform config
│   └── terraform.tf     # Provider requirements
├── build.sh             # Build script
├── test.sh              # Test script
└── clean.sh             # Cleanup script
```

## 🚀 Quick Start

### Step 1: Build the Provider

```bash
# Clone the Flavor repository (if you haven't already)
git clone https://github.com/your-org/flavor.git
cd flavor/docs/examples/simple-provider

# Run the build script
./build.sh
```

The build script will:
1. Generate signing keys
2. Build the Flavor package
3. Verify the package
4. Test basic functionality

### Step 2: Test the Provider

```bash
# Run integration tests
./test.sh

# Or test manually
cd terraform-test
terraform init
terraform plan
```

### Step 3: Clean Up (Optional)

```bash
# Remove generated files
./clean.sh
```

## 📋 Step-by-Step Walkthrough

### Understanding the Provider Code

**`src/main.py`** - Entry point that terraform calls:
```python
#!/usr/bin/env python3
"""
Simple Terraform Provider - Flavor Example
"""
import sys
import json
import logging
from provider import SimpleProvider

def main():
    """Main entry point for the terraform provider."""
    logging.basicConfig(level=logging.INFO)
    
    # Create provider instance
    provider = SimpleProvider()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            provider.show_help()
            return
        elif sys.argv[1] == '--version':
            provider.show_version()
            return
    
    # Run as terraform provider (Protocol 6)
    provider.serve()

if __name__ == "__main__":
    main()
```

**`src/provider.py`** - Core provider implementation:
```python
"""Simple provider implementation."""
import json
from typing import Dict, Any

class SimpleProvider:
    """A minimal terraform provider for demonstration."""
    
    def __init__(self):
        self.name = "simple"
        self.version = "1.0.0"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return provider schema."""
        return {
            "format_version": "1.0",
            "provider_schemas": {
                self.name: {
                    "provider": {
                        "version": 0,
                        "block": {
                            "attributes": {
                                "endpoint": {
                                    "type": "string",
                                    "description": "API endpoint URL",
                                    "optional": True
                                }
                            }
                        }
                    },
                    "resource_schemas": {
                        "simple_file": {
                            "version": 0,
                            "block": {
                                "attributes": {
                                    "filename": {
                                        "type": "string",
                                        "required": True,
                                        "description": "Name of the file to create"
                                    },
                                    "content": {
                                        "type": "string",
                                        "required": True,
                                        "description": "Content to write to the file"
                                    },
                                    "id": {
                                        "type": "string",
                                        "computed": True,
                                        "description": "Unique identifier for the file"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def serve(self):
        """Serve the provider using terraform protocol."""
        # In a real implementation, this would start the gRPC server
        # For this demo, just output the schema
        schema = self.get_schema()
        print(json.dumps(schema, indent=2))
    
    def show_help(self):
        """Show provider help information."""
        print(f"""
Simple Terraform Provider v{self.version}
=========================================

A minimal terraform provider packaged with Flavor.

Usage:
  terraform-provider-simple              # Run as terraform provider
  terraform-provider-simple --help       # Show this help
  terraform-provider-simple --version    # Show version

Resources:
  simple_file    # Creates a simple file with specified content

This provider demonstrates:
✅ Flavor packaging with embedded Python runtime
✅ Self-contained binary with zero dependencies
✅ Cryptographic signing and verification
✅ Cross-platform compatibility

Example terraform configuration:

  terraform {{
    required_providers {{
      simple = {{
        source = "local/simple"
        version = "1.0.0"
      }}
    }}
  }}
  
  provider "simple" {{
    endpoint = "https://api.example.com"
  }}
  
  resource "simple_file" "example" {{
    filename = "hello.txt"
    content  = "Hello from Flavor!"
  }}

Learn more about Flavor: https://github.com/your-org/flavor
        """)
    
    def show_version(self):
        """Show provider version."""
        print(f"Simple Provider v{self.version} (Flavor Package)")
```

### Understanding the Build Process

**`build.sh`** - Complete build workflow:
```bash
#!/bin/bash
set -euo pipefail

echo "🏗️ Building Simple Provider Flavor Package"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROVIDER_NAME="simple"
VERSION="1.0.0"
DIST_DIR="./dist"
KEYS_DIR="./keys"
SRC_DIR="./src"

# Step 1: Setup directories
echo -e "${BLUE}📁 Setting up directories...${NC}"
mkdir -p "$DIST_DIR" "$KEYS_DIR"

# Step 2: Generate keys if they don't exist
if [[ ! -f "$KEYS_DIR/provider-private.key" ]]; then
    echo -e "${BLUE}🔑 Generating signing keys...${NC}"
    flavor-packager keygen --out-dir "$KEYS_DIR"
    echo -e "${GREEN}✅ Keys generated${NC}"
else
    echo -e "${GREEN}✅ Using existing keys${NC}"
fi

# Step 3: Build the Flavor package
echo -e "${BLUE}📦 Building Flavor package...${NC}"
flavor-packager build \
    --out "$DIST_DIR/terraform-provider-${PROVIDER_NAME}_v${VERSION}" \
    --payload-dir "$SRC_DIR" \
    --package-key "$KEYS_DIR/provider-private.key" \
    --public-key "$KEYS_DIR/provider-public.key" \
    --launcher-bin "$(which flavor-launcher)"

echo -e "${GREEN}✅ Package built successfully${NC}"

# Step 4: Verify the package
echo -e "${BLUE}🔍 Verifying package...${NC}"
flavor-packager verify "$DIST_DIR/terraform-provider-${PROVIDER_NAME}_v${VERSION}"
echo -e "${GREEN}✅ Package verified${NC}"

# Step 5: Show package info
echo -e "${BLUE}📊 Package information:${NC}"
flavor-packager info "$DIST_DIR/terraform-provider-${PROVIDER_NAME}_v${VERSION}"

# Step 6: Test basic functionality
echo -e "${BLUE}🧪 Testing basic functionality...${NC}"
PROVIDER_PATH="$DIST_DIR/terraform-provider-${PROVIDER_NAME}_v${VERSION}"

# Make executable
chmod +x "$PROVIDER_PATH"

# Test help
echo -e "${BLUE}  Testing --help...${NC}"
"$PROVIDER_PATH" --help | head -5

# Test version
echo -e "${BLUE}  Testing --version...${NC}"
"$PROVIDER_PATH" --version

echo -e "${GREEN}🎉 Build completed successfully!${NC}"
echo ""
echo "📦 Package location: $PROVIDER_PATH"
echo "💾 Package size: $(du -h "$PROVIDER_PATH" | cut -f1)"
echo ""
echo "Next steps:"
echo "  ./test.sh                  # Run integration tests"
echo "  cd terraform-test && terraform init  # Test with terraform"
```

### Understanding the Terraform Integration

**`terraform-test/main.tf`** - Test configuration:
```hcl
# Test configuration for simple provider
terraform {
  required_providers {
    simple = {
      source  = "local/simple"
      version = "1.0.0"
    }
  }
}

provider "simple" {
  endpoint = "https://api.example.com"
}

# Example resource (commented out since we don't implement full CRUD)
# resource "simple_file" "example" {
#   filename = "hello.txt"
#   content  = "Hello from Flavor!"
# }

# Output to verify provider is working
output "provider_info" {
  value = "Simple provider loaded successfully via Flavor!"
}
```

### Understanding the Test Process

**`test.sh`** - Integration testing:
```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Testing Simple Provider Flavor Package"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROVIDER_NAME="simple"
VERSION="1.0.0"
PROVIDER_PATH="./dist/terraform-provider-${PROVIDER_NAME}_v${VERSION}"
TEST_DIR="./terraform-test"

# Check if package exists
if [[ ! -f "$PROVIDER_PATH" ]]; then
    echo -e "${RED}❌ Package not found. Run ./build.sh first.${NC}"
    exit 1
fi

# Step 1: Test provider directly
echo -e "${BLUE}🔧 Testing provider binary...${NC}"

echo -e "${BLUE}  Testing help command...${NC}"
"$PROVIDER_PATH" --help > /dev/null
echo -e "${GREEN}  ✅ Help command works${NC}"

echo -e "${BLUE}  Testing version command...${NC}"
VERSION_OUTPUT=$("$PROVIDER_PATH" --version)
echo -e "${GREEN}  ✅ Version: $VERSION_OUTPUT${NC}"

echo -e "${BLUE}  Testing schema output...${NC}"
"$PROVIDER_PATH" | jq '.format_version' > /dev/null
echo -e "${GREEN}  ✅ Valid JSON schema output${NC}"

# Step 2: Set up terraform test environment
echo -e "${BLUE}🏗️ Setting up terraform test environment...${NC}"
cd "$TEST_DIR"

# Create terraform plugins directory
PLUGINS_DIR=".terraform/providers/local/${PROVIDER_NAME}/${VERSION}"
PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/arm64/aarch64/')"
PLUGIN_PATH="$PLUGINS_DIR/$PLATFORM"

mkdir -p "$PLUGIN_PATH"
cp "../$PROVIDER_PATH" "$PLUGIN_PATH/terraform-provider-${PROVIDER_NAME}"
chmod +x "$PLUGIN_PATH/terraform-provider-${PROVIDER_NAME}"

echo -e "${GREEN}  ✅ Provider installed to terraform plugins directory${NC}"

# Step 3: Test terraform init
echo -e "${BLUE}🚀 Testing terraform init...${NC}"
if terraform init; then
    echo -e "${GREEN}  ✅ Terraform init successful${NC}"
else
    echo -e "${RED}  ❌ Terraform init failed${NC}"
    exit 1
fi

# Step 4: Test terraform plan
echo -e "${BLUE}📋 Testing terraform plan...${NC}"
if terraform plan; then
    echo -e "${GREEN}  ✅ Terraform plan successful${NC}"
else
    echo -e "${RED}  ❌ Terraform plan failed${NC}"
    exit 1
fi

# Step 5: Test terraform providers command
echo -e "${BLUE}🔍 Testing terraform providers...${NC}"
terraform providers
echo -e "${GREEN}  ✅ Provider listed successfully${NC}"

# Cleanup and return
cd ..
echo -e "${GREEN}🎉 All tests passed!${NC}"
echo ""
echo "✅ Provider binary works correctly"
echo "✅ Flavor package structure is valid"
echo "✅ Terraform integration successful"
echo "✅ Provider schema is valid JSON"
echo ""
echo "Your simple provider Flavor package is ready for use!"
```

## 🎓 Learning Objectives

By completing this example, you will understand:

1. **Flavor Packaging Workflow**
   - Key generation with `flavor-packager keygen`
   - Package building with `flavor-packager build`
   - Package verification with `flavor-packager verify`

2. **Provider Development**
   - Minimal provider structure
   - Schema definition
   - Command-line interface

3. **Terraform Integration**
   - Plugin directory structure
   - Provider registration
   - Configuration requirements

4. **Security Features**
   - Cryptographic signing
   - Package verification
   - Secure key management

## 🔧 Customization Ideas

**Extend this example by:**

1. **Add Real Resources**
   - Implement actual CRUD operations
   - Add state management
   - Handle terraform lifecycle

2. **Add Error Handling**
   - Comprehensive error messages
   - Validation logic
   - Graceful failure modes

3. **Add Configuration**
   - Provider-level configuration
   - Environment variable support
   - Configuration validation

4. **Add Testing**
   - Unit tests for resources
   - Integration test automation
   - Performance benchmarks

## 🆘 Troubleshooting

### Common Issues

**"flavor-packager: command not found"**
- Install Flavor tools first: [Installation Guide](../../installation.md)
- Check PATH includes Flavor binary directory

**"Permission denied" when running package**
```bash
chmod +x ./dist/terraform-provider-simple_v1.0.0
```

**"Package verification failed"**
- Ensure you're using the same key pair for build and verify
- Check if package was corrupted during transfer

**Terraform can't find provider**
- Check provider naming: `terraform-provider-simple`
- Verify directory structure in `.terraform/providers/`
- Ensure binary has execute permissions

### Getting Help

- **[Flavor FAQ](../../faq.md)** - Common questions
- **[Troubleshooting Guide](../../troubleshooting.md)** - Detailed solutions
- **[GitHub Issues](https://github.com/your-org/flavor/issues)** - Report problems

## 🚀 Next Steps

After mastering this simple example:

1. **[AWS Resources Example](../aws-resources/)** - Real-world provider with multiple resources
2. **[Database Provider Example](../database-provider/)** - Stateful resource management
3. **[Multi-Platform Build Example](../multi-platform/)** - CI/CD integration
4. **[Migration Guide](../../migration-guide.md)** - Package your existing provider

---

**Questions?** 👉 [GitHub Discussions](https://github.com/your-org/flavor/discussions) | [Examples Overview](../README.md)