# Configuration System Refactor Plan

## Current State Analysis

### Problem Summary
The codebase has a sophisticated configuration system (`BaseConfig`, `RuntimeConfig`, `field`, `env_field`) but most config classes bypass it by implementing manual `from_env()` methods with direct `os.getenv()` calls. This creates:
- Code duplication across config classes
- Inconsistent parsing and validation
- Unused field metadata (`env_var` declarations are ignored)
- No centralized environment variable handling

### Affected Files
- `src/provide/foundation/logger/config/logging.py` - 50+ manual `os.getenv()` calls
- `src/provide/foundation/logger/config/telemetry.py` - 20+ manual `os.getenv()` calls  
- `src/provide/foundation/transport/config.py` - 10+ manual `os.getenv()` calls
- `src/provide/foundation/streams/console.py` - Direct `os.getenv()` for flags
- `src/provide/foundation/streams/core.py` - Direct `os.getenv()` for testing

## Implementation Checklist

### Phase 1: Refactor Config Classes to Use RuntimeConfig
- [ ] Change `LoggingConfig` to inherit from `RuntimeConfig`
- [ ] Change `TelemetryConfig` to inherit from `RuntimeConfig`
- [ ] Change `TransportConfig` to inherit from `RuntimeConfig`
- [ ] Change `HTTPConfig` to inherit from `RuntimeConfig`
- [ ] Remove manual `from_env()` implementations from all config classes
- [ ] Update callers to use `RuntimeConfig.from_env()` method

### Phase 2: Enhance Field Declarations
- [ ] Add converter for `module_levels` field (parse "module1:LEVEL,module2:LEVEL")
- [ ] Add converter for `rate_limit_per_logger` field (parse "logger1:rate:capacity")
- [ ] Exclude emoji sets fields from config (not implemented in logger)
- [ ] Add validators to fields instead of post-validation
- [ ] Use declarative field definitions instead of manual parsing

### Phase 3: Centralize Simple Environment Checks
- [ ] Create `StreamConfig` class for console settings
- [ ] Add fields for `NO_COLOR`, `FORCE_COLOR`, `CLICK_TESTING`
- [ ] Replace direct `os.getenv()` calls in streams modules
- [ ] Register `StreamConfig` with ConfigManager

### Phase 4: Leverage Config Manager
- [ ] Register all configs at application startup
- [ ] Replace direct config instantiation with manager-based loading
- [ ] Add config watching capabilities
- [ ] Enable hot-reloading for development

## Specific Changes for Phase 1 & 2

### 1. LoggingConfig Changes

**Current Structure:**
```python
@define(slots=True, repr=False)
class LoggingConfig(BaseConfig):
    default_level: LogLevelStr = field(
        default="WARNING",
        env_var="PROVIDE_LOG_LEVEL",
        description="Default logging level",
    )
    # ... more fields ...
    
    @classmethod
    def from_env(cls, strict: bool = True) -> "LoggingConfig":
        config_dict = {}
        if level := os.getenv("PROVIDE_LOG_LEVEL"):  # Manual parsing
            # ... validation logic ...
        # ... 200+ lines of manual env var reading ...
        return cls(**config_dict)
```

**New Structure:**
```python
@define(slots=True, repr=False)
class LoggingConfig(RuntimeConfig):
    default_level: LogLevelStr = field(
        default="WARNING",
        env_var="PROVIDE_LOG_LEVEL",
        converter=parse_log_level,  # Add converter
        validator=validate_log_level,  # Add validator
        description="Default logging level",
    )
    
    module_levels: dict[str, LogLevelStr] = field(
        factory=lambda: {},
        env_var="PROVIDE_LOG_MODULE_LEVELS",
        converter=parse_module_levels,  # Custom parser for "mod1:LEVEL,mod2:LEVEL"
        description="Per-module log levels",
    )
    
    # Emoji sets functionality is not implemented in the logger
    # These fields should not be present in the refactored version
    # ... other fields with proper converters ...
    
    # No more from_env() method needed! RuntimeConfig handles it
```

### 2. TelemetryConfig Changes

**Current Structure:**
```python
@define(slots=True, repr=False)
class TelemetryConfig(BaseConfig):
    service_name: str | None = field(
        default=None,
        env_var="PROVIDE_SERVICE_NAME",
        description="Service name for telemetry",
    )
    # ... more fields ...
    
    @classmethod
    def from_env(cls, strict: bool = True) -> "TelemetryConfig":
        config_dict = {}
        service_name = os.getenv("OTEL_SERVICE_NAME") or os.getenv("PROVIDE_SERVICE_NAME")
        # ... manual parsing ...
        return cls(**config_dict)
```

