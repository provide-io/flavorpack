# Shared Theme Developer Guide

This guide is for developers working on the shared theme system itself. If you're just using the theme in a project, see [README.md](README.md) instead.

## Architecture

### Namespace Package Distribution

The shared theme is distributed as a **Python namespace package** at `provide.foundry.theme`. Theme files are accessed directly from the installed package, eliminating the need for file synchronization or copying. During development, `uv pip install -e .` provides immediate access to theme changes.

### File Structure

```
provide-foundry/
├── src/
│   └── provide/
│       └── foundry/
│           └── theme/              # Namespace package (source of truth)
│               ├── __init__.py     # Exposes THEME_DIR
│               ├── stylesheets/
│               │   ├── provide-theme.css  # Main theme styles
│               │   └── termynal.css       # Terminal simulator
│               ├── javascripts/
│               │   ├── mermaid-init.js    # Mermaid diagram config
│               │   ├── termynal.js        # Terminal animation engine
│               │   └── custom.js          # Termynal integration
│               ├── data/           # YAML data for macros plugin
│               │   ├── contributors.yml
│               │   ├── external_links.yml
│               │   ├── people.yml
│               │   └── sponsors.yml
│               ├── assets/         # Images, logos, etc.
│               ├── README.md       # User documentation
│               └── DEVELOPER_GUIDE.md  # This file
└── pyproject.toml                 # Package configuration

projects/
├── plating/
│   ├── mkdocs.yml                 # Inherits from base-mkdocs.yml
│   └── docs/                      # Project documentation
├── wrknv/
│   ├── mkdocs.yml                 # Inherits from base-mkdocs.yml
│   └── docs/                      # Project documentation
└── ... (10 more projects)
```

### How It Works

1. **Installation**: `uv pip install -e /path/to/provide-foundry` installs theme as editable package
2. **Access**: Python code imports `from provide.foundry.theme import THEME_DIR`
3. **Resolution**: `THEME_DIR` points to the actual theme directory in the installed package
4. **Configuration**: Projects inherit from `base-mkdocs.yml` which already configures theme paths
5. **Updates**: Changes to theme files are immediately available to all projects (editable install)

### Namespace Package Implementation

**File**: `src/provide/foundry/theme/__init__.py`

```python
"""Shared theme for provide.io documentation."""

from pathlib import Path

# Expose the theme directory for MkDocs configuration
THEME_DIR = Path(__file__).parent

__all__ = ["THEME_DIR"]
```

This simple implementation allows projects to reference the theme directory without hardcoding paths.

## Development Workflow

### Setting Up for Development

```bash
# Clone provide-foundry
cd /path/to/provide-foundry

# Install in editable mode
uv pip install -e .

# Verify installation
python -c "from provide.foundry.theme import THEME_DIR; print(THEME_DIR)"
```

### Making Changes to Theme Files

With an editable install, changes are immediately available to all projects:

```bash
# Edit theme files
vim src/provide/foundry/theme/stylesheets/provide-theme.css

# Changes are IMMEDIATELY available to all projects
# No sync, no copy, no distribution step needed

# Test in provide-foundry
cd /path/to/provide-foundry
mkdocs serve

# Test in any project
cd /path/to/plating
mkdocs serve  # Already sees your changes!
```

### Project Configuration

Projects reference the theme by inheriting from `base-mkdocs.yml`:

**Example project mkdocs.yml**:
```yaml
INHERIT: ../provide-foundry/base-mkdocs.yml

site_name: My Project
site_description: My project documentation

# All theme configuration is inherited
# No need to specify extra_css, extra_javascript, etc.
```

**Base configuration** (`base-mkdocs.yml`):
```yaml
extra_css:
  - !relative $THEME_DIR/stylesheets/provide-theme.css
  - !relative $THEME_DIR/stylesheets/termynal.css

extra_javascript:
  - !relative $THEME_DIR/javascripts/mermaid-init.js
  - !relative $THEME_DIR/javascripts/termynal.js
  - !relative $THEME_DIR/javascripts/custom.js

plugins:
  - macros:
      include_dir: !relative $THEME_DIR/data
```

The `!relative` tag and `$THEME_DIR` variable are resolved by the configuration system to point to the installed theme package.

## Modifying Theme Files

### CSS Changes

**File**: `src/provide/foundry/theme/stylesheets/provide-theme.css`

**Structure**:
```css
/* Typography */
h1, h2, h3 { font-family: 'Chakra Petch', sans-serif; }

/* Interactive Elements */
.md-typeset a:hover { /* hover styles */ }

/* Layout Components */
.feature-grid { /* grid layout */ }

/* Terminal Simulator */
.termy { /* terminal styling */ }
```

**After making changes**:
```bash
# Changes are immediately available
# Just refresh your browser (Cmd+Shift+R to clear cache)

# Test in provide-foundry
cd /path/to/provide-foundry
mkdocs serve

# Test in a project
cd /path/to/plating
mkdocs serve
```

