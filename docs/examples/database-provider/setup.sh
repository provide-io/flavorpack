#!/bin/bash
set -euo pipefail

echo "🏗️ Setting up Database Provider Example"
echo "======================================="

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

# Check Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    echo "Please install Docker to continue"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon not running${NC}"
    echo "Please start Docker daemon"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found${NC}"
    echo "Please install Docker Compose"
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"

# Check PSPF tools
if ! command -v flavor-packager &> /dev/null; then
    echo -e "${YELLOW}⚠️ PSPF tools not found in PATH${NC}"
    echo "Please install PSPF tools first:"
    echo "  https://github.com/your-org/flavor/docs/installation.md"
    echo ""
    read -p "Continue without PSPF tools? (build.sh will fail) [y/N]: " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ PSPF tools found${NC}"
fi

# Step 2: Create directory structure
echo -e "${BLUE}📁 Creating directory structure...${NC}"

DIRECTORIES=(
    "src/resources"
    "src/data_sources" 
    "src/utils"
    "tests/unit"
    "tests/integration"
    "tests/performance"
    "docker/postgres/init"
    "docker/mysql/init"
    "docker/mysql/conf"
    "docker/redis"
    "docker/pgadmin"
    "docker/db-init/scripts"
    "terraform-examples/basic"
    "terraform-examples/migration"
    "terraform-examples/multi-tenant"
    "migrations"
    "keys"
    "dist"
    "logs"
)

for dir in "${DIRECTORIES[@]}"; do
    mkdir -p "$dir"
done

echo -e "${GREEN}✅ Directory structure created${NC}"

# Step 3: Set up Python virtual environment
echo -e "${BLUE}🐍 Setting up Python environment...${NC}"

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

# Step 4: Install Python dependencies
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"

# Core dependencies
pip install \
    asyncpg>=0.28.0 \
    aiomysql>=0.2.0 \
    aioredis>=2.0.0 \
    sqlalchemy[asyncio]>=2.0.0 \
    alembic>=1.12.0 \
    pydantic>=2.0.0 \
    structlog>=22.3.0 \
    tenacity>=8.2.0 \
    cryptography>=41.0.0 \
    python-dotenv>=1.0.0

echo -e "${GREEN}✅ Core dependencies installed${NC}"

# Development dependencies
echo -e "${BLUE}  Installing development dependencies...${NC}"
pip install \
    pytest>=7.4.0 \
    pytest-asyncio>=0.21.0 \
    pytest-cov>=4.1.0 \
    pytest-mock>=3.11.0 \
    pytest-benchmark>=4.0.0 \
    black>=23.0.0 \
    flake8>=6.0.0 \
    mypy>=1.5.0 \
    factory-boy>=3.3.0

echo -e "${GREEN}✅ Development dependencies installed${NC}"

# Step 5: Create Docker configuration files
echo -e "${BLUE}🐳 Setting up Docker configuration...${NC}"

# PostgreSQL initialization script
cat > docker/postgres/init/01_init.sql << 'EOF'
-- PostgreSQL initialization script for PSPF Database Provider testing

-- Create additional test databases
CREATE DATABASE testdb_migration;
CREATE DATABASE testdb_performance;

-- Create test schemas
\c testdb;
CREATE SCHEMA IF NOT EXISTS app_schema;
CREATE SCHEMA IF NOT EXISTS tenant_a;
CREATE SCHEMA IF NOT EXISTS tenant_b;

-- Create test roles
CREATE ROLE app_read_role;
CREATE ROLE app_write_role;
CREATE ROLE tenant_role;

-- Grant permissions
GRANT CONNECT ON DATABASE testdb TO app_read_role;
GRANT CONNECT ON DATABASE testdb TO app_write_role;
GRANT CONNECT ON DATABASE testdb TO tenant_role;

