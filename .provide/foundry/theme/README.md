# Provide.io Shared Theme

This directory contains the shared MkDocs Material theme used across all provide.io documentation. Inspired by FastAPI's excellent documentation system.

## Quick Start

The shared theme is distributed as a **Python namespace package**. Theme files are accessed directly from the `provide.foundry.theme` package installed in editable mode.

### Step 1: Install provide-foundry Package

```bash
cd provide-foundry
uv pip install -e .
```

### Step 2: Use Shared Base Configuration

The simplest approach is to inherit from `base-mkdocs.yml`, which already includes theme configuration:

```yaml
# your-project/mkdocs.yml
INHERIT: ../provide-foundry/base-mkdocs.yml

# Project-specific configuration
site_name: Your Project Documentation
site_url: https://foundry.provide.io/your-project/
```

### Step 3: Custom Configuration (Advanced)

If you need custom theme setup without inheriting base-mkdocs.yml:

```python
# your-project/docs/scripts/get_theme_dir.py
from provide.foundry.theme import THEME_DIR

# Use THEME_DIR in your build scripts
```

```yaml
# your-project/mkdocs.yml
theme:
  name: material
  # ... other theme config ...

extra_css:
  - !relative $THEME_DIR/stylesheets/provide-theme.css
  - !relative $THEME_DIR/stylesheets/termynal.css

extra_javascript:
  - https://unpkg.com/mermaid@10/dist/mermaid.min.js
  - !relative $THEME_DIR/javascripts/mermaid-init.js
  - !relative $THEME_DIR/javascripts/termynal.js
  - !relative $THEME_DIR/javascripts/custom.js
```

## Structure

```
src/provide/foundry/theme/
├── __init__.py               # Exposes THEME_DIR constant
├── stylesheets/
│   ├── provide-theme.css     # Main theme CSS
│   └── termynal.css          # Terminal simulator styles
├── javascripts/
│   ├── mermaid-init.js       # Mermaid diagram initialization
│   ├── termynal.js           # Terminal simulator
│   └── custom.js             # Custom behaviors (termynal integration)
├── data/                     # YAML data files for mkdocs-macros
│   ├── contributors.yml
│   ├── sponsors.yml
│   ├── external_links.yml
│   └── people.yml
├── assets/                   # Shared assets (logos, images)
└── README.md                 # This file
```

## Features

### Typography
- **Headers (H1-H3)**: Chakra Petch font family (bold, professional)
- **Smaller headers (H4-H6)**: IBM Plex Serif
- **Body text**: System font stack for optimal readability
- **Code**: Monospace font stack (SF Mono, Menlo, Monaco, Consolas)

### Terminal Simulator (Termynal)

Animated terminal demonstrations for CLI tools. Perfect for plating, tofusoup, wrknv, supsrc, and other CLI projects.

**Usage in Markdown:**

````markdown
<div class="termy">

```console
$ we run docs.serve
// Starting documentation server...
Server running at http://localhost:11000
Press Ctrl+C to stop

$ we run docs.build
// Building documentation site...
---> 100%
Build complete! Output: site/
```

</div>
````

**Syntax:**
- Lines starting with `$` are animated as typed input
- Lines starting with `// ` are shown as comments with 💬 emoji
- `---> 100%` shows an animated progress bar
- Other lines are shown as output
- Includes "fast →" and "restart ↻" controls

**Custom prompts:**

```console
# venv $ source .venv/bin/activate
# (venv) $ python main.py
```

### Interactive Elements
- Smooth hover transitions on all links and navigation
- Fade-in permalink anchors on header hover
- Accent color highlights for hover states
- Terminal animations with restart/fast-forward controls

### Layout Components
- `.feature-grid` - Responsive grid for feature cards
- `.feature-card` - Individual feature card with hover effects
- `.getting-started-grid` - Getting started section layout
- `.getting-started-card` - Getting started card with CTA button

### Spacing & Rhythm
- Professional header spacing (2.5rem, 2rem, 1.75rem for H1-H3)
- Optimal paragraph line-height (1.7)
- Consistent list and code block spacing

### MkDocs Macros Integration

Use YAML data files to separate content from data:

**In your markdown:**

```markdown
## Contributors

{% for contributor in contributors %}
- [{{ contributor.name }}](https://github.com/{{ contributor.github }})
{% endfor %}
```

**Data files available:**
- `contributors.yml` - Project contributors
- `sponsors.yml` - Project sponsors
- `external_links.yml` - External resources
- `people.yml` - Team members and roles

## Customization

Individual projects can override or extend the shared theme by adding their own CSS:

```yaml
extra_css:
  - !relative $THEME_DIR/stylesheets/provide-theme.css
  - !relative $THEME_DIR/stylesheets/termynal.css
  - stylesheets/project-specific.css  # Project overrides
```

## Terminal Simulator Examples

### Basic CLI Demo

```markdown
<div class="termy">

```console
$ wrknv init my-project
// Creating new work environment...
✓ Created my-project/
✓ Initialized configuration
$ cd my-project
$ wrknv status
Environment: my-project
Status: active
```

</div>
```

### With Progress Bar

```markdown
<div class="termy">

```console
$ tofusoup test --all
// Running conformance tests...
---> 100%
All tests passed! 42/42
```

</div>
```

### Multi-step Tutorial

```markdown
<div class="termy">

```console
$ uv sync
// Installing dependencies...
Resolved 24 packages in 1.2s

$ uv run pytest
// Running test suite...
======================== 15 passed in 0.82s ========================

$ uv run python -m my_app
Hello from my_app!
```

</div>
```

## Maintenance

The shared theme is maintained in the `provide-foundry` repository as a namespace package.

### Updating the Theme

After editing theme files in `src/provide/foundry/theme/`:

```bash
cd provide-foundry

# Test changes locally
mkdocs serve

# Changes are immediately available to all projects
# (since they install provide-foundry in editable mode)

# Test a project
cd ../plating
mkdocs serve  # Check http://127.0.0.1:8009
```

### Why Namespace Package?

The namespace package approach provides:
- **Direct access**: No file copying or syncing required
- **Editable installs**: `uv pip install -e .` makes changes immediately available
- **Type safety**: `from provide.foundry.theme import THEME_DIR` is type-checked
- **No gitignore needed**: No generated files in project directories
- **Python-based distribution**: Theme assets managed as a proper Python package

### Adding Dependencies

To use the full shared theme, ensure your project includes:

```toml
[dependency-groups]
docs = [
    "mkdocs>=1.6.0",
    "mkdocs-material>=9.6.0",
    "mkdocstrings[python]>=0.26.0",
    "mkdocs-autorefs>=1.4.0",
    "mkdocs-macros-plugin>=1.4.0",
]
```

Or reference provide-testkit:

```toml
[dependency-groups]
docs = ["provide-testkit[docs]"]
```

## Design Philosophy

- **Professional**: Clean, corporate-appropriate styling
- **Readable**: Optimal typography and spacing
- **Consistent**: Same look across all provide.io docs
- **Accessible**: High contrast, clear hierarchy
- **Interactive**: Smooth transitions, hover states, and animations
- **Engaging**: Terminal demonstrations bring CLI tools to life

## Credits

- Terminal simulator (Termynal) by Ines Montani, adapted from FastAPI
- Theme design inspired by FastAPI's documentation excellence
- Built on Material for MkDocs
