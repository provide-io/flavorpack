#!/usr/bin/env python3
"""Taster CLI - Comprehensive test commands for flavor packages"""

import os
import sys
import json
import platform
import subprocess
from pathlib import Path
import click


@click.group()
@click.version_option("1.0.0")
def cli():
    """🍯 Taster - Test package for flavor functionality"""
    pass


@cli.command()
def env():
    """🌍 Test environment variable processing"""
    env_vars = dict(os.environ)
    
    click.secho("=" * 60, fg='cyan')
    click.secho("🌍 ENVIRONMENT VARIABLE TEST", fg='cyan', bold=True)
    click.secho("=" * 60, fg='cyan')
    click.secho(f"📊 Total variables: {len(env_vars)}", fg='yellow')
    
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
        "Other": []
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
            click.secho(f"\n📁 {category} ({len(vars)} variables):", fg='blue', bold=True)
            for var in sorted(vars)[:5]:
                value = env_vars.get(var, "")
                if len(value) > 50:
                    value = value[:47] + "..."
                click.echo(f"  {var} = {value}")
            if len(vars) > 5:
                click.secho(f"  ... and {len(vars) - 5} more", dim=True)
    
    # Test expected values from runtime.env
    click.secho("\n" + "=" * 60, fg='cyan')
    click.secho("🔬 RUNTIME.ENV VERIFICATION", fg='cyan', bold=True)
    click.secho("=" * 60, fg='cyan')
    
    tests = [
        ("TASTER_MODE", "test", "Set operation"),
        ("TASTER_VERSION", "1.0.0", "Set operation"),
        ("NEW_VAR", None, "Map operation (if OLD_VAR was set)"),
        ("FLAVOR_WORKENV", None, "Launcher-provided"),
        ("FLAVOR_COMMAND_NAME", None, "Launcher-provided"),
    ]
    
    for var, expected, description in tests:
        actual = env_vars.get(var)
        if expected:
            if actual == expected:
                click.secho(f"✅ {var}: '{actual}' ({description})", fg='green')
            else:
                click.secho(f"❌ {var}: expected '{expected}', got '{actual}' ({description})", fg='red')
        else:
            if actual:
                click.secho(f"✅ {var}: '{actual}' ({description})", fg='green')
            else:
                click.secho(f"⚠️  {var}: not set ({description})", fg='yellow')
    
    # Check for variables that shouldn't exist (testing unset = ["*"])
    click.secho("\n" + "=" * 60, fg='cyan')
    click.secho("🛡️ WHITELIST TEST (unset = ['*'])", fg='cyan', bold=True)
    click.secho("=" * 60, fg='cyan')
    
    unexpected = []
    for key in env_vars:
        # These shouldn't exist if whitelist is working
        if key.startswith("DEBUG_") or key.startswith("TEMP_") or key.startswith("TEST_"):
            if not key.startswith("TASTER_"):
                unexpected.append(key)
    
    if unexpected:
        click.secho(f"❌ Found {len(unexpected)} unexpected variables:", fg='red')
        for var in unexpected[:10]:
            click.echo(f"  - {var}")
    else:
        click.secho("✅ No unexpected variables (whitelist working correctly)", fg='green', bold=True)


@cli.command()
def argv():
    """🎯 Test argv[0] and command information"""
    click.secho("=" * 60, fg='cyan')
    click.secho("🎯 ARGV[0] AND COMMAND TEST", fg='cyan', bold=True)
    click.secho("=" * 60, fg='cyan')
    
    click.secho(f"📝 sys.argv[0]: {sys.argv[0]}", fg='yellow')
    click.secho(f"📝 sys.argv: {sys.argv}", fg='yellow')
    click.secho(f"📝 sys.executable: {sys.executable}", fg='yellow')
    
    click.secho("\n🏷️ Flavor environment variables:", fg='blue', bold=True)
    for key in sorted(os.environ):
        if "COMMAND" in key or "FLAVOR" in key:
            click.echo(f"  {key} = {os.environ[key]}")
    
    click.secho(f"\n🔍 Process info:", fg='blue', bold=True)
    click.echo(f"  PID: {os.getpid()}")
    click.echo(f"  CWD: {os.getcwd()}")
    
    # Try to get process name
    try:
        import psutil
        proc = psutil.Process()
        click.echo(f"  Process name: {proc.name()}")
        click.echo(f"  Process cmdline: {proc.cmdline()[:3]}...")
    except ImportError:
        try:
            # Fallback to ps command
            result = subprocess.run(
                ["ps", "-p", str(os.getpid()), "-o", "comm="],
                capture_output=True, text=True
            )
            click.echo(f"  Process name (ps): {result.stdout.strip()}")
        except:
            click.echo("  Process name: (unable to determine)")