GRANT USAGE ON SCHEMA public TO app_read_role;
GRANT USAGE ON SCHEMA public TO app_write_role;
GRANT USAGE ON SCHEMA app_schema TO app_read_role;
GRANT USAGE ON SCHEMA app_schema TO app_write_role;

-- Create sample tables for testing
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    bio TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert test data
INSERT INTO users (username, email, last_login) VALUES
    ('alice', 'alice@example.com', NOW() - INTERVAL '5 days'),
    ('bob', 'bob@example.com', NOW() - INTERVAL '45 days'),
    ('charlie', 'charlie@example.com', NOW() - INTERVAL '2 days'),
    ('diana', 'diana@example.com', NOW() - INTERVAL '60 days');

INSERT INTO user_profiles (user_id, first_name, last_name, bio) VALUES
    (1, 'Alice', 'Johnson', 'Software engineer'),
    (2, 'Bob', 'Smith', 'Product manager'),
    (3, 'Charlie', 'Brown', 'Designer'),
    (4, 'Diana', 'Wilson', 'Data scientist');

-- Create indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_last_login ON users(last_login);

-- Create migration tracking table
CREATE TABLE IF NOT EXISTS pspf_migrations (
    version VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);

EOF

# MySQL initialization script
cat > docker/mysql/init/01_init.sql << 'EOF'
-- MySQL initialization script for PSPF Database Provider testing

-- Use the test database
USE testdb;

-- Create test tables
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS user_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    bio TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Insert test data
INSERT INTO users (username, email, last_login) VALUES
    ('alice_mysql', 'alice.mysql@example.com', DATE_SUB(NOW(), INTERVAL 5 DAY)),
    ('bob_mysql', 'bob.mysql@example.com', DATE_SUB(NOW(), INTERVAL 45 DAY)),
    ('charlie_mysql', 'charlie.mysql@example.com', DATE_SUB(NOW(), INTERVAL 2 DAY));

INSERT INTO user_profiles (user_id, first_name, last_name, bio) VALUES
    (1, 'Alice', 'MySQL', 'MySQL test user'),
    (2, 'Bob', 'MySQL', 'MySQL test user'),
    (3, 'Charlie', 'MySQL', 'MySQL test user');

-- Create indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- Migration tracking table
CREATE TABLE IF NOT EXISTS pspf_migrations (
    version VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);
EOF

# MySQL configuration
cat > docker/mysql/conf/custom.cnf << 'EOF'
[mysqld]
# Custom MySQL configuration for PSPF testing

# Connection settings
max_connections = 100
max_connect_errors = 10000

# Performance settings
innodb_buffer_pool_size = 128M
innodb_log_file_size = 64M
innodb_flush_log_at_trx_commit = 2

# Logging
general_log = 1
general_log_file = /var/log/mysql/general.log
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2

# Character set
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[client]
default-character-set = utf8mb4
EOF

# Redis configuration
cat > docker/redis/redis.conf << 'EOF'
# Redis configuration for PSPF Database Provider testing

# Network settings
bind 0.0.0.0
port 6379
timeout 0
tcp-keepalive 300

# General settings
databases 16
save 900 1
save 300 10
save 60 10000

# Memory management
maxmemory 128mb
maxmemory-policy allkeys-lru

# Security
protected-mode no
requirepass ""

# Logging
loglevel notice
logfile ""

# Persistence
dir /data
dbfilename dump.rdb
EOF

# pgAdmin servers configuration
cat > docker/pgadmin/servers.json << 'EOF'
{
  "Servers": {
    "1": {
      "Name": "PSPF Test PostgreSQL",
      "Group": "Servers",
      "Host": "postgres",
      "Port": 5432,
      "MaintenanceDB": "testdb",
      "Username": "testuser",
      "SSLMode": "prefer",
      "SSLCert": "<STORAGE_DIR>/.postgresql/postgresql.crt",
      "SSLKey": "<STORAGE_DIR>/.postgresql/postgresql.key",
      "SSLCompression": 0,
      "Timeout": 10,
      "UseSSHTunnel": 0,
      "TunnelPort": "22",
      "TunnelAuthentication": 0
    }
  }
}
EOF

