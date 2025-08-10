# Database Provider Example

A sophisticated terraform provider demonstrating Flavor packaging with database connectivity, connection management, and stateful resource handling.

## 🎯 What This Example Shows

- ✅ Database connection lifecycle management
- ✅ Resource state persistence and drift detection
- ✅ Transaction handling and rollback scenarios
- ✅ Connection pooling and performance optimization
- ✅ Secrets and credential management
- ✅ Docker-based testing environment
- ✅ Advanced error handling and recovery
- ✅ Database schema migrations

**Perfect for:** Providers managing stateful resources with external dependencies

## 📁 Project Structure

```
database-provider/
├── README.md              # This file
├── src/                   # Provider source code
│   ├── main.py           # Provider entry point
│   ├── provider.py       # Core provider implementation
│   ├── config.py         # Database configuration
│   ├── models.py         # Database models and schemas
│   ├── resources/        # Resource implementations
│   │   ├── __init__.py
│   │   ├── database.py   # Database resource
│   │   ├── user.py       # Database user resource
│   │   └── schema.py     # Database schema resource
│   ├── data_sources/     # Data source implementations
│   │   ├── __init__.py
│   │   └── query.py      # SQL query data source
│   ├── utils/            # Utility modules
│   │   ├── __init__.py
│   │   ├── db_client.py  # Database client wrapper
│   │   ├── connection.py # Connection management
│   │   └── migrations.py # Schema migration utilities
│   └── requirements.txt  # Dependencies with database drivers
├── tests/                # Comprehensive test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests with real DB
│   └── performance/      # Performance and load tests
├── docker/               # Docker configuration
│   ├── postgres/         # PostgreSQL test setup
│   ├── mysql/            # MySQL test setup
│   └── init-scripts/     # Database initialization
├── terraform-examples/   # Example configurations
│   ├── basic/            # Basic database operations
│   ├── migration/        # Schema migration example
│   └── multi-tenant/     # Multi-tenant setup
├── keys/                 # Flavor signing keys
├── dist/                 # Built packages
├── setup.sh             # Environment setup
├── build.sh             # Build script
├── test.sh              # Test runner
├── docker-compose.yml   # Test database setup
└── migrations/          # Example schema migrations
    ├── 001_initial.sql
    └── 002_add_indexes.sql
```

## 🚀 Quick Start

### Step 1: Set up Environment

```bash
# Navigate to example directory
cd database-provider

# Set up dependencies and test databases
./setup.sh
```

### Step 2: Start Test Databases

```bash
# Start PostgreSQL and MySQL test instances
docker-compose up -d

# Verify databases are ready
./wait-for-db.sh
```

### Step 3: Build Provider

```bash
# Build Flavor package
./build.sh
```

### Step 4: Run Tests

```bash
# Run comprehensive test suite
./test.sh
```

### Step 5: Try Examples

```bash
# Try basic database operations
cd terraform-examples/basic
terraform init
terraform plan
terraform apply
```

## 🏗️ Architecture Deep Dive

### Connection Management

The provider implements sophisticated connection management:

**Connection Pool**: Efficient resource utilization
- Configurable pool size and timeouts
- Automatic connection recycling
- Health checks and reconnection logic
- Support for read/write splitting

**Transaction Handling**: ACID compliance
- Automatic transaction boundaries
- Rollback on errors
- Nested transaction support
- Deadlock detection and retry

**Security**: Secure credential handling
- Encrypted connection strings
- SSL/TLS certificate validation
- Credential rotation support
- Audit logging for sensitive operations

### Resource Implementations

#### `dbdemo_database`
Complete database lifecycle management:
```hcl
resource "dbdemo_database" "app_db" {
  name     = "myapp"
  owner    = "app_user"
  encoding = "UTF8"
  
  # Advanced configuration
  template = "template0"
  lc_collate = "en_US.UTF-8"
  lc_ctype   = "en_US.UTF-8"
  
  # Connection limits
  connection_limit = 100
  
  # Custom settings
  settings = {
    "shared_preload_libraries" = "pg_stat_statements"
    "max_connections" = "200"
  }
}
```

#### `dbdemo_user`
User and role management:
```hcl
resource "dbdemo_user" "app_user" {
  username = "myapp_user"
  password = var.db_password
  
  # Permissions
  superuser    = false
  create_db    = true
  create_role  = false
  inherit      = true
  login        = true
  replication  = false
  
  # Connection limits
  connection_limit = 50
  
  # Valid until
  valid_until = "2024-12-31 23:59:59"
  
  # Grant database access
  databases = [dbdemo_database.app_db.name]
  
  # Custom privileges
  privileges = [
    "SELECT", "INSERT", "UPDATE", "DELETE"
  ]
}
```