### JavaScript Changes

**Files**:
- `javascripts/termynal.js` - Terminal animation engine (forked from FastAPI)
- `javascripts/custom.js` - Integration code
- `javascripts/mermaid-init.js` - Mermaid configuration

**Custom.js Integration**:
```javascript
// Initialize Termynal on page load
document.addEventListener('DOMContentLoaded', function() {
  const termyElements = document.querySelectorAll('.termy');
  termyElements.forEach(element => {
    new Termynal(element, {
      // Configuration options
    });
  });
});
```

**Testing JavaScript Changes**:
1. Edit the file in `src/provide/foundry/theme/javascripts/`
2. Test with `mkdocs serve` in provide-foundry or any project
3. Open browser console to check for errors
4. Test terminal animations on actual documentation pages
5. Changes are immediately available (editable install)

### Data Files

**Location**: `src/provide/foundry/theme/data/*.yml`

**Purpose**: Provide dynamic content via mkdocs-macros plugin

**Example** (`contributors.yml`):
```yaml
contributors:
  - name: "Developer Name"
    github: "username"
    contributions: 42
    avatar: "https://github.com/username.png"
```

**Usage in Markdown**:
```markdown
## Contributors

{% for contributor in contributors %}
- ![{{ contributor.name }}]({{ contributor.avatar }})
  [{{ contributor.name }}](https://github.com/{{ contributor.github }})
  - {{ contributor.contributions }} contributions
{% endfor %}
```

## Testing Workflow

### 1. Local Testing (provide-foundry)

```bash
cd /path/to/provide-foundry

# Edit theme files
vim src/provide/foundry/theme/stylesheets/provide-theme.css

# Test immediately (changes already available)
mkdocs serve
# Open http://127.0.0.1:11000

# Check browser console for errors
# Verify visual changes
```

### 2. Single Project Testing

```bash
# Changes are already available to all projects
# Just test in any project

cd /path/to/plating
mkdocs serve
# Open http://127.0.0.1:8009

# No sync needed - editable install makes changes immediate
```

### 3. Multi-Project Verification

```bash
# Spot-check multiple projects to ensure compatibility
cd /path/to/wrknv && mkdocs serve
cd /path/to/pyvider && mkdocs serve
cd /path/to/flavorpack && mkdocs serve
```

### 4. Build Verification

```bash
# Test that all projects build successfully
cd /path/to/provide-io
for project in */mkdocs.yml; do
  echo "Building $(dirname $project)..."
  cd $(dirname $project)
  mkdocs build --strict || echo "FAILED: $project"
  cd ..
done
```

## Terminal Simulator (Termynal)

### How It Works

**Source**: Forked from FastAPI's implementation (originally by Ines Montani)

**Process**:
1. Finds all `.termy` divs in the page
2. Parses the console code block inside
3. Identifies command lines (start with `$`)
4. Identifies comments (start with `//`)
5. Identifies progress bars (`---> 100%`)
6. Animates typing for commands
7. Shows output instantly
8. Provides restart and fast-forward controls

**Syntax**:
```console
$ command to type          # Animated input
// Comment text            # Shows with emoji
---> 100%                  # Animated progress bar
Regular output             # Shown instantly
```

### Customizing Terminal Behavior

**File**: `src/provide/foundry/theme/javascripts/custom.js`

**Configuration Options**:
```javascript
new Termynal(element, {
  prefix: '$',           // Command prompt
  startDelay: 600,       // Initial delay (ms)
  typeDelay: 90,         // Typing speed (ms per char)
  lineDelay: 1500,       // Delay between lines (ms)
  progressLength: 40,    // Progress bar length
  progressChar: '█',     // Progress bar character
  cursor: '▋',           // Cursor character
  noInit: false          // Manual initialization
});
```

### Adding New Line Types

To add a new line type (like comments `//`):

1. **Update Termynal.js**:
```javascript
// In the render method
if (line.startsWith('// ')) {
  return this.renderComment(line.substring(3));
}

// Add render method
renderComment(text) {
  const div = document.createElement('div');
  div.className = 'termynal-comment';
  div.textContent = `💬 ${text}`;
  return div;
}
```

2. **Update CSS** (`termynal.css`):
```css
.termynal-comment {
  color: #6c757d;
  font-style: italic;
}
```

3. **Test changes**:
```bash
# Changes are immediately available via editable install
mkdocs serve  # Test locally
```

## Design System

### Typography

The theme uses **Chakra Petch** for headings and **Inter** for body text:

```css
/* Headings - Chakra Petch */
h1, h2, h3, h4, h5, h6 {
  font-family: 'Chakra Petch', sans-serif;
  font-weight: 600;
}

/* Body - Inter */
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Code - JetBrains Mono */
code, pre {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
```

### Color Palette