echo -e "${GREEN}✅ Docker configuration files created${NC}"

# Step 6: Create database initialization service
cat > docker/db-init/Dockerfile << 'EOF'
FROM python:3.11-alpine

# Install system dependencies
RUN apk add --no-cache \
    postgresql-client \
    mysql-client \
    curl

# Install Python dependencies
RUN pip install --no-cache-dir \
    asyncpg \
    aiomysql \
    aioredis \
    sqlalchemy[asyncio] \
    alembic

# Copy scripts
COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

WORKDIR /scripts
CMD ["./init-databases.sh"]
EOF

cat > docker/db-init/scripts/init-databases.sh << 'EOF'
#!/bin/bash
set -euo pipefail

echo "🔧 Initializing databases for PSPF Database Provider testing..."

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
    echo "PostgreSQL is not ready - sleeping"
    sleep 1
done
echo "✅ PostgreSQL is ready"

# Wait for MySQL
echo "Waiting for MySQL..."
until mysqladmin ping -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" --silent; do
    echo "MySQL is not ready - sleeping"
    sleep 1
done
echo "✅ MySQL is ready"

# Wait for Redis
echo "Waiting for Redis..."
until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping; do
    echo "Redis is not ready - sleeping"
    sleep 1
done
echo "✅ Redis is ready"

echo "🎉 All databases are ready!"
EOF

chmod +x docker/db-init/scripts/init-databases.sh

echo -e "${GREEN}✅ Database initialization service created${NC}"

# Step 7: Create sample migrations
echo -e "${BLUE}📄 Creating sample migrations...${NC}"

cat > migrations/001_initial.sql << 'EOF'
-- Migration: 001_initial
-- Description: Create initial application schema

CREATE SCHEMA IF NOT EXISTS app;

-- Users table
CREATE TABLE app.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- User sessions table
CREATE TABLE app.user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES app.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_app_users_username ON app.users(username);
CREATE INDEX idx_app_users_email ON app.users(email);
CREATE INDEX idx_app_user_sessions_user_id ON app.user_sessions(user_id);
CREATE INDEX idx_app_user_sessions_token_hash ON app.user_sessions(token_hash);
CREATE INDEX idx_app_user_sessions_expires_at ON app.user_sessions(expires_at);

-- Insert migration record
INSERT INTO pspf_migrations (version, name, checksum) VALUES 
    ('001', 'initial', 'sha256:abc123def456');
EOF

cat > migrations/002_add_indexes.sql << 'EOF'
-- Migration: 002_add_indexes
-- Description: Add performance indexes and constraints

-- Add user profile information
ALTER TABLE app.users ADD COLUMN first_name VARCHAR(50);
ALTER TABLE app.users ADD COLUMN last_name VARCHAR(50);
ALTER TABLE app.users ADD COLUMN last_login TIMESTAMP;

-- Create partial index for active users
CREATE INDEX idx_app_users_active_last_login ON app.users(last_login) 
    WHERE is_active = true;

-- Create composite index for name searches
CREATE INDEX idx_app_users_name ON app.users(first_name, last_name);

-- Add constraint for email validation
ALTER TABLE app.users ADD CONSTRAINT check_email_format 
    CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- Insert migration record
INSERT INTO pspf_migrations (version, name, checksum) VALUES 
    ('002', 'add_indexes', 'sha256:def456ghi789');
EOF

echo -e "${GREEN}✅ Sample migrations created${NC}"

# Step 8: Create environment configuration
echo -e "${BLUE}⚙️ Setting up environment configuration...${NC}"