**New Structure:**
```python
@define(slots=True, repr=False)
class TelemetryConfig(RuntimeConfig):
    service_name: str | None = field(
        default=None,
        env_var="PROVIDE_SERVICE_NAME",
        converter=lambda v: v or os.getenv("OTEL_SERVICE_NAME"),  # Handle fallback
        description="Service name for telemetry",
    )
    
    logging: LoggingConfig = field(
        factory=lambda: LoggingConfig.from_env(),  # Nested config loading
        description="Logging configuration"
    )
    
    trace_sample_rate: float = field(
        default=1.0,
        env_var="OTEL_TRACE_SAMPLE_RATE",
        converter=parse_float_with_validation,  # Parse and validate 0.0-1.0
        validator=validate_sample_rate,
        description="Sampling rate for traces (0.0 to 1.0)",
    )
    # ... other fields with proper converters ...
```

### 3. New Converter Functions (to be added)

```python
# In src/provide/foundation/config/converters.py

def parse_log_level(value: str) -> LogLevelStr:
    """Parse and validate log level string."""
    level = value.upper()
    if level not in _VALID_LOG_LEVEL_TUPLE:
        raise ValueError(f"Invalid log level: {value}")
    return level

def parse_module_levels(value: str) -> dict[str, LogLevelStr]:
    """Parse module:LEVEL,module:LEVEL format."""
    result = {}
    for pair in value.split(","):
        if ":" in pair:
            module, level = pair.split(":", 1)
            result[module.strip()] = parse_log_level(level.strip())
    return result

def parse_comma_list(value: str) -> list[str]:
    """Parse comma-separated list."""
    return [item.strip() for item in value.split(",") if item.strip()]

def parse_rate_limits(value: str) -> dict[str, tuple[float, float]]:
    """Parse logger:rate:capacity format."""
    result = {}
    for item in value.split(","):
        parts = item.split(":")
        if len(parts) == 3:
            logger, rate, capacity = parts
            result[logger.strip()] = (float(rate), float(capacity))
    return result
```

### 4. Usage After Refactor

```python
# Old way (manual):
config = LoggingConfig.from_env()

# New way (automatic via RuntimeConfig):
config = LoggingConfig.from_env()  # Uses RuntimeConfig.from_env()
# or with prefix:
config = LoggingConfig.from_env(prefix="PROVIDE_LOG")

# The RuntimeConfig.from_env() automatically:
# 1. Reads env vars based on field metadata
# 2. Applies converters for type conversion
# 3. Runs validators
# 4. Tracks source as ConfigSource.ENV
# 5. Handles file:// secrets
```

## Benefits

1. **Code Reduction**: Removes ~500+ lines of manual env var parsing
2. **Consistency**: All configs use the same loading mechanism
3. **Type Safety**: Converters ensure proper types at field level
4. **Validation**: Validators run automatically during loading
5. **Maintainability**: Adding new env vars only requires field declaration
6. **Features**: Automatic support for file-based secrets, source tracking, etc.

## Testing Requirements & Coverage Plan

### Existing Test Files to Update

1. **tests/config/test_config_logger.py**
   - Update `TestTelemetryConfigFromEnv` class to test RuntimeConfig inheritance
   - Remove tests for emoji sets functionality (dead code)
   - Add tests for converter functions
   - Test that field metadata is properly used

2. **tests/logger/test_config_coverage.py**
   - Update environment variable loading tests
   - Remove emoji sets related assertions
   - Add coverage for new converter functions

3. **tests/transport/test_transport_config.py** (create if doesn't exist)
   - Test TransportConfig with RuntimeConfig inheritance
   - Test HTTPConfig with proper field converters
   - Test environment variable precedence

### New Test Files to Create

1. **tests/config/test_converters.py**
   ```python
   # Test all converter functions:
   - test_parse_log_level()
   - test_parse_module_levels()
   - test_parse_rate_limits()
   - test_parse_float_with_validation()
   - test_parse_bool_extended()
   ```

2. **tests/config/test_runtime_config.py**
   ```python
   # Test RuntimeConfig.from_env() behavior:
   - test_from_env_with_prefix()
   - test_from_env_case_sensitivity()
   - test_from_env_file_secrets()
   - test_from_env_with_converters()
   - test_from_env_with_validators()
   - test_from_env_source_tracking()
   ```

### Test Coverage Matrix

| Component | Current Coverage | Target Coverage | Notes |
|-----------|-----------------|-----------------|-------|
| LoggingConfig.from_env() | Manual parsing tested | RuntimeConfig.from_env() tested | Remove 200+ lines of manual tests |
| TelemetryConfig.from_env() | Manual parsing tested | RuntimeConfig.from_env() tested | Simplify test assertions |
| TransportConfig.from_env() | Basic tests | Full converter coverage | Add edge case tests |
| Field converters | None | 100% coverage | New test file |
| Field validators | Inline in from_env() | Field-level coverage | Test at field definition |
| Emoji sets | N/A | N/A | Not implemented |

### Specific Test Cases

#### 1. Environment Variable Loading
```python
@pytest.mark.parametrize("env_vars,expected", [
    # Test basic types
    ({"PROVIDE_LOG_LEVEL": "DEBUG"}, {"default_level": "DEBUG"}),
    ({"PROVIDE_LOG_LEVEL": "invalid"}, ValidationError),  # Should fail
    
    # Test complex parsing
    ({"PROVIDE_LOG_MODULE_LEVELS": "auth:TRACE,db:ERROR"}, 
     {"module_levels": {"auth": "TRACE", "db": "ERROR"}}),
    
    # Test rate limits
    ({"PROVIDE_LOG_RATE_LIMIT_PER_LOGGER": "api:10:100,worker:5:50"},
     {"rate_limit_per_logger": {"api": (10.0, 100.0), "worker": (5.0, 50.0)}}),
])
def test_logging_config_from_env(monkeypatch, env_vars, expected):
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            LoggingConfig.from_env()
    else:
        config = LoggingConfig.from_env()
        for key, value in expected.items():
            assert getattr(config, key) == value
```

#### 2. Converter Functions
```python
def test_parse_module_levels():
    # Valid input
    result = parse_module_levels("auth.service:DEBUG,database:ERROR")
    assert result == {"auth.service": "DEBUG", "database": "ERROR"}
    
    # Empty input
    assert parse_module_levels("") == {}
    
    # Invalid format (missing colon)
    assert parse_module_levels("auth.service") == {}  # Skip invalid
    
    # Whitespace handling
    result = parse_module_levels(" auth : DEBUG , database : ERROR ")
    assert result == {"auth": "DEBUG", "database": "ERROR"}
```

#### 3. Field Validation
```python
def test_field_level_validation():
    # Test that validation happens at field level
    with pytest.raises(ValueError, match="Invalid port"):
        HTTPConfig(port=70000)  # Out of range
    
    # Test converter + validator chain
    config = HTTPConfig.from_env()  # PROVIDE_HTTP_PORT="8080"
    assert config.port == 8080
    assert isinstance(config.port, int)
```

#### 4. Source Tracking
```python
def test_config_source_tracking():
    # Load from environment
    monkeypatch.setenv("PROVIDE_LOG_LEVEL", "DEBUG")
    config = LoggingConfig.from_env()
    
    assert config.get_source("default_level") == ConfigSource.ENV
    assert config.get_source("console_formatter") == ConfigSource.DEFAULT
```

### Tests Not Needed

1. **Emoji sets tests** (functionality not implemented):
   - `test_from_env_parses_enabled_emoji_sets`
   - `test_from_env_handles_malformed_custom_emoji_sets_json`
   - Assertions checking emoji sets fields

### Migration Test Strategy

1. **Phase 1: Parallel Testing**
   - Keep old `from_env()` methods temporarily
   - Add new test that compares old vs new implementation:
   ```python
   def test_migration_compatibility():
       # Set up complex environment
       setup_test_environment()
       
       # Load with old method
       old_config = LoggingConfig.from_env_legacy()
       
       # Load with new RuntimeConfig method
       new_config = LoggingConfig.from_env()
       
       # Compare all fields
       assert old_config.to_dict() == new_config.to_dict()
   ```

2. **Phase 2: Cutover**
   - Remove legacy `from_env()` methods
   - Remove compatibility tests
   - Ensure all tests use RuntimeConfig.from_env()

### Performance Tests

```python
def test_config_loading_performance(benchmark):
    # Set up environment with many variables
    setup_complex_environment()
    
    # Benchmark new implementation
    result = benchmark(LoggingConfig.from_env)
    
    # Should be faster than old implementation
    # Old: ~500 lines of manual parsing
    # New: Automated field iteration
    assert benchmark.stats['mean'] < 0.001  # Less than 1ms
```

## Migration Notes

- No breaking changes for users - `from_env()` calls still work
- Internal implementation becomes cleaner and more maintainable
- Field metadata is now actually used instead of being decorative
- Validation happens at parse time, not after object creation
- Emoji sets fields excluded (functionality not implemented in logger)

## Clean Code Benefits After Refactor

1. **Single Source of Truth**: Field definitions contain all metadata (env var name, converter, validator)
2. **DRY Principle**: No duplicate parsing logic across config classes
3. **Type Safety**: Converters ensure correct types at field level
4. **Testability**: Each converter/validator can be tested independently
5. **Maintainability**: Adding a new env var only requires adding a field definition
6. **Consistency**: All configs use the same loading mechanism
7. **Clean Architecture**: Only implemented features are exposed in config