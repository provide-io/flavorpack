# Migration Guide

This guide helps you migrate existing terraform providers to Flavor packaging. Whether you have a Python-based provider, Go provider, or other implementation, this guide covers the migration process.

## 🎯 Migration Overview

**What changes:**
- ✅ Distribution becomes a single, self-contained binary
- ✅ Cryptographic signing ensures integrity
- ✅ Cross-platform compatibility improves
- ✅ Installation becomes zero-dependency

**What stays the same:**
- ✅ Your provider logic and code
- ✅ Terraform compatibility and protocols
- ✅ User-facing terraform configuration
- ✅ Provider APIs and functionality

## 📋 Prerequisites

Before starting migration:
- [ ] Flavor tools installed ([Installation Guide](./installation.md))
- [ ] Your existing provider source code
- [ ] Understanding of your provider's dependencies
- [ ] Testing environment with terraform

## 🗺️ Migration Paths

Choose your migration path based on your current provider type:

### Path A: Python Providers (Pyvider-based)
**✅ Recommended - Direct Flavor support**
- Easiest migration path
- Built-in Flavor integration
- Full feature compatibility

### Path B: Go Providers  
**⚠️ Requires adapter - Future support**
- Needs Go-to-Python adapter layer
- Performance considerations
- Full functionality possible

### Path C: Other Languages
**⚠️ Complex migration**
- Requires rewrite or significant adaptation
- Consider benefits vs. effort
- May need custom integration

Let's walk through each path:

---

## 🐍 Path A: Python Provider Migration

### Step 1: Assess Current Provider

First, understand your current provider structure:

```bash
# Example provider structure
my-terraform-provider/
├── src/
│   ├── main.py              # Provider entry point
│   ├── resources/           # Resource implementations
│   ├── data_sources/        # Data source implementations  
│   └── functions/           # Provider functions
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project metadata
└── README.md
```

**Assessment checklist:**
- [ ] Python dependencies and versions
- [ ] External system dependencies (databases, APIs)
- [ ] File system access patterns
- [ ] Network connectivity requirements
- [ ] Performance characteristics

### Step 2: Prepare for Flavor

Update your provider structure for Flavor compatibility:

```bash
# Create Flavor-ready structure
mkdir -p my-provider-flavor/{payload,keys,dist}

# Copy source code
cp -r src/ my-provider-flavor/payload/

# Create Flavor metadata
cat > my-provider-flavor/payload/flavor-metadata.json << EOF
{
  "name": "my-terraform-provider",
  "version": "1.0.0",
  "description": "My awesome terraform provider",
  "provider_protocol_version": "6.0",
  "entry_point": "main.py"
}
EOF

# Update requirements if needed
cp requirements.txt my-provider-flavor/payload/
```

### Step 3: Test Locally

Before packaging, ensure your provider works in the new structure:

```bash
cd my-provider-flavor/payload

# Test provider functionality
python main.py --help

# Test with sample terraform config
# (create test configuration in separate directory)
```

### Step 4: Generate Signing Keys

```bash
# Generate production keys (do this once)
flavor-packager keygen --out-dir my-provider-flavor/keys

# For CI/CD, store private key securely
# - GitHub Secrets
# - AWS Secrets Manager  
# - Azure Key Vault
# - HashiCorp Vault
```

### Step 5: Build Flavor Package

```bash
cd my-provider-flavor

# Build the package
flavor-packager build \
  --out ./dist/terraform-provider-mycompany_v1.0.0 \
  --payload-dir ./payload \
  --package-key ./keys/provider-private.key \
  --public-key ./keys/provider-public.key \
  --launcher-bin $(which flavor-launcher)

# Verify the package
flavor-packager verify ./dist/terraform-provider-mycompany_v1.0.0

echo "✅ Flavor package built successfully!"
```

### Step 6: Integration Testing

Test your new Flavor package with terraform:

```bash
# Create test terraform configuration
mkdir -p terraform-test
cd terraform-test

# Set up provider
mkdir -p .terraform/providers/local/mycompany/1.0.0/linux_amd64
cp ../my-provider-flavor/dist/terraform-provider-mycompany_v1.0.0 \
   .terraform/providers/local/mycompany/1.0.0/linux_amd64/terraform-provider-mycompany

# Create test configuration
cat > main.tf << 'EOF'
terraform {
  required_providers {
    mycompany = {
      source = "local/mycompany"
      version = "1.0.0"
    }
  }
}

provider "mycompany" {
  # Your provider configuration
}

# Test your resources
resource "mycompany_example" "test" {
  name = "flavor-test"
}
EOF

# Test terraform operations
terraform init
terraform plan
terraform apply
terraform destroy
```

---

## 🐹 Path B: Go Provider Migration

> **Note:** Go provider support requires additional adapter layers. This is a future enhancement.

### Current Limitations
- Go providers need adaptation layer to work with Flavor
- Performance overhead from Go ↔ Python bridge
- Complex dependency management

### Recommended Approach
1. **Evaluate rewrite cost** vs. Flavor benefits
2. **Consider hybrid approach** - keep Go for compute-heavy parts
3. **Wait for native Go support** in future Flavor versions

### Migration Steps (Future)

When Go support is available:

```bash
# Future command structure
flavor-packager build-go \
  --out ./dist/terraform-provider-mycompany_v1.0.0 \
  --go-module ./my-go-provider \
  --package-key ./keys/provider-private.key \
  --public-key ./keys/provider-public.key \
  --launcher-bin ./flavor-go-launcher
```

---

## 🔄 Path C: Other Language Migration