#### `dbdemo_schema`
Schema and migration management:
```hcl
resource "dbdemo_schema" "app_schema" {
  name     = "app"
  database = dbdemo_database.app_db.name
  owner    = dbdemo_user.app_user.username
  
  # Migration settings
  migration_path = "./migrations"
  auto_migrate   = true
  
  # Rollback configuration
  backup_before_migrate = true
  rollback_on_failure   = true
}
```

### Data Sources

#### `dbdemo_query`
Flexible SQL query execution:
```hcl
data "dbdemo_query" "user_stats" {
  database = dbdemo_database.app_db.name
  
  query = <<-SQL
    SELECT 
      count(*) as total_users,
      count(CASE WHEN last_login > NOW() - INTERVAL '30 days' THEN 1 END) as active_users
    FROM users
  SQL
  
  # Cache settings
  cache_duration = "5m"
  
  # Query timeout
  timeout = "30s"
}

output "user_statistics" {
  value = {
    total_users  = data.dbdemo_query.user_stats.results[0].total_users
    active_users = data.dbdemo_query.user_stats.results[0].active_users
  }
}
```

## 🔧 Implementation Details

### Database Client Architecture

```python
# src/utils/db_client.py
class DatabaseClient:
    """Advanced database client with connection pooling and error handling."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pools = {}  # Connection pools by database
        self._health_checks = {}
    
    async def get_connection(self, database: str = None) -> AsyncConnection:
        """Get connection from pool with health checking."""
        pool_key = database or 'default'
        
        if pool_key not in self.pools:
            self.pools[pool_key] = await self._create_pool(database)
        
        pool = self.pools[pool_key]
        
        # Health check with retry
        for attempt in range(3):
            try:
                conn = await pool.acquire()
                await self._health_check(conn)
                return ConnectionWrapper(conn, pool)
            except Exception as e:
                logger.warning(f"Connection health check failed (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    raise
                await asyncio.sleep(1)
    
    async def execute_transaction(self, operations: List[Operation]) -> List[Any]:
        """Execute multiple operations in a single transaction."""
        async with await self.get_connection() as conn:
            async with conn.transaction():
                results = []
                for op in operations:
                    result = await op.execute(conn)
                    results.append(result)
                return results
```

### Resource State Management

```python
# src/resources/database.py
class DatabaseResource:
    """Database resource with comprehensive state management."""
    
    async def create(self, config: DatabaseConfig) -> ResourceState:
        """Create database with validation and error handling."""
        # Validate configuration
        await self._validate_config(config)
        
        # Check if database already exists
        if await self._database_exists(config.name):
            raise ResourceAlreadyExistsError(f"Database {config.name} already exists")
        
        try:
            # Create database in transaction
            async with self.db_client.get_connection() as conn:
                await conn.execute(
                    "CREATE DATABASE {} WITH OWNER = {} ENCODING = {}",
                    config.name, config.owner, config.encoding
                )
                
                # Apply additional settings
                if config.settings:
                    await self._apply_settings(conn, config.name, config.settings)
            
            # Generate state
            state = await self.read(config.name)
            logger.info(f"Created database: {config.name}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to create database {config.name}: {e}")
            # Cleanup on failure
            await self._cleanup_failed_creation(config.name)
            raise
    
    async def read(self, database_name: str) -> Optional[ResourceState]:
        """Read database state with drift detection."""
        async with self.db_client.get_connection() as conn:
            # Get database information
            db_info = await conn.fetchrow("""
                SELECT 
                    datname,
                    datowner::regrole::text as owner,
                    encoding,
                    datcollate,
                    datctype,
                    datconnlimit
                FROM pg_database 
                WHERE datname = $1
            """, database_name)
            
            if not db_info:
                return None
            
            # Get additional settings
            settings = await self._get_database_settings(conn, database_name)
            
            return ResourceState(
                id=database_name,
                name=database_name,
                owner=db_info['owner'],
                encoding=db_info['encoding'],
                collate=db_info['datcollate'],
                ctype=db_info['datctype'],
                connection_limit=db_info['datconnlimit'],
                settings=settings,
                created_at=await self._get_creation_time(conn, database_name)
            )
```

### Migration System

```python
# src/utils/migrations.py
class MigrationManager:
    """Handle database schema migrations with rollback support."""
    
    async def apply_migrations(self, database: str, migration_path: str) -> MigrationResult:
        """Apply pending migrations with backup and rollback capability."""
        migrations = await self._discover_migrations(migration_path)
        applied = await self._get_applied_migrations(database)
        
        pending = [m for m in migrations if m.version not in applied]
        
        if not pending:
            return MigrationResult(applied=0, skipped=len(migrations))
        
        # Create backup before migrations
        backup_id = await self._create_backup(database)
        
        try:
            results = []
            async with self.db_client.get_connection(database) as conn:
                for migration in pending:
                    await self._apply_single_migration(conn, migration)
                    results.append(migration)
                    logger.info(f"Applied migration: {migration.name}")
            
            return MigrationResult(applied=len(results), migrations=results)
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            await self._rollback_to_backup(database, backup_id)
            raise MigrationFailedError(f"Migration failed and rolled back: {e}")
```

