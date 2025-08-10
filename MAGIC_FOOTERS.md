# Magic Footer Standard

All source files in the flavor project must have a "magic footer" consisting of 4 emojis that identify the project and file purpose.

## Format

```
<blank line>
<comment-char> 📦🍜<file-emoji>🪄
```

- **First emoji (📦)**: Represents "package" - the P in Flavor
- **Second emoji (🍜)**: Represents "flavor" - the project name
- **Third emoji**: Represents the file's primary function (see table below)
- **Fourth emoji (🪄)**: Magic marker - indicates this is a magic footer

## File Type Emoji Mapping

| File Type | Emoji | Description | Examples |
|-----------|-------|-------------|----------|
| API/Interface | 🔌 | API endpoints, interfaces | api.py, interface.go |
| CLI | 🖥️ | Command-line interface | cli.py, cmd/*.go |
| Build/Compiler | 🔨 | Build tools, compilation | build.py, compiler.py, build.go |
| Keys/Crypto | 🔑 | Cryptography, signing, verification | keys.py, crypto.rs, verify.go |
| Metadata | 📋 | Metadata handling | metadata.py |
| Exceptions | ⚠️ | Error handling | exceptions.py, errors.go |
| Reader/Parser | 📖 | File reading, parsing | reader.py, parser.go |
| Models/Data | 📊 | Data structures, schemas | models.py, schema.go |
| Packaging | 📦 | Package assembly | orchestrator.py, packager.go |
| Testing | 🧪 | Test files | *_test.py, *_test.go, test_*.py |
| Config | ⚙️ | Configuration | config.py, settings.go |
| Init/Main | 🚀 | Entry points, initialization | __init__.py, main.go, main.rs |
| Default | 📄 | Other files | utils.py, helpers.go |

## Language-Specific Comments

- **Python**: `# 📦🍜<emoji>🪄`
- **Go**: `// 📦🍜<emoji>🪄`
- **Rust**: `// 📦🍜<emoji>🪄`

## Implementation

Use the provided update scripts to automatically add or update magic footers:
- `update_footers.py` - Updates Python files
- `update_go_rust_footers.py` - Updates Go and Rust files

These scripts will:
1. Remove any existing magic footer (identified by the 🪄 emoji)
2. Add the appropriate new footer based on file analysis
3. Ensure consistent formatting with a blank line before the footer

## Examples

```python
# Python file (api.py)
def verify_package(package_path: Path) -> None:
    """Verifies a Flavor package."""
    # ... code ...

# 📦🍜🔌🪄
```

```go
// Go file (main.go)
func main() {
    // ... code ...
}

// 📦🍜🚀🪄
```

```rust
// Rust file (crypto.rs)
pub fn sign_package(data: &[u8]) -> Result<Signature> {
    // ... code ...
}

// 📦🍜🔑🪄
```