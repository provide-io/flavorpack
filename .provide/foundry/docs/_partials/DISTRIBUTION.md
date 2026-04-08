# Documentation Partials Distribution

## Overview

Documentation partials are shared snippets that are **packaged with provide-foundry** and distributed to all projects that use it.

## How It Works

### 1. Source Location

Partials are stored in the provide-foundry package:
```
provide-foundry/
└── src/
    └── provide/
        └── foundry/
            └── docs/
                └── _partials/
                    ├── README.md
                    ├── python-requirements.md
                    ├── uv-installation.md
                    ├── python-version-setup.md
                    ├── virtual-env-setup.md
                    ├── platform-specific-macos.md
                    └── troubleshooting-common.md
```

### 2. Package Distribution

The partials are included in the provide-foundry wheel package via `pyproject.toml`:

```toml
[tool.setuptools.package-data]
"provide.foundry.docs" = [
    "*.py",
    "_partials/*.md",
]
```

### 3. Extraction to Projects

When building documentation, projects run:

```bash
we run docs.setup
```

Which executes:

```python
from provide.foundry.config import extract_base_mkdocs
from pathlib import Path

extract_base_mkdocs(Path('.'))
```

This extracts to `.provide/foundry/docs/_partials/`:

```
your-project/
└── .provide/
    └── foundry/
        ├── base-mkdocs.yml
        ├── theme/
        └── docs/
            └── _partials/      # Partials extracted here
                ├── python-requirements.md
                ├── uv-installation.md
                └── ...
```

### 4. Usage in Documentation

Projects reference partials using the local path:

```markdown
## Installation

--8<-- ".provide/foundry/docs/_partials/uv-installation.md"
```

## Benefits

✅ **Works in All Scenarios:**
- Monorepo builds (provide-foundry)
- Standalone project builds
- Installed packages
- Development environments

✅ **Single Source of Truth:**
- Update once in provide-foundry
- All projects get updated partials on next extraction

✅ **Automatic Distribution:**
- No manual copying needed
- Packaged with provide-foundry
- Extracted on-demand

## Development Workflow

### Adding a New Partial

1. Create in package source:
   ```bash
   vim provide-foundry/src/provide/foundry/docs/_partials/new-partial.md
   ```

2. Add to package-data (already configured for `*.md`)

3. The partial will be automatically:
   - Packaged with provide-foundry
   - Extracted when projects run `we run docs.setup`
   - Available at `.provide/foundry/docs/_partials/new-partial.md`

### Updating Existing Partials

1. Edit in package source:
   ```bash
   vim provide-foundry/src/provide/foundry/docs/_partials/existing-partial.md
   ```

2. Projects update partials by running:
   ```bash
   we run docs.setup  # Re-extracts latest partials
   ```

## File Locations Summary

| Context | Location |
|---------|----------|
| **Source** (for editing) | `provide-foundry/src/provide/foundry/docs/_partials/` |
| **Packaged** (in wheel) | `provide/foundry/docs/_partials/` (inside package) |
| **Extracted** (in projects) | `.provide/foundry/docs/_partials/` |
| **Referenced** (in docs) | `--8<-- ".provide/foundry/docs/_partials/...md"` |

## Synchronization

The `.provide/` directory is:
- **Gitignored** - Not tracked in version control
- **Ephemeral** - Generated/extracted as needed
- **Project-local** - Each project has its own copy

To update:
```bash
# In any project
we run docs.setup
```

This ensures all projects use the latest partials from their installed provide-foundry version.
