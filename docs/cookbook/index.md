# Cookbook

Practical, real-world examples and recipes for packaging applications with Flavorpack.

## What's in the Cookbook?

The cookbook contains two types of content:

### 📚 **Examples**

Complete, working examples of packaging different types of applications. Each example includes full source code, configuration, and step-by-step instructions.

### 🧪 **Recipes**

Short, focused how-to guides for specific integration scenarios and workflows.

## Examples

### :material-console: **CLI Tools**

Package command-line applications and utilities.

**[CLI Tools Example →](examples/cli-tool/)**

Learn how to package:

- Click-based CLI tools
- Argument parsing
- Multi-command applications
- Distribution and installation

### :material-web: **Web Applications**

Package FastAPI, Flask, and other web applications.

**[Web Applications Example →](examples/web-app/)**

Learn how to package:

- FastAPI APIs
- Flask web apps
- Static file handling
- Production deployment

## Recipes

### :material-docker: **Docker Integration**

Use Flavorpack packages in Docker containers.

**[Docker Integration Recipe →](recipes/docker/)**

Learn about:

- Minimal Docker images
- Multi-stage builds
- Volume mounts
- Docker Compose

### :material-pipe: **CI/CD Pipelines**

Automate packaging in CI/CD.

**[CI/CD Pipelines Recipe →](recipes/ci-cd/)**

Learn about:

- GitHub Actions
- GitLab CI
- CircleCI
- Artifact management

## Quick Navigation

### By Application Type

- **CLI Tools** → [CLI Example](examples/cli-tool/)
- **Web APIs** → [Web App Example](examples/web-app/)
- **Terraform Providers** → [Pyvider Integration](../guide/integration/pyvider/)

### By Integration

- **Docker** → [Docker Recipe](recipes/docker/)
- **CI/CD** → [CI/CD Recipe](recipes/ci-cd/)

### By Use Case

- **Development** → [Testing Guide](../development/testing/index/)
- **Production** → [Docker Recipe](recipes/docker/)
- **Distribution** → [CI/CD Recipe](recipes/ci-cd/)

## Contributing Examples

Have a great example or recipe? We'd love to include it!

1. Create your example with complete code
1. Test it thoroughly
1. Submit a pull request
1. Include clear documentation

See [Contributing Guide](../development/contributing/) for details.

## Example Template

Each example follows this structure:

```markdown
# Example Title

## Overview
What this example demonstrates

## Prerequisites
What you need before starting

## Step 1: Create Application
Source code for the application

## Step 2: Configure Packaging
Manifest and configuration files

## Step 3: Build Package
Build commands and output

## Step 4: Test & Deploy
Testing and deployment steps

## Troubleshooting
Common issues and solutions

## Next Steps
Related examples and topics
```

## Need Help?

- 📖 Check the [User Guide](../guide/index/)
- 🔍 Search the documentation
- 💬 Ask in [Community Support](../community/support/)
- 🐛 Report issues on [GitHub](https://github.com/provide-io/flavorpack/issues)

______________________________________________________________________

**Ready to start?** Try the [CLI Tools Example](examples/cli-tool/) or [Web Applications Example](examples/web-app/).