@cli.command()
def test():
    """🧪 Run all tests"""
    click.secho("=" * 60, fg='magenta')
    click.secho("🧪 TASTER COMPREHENSIVE TEST SUITE", fg='magenta', bold=True)
    click.secho("=" * 60, fg='magenta')
    
    click.secho("\n>>> Running environment test...", fg='blue')
    ctx = click.Context(env)
    ctx.invoke(env)
    
    click.secho("\n>>> Running argv test...", fg='blue')
    ctx = click.Context(argv)
    ctx.invoke(argv)
    
    click.secho("\n>>> Running info test...", fg='blue')
    ctx = click.Context(info)
    ctx.invoke(info)
    
    click.secho("\n" + "=" * 60, fg='magenta')
    click.secho("✨ TEST SUITE COMPLETE", fg='magenta', bold=True)
    click.secho("=" * 60, fg='magenta')


@cli.command()
def shell():
    """🐚 Start interactive Python shell"""
    click.secho("=" * 60, fg='cyan')
    click.secho("🐚 TASTER INTERACTIVE SHELL", fg='cyan', bold=True)
    click.secho("=" * 60, fg='cyan')
    click.secho(f"🐍 Python {sys.version}", fg='yellow')
    click.secho("Type 'exit()' or Ctrl-D to exit", dim=True)
    click.secho("\n📚 Available in namespace:", fg='blue')
    click.echo("  - os, sys, json, platform")
    click.echo("  - env = dict(os.environ)")
    click.echo("  - argv = sys.argv")
    click.echo()
    
    import code
    env_vars = dict(os.environ)
    argv = sys.argv
    code.interact(local={'os': os, 'sys': sys, 'json': json, 'platform': platform, 
                         'env': env_vars, 'argv': argv})


@cli.command()
@click.argument('args', nargs=-1)
def echo(args):
    """📢 Echo arguments for testing"""
    click.secho("=" * 60, fg='cyan')
    click.secho("📢 ECHO TEST", fg='cyan', bold=True)
    click.secho("=" * 60, fg='cyan')
    click.secho(f"📝 Arguments ({len(args)}):", fg='yellow')
    for i, arg in enumerate(args, 1):
        click.echo(f"  [{i}] {arg}")


@cli.command()
def info():
    """ℹ️ Display package and system information"""
    click.secho("=" * 60, fg='cyan')
    click.secho("ℹ️ PACKAGE AND SYSTEM INFO", fg='cyan', bold=True)
    click.secho("=" * 60, fg='cyan')
    
    click.secho("📦 Package info:", fg='blue', bold=True)
    click.echo(f"  Name: taster")
    click.echo(f"  Version: 1.0.0")
    click.echo(f"  Entry point: {__name__}")
    
    click.secho("\n🐍 Python info:", fg='blue', bold=True)
    click.echo(f"  Version: {sys.version}")
    click.echo(f"  Executable: {sys.executable}")
    click.echo(f"  Path entries: {len(sys.path)}")
    
    click.secho("\n💻 System info:", fg='blue', bold=True)
    click.echo(f"  Platform: {platform.platform()}")
    click.echo(f"  Architecture: {platform.machine()}")
    click.echo(f"  Processor: {platform.processor()}")
    
    click.secho("\n🎨 Flavor info:", fg='blue', bold=True)
    workenv = os.environ.get("FLAVOR_WORKENV", "not set")
    click.echo(f"  Workenv: {workenv}")
    if workenv != "not set":
        workenv_path = Path(workenv)
        if workenv_path.exists():
            click.secho(f"  ✅ Workenv exists", fg='green')
            venv = workenv_path / "venv"
            if venv.exists():
                click.secho(f"  ✅ Virtual env", fg='green')
            metadata = workenv_path / "metadata"
            if metadata.exists():
                click.secho(f"  ✅ Metadata", fg='green')


def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main()