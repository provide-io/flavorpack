# Flavor Examples

This directory contains practical examples demonstrating how to package Terraform providers using Flavor.

## Available Examples

| Example | Description | Complexity |
|---------|-------------|------------|
| [**simple-provider**](./simple-provider/) | Basic terraform provider with minimal dependencies | 🟢 Beginner |
| [**aws-resources**](./aws-resources/) | Provider with AWS SDK and multiple resources | 🟡 Intermediate |
| [**database-provider**](./database-provider/) | Provider with database connectivity | 🟡 Intermediate |
| [**multi-platform**](./multi-platform/) | CI/CD setup for cross-platform packages | 🔴 Advanced |

## Quick Start

### Simple Provider Example

The simplest example to understand Flavor packaging:

```bash
cd simple-provider
./build.sh              # Build the package
./test.sh              # Run tests
```

This example demonstrates:
- Basic project structure
- Key generation and signing
- Building a Flavor package
- Testing with Terraform

### AWS Resources Provider

A more complex example with external dependencies:

```bash
cd aws-resources
./setup.sh             # Set up environment
# Follow the README for detailed steps
```

This example shows:
- Managing Python dependencies
- Multiple resource implementations
- Complex provider patterns

### Database Provider

Example with database connectivity:

```bash
cd database-provider
docker-compose up -d   # Start test database
./setup.sh            # Set up and build
```

Demonstrates:
- External service dependencies
- Connection management
- Stateful resources

### Multi-Platform CI/CD

GitHub Actions workflow for automated builds:

```bash
cd multi-platform
cat .github/workflows/*.yml
```

Shows:
- Cross-platform builds
- Automated testing
- Release automation

## Example Structure

Each example follows a similar structure:

```
example-name/
├── README.md          # Detailed instructions
├── src/              # Provider source code
├── build.sh          # Build script
├── test.sh           # Test script (if applicable)
└── setup.sh          # Setup script (if needed)
```

## Contributing

Feel free to contribute additional examples! Each example should:
- Include a comprehensive README
- Follow the standard structure
- Include build and test scripts
- Demonstrate specific Flavor features

## Getting Help

- Check individual example READMEs for detailed instructions
- See the main [Flavor documentation](../../README.md)
- Report issues via [GitHub Issues](https://github.com/provide-io/flavor/issues)