For providers in other languages, consider:

### Option 1: Rewrite in Python
**Pros:**
- Full Flavor compatibility
- Better terraform provider ecosystem
- Easier maintenance

**Cons:**
- Significant development effort
- Need to relearn ecosystem
- Migration risk

### Option 2: Create Bridge
**Pros:**
- Keep existing logic
- Gradual migration possible

**Cons:**
- Complex architecture
- Performance overhead
- Maintenance burden

### Option 3: Wait for Native Support
**Pros:**
- No immediate work needed
- Better future integration

**Cons:**
- Delayed Flavor benefits
- Uncertain timeline

---

## 🚀 CI/CD Integration

After successful local migration, integrate Flavor packaging into your CI/CD pipeline:

### GitHub Actions Example

```yaml
name: Build Flavor Package

on:
  push:
    tags: ['v*']

jobs:
  build-flavor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Flavor tools
        run: |
          curl -L https://github.com/your-org/flavor/releases/latest/download/flavor-linux-x86_64.tar.gz | tar xz
          sudo mv flavor-* /usr/local/bin/
      
      - name: Build Flavor package
        env:
          SIGNING_KEY: ${{ secrets.PSPF_PRIVATE_KEY }}
        run: |
          echo "$SIGNING_KEY" > private.key
          
          flavor-packager build \
            --out "./dist/terraform-provider-mycompany_${GITHUB_REF#refs/tags/}" \
            --payload-dir ./src \
            --package-key ./private.key \
            --public-key ./keys/provider-public.key \
            --launcher-bin $(which flavor-launcher)
          
          rm private.key  # Clean up
      
      - name: Verify package
        run: |
          flavor-packager verify "./dist/terraform-provider-mycompany_${GITHUB_REF#refs/tags/}"
      
      - name: Upload release assets
        uses: softprops/action-gh-release@v1
        with:
          files: ./dist/*
```

### GitLab CI Example

```yaml
build-flavor:
  stage: build
  image: ubuntu:latest
  before_script:
    - apt-get update && apt-get install -y curl
    - curl -L https://github.com/your-org/flavor/releases/latest/download/flavor-linux-x86_64.tar.gz | tar xz
    - mv flavor-* /usr/local/bin/
  
  script:
    - echo "$PSPF_PRIVATE_KEY" > private.key
    - |
      flavor-packager build \
        --out "./dist/terraform-provider-mycompany_${CI_COMMIT_TAG}" \
        --payload-dir ./src \
        --package-key ./private.key \
        --public-key ./keys/provider-public.key \
        --launcher-bin $(which flavor-launcher)
    - flavor-packager verify "./dist/terraform-provider-mycompany_${CI_COMMIT_TAG}"
    - rm private.key
  
  artifacts:
    paths:
      - dist/
  
  only:
    - tags
```

---

## 📊 Migration Checklist

### Pre-Migration
- [ ] Current provider assessment complete
- [ ] Migration path selected
- [ ] Test environment prepared  
- [ ] Backup created of current provider

### During Migration
- [ ] Flavor tools installed and tested
- [ ] Signing keys generated and secured
- [ ] Provider payload prepared
- [ ] Package built successfully
- [ ] Package verification passes
- [ ] Integration tests pass

### Post-Migration
- [ ] CI/CD pipeline updated
- [ ] Documentation updated
- [ ] Team trained on new process
- [ ] Monitoring and alerting updated
- [ ] Rollback plan prepared

### Deployment
- [ ] Staged deployment tested
- [ ] Production deployment successful
- [ ] User communication sent
- [ ] Monitoring confirms stability

---

## 🎯 Best Practices

### Security
- **Never commit private keys** to version control
- **Use secure key storage** (secrets management)
- **Rotate keys periodically** for production
- **Verify packages** before deployment

### Testing
- **Test locally first** before CI/CD integration
- **Use staging environment** for integration testing
- **Maintain backward compatibility** during transition
- **Monitor performance** after migration

### Operations
- **Document the process** for your team
- **Prepare rollback procedures** in case of issues
- **Monitor package sizes** and performance
- **Plan regular updates** of Flavor tools

---

## 🆘 Troubleshooting

### Common Migration Issues

**"Package too large":**
- Review dependencies - remove unused packages
- Consider payload compression options
- See [Performance Tuning](./performance-tuning.md)

**"Provider not found by terraform":**
- Check provider naming convention
- Verify directory structure matches terraform expectations
- Ensure binary permissions are correct

**"Signature verification fails":**
- Confirm you're using matching key pairs
- Check that private key wasn't corrupted
- Verify package wasn't modified after signing

**"Performance degradation":**
- Compare startup times before/after
- Check for unnecessary dependencies
- Consider payload optimization

### Getting Help

1. **Check [FAQ](./faq.md)** for common questions
2. **Review [Troubleshooting Guide](./troubleshooting.md)** for detailed solutions
3. **Join [GitHub Discussions](https://github.com/your-org/flavor/discussions)** for community help
4. **Open [GitHub Issue](https://github.com/your-org/flavor/issues)** for bugs

---

## 🎉 Success Stories

> **"We migrated our 15-resource terraform provider to Flavor in 2 days. The security and deployment improvements were immediate."**  
> *— DevOps Team, TechCorp*

> **"Flavor eliminated our complex dependency management. Now we ship a single binary that just works."**  
> *— Platform Engineer, CloudCo*

---

**Ready to migrate?** 👉 [Quick Start](./quickstart.md) | [CLI Reference](./cli-reference.md) | [Examples](./examples/)