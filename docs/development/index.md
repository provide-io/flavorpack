# Development Guide

Contribute to FlavorPack by developing new features, fixing bugs, or improving documentation.

## Getting Started

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/provide-io/flavorpack.git
cd flavorpack

# Set up environment
uv sync

# Build helpers (Go and Rust)
make build-helpers

# Run tests
make test
```

## Development Topics

### :material-book-open: **Contributing**

Learn how to contribute to FlavorPack.

**[Contributing Guide →](contributing/)**

- Code of conduct
- Development workflow
- Pull request process
- Code style guidelines

### :material-sitemap: **Architecture**

Understand FlavorPack's architecture.

**[Architecture Guide →](architecture/)**

- System design
- Component interaction
- Data flow
- Design decisions

### :material-hammer: **Building Helpers**

Develop and build native helpers.

**[Building Helpers →](helpers/)**

- Go helper development
- Rust helper development
- Cross-compilation
- Testing helpers

### :material-test-tube: **Testing**

Write and run tests.

**[Testing Guide →](testing/index/)**

- Unit tests
- Integration tests
- Cross-language tests
- Test infrastructure

### :material-rocket: **CI/CD**

Understand the CI/CD pipeline.

**[CI/CD Guide →](ci-cd/)**

- GitHub Actions workflows
- Build matrix
- Release process
- Artifact management

### :material-tag: **Release Process**

Learn about releasing new versions.

**[Release Process →](release/)**

- Version management
- Changelog
- Publishing wheels
- GitHub releases

## Development Workflow

```mermaid
graph LR
    FORK[Fork Repository] --> CLONE[Clone Locally]
    CLONE --> BRANCH[Create Branch]
    BRANCH --> DEV[Develop & Test]
    DEV --> COMMIT[Commit Changes]
    COMMIT --> PUSH[Push to Fork]
    PUSH --> PR[Create Pull Request]
    PR --> REVIEW[Code Review]
    REVIEW --> MERGE[Merge]

    classDef start fill:#e8f5e8,stroke:#1b5e20
    classDef process fill:#e1f5fe,stroke:#01579b
    classDef end fill:#f3e5f5,stroke:#4a148c

    class FORK start
    class CLONE,BRANCH,DEV,COMMIT,PUSH,PR,REVIEW process
    class MERGE end
```

## Code Quality

FlavorPack maintains high code quality standards:

### Python Code
```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/flavor
```

### Go Code
```bash
cd src/flavor-go

# Format
gofmt -w .

# Lint
go vet ./...

# Test
go test ./...
```

### Rust Code
```bash
cd src/flavor-rs

# Format
cargo fmt

# Lint
cargo clippy

# Test
cargo test
```

## Community

### Communication Channels

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - Questions and ideas
- **Pull Requests** - Code contributions

### Getting Help

- Read the [Contributing Guide](contributing/)
- Check existing issues and PRs
- Ask in Discussions
- Join community calls (announced in Discussions)

## Next Steps

1. **First contribution?** → Start with [Contributing Guide](contributing/)
2. **Want to understand the code?** → Read [Architecture](architecture/)
3. **Building helpers?** → See [Building Helpers](helpers/)
4. **Writing tests?** → Check [Testing Guide](testing/index/)

---

**Ready to contribute?** Head to the **[Contributing Guide](contributing/)**!
