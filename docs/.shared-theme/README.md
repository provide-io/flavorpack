# Provide.io Shared Theme

This directory contains the shared MkDocs Material theme used across all provide.io documentation. Inspired by FastAPI's excellent documentation system.

## Quick Start

To use the shared theme in your project's `mkdocs.yml`:

```yaml
theme:
  name: material
  # ... other theme config ...

extra_css:
  - ../../provide-foundry/shared-theme/stylesheets/provide-theme.css
  - ../../provide-foundry/shared-theme/stylesheets/termynal.css

extra_javascript:
  - https://unpkg.com/mermaid@10/dist/mermaid.min.js
  - ../../provide-foundry/shared-theme/javascripts/mermaid-init.js
  - ../../provide-foundry/shared-theme/javascripts/termynal.js
  - ../../provide-foundry/shared-theme/javascripts/custom.js

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            show_source: true
            show_root_heading: true
  - macros:
      include_dir: ../../provide-foundry/shared-theme/data
```

## Structure

```
shared-theme/
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
$ plating serve --port 8000
// Starting plating development server...
Server running at http://localhost:8000
Press Ctrl+C to stop

$ plating build
// Building static site...
---> 100%
Build complete! Output: dist/
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

Individual projects can override or extend the shared theme by adding their own CSS after the shared theme:

```yaml
extra_css:
  - ../../provide-foundry/shared-theme/stylesheets/provide-theme.css
  - ../../provide-foundry/shared-theme/stylesheets/termynal.css
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

The shared theme is maintained in the `provide-foundry` repository. Updates to the theme will automatically propagate to all projects using it.

### Updating Projects

After updating the shared theme:

1. Run `make docs-collect` in provide-foundry to refresh aggregated docs
2. Individual projects will pick up changes on next build
3. No action needed for aggregated documentation site

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
