# FlavorPack Documentation

This directory contains the source for FlavorPack's documentation, built with MkDocs and the Material theme.

## Building Documentation

### Prerequisites

Install documentation dependencies:

```bash
# Using the docs dependency group
uv pip install --group docs

# Or install individually
uv pip install mkdocs mkdocs-material "mkdocstrings[python]"
```

### Local Development

Start the development server:

```bash
mkdocs serve
```

The documentation will be available at http://localhost:8000 with live reload.

### Building for Production

Build the static site:

```bash
mkdocs build
```

The built documentation will be in the `site/` directory.

## Documentation Structure

- `index.md` - Main landing page
- `getting-started/` - Installation and quick start guides
- `guide/` - User guide with concepts and tutorials
- `api/` - API reference (auto-generated)
- `spec/` - PSPF specification and FEPs
- `cookbook/` - Recipes and examples
- `troubleshooting/` - Common issues and solutions

## Auto-Generated Content

API documentation is automatically generated from Python docstrings using mkdocstrings. The generation script is in `gen_ref_pages.py`.

## Styling

Custom styles are in `stylesheets/extra.css`, following the provide.io design language with a minimalist, professional aesthetic.

## Contributing

When adding new documentation:

1. Follow the existing structure and naming conventions
2. Use Google-style docstrings for API documentation
3. Add navigation entries to `mkdocs.yml`
4. Test locally with `mkdocs serve` before committing