```css
/* Primary Colors */
--md-primary-fg-color: #00a8ff;        /* provide.io blue */
--md-primary-fg-color--light: #33b9ff;
--md-primary-fg-color--dark: #0087cc;

/* Accent Colors */
--md-accent-fg-color: #7c4dff;         /* Purple accents */
--md-accent-fg-color--light: #9b6dff;

/* Semantic Colors */
--md-success-fg-color: #00c851;        /* Success/Green */
--md-warning-fg-color: #ffbb33;        /* Warning/Orange */
--md-error-fg-color: #ff4444;          /* Error/Red */
```

### Spacing System

The theme uses a consistent 8px-based spacing scale:

```css
--spacing-xs: 0.25rem;   /* 4px */
--spacing-sm: 0.5rem;    /* 8px */
--spacing-md: 1rem;      /* 16px */
--spacing-lg: 1.5rem;    /* 24px */
--spacing-xl: 2rem;      /* 32px */
--spacing-2xl: 3rem;     /* 48px */
```

### Interactive Elements

```css
/* Links */
.md-typeset a {
  color: var(--md-primary-fg-color);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s ease;
}

.md-typeset a:hover {
  border-bottom-color: var(--md-primary-fg-color);
}

/* Buttons */
.md-button {
  padding: 0.5rem 1.5rem;
  border-radius: 4px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.md-button--primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 168, 255, 0.3);
}
```

## Common Issues & Solutions

### Issue: Theme not found

**Symptom**: `ModuleNotFoundError: No module named 'provide.foundry.theme'`

**Cause**: Package not installed or not installed in editable mode

**Solution**:
```bash
# Install in editable mode
cd /path/to/provide-foundry
uv pip install -e .

# Verify installation
python -c "from provide.foundry.theme import THEME_DIR; print(THEME_DIR)"
```

### Issue: Changes not appearing

**Symptom**: Made changes to theme but they don't show up

**Cause**: Browser cache or server not reloaded

**Solution**:
```bash
# Clear browser cache (Cmd+Shift+R / Ctrl+F5)

# Restart mkdocs serve if needed
# Ctrl+C to stop
mkdocs serve
```

### Issue: Terminal animations not working

**Symptom**: Terminal blocks show as static code blocks

**Possible Causes**:
1. Missing `.termy` wrapper div
2. JavaScript not loaded
3. Console errors in browser

**Debug Steps**:
```bash
# 1. Check theme is installed
python -c "from provide.foundry.theme import THEME_DIR; print(THEME_DIR)"

# 2. Check JavaScript files exist
ls $(python -c "from provide.foundry.theme import THEME_DIR; print(THEME_DIR)")/javascripts/

# 3. Check browser console
# Open DevTools → Console → Look for errors

# 4. Verify HTML structure
# View source → Search for "termy" class
```

### Issue: Path resolution errors

**Symptom**: `FileNotFoundError` or 404 for theme files

**Cause**: Project not inheriting from `base-mkdocs.yml` correctly

**Solution**:
```yaml
# In project mkdocs.yml
INHERIT: ../provide-foundry/base-mkdocs.yml

# Make sure the relative path is correct
# Adjust based on your project's location relative to provide-foundry
```

## Package Development

### Adding New Theme Files

```bash
# Add new file to theme package
cd /path/to/provide-foundry
touch src/provide/foundry/theme/stylesheets/new-component.css

# File is immediately available (editable install)
# Reference it in base-mkdocs.yml if needed
```

### Updating Package Metadata

**File**: `pyproject.toml`

```toml
[project]
name = "provide-foundry"
version = "0.1.0"
description = "Documentation hub for provide.io ecosystem"

[tool.uv]
package = true

# Theme package is automatically included via src layout
```

### Testing Package Installation

```bash
# Test clean install (in isolated environment)
uv venv .test-venv
source .test-venv/bin/activate
uv add /path/to/provide-foundry

# Verify theme is accessible
python -c "from provide.foundry.theme import THEME_DIR; print(THEME_DIR)"

# Deactivate and cleanup
deactivate
rm -rf .test-venv
```

## Contributing

When contributing to the shared theme:

1. **Install in editable mode** for development
2. **Test in provide-foundry** first
3. **Test in multiple projects** to ensure compatibility
4. **Check all projects build** with `mkdocs build --strict`
5. **Document breaking changes** in commit message
6. **Update this guide** if adding new features

### Commit Guidelines

```bash
# Good commit messages for theme changes
git commit -m "Update terminal simulator colors for better contrast"
git commit -m "Add support for custom progress bar characters"
git commit -m "Fix responsive layout for mobile devices"

# Include projects affected if breaking change
git commit -m "Update CSS class names (affects all projects)"
```

## Questions?

- Review the main [README.md](README.md) for user documentation
- Review commit history for past changes
- Ask in the provide.io discussion forum

---

**Maintained by**: provide.io team
**Last Updated**: 2025-10-31
**Related**: [README.md](README.md)
