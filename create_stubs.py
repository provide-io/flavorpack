#!/usr/bin/env python3
"""Create stub documentation files for FlavorPack."""

import os
from pathlib import Path

# Base documentation directory
DOCS_DIR = Path("docs")

# Define all documentation files with their titles
STUB_FILES = {
    # Root
    "index.md": "FlavorPack Documentation",
    
    # Getting Started
    "getting-started/index.md": "Getting Started",
    "getting-started/installation.md": "Installation",
    "getting-started/quickstart.md": "Quick Start",
    "getting-started/first-package.md": "Your First Package",
    "getting-started/examples.md": "Examples",
    
    # Guide - Core Concepts
    "guide/index.md": "User Guide",
    "guide/concepts/index.md": "Core Concepts",
    "guide/concepts/pspf-format.md": "PSPF Format",
    "guide/concepts/package-structure.md": "Package Structure",
    "guide/concepts/security.md": "Security Model",
    "guide/concepts/workenv.md": "Work Environments",
    
    # Guide - Creating Packages
    "guide/packaging/index.md": "Creating Packages",
    "guide/packaging/python.md": "Python Applications",
    "guide/packaging/configuration.md": "Package Configuration",
    "guide/packaging/manifest.md": "Manifest Files",
    "guide/packaging/signing.md": "Signing & Verification",
    "guide/packaging/platforms.md": "Platform Support",
    
    # Guide - Using Packages
    "guide/usage/index.md": "Using Packages",
    "guide/usage/running.md": "Running Packages",
    "guide/usage/cli.md": "Command Line Interface",
    "guide/usage/inspection.md": "Extracting & Inspecting",
    "guide/usage/cache.md": "Cache Management",
    "guide/usage/environment.md": "Environment Variables",
    
    # Guide - Advanced Topics
    "guide/advanced/index.md": "Advanced Topics",
    "guide/advanced/cross-language.md": "Cross-Language Support",
    "guide/advanced/launchers.md": "Custom Launchers",
    "guide/advanced/builders.md": "Builder Selection",
    "guide/advanced/performance.md": "Performance Optimization",
    "guide/advanced/debugging.md": "Debugging",
    
    # API Reference
    "api/index.md": "API Reference",
    
    # Python API
    "api/python/index.md": "Python API",
    "api/python/api.md": "Core API",
    "api/python/cli.md": "CLI",
    
    # Python API - Packaging
    "api/python/packaging/index.md": "Packaging",
    "api/python/packaging/orchestrator.md": "Orchestrator",
    "api/python/packaging/python_packager.md": "Python Packager",
    "api/python/packaging/keys.md": "Keys",
    
    # Python API - PSP Format
    "api/python/psp/index.md": "PSPF Format",
    "api/python/psp/builder.md": "Builder",
    "api/python/psp/reader.md": "Reader",
    "api/python/psp/launcher.md": "Launcher",
    "api/python/psp/crypto.md": "Crypto",
    "api/python/psp/metadata.md": "Metadata",
    "api/python/psp/slots.md": "Slots",
    
    # Python API - Utilities
    "api/python/utils/index.md": "Utilities",
    "api/python/utils/platform.md": "Platform",
    "api/python/utils/permissions.md": "Permissions",
    "api/python/utils/archive.md": "Archive",
    
    # Native Components
    "api/native/index.md": "Native Components",
    "api/native/go.md": "Go Ingredients",
    "api/native/rust.md": "Rust Ingredients",
    "api/native/cross-language.md": "Cross-Language API",
    
    # Development
    "development/index.md": "Development",
    "development/contributing.md": "Contributing",
    "development/architecture.md": "Architecture",
    "development/ingredients.md": "Building Ingredients",
    "development/testing/index.md": "Testing",
    "development/testing/unit.md": "Unit Tests",
    "development/testing/integration.md": "Integration Tests",
    "development/testing/cross-language.md": "Cross-Language Tests",
    "development/ci-cd.md": "CI/CD",
    "development/release.md": "Release Process",
    
    # PSPF Specification
    "spec/index.md": "PSPF Specification",
    "spec/overview.md": "Format Overview",
    "spec/pspf-2025.md": "PSPF 2025 Edition",
    "spec/binary-layout.md": "Binary Layout",
    "spec/metadata.md": "Metadata Format",
    "spec/slots.md": "Slot System",
    "spec/crypto.md": "Cryptography",
    "spec/feps/index.md": "FEPs (Enhancement Proposals)",
    "spec/feps/fep-0001.md": "FEP-0001 Core Specification",
    "spec/feps/fep-0002.md": "FEP-0002 Workenv Management",
    "spec/feps/fep-0003.md": "FEP-0003 Runtime Security",
    "spec/feps/fep-0004.md": "FEP-0004 Staged Payload",
    "spec/feps/fep-0005.md": "FEP-0005 JIT Loading",
    
    # Cookbook
    "cookbook/index.md": "Cookbook",
    "cookbook/recipes/index.md": "Recipes",
    "cookbook/recipes/docker.md": "Docker Integration",
    "cookbook/recipes/ci-cd.md": "CI/CD Pipelines",
    "cookbook/recipes/multi-platform.md": "Multi-Platform Builds",
    "cookbook/recipes/cloud.md": "Cloud Deployment",
    "cookbook/recipes/testing.md": "Testing Strategies",
    "cookbook/examples/index.md": "Examples",
    "cookbook/examples/cli-tool.md": "CLI Tools",
    "cookbook/examples/web-app.md": "Web Applications",
    "cookbook/examples/data-pipeline.md": "Data Pipelines",
    "cookbook/examples/microservices.md": "Microservices",
    "cookbook/examples/ml-models.md": "Machine Learning",
    
    # Troubleshooting
    "troubleshooting/index.md": "Troubleshooting",
    "troubleshooting/common.md": "Common Issues",
    "troubleshooting/platforms/index.md": "Platform-Specific",
    "troubleshooting/platforms/macos.md": "macOS",
    "troubleshooting/platforms/linux.md": "Linux",
    "troubleshooting/platforms/windows.md": "Windows",
    "troubleshooting/errors.md": "Error Messages",
    "troubleshooting/faq.md": "FAQ",
    
    # Community
    "community/index.md": "Community",
    "community/support.md": "Support",
    "community/discussions.md": "Discussions",
    "community/blog.md": "Blog",
}