ENV_FILE=".env"
if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" << 'EOF'
# Database Provider Environment Configuration

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=testdb
POSTGRES_USER=testuser
POSTGRES_PASSWORD=testpass

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=testdb
MYSQL_USER=testuser
MYSQL_PASSWORD=testpass

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Provider Configuration
DB_PROVIDER_LOG_LEVEL=INFO
DB_MAX_POOL_SIZE=20
DB_MIN_POOL_SIZE=5
DB_POOL_TIMEOUT=30
DB_QUERY_TIMEOUT=30

# Development Configuration
PYTHONPATH=./src
TF_LOG=INFO
FLAVOR_LOG_LEVEL=INFO

# Testing Configuration
TEST_DB_CLEANUP=true
TEST_MIGRATION_PATH=./migrations
PYTEST_ARGS=-v --tb=short
EOF
    echo -e "${GREEN}  ✅ Created .env file${NC}"
else
    echo -e "${BLUE}  ℹ️ Using existing .env file${NC}"
fi

# Step 9: Create basic Terraform example
echo -e "${BLUE}🏗️ Creating Terraform examples...${NC}"

cat > terraform-examples/basic/main.tf << 'EOF'
terraform {
  required_providers {
    dbdemo = {
      source  = "local/dbdemo"
      version = "1.0.0"
    }
  }
}

provider "dbdemo" {
  # PostgreSQL connection for testing
  host     = "localhost"
  port     = 5432
  username = "testuser"
  password = "testpass"
  database = "testdb"
  
  # Connection pool settings
  max_connections = 20
  min_connections = 5
  
  # SSL settings (disabled for local testing)
  ssl_mode = "disable"
}

# Create a database
resource "dbdemo_database" "app_db" {
  name     = "myapp_${random_id.db_suffix.hex}"
  owner    = "testuser"
  encoding = "UTF8"
  
  # PostgreSQL specific settings
  template   = "template0"
  lc_collate = "en_US.UTF-8"
  lc_ctype   = "en_US.UTF-8"
  
  connection_limit = 100
}

# Create a database user
resource "dbdemo_user" "app_user" {
  username = "myapp_user_${random_id.user_suffix.hex}"
  password = var.app_user_password
  
  # User privileges
  create_db = true
  login     = true
  
  # Grant access to the database
  databases = [dbdemo_database.app_db.name]
  
  depends_on = [dbdemo_database.app_db]
}

# Create a schema
resource "dbdemo_schema" "app_schema" {
  name     = "app"
  database = dbdemo_database.app_db.name
  owner    = dbdemo_user.app_user.username
  
  # Migration settings
  migration_path = "../../migrations"
  auto_migrate   = true
  
  depends_on = [dbdemo_user.app_user]
}

# Query existing data
data "dbdemo_query" "user_count" {
  database = "testdb"
  
  query = <<-SQL
    SELECT 
      count(*) as total_users,
      count(CASE WHEN last_login > NOW() - INTERVAL '30 days' THEN 1 END) as active_users
    FROM users
  SQL
  
  depends_on = [dbdemo_database.app_db]
}

# Random suffixes for unique names
resource "random_id" "db_suffix" {
  byte_length = 4
}

resource "random_id" "user_suffix" {
  byte_length = 4
}

# Variables
variable "app_user_password" {
  description = "Password for the application database user"
  type        = string
  default     = "changeme123"
  sensitive   = true
}

# Outputs
output "database_info" {
  value = {
    name = dbdemo_database.app_db.name
    host = "localhost"
    port = 5432
  }
  description = "Database connection information"
}

output "user_info" {
  value = {
    username = dbdemo_user.app_user.username
    database = dbdemo_database.app_db.name
  }
  description = "Database user information"
  sensitive = true
}

output "user_statistics" {
  value = {
    total_users  = tonumber(data.dbdemo_query.user_count.results[0].total_users)
    active_users = tonumber(data.dbdemo_query.user_count.results[0].active_users)
  }
  description = "Current user statistics from the database"
}
EOF

echo -e "${GREEN}✅ Basic Terraform example created${NC}"

