# AWS Resources Provider Example

A production-ready terraform provider demonstrating Flavor packaging with AWS SDK integration and comprehensive resource management.

## 🎯 What This Example Shows

- ✅ Real-world provider architecture with AWS SDK
- ✅ Multiple resource types and data sources
- ✅ Proper error handling and validation
- ✅ State management and lifecycle operations
- ✅ Configuration management and authentication
- ✅ Unit and integration testing
- ✅ CI/CD pipeline integration

**Perfect for:** Teams building production terraform providers

## 📁 Project Structure

```
aws-resources/
├── README.md              # This file
├── src/                   # Provider source code
│   ├── main.py           # Provider entry point
│   ├── provider.py       # Core provider implementation
│   ├── config.py         # Configuration and authentication
│   ├── resources/        # Resource implementations
│   │   ├── __init__.py
│   │   ├── s3_bucket.py  # S3 bucket resource
│   │   └── ec2_instance.py # EC2 instance resource
│   ├── data_sources/     # Data source implementations
│   │   ├── __init__.py
│   │   └── ami.py        # AMI data source
│   ├── utils/            # Utility modules
│   │   ├── __init__.py
│   │   ├── aws_client.py # AWS client wrapper
│   │   └── validation.py # Input validation
│   └── requirements.txt  # Production dependencies
├── tests/                # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── conftest.py       # Pytest configuration
├── keys/                 # Generated signing keys
├── dist/                 # Built Flavor packages
├── terraform-examples/   # Example Terraform configurations
│   ├── basic/            # Basic usage example
│   ├── advanced/         # Advanced features
│   └── integration/      # Integration testing
├── build.sh             # Build script
├── test.sh              # Test script
├── setup.sh             # Environment setup
└── docker-compose.yml   # LocalStack for testing
```

## 🚀 Quick Start

### Step 1: Set up the Environment

```bash
# Clone or navigate to this example
cd aws-resources

# Set up dependencies and test environment
./setup.sh
```

### Step 2: Build the Provider

```bash
# Build the Flavor package
./build.sh
```

### Step 3: Run Tests

```bash
# Run comprehensive test suite
./test.sh
```

### Step 4: Try with Terraform

```bash
# Use the basic example
cd terraform-examples/basic
terraform init
terraform plan
```

## 🏗️ Architecture Overview

### Provider Design

This example demonstrates production-ready provider patterns:

**Authentication**: Multiple authentication methods
- AWS credentials file
- Environment variables  
- IAM roles (when running on EC2)
- Temporary credentials

**Error Handling**: Comprehensive error management
- AWS API error translation
- Resource state validation
- Retry logic with exponential backoff
- Graceful degradation

**Resource Lifecycle**: Full CRUD operations
- Create with validation
- Read with drift detection
- Update with change planning
- Delete with dependency checking

### Supported Resources

#### `awsdemo_s3_bucket`
Complete S3 bucket management with:
- Bucket creation and deletion
- Versioning configuration
- Public access blocking
- Server-side encryption
- Lifecycle policies

#### `awsdemo_ec2_instance`
EC2 instance lifecycle management:
- Instance launch and termination
- Security group assignment
- Key pair management
- User data scripts
- State monitoring

### Data Sources

#### `awsdemo_ami`
AMI lookup with filtering:
- Name-based searches
- Owner filtering
- Architecture filtering
- Most recent selection

## 📋 Implementation Details

### AWS Client Management

```python
# src/utils/aws_client.py
class AWSClientManager:
    """Manages AWS SDK clients with proper authentication and error handling."""
    
    def __init__(self, config):
        self.config = config
        self._clients = {}
    
    def get_client(self, service_name: str):
        """Get or create AWS service client."""
        if service_name not in self._clients:
            self._clients[service_name] = self._create_client(service_name)
        return self._clients[service_name]
    
    def _create_client(self, service_name: str):
        session = boto3.Session(
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region
        )
        return session.client(service_name)
```

### Resource Implementation Example

```python
# src/resources/s3_bucket.py
class S3BucketResource:
    """AWS S3 bucket resource implementation."""
    
    def create(self, name: str, region: str, **kwargs) -> dict:
        """Create S3 bucket with specified configuration."""
        s3_client = self.aws_client.get_client('s3')
        
        # Create bucket
        if region != 'us-east-1':
            s3_client.create_bucket(
                Bucket=name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        else:
            s3_client.create_bucket(Bucket=name)
        
        # Configure versioning if requested
        if kwargs.get('versioning_enabled', False):
            s3_client.put_bucket_versioning(
                Bucket=name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
        
        return self.read(name)
    
    def read(self, name: str) -> dict:
        """Read S3 bucket configuration and state."""
        s3_client = self.aws_client.get_client('s3')
        
        try:
            # Get bucket location
            location = s3_client.get_bucket_location(Bucket=name)
            region = location.get('LocationConstraint') or 'us-east-1'
            
            # Get versioning status
            versioning = s3_client.get_bucket_versioning(Bucket=name)
            versioning_enabled = versioning.get('Status') == 'Enabled'
            
            return {
                'name': name,
                'region': region,
                'versioning_enabled': versioning_enabled,
                'arn': f'arn:aws:s3:::{name}'
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                return None
            raise
```