## 🧪 Testing Strategy

### Multi-Database Testing

The example supports testing against multiple database engines:

**PostgreSQL**: Primary test database
- Full feature support
- Advanced PostgreSQL-specific features
- Performance optimization testing

**MySQL**: Compatibility testing
- Cross-database compatibility
- Feature subset validation
- Migration between engines

**SQLite**: Lightweight testing
- Fast unit tests
- CI/CD integration
- Development workflow

### Test Categories

#### Unit Tests
```bash
pytest tests/unit/ -v
# Test individual components in isolation
# Mock database connections
# Validate business logic
```

#### Integration Tests
```bash
pytest tests/integration/ -v
# Real database connections
# End-to-end workflows
# Error scenario testing
```

#### Performance Tests
```bash
pytest tests/performance/ -v
# Connection pool performance
# Query optimization
# Load testing scenarios
```

### Docker Test Environment

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: testdb
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpass
    ports:
      - "5432:5432"
    volumes:
      - ./docker/postgres/init:/docker-entrypoint-initdb.d
  
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: testdb
      MYSQL_USER: testuser
      MYSQL_PASSWORD: testpass
    ports:
      - "3306:3306"
    volumes:
      - ./docker/mysql/init:/docker-entrypoint-initdb.d
```

## 🔒 Security Features

### Credential Management
- Encrypted connection strings in state
- Support for AWS Secrets Manager, HashiCorp Vault
- Automatic credential rotation
- Principle of least privilege

### Connection Security
- TLS/SSL enforcement
- Certificate validation
- IP allowlisting support
- Audit logging

### Data Protection
- Encryption at rest
- Encrypted backups
- PII detection and masking
- Compliance reporting

## ⚡ Performance Optimization

### Connection Pooling
```python
# Optimized connection pool configuration
POOL_CONFIG = {
    'min_size': 5,
    'max_size': 50,
    'max_queries': 50000,
    'max_inactive_connection_lifetime': 300,
    'timeout': 10,
    'command_timeout': 60,
    'server_settings': {
        'jit': 'off',  # Disable JIT for simple queries
        'application_name': 'pspf_db_provider'
    }
}
```

### Query Optimization
- Prepared statement caching
- Query plan analysis
- Index recommendation
- Slow query monitoring

### Resource Caching
- Metadata caching with TTL
- Connection state caching
- Query result caching
- Invalidation strategies

## 🚀 Advanced Features

### Multi-Tenant Support
```hcl
# Separate databases per tenant
resource "dbdemo_database" "tenant_db" {
  for_each = var.tenants
  
  name     = "tenant_${each.key}"
  owner    = dbdemo_user.tenant_users[each.key].username
  template = "tenant_template"
  
  # Tenant-specific configuration
  connection_limit = each.value.max_connections
  settings = each.value.db_settings
}
```

### Blue-Green Deployments
```hcl
# Blue-green database deployment
resource "dbdemo_database" "app_db_blue" {
  name = "myapp_blue"
  # ... configuration
}

resource "dbdemo_database" "app_db_green" {
  name = "myapp_green"
  # ... configuration
}

# Switch traffic using data source
data "dbdemo_query" "active_database" {
  query = "SELECT current_database FROM deployment_config WHERE active = true"
}
```

## 🆘 Troubleshooting

### Common Issues

**Connection Pool Exhaustion**
```bash
# Check pool status
terraform-provider-dbdemo --debug --pool-status

# Increase pool size
export DB_MAX_POOL_SIZE=100
```

**Migration Failures**
```bash
# Check migration status
terraform-provider-dbdemo --migration-status

# Manual rollback
terraform-provider-dbdemo --rollback-to-version 001
```

**Performance Issues**
```bash
# Enable query logging
export DB_LOG_QUERIES=true
export DB_LOG_SLOW_QUERIES=5s

# Analyze slow queries
terraform-provider-dbdemo --analyze-queries
```

### Debug Mode
```bash
# Enable comprehensive debugging
export TF_LOG=DEBUG
export DB_DEBUG=true
export PSPF_LOG_LEVEL=TRACE

terraform plan
```

## 📚 Learning Outcomes

After completing this example, you'll understand:

1. **Stateful Resource Management**
   - External state synchronization
   - Drift detection and correction
   - Resource dependencies

2. **Connection Management**
   - Pool configuration and tuning
   - Health checks and failover
   - Security and authentication

3. **Transaction Handling**
   - ACID compliance
   - Rollback scenarios
   - Nested transactions

4. **Performance Optimization**
   - Query optimization
   - Connection pooling
   - Caching strategies

5. **Production Concerns**
   - Monitoring and alerting
   - Backup and recovery
   - Security compliance

---

**Ready to dive deeper?** 👉 [Multi-Platform CI/CD](../multi-platform/) | [Enterprise Security](../enterprise-security/) | [Examples Overview](../README.md)