# Step 10: Start database services
echo -e "${BLUE}🚀 Starting database services...${NC}"

# Start the databases
if docker-compose up -d postgres mysql redis; then
    echo -e "${GREEN}✅ Database services started${NC}"
    
    # Wait for services to be ready
    echo -e "${BLUE}  Waiting for services to be ready...${NC}"
    
    # Wait for PostgreSQL
    echo -e "${BLUE}    Checking PostgreSQL...${NC}"
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U testuser -d testdb > /dev/null 2>&1; then
            echo -e "${GREEN}    ✅ PostgreSQL is ready${NC}"
            break
        fi
        echo -e "${BLUE}      Waiting... (${i}/30)${NC}"
        sleep 2
    done
    
    # Wait for MySQL
    echo -e "${BLUE}    Checking MySQL...${NC}"
    for i in {1..30}; do
        if docker-compose exec -T mysql mysqladmin ping -h localhost -u testuser -ptestpass --silent > /dev/null 2>&1; then
            echo -e "${GREEN}    ✅ MySQL is ready${NC}"
            break
        fi
        echo -e "${BLUE}      Waiting... (${i}/30)${NC}"
        sleep 2
    done
    
    # Wait for Redis
    echo -e "${BLUE}    Checking Redis...${NC}"
    for i in {1..10}; do
        if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN}    ✅ Redis is ready${NC}"
            break
        fi
        echo -e "${BLUE}      Waiting... (${i}/10)${NC}"
        sleep 1
    done
    
else
    echo -e "${YELLOW}⚠️ Some database services may not have started correctly${NC}"
fi

# Deactivate virtual environment
deactivate 2>/dev/null || true

# Step 11: Setup complete
echo ""
echo -e "${GREEN}🎉 Database Provider setup completed successfully!${NC}"
echo ""
echo "📋 Setup Summary:"
echo "=================="
echo -e "${GREEN}✅ Python virtual environment created (venv/)${NC}"
echo -e "${GREEN}✅ Database dependencies installed${NC}"
echo -e "${GREEN}✅ Docker services configured and started${NC}"
echo -e "${GREEN}✅ PostgreSQL test database ready (port 5432)${NC}"
echo -e "${GREEN}✅ MySQL test database ready (port 3306)${NC}"
echo -e "${GREEN}✅ Redis cache ready (port 6379)${NC}"
echo -e "${GREEN}✅ Sample migrations created${NC}"
echo -e "${GREEN}✅ Terraform examples created${NC}"

echo ""
echo "🔗 Database Connections:"
echo "========================"
echo "PostgreSQL: postgresql://testuser:testpass@localhost:5432/testdb"
echo "MySQL:      mysql://testuser:testpass@localhost:3306/testdb"
echo "Redis:      redis://localhost:6379/0"

echo ""
echo "🌐 Management Interfaces:"
echo "========================"
echo "pgAdmin:    http://localhost:8080 (admin@flavor.local / admin)"
echo "phpMyAdmin: http://localhost:8081 (root / rootpass)"

echo ""
echo "🚀 Next Steps:"
echo "=============="
echo "1. Activate Python environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Load environment variables:"
echo "   source .env"
echo ""
echo "3. Build the PSPF package:"
echo "   ./build.sh"
echo ""
echo "4. Run tests:"
echo "   ./test.sh"
echo ""
echo "5. Try Terraform example:"
echo "   cd terraform-examples/basic"
echo "   terraform init && terraform plan"
echo ""
echo "🛠️ Development Commands:"
echo "   docker-compose ps                    # Check service status"
echo "   docker-compose logs postgres         # View PostgreSQL logs"
echo "   docker-compose exec postgres psql -U testuser testdb  # Connect to PostgreSQL"
echo "   docker-compose down                  # Stop all services"
echo ""
echo -e "${BLUE}Ready to build advanced database providers with PSPF! 🚀${NC}"

# 📦🍜📄🪄