### Configuration and Validation

```python
# src/config.py
@dataclass
class ProviderConfig:
    """Provider configuration with validation."""
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    region: str = "us-west-2"
    profile: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.region:
            raise ValueError("AWS region is required")
        
        # Load credentials from various sources
        if not self.access_key and not self.profile:
            # Try to load from environment or credentials file
            session = boto3.Session(profile_name=self.profile)
            credentials = session.get_credentials()
            
            if credentials:
                self.access_key = credentials.access_key
                self.secret_key = credentials.secret_key
```

## 🧪 Testing Strategy

### Unit Tests
- Resource creation/deletion logic
- Configuration validation
- Error handling scenarios
- State management

### Integration Tests
- Real AWS API interactions (using LocalStack)
- End-to-end resource lifecycle
- Authentication methods
- Performance benchmarks

### Test Environment
```bash
# Start LocalStack for integration testing
docker-compose up -d

# Run tests against LocalStack
AWS_ENDPOINT_URL=http://localhost:4566 ./test.sh
```

## 🔧 Configuration Examples

### Basic Configuration

```hcl
terraform {
  required_providers {
    awsdemo = {
      source = "local/awsdemo" 
      version = "1.0.0"
    }
  }
}

provider "awsdemo" {
  region = "us-west-2"
  # Credentials loaded from ~/.aws/credentials or environment
}

resource "awsdemo_s3_bucket" "example" {
  name               = "my-terraform-flavor-demo"
  region             = "us-west-2"
  versioning_enabled = true
}
```

### Advanced Configuration

```hcl
provider "awsdemo" {
  region     = var.aws_region
  profile    = var.aws_profile
  access_key = var.aws_access_key  # Not recommended - use IAM roles
  secret_key = var.aws_secret_key  # Not recommended - use IAM roles
}

resource "awsdemo_ec2_instance" "web_server" {
  ami           = data.awsdemo_ami.ubuntu.id
  instance_type = "t3.micro"
  key_name      = "my-key-pair"
  
  user_data = base64encode(<<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y nginx
    systemctl start nginx
    systemctl enable nginx
  EOF
  )
  
  tags = {
    Name = "Flavor Demo Instance"
    Environment = "demo"
  }
}

data "awsdemo_ami" "ubuntu" {
  name_regex  = "ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"
  owners      = ["099720109477"] # Canonical
  most_recent = true
}
```

## 🔒 Security Considerations

### Credential Management
- Never hardcode AWS credentials
- Use IAM roles when possible
- Support multiple authentication methods
- Implement credential rotation

### Resource Security
- Validate all input parameters
- Implement least privilege access
- Audit resource creation/modification
- Support encryption at rest and in transit

### Package Security
- Flavor cryptographic signatures
- Dependency vulnerability scanning
- Secure build pipeline
- Supply chain security

## ⚡ Performance Optimization

### AWS API Efficiency
- Connection pooling and reuse
- Batch operations where possible
- Intelligent retry with backoff
- Caching of read operations

### Package Optimization
- Minimal dependency set
- Compressed payload
- Fast startup time
- Efficient memory usage

## 🚀 Deployment and Usage

### Local Development
```bash
# Build and test locally
./build.sh && ./test.sh

# Use in terraform projects
terraform init
terraform plan
```

### CI/CD Pipeline
```yaml
# Example GitHub Actions workflow
name: AWS Provider Flavor Build
on: [push, pull_request]

jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Flavor
        run: |
          curl -L https://github.com/your-org/flavor/releases/latest/download/flavor-linux-x86_64.tar.gz | tar xz
          sudo mv flavor-* /usr/local/bin/
      
      - name: Build provider
        run: ./build.sh
        
      - name: Run tests  
        run: ./test.sh
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Production Deployment
- Store packages in secure artifact registry
- Implement automated testing pipeline
- Monitor provider performance and errors
- Plan for credential rotation and updates

## 🆘 Troubleshooting

### Common Issues

**AWS Authentication Errors**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check provider configuration
terraform-provider-awsdemo --test
```

**Resource State Drift**
```bash
# Force refresh state
terraform refresh

# Compare current vs. desired state
terraform plan -detailed-exitcode
```

**Performance Issues**
```bash
# Enable debug logging
TF_LOG=DEBUG terraform plan

# Profile provider startup
time ./dist/terraform-provider-awsdemo --version
```

## 📚 Next Steps

After mastering this example:

1. **[Database Provider Example](../database-provider/)** - Stateful resource management
2. **[Multi-Platform CI/CD](../multi-platform/)** - Advanced deployment
3. **[Enterprise Security](../enterprise-security/)** - HSM and compliance features

---

**Questions?** 👉 [GitHub Discussions](https://github.com/your-org/flavor/discussions) | [Examples Overview](../README.md)