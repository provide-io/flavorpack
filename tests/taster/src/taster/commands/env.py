"""Environment variable testing command"""

import os

import click


@click.command("env")
def env_command() -> None:
    """🌍 Test environment variable processing"""
    env_vars = dict(os.environ)

    click.secho("=" * 60, fg="cyan")
    click.secho("🌍 ENVIRONMENT VARIABLE TEST", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.secho(f"📊 Total variables: {len(env_vars)}", fg="yellow")

    # Categorize variables
    categories = {
        "System": ["PATH", "HOME", "USER", "TERM", "SHELL", "PWD"],
        "Locale": [k for k in env_vars if k.startswith("LANG") or k.startswith("LC_")],
        "Flavor": [k for k in env_vars if k.startswith("FLAVOR_")],
        "Taster": [k for k in env_vars if k.startswith("TASTER_")],
        "Keep": [k for k in env_vars if k.startswith("KEEP_")],
        "Terraform": [k for k in env_vars if k.startswith("TF_")],
        "Go": [k for k in env_vars if k.startswith("GO")],
        "Python": [k for k in env_vars if k.startswith("PYTHON") or k.startswith("PY")],
        "Other": [],
    }

    # Find uncategorized
    categorized = set()
    for cat_vars in categories.values():
        if isinstance(cat_vars, list):
            categorized.update(cat_vars)

    for key in env_vars:
        if key not in categorized:
            categories["Other"].append(key)

    # Display categories
    for category, vars in categories.items():
        if vars:
            click.secho(f"\n📁 {category} ({len(vars)} variables):", fg="blue", bold=True)
            for var in sorted(vars)[:5]:
                value = env_vars.get(var, "")
                if len(value) > 50:
                    value = value[:47] + "..."
                click.echo(f"  {var} = {value}")
            if len(vars) > 5:
                click.secho(f"  ... and {len(vars) - 5} more", dim=True)

    # Test expected values from runtime.env
    click.secho("\n" + "=" * 60, fg="cyan")
    click.secho("🔬 RUNTIME.ENV VERIFICATION", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")

    # Check for expected variables set by runtime.env
    expected_vars = {
        "TASTER_MODE": "test",
        "TASTER_VERSION": "1.0.0",
    }

    click.secho("\n📋 Expected Variables (from runtime.env.set):", fg="green")
    for var, expected in expected_vars.items():
        actual = os.environ.get(var)
        if actual == expected:
            click.echo(f"  ✅ {var} = {actual}")
        else:
            click.echo(f"  ❌ {var} = {actual} (expected: {expected})")

    # Check mapped variables
    click.secho("\n🔄 Mapped Variables (from runtime.env.map):", fg="yellow")
    mappings = {
        "OLD_VAR": "NEW_VAR",
    }
    for old, new in mappings.items():
        if old in os.environ:
            click.echo(f"  ⚠️ {old} still exists (should be mapped to {new})")
        if new in os.environ:
            click.echo(f"  ✅ {new} = {os.environ[new]} (mapped from {old})")

    # Test whitelist mode (unset = ["*"] with pass list)
    click.secho("\n🔒 Whitelist Mode Test:", fg="magenta")
    allowed_patterns = [
        "PATH",
        "HOME",
        "USER",
        "TERM",
        "LANG",
        "LC_*",
        "FLAVOR_*",
        "TASTER_*",
        "KEEP_*",
    ]
    click.echo(f"  Allowed patterns: {', '.join(allowed_patterns)}")

    # Check for unexpected variables (ones that should have been removed)
    unexpected = []
    for key in env_vars:
        # Check if this key matches any allowed pattern
        allowed = False
        for pattern in allowed_patterns:
            if pattern.endswith("*"):
                if key.startswith(pattern[:-1]):
                    allowed = True
                    break
            elif key == pattern:
                allowed = True
                break
        if not allowed and key not in ["NEW_VAR", "TASTER_MODE", "TASTER_VERSION"]:
            unexpected.append(key)

    if unexpected:
        click.secho(f"\n  ⚠️ Found {len(unexpected)} unexpected variables:", fg="red")
        for var in unexpected[:5]:
            click.echo(f"    - {var}")
        if len(unexpected) > 5:
            click.echo(f"    ... and {len(unexpected) - 5} more")
    else:
        click.secho("  ✅ No unexpected variables found", fg="green")

    # Show environment source
    click.secho("\n" + "=" * 60, fg="cyan")
    click.secho("📍 ENVIRONMENT SOURCE", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")

    if "FLAVOR_WORKENV" in os.environ:
        click.echo(f"  Work Environment: {os.environ['FLAVOR_WORKENV']}")
    if "FLAVOR_COMMAND_NAME" in os.environ:
        click.echo(f"  Command Name: {os.environ['FLAVOR_COMMAND_NAME']}")
    if "FLAVOR_ORIGINAL_COMMAND" in os.environ:
        click.echo(f"  Original Command: {os.environ['FLAVOR_ORIGINAL_COMMAND']}")