def create_stub_content(title: str, file_path: str) -> str:
    """Generate stub content for a documentation file."""
    
    # Determine the type of documentation based on path
    if "api/" in file_path:
        doc_type = "API reference"
    elif "guide/" in file_path:
        doc_type = "guide"
    elif "spec/" in file_path:
        doc_type = "specification"
    elif "cookbook/" in file_path:
        doc_type = "cookbook entry"
    elif "troubleshooting/" in file_path:
        doc_type = "troubleshooting guide"
    else:
        doc_type = "documentation"
    
    # Get section name for context
    parts = file_path.split("/")
    section = parts[0] if len(parts) > 1 else "main"
    
    content = f"""# {title}

!!! info "Documentation in Development"
    This {doc_type} is currently being developed. Content will be added soon.

## Overview

This page will provide comprehensive information about {title.lower()}.

"""
    
    # Add section-specific content
    if "api/" in file_path:
        content += """## API Documentation

This section will contain detailed API reference documentation.

### Classes

_Documentation coming soon_

### Functions

_Documentation coming soon_

### Examples

_Code examples coming soon_

"""
    elif "guide/" in file_path:
        content += """## In This Guide

- Understanding the concepts
- Step-by-step instructions
- Best practices
- Common patterns

## Prerequisites

_Prerequisites will be listed here_

## Getting Started

_Getting started content coming soon_

"""
    elif "cookbook/" in file_path:
        content += """## What You'll Learn

- Key concepts
- Implementation steps
- Code examples
- Best practices

## Prerequisites

_Prerequisites will be listed here_

## Implementation

_Step-by-step implementation coming soon_

"""
    elif "spec/" in file_path:
        content += """## Specification Details

_Technical specification content coming soon_

## Requirements

_Requirements will be listed here_

## Implementation Notes

_Implementation notes coming soon_

"""
    
    # Add related documentation links
    content += """## Related Documentation

"""
    
    # Add contextual related links
    if "getting-started" in file_path:
        content += """- [User Guide](../guide/index.md)
- [API Reference](../api/index.md)
- [Examples](../cookbook/examples/index.md)
"""
    elif "guide" in file_path:
        content += """- [Getting Started](../getting-started/index.md)
- [API Reference](../api/index.md)
- [Troubleshooting](../troubleshooting/index.md)
"""
    elif "api" in file_path:
        content += """- [User Guide](../guide/index.md)
- [Examples](../cookbook/examples/index.md)
- [Development](../development/index.md)
"""
    else:
        content += """- [Getting Started](../getting-started/index.md)
- [User Guide](../guide/index.md)
- [API Reference](../api/index.md)
"""
    
    # Add next steps
    content += """
## Next Steps

- Explore related documentation
- Try the examples
- Join the community discussions
"""
    
    return content

def main():
    """Create all stub documentation files."""
    created_count = 0
    skipped_count = 0
    
    for file_path, title in STUB_FILES.items():
        full_path = DOCS_DIR / file_path
        
        # Skip if file already exists
        if full_path.exists():
            print(f"Skipping existing file: {file_path}")
            skipped_count += 1
            continue
        
        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate and write content
        content = create_stub_content(title, file_path)
        full_path.write_text(content)
        print(f"Created: {file_path}")
        created_count += 1
    
    print(f"\n✅ Created {created_count} stub files")
    if skipped_count > 0:
        print(f"ℹ️  Skipped {skipped_count} existing files")

if __name__ == "__main__":
    main()