#!/usr/bin/env python3
"""Simple test script for builder/launcher combinations."""
import os
import sys

def handle_command(cmd, *args):
    """Handle different test commands."""
    if cmd == "info":
        print("📦 Combination Test Package")
        print(f"  Package: pretaster-combination")
        print(f"  Version: 1.0.0")
        print(f"  Python: {sys.executable}")
        print(f"  Workenv: {os.getenv('FLAVOR_WORKENV', 'Not set')}")
        return 0
    elif cmd == "env":
        print("🌍 Environment Variables:")
        for key in sorted(os.environ.keys())[:10]:
            print(f"  {key}={os.environ[key][:50]}")
        print(f"  ... ({len(os.environ)} total)")
        return 0
    elif cmd == "argv":
        print("📝 Arguments received:")
        for i, arg in enumerate(args):
            print(f"  [{i}]: {arg}")
        return 0
    elif cmd == "echo":
        print(" ".join(args))
        return 0
    elif cmd == "file":
        # Simple file test
        if args and args[0] == "workenv-test":
            test_file = "/tmp/workenv-test.txt"
            with open(test_file, "w") as f:
                f.write("Test content")
            print(f"✅ File written to {test_file}")
            return 0
        print("❌ Unknown file command")
        return 1
    elif cmd == "exit":
        exit_code = int(args[0]) if args else 0
        print(f"🚪 Exiting with code {exit_code}")
        return exit_code
    else:
        print(f"❌ Unknown command: {cmd}")
        return 1

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: combo_test.py <command> [args...]")
        sys.exit(1)
    
    cmd = args[0]
    cmd_args = args[1:] if len(args) > 1 else []
    exit_code = handle_command(cmd, *cmd_args)
    sys.exit(exit_code)