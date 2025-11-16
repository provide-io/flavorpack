# JSON Output Implementation Plan for Flavor CLI

## Overview
Implement JSON output format capability for all CLI commands across Python, Go, and Rust implementations to enable programmatic debugging and tool integration.

## Output Format Specification

### Command-Line Interface
```bash
# Output format flag (text or json)
--output-format=json  # or text (default)

# Output destination flag
--output-file=STDOUT                    # stdout only (default)
--output-file=STDERR                    # stderr only  
--output-file=STDOUT,/tmp/output.json   # stdout AND file
--output-file=STDERR,/var/log/app.json  # stderr AND file
```

### JSON Output Structure
```json
{
  "command": "package",
  "timestamp": "2025-01-17T12:00:00Z",
  "success": true,
  "data": {
    // Command-specific output
  },
  "errors": [],
  "warnings": [],
  "metadata": {
    "duration_ms": 1234,
    "version": "1.0.0"
  }
}
```

## Test-Driven Development Plan

### 1. Python Implementation Tests

#### Test File: `tests/test_json_output.py`
```python
# Test markers:
# @pytest.mark.unit - Fast unit tests
# @pytest.mark.cli - CLI integration tests
# @pytest.mark.json - JSON output specific tests

# Test cases:
- test_output_handler_json_format()
- test_output_handler_text_format()
- test_output_handler_stdout_destination()
- test_output_handler_stderr_destination()
- test_output_handler_file_destination()
- test_output_handler_dual_destination()
- test_cli_package_json_output()
- test_cli_verify_json_output()
- test_cli_inspect_json_output()
- test_cli_error_json_format()
- test_json_output_environment_vars()
```

### 2. Go Implementation Tests

#### Test File: `helpers/flavor-go/output_test.go`
```go
// Test functions:
- TestJSONOutputFormat
- TestTextOutputFormat
- TestOutputDestinations
- TestDualOutput
- TestJSONStructure
- TestErrorHandling
- TestCommandLineFlags
```

### 3. Rust Implementation Tests

#### Test File: `helpers/flavor-rs/src/output.rs` (test module)
```rust
#[cfg(test)]
mod tests {
    // Test functions:
    - test_json_output_format
    - test_text_output_format
    - test_output_destinations
    - test_dual_output
    - test_json_structure
    - test_error_handling
    - test_command_line_args
}
```

## Implementation Steps

### Phase 1: Python Core (TDD)
1. **Write failing tests** for `OutputHandler` enhancements
   - Test JSON serialization
   - Test dual output (stream + file)
   - Test error handling
   
2. **Enhance `OutputHandler` class**
   - Parse `--output-file` format: "STREAM[,filepath]"
   - Support dual output streams
   - Implement JSON structure wrapper
   
3. **Wire up to CLI commands**
   - Add `--output-format` and `--output-file` to all commands
   - Use context to pass OutputHandler
   - Modify command output to use handler

### Phase 2: Go Helpers (TDD)
1. **Write failing tests** for output package
2. **Create `output` package**
   ```go
   type OutputHandler struct {
       Format     OutputFormat
       Streams    []io.Writer
       startTime  time.Time
   }
   ```
3. **Integrate with commands**
   - Parse flags in main
   - Pass handler to command functions
   - Convert outputs to use handler

### Phase 3: Rust Helpers (TDD)
1. **Write failing tests** for output module
2. **Create `output` module**
   ```rust
   pub struct OutputHandler {
       format: OutputFormat,
       streams: Vec<Box<dyn Write>>,
       start_time: Instant,
   }
   ```
3. **Integrate with commands**
   - Parse args with clap
   - Pass handler to command functions
   - Convert outputs to use handler

### Phase 4: Integration Testing
1. **Cross-language compatibility tests**
   - Verify JSON schema consistency
   - Test piping between tools
   - Validate error formats

2. **End-to-end workflow tests**
   ```bash
   # Python builds, Rust verifies, output to JSON
   flavor package --output-format=json --output-file=STDOUT,build.json
   taster.psp info --output-format=json | jq '.data.version'
   ```

## File Structure

### Python Files to Modify/Create
- `src/flavor/output.py` - Enhance existing OutputHandler
- `src/flavor/cli.py` - Add global output options
- `src/flavor/commands/*.py` - Update all commands
- `tests/test_json_output.py` - New test file

### Go Files to Create
- `helpers/flavor-go/pkg/output/handler.go`
- `helpers/flavor-go/pkg/output/json.go`
- `helpers/flavor-go/pkg/output/handler_test.go`
- Update all `cmd/*/main.go` files

### Rust Files to Create
- `helpers/flavor-rs/src/output/mod.rs`
- `helpers/flavor-rs/src/output/handler.rs`
- `helpers/flavor-rs/src/output/json.rs`
- Update all binary crates

## Test Markers Strategy

### Python pytest markers
```ini
[pytest]
markers =
    unit: Fast unit tests (no I/O)
    integration: Integration tests (may use filesystem)
    cli: CLI command tests
    json: JSON output specific tests
    cross_language: Tests requiring multiple language implementations
```

### Running specific test suites
```bash
# Run only JSON output tests
pytest -m json

# Run unit tests for JSON
pytest -m "unit and json"

# Run all output tests
pytest tests/test_json_output.py
```

## Success Criteria
1. All tests pass with >90% coverage for output modules
2. JSON output validates against schema
3. Dual output (stream + file) works correctly
4. All three language implementations produce compatible JSON
5. Performance impact <5% for JSON formatting
6. Documentation updated with examples

## Environment Variables
- `FLAVOR_OUTPUT_FORMAT` - Default output format (text/json)
- `FLAVOR_OUTPUT_FILE` - Default output destination
- These can be overridden by command-line flags

## Example Usage
```bash
# JSON to stdout
flavor package --output-format=json

# JSON to stderr and file
flavor verify bundle.psp --output-format=json --output-file=STDERR,/tmp/verify.json

# Using environment variables
export FLAVOR_OUTPUT_FORMAT=json
export FLAVOR_OUTPUT_FILE=STDOUT,/var/log/flavor.json
flavor inspect package.psp  # Uses env defaults
```

## Implementation Timeline
1. **Day 1**: Python TDD tests and core OutputHandler enhancements
2. **Day 2**: Python CLI integration and testing
3. **Day 3**: Go implementation with tests
4. **Day 4**: Rust implementation with tests
5. **Day 5**: Cross-language integration testing and documentation

## Risk Mitigation
- **Backward compatibility**: Default to text output, JSON is opt-in
- **Performance**: Use streaming JSON writers for large outputs
- **Error handling**: Gracefully fallback to text on JSON serialization errors
- **Testing**: Comprehensive test coverage before any production use