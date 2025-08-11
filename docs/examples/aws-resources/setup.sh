#!/bin/bash
set -euo pipefail

echo "🏗️ Setting up AWS Resources Provider Example"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ensure we're in the right directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}📍 Working directory: $(pwd)${NC}"

# Step 1: Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    echo "Please install Python 3.8+ to continue"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
echo -e "${GREEN}✅ Python ${PYTHON_VERSION} found${NC}"

# Check if we need to install PSPF tools
if ! command -v flavor-packager &> /dev/null; then
    echo -e "${YELLOW}⚠️ PSPF tools not found in PATH${NC}"
    echo "Please install PSPF tools first:"
    echo "  https://github.com/your-org/flavor/docs/installation.md"
    echo ""
    echo "Or build from source in the PSPF repository"
    echo ""
    read -p "Continue without PSPF tools? (build.sh will fail) [y/N]: " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ PSPF tools found${NC}"
fi

# Check Docker for integration testing
if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo -e "${GREEN}✅ Docker available for integration testing${NC}"
    HAS_DOCKER=true
else
    echo -e "${YELLOW}⚠️ Docker not available - integration tests will be limited${NC}"
    HAS_DOCKER=false
fi

# Step 2: Set up Python virtual environment
echo -e "${BLUE}🐍 Setting up Python environment...${NC}"

# Check if venv already exists
if [[ -d "venv" ]]; then
    echo -e "${BLUE}  Using existing virtual environment${NC}"
    source venv/bin/activate
else
    echo -e "${BLUE}  Creating new virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Upgrade pip
pip install --upgrade pip setuptools wheel

echo -e "${GREEN}✅ Python environment ready${NC}"

# Step 3: Install Python dependencies
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"

if [[ -f "src/requirements.txt" ]]; then
    pip install -r src/requirements.txt
    echo -e "${GREEN}✅ Production dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️ src/requirements.txt not found${NC}"
fi

# Install development dependencies
echo -e "${BLUE}  Installing development dependencies...${NC}"
pip install \
    pytest>=7.0.0 \
    pytest-asyncio>=0.21.0 \
    pytest-cov>=4.0.0 \
    pytest-mock>=3.10.0 \
    black>=22.0.0 \
    flake8>=5.0.0 \
    mypy>=1.0.0 \
    moto[all]>=4.0.0 \
    localstack-client>=1.0.0

echo -e "${GREEN}✅ Development dependencies installed${NC}"

# Step 4: Create directory structure
echo -e "${BLUE}📁 Creating directory structure...${NC}"

mkdir -p {keys,dist,logs,terraform-examples/basic,terraform-examples/advanced,tests/unit,tests/integration}

echo -e "${GREEN}✅ Directory structure created${NC}"

# Step 5: Set up testing infrastructure
if [[ "$HAS_DOCKER" == "true" ]]; then
    echo -e "${BLUE}🐳 Setting up testing infrastructure...${NC}"
    
    # Check if docker-compose.yml exists, create if not
    if [[ ! -f "docker-compose.yml" ]]; then
        cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  localstack:
    image: localstack/localstack:latest
    container_name: flavor-aws-localstack
    ports:
      - "4566:4566"
      - "4510-4559:4510-4559"
    environment:
      - DEBUG=1
      - SERVICES=s3,ec2,sts,iam
      - DATA_DIR=/tmp/localstack/data
      - DOCKER_HOST=unix:///var/run/docker.sock
      - HOST_TMP_FOLDER=/tmp/localstack
    volumes:
      - "/tmp/localstack:/tmp/localstack"
      - "/var/run/docker.sock:/var/run/docker.sock"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
EOF
        echo -e "${GREEN}  ✅ Created docker-compose.yml for LocalStack${NC}"
    fi
    
    # Start LocalStack for testing
    echo -e "${BLUE}  Starting LocalStack container...${NC}"
    if docker-compose up -d localstack; then
        echo -e "${GREEN}  ✅ LocalStack started${NC}"
        
        # Wait for LocalStack to be ready
        echo -e "${BLUE}  Waiting for LocalStack to be ready...${NC}"
        for i in {1..30}; do
            if curl -s http://localhost:4566/health > /dev/null; then
                echo -e "${GREEN}  ✅ LocalStack is ready${NC}"
                break
            fi
            echo -e "${BLUE}    Waiting... (${i}/30)${NC}"
            sleep 2
        done
        
        if ! curl -s http://localhost:4566/health > /dev/null; then
            echo -e "${YELLOW}  ⚠️ LocalStack may not be fully ready${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠️ Failed to start LocalStack - integration tests may not work${NC}"
    fi
fi

# Step 6: Validate source code structure
echo -e "${BLUE}🔍 Validating source code structure...${NC}"

REQUIRED_FILES=(
    "src/main.py"
    "src/config.py"
    "src/requirements.txt"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}  ✅ Found $file${NC}"
        # Test Python syntax
        if [[ "$file" == *.py ]]; then
            python3 -m py_compile "$file"
        fi
    else
        echo -e "${RED}  ❌ Missing $file${NC}"
        echo "Run this setup from the aws-resources example directory"
        exit 1
    fi
done

# Step 7: Set up environment variables
echo -e "${BLUE}⚙️ Setting up environment variables...${NC}"

ENV_FILE=".env"
if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" << 'EOF'
# AWS Resources Provider Environment Configuration

# AWS Configuration (for testing)
AWS_DEFAULT_REGION=us-west-2
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test

# LocalStack Configuration (for integration testing)
AWS_ENDPOINT_URL=http://localhost:4566

# Provider Configuration
FLAVOR_LOG_LEVEL=INFO
TF_LOG=INFO

# Development Configuration
PYTHONPATH=./src
EOF
    echo -e "${GREEN}  ✅ Created .env file with default values${NC}"
else
    echo -e "${BLUE}  ℹ️ Using existing .env file${NC}"
fi

# Step 8: Create basic test configuration
echo -e "${BLUE}🧪 Creating test configuration...${NC}"

# Create basic Terraform example
cat > terraform-examples/basic/main.tf << 'EOF'
terraform {
  required_providers {
    awsdemo = {
      source  = "local/awsdemo"
      version = "1.0.0"
    }
  }
}

provider "awsdemo" {
  region = "us-west-2"
  # For testing with LocalStack
  endpoint_url = "http://localhost:4566"
}

# Example S3 bucket
resource "awsdemo_s3_bucket" "example" {
  name               = "flavor-demo-bucket-${random_id.bucket_suffix.hex}"
  region             = "us-west-2"
  versioning_enabled = true
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

output "bucket_info" {
  value = {
    name = awsdemo_s3_bucket.example.name
    arn  = awsdemo_s3_bucket.example.arn
  }
}
EOF

echo -e "${GREEN}  ✅ Created basic Terraform example${NC}"

# Step 9: Final setup validation
echo -e "${BLUE}🔍 Running setup validation...${NC}"

# Test Python imports
python3 -c "
import sys
sys.path.append('src')

try:
    import boto3
    print('✅ boto3 import successful')
except ImportError as e:
    print(f'❌ boto3 import failed: {e}')
    sys.exit(1)

try:
    from config import ProviderConfig
    print('✅ config module import successful')
except ImportError as e:
    print(f'❌ config module import failed: {e}')
    sys.exit(1)
"

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}  ✅ Python imports validation passed${NC}"
else
    echo -e "${RED}  ❌ Python imports validation failed${NC}"
    exit 1
fi

# Deactivate virtual environment for user
deactivate 2>/dev/null || true

# Step 10: Setup complete
echo ""
echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo ""
echo "📋 Setup Summary:"
echo "=================="
echo -e "${GREEN}✅ Python virtual environment created (venv/)${NC}"
echo -e "${GREEN}✅ Production dependencies installed${NC}"
echo -e "${GREEN}✅ Development dependencies installed${NC}"
echo -e "${GREEN}✅ Directory structure created${NC}"
echo -e "${GREEN}✅ Environment configuration created (.env)${NC}"
echo -e "${GREEN}✅ Basic Terraform example created${NC}"

if [[ "$HAS_DOCKER" == "true" ]]; then
    echo -e "${GREEN}✅ LocalStack testing infrastructure started${NC}"
fi

echo ""
echo "🚀 Next Steps:"
echo "=============="
echo "1. Activate the Python environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Build the PSPF package:"
echo "   ./build.sh"
echo ""
echo "3. Run tests:"
echo "   ./test.sh"
echo ""
echo "4. Try the Terraform example:"
echo "   cd terraform-examples/basic"
echo "   terraform init"
echo "   terraform plan"
echo ""
echo "🔧 Development workflow:"
echo "   source venv/bin/activate  # Activate Python environment"
echo "   source .env               # Load environment variables"
echo "   cd src && python main.py --help  # Test provider directly"
echo ""
echo -e "${BLUE}Happy coding with PSPF! 🚀${NC}"

# 📦🍜📄🪄
