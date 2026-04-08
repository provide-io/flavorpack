# Documentation Partials

This directory contains reusable documentation snippets that are shared across the provide.io ecosystem.

## Usage

Use the `--8<--` syntax from `pymdownx.snippets` to include partials in your documentation:

```markdown
--8<-- ".provide/foundry/docs/_partials/python-requirements.md"
```

**Note:** Use `.provide/foundry/` prefix - this references the extracted partials.

## Available Partials

### Installation & Setup (7 partials)
- **python-requirements.md** - Python version requirements table
- **uv-installation.md** - Installing the UV package manager
- **python-version-setup.md** - Setting up Python versions with UV
- **virtual-env-setup.md** - Creating and activating virtual environments
- **platform-specific-macos.md** - macOS-specific setup notes
- **troubleshooting-common.md** - Common troubleshooting issues
- **DISTRIBUTION.md** - How the partial distribution system works

### Development (3 partials)
- **testing-setup.md** - Standard pytest commands and options
- **code-quality-setup.md** - Ruff, mypy, bandit commands
- **verification-commands.md** - Post-install verification steps

## Guidelines

- Keep partials focused and single-purpose
- Use clear, descriptive filenames
- Include only content that is truly shared across multiple projects
- Project-specific content belongs in the project's own docs
- Use `{{PLACEHOLDER}}` syntax for values that should be customized per-project
