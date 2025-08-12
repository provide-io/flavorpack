#!/usr/bin/env python3
"""
Demonstration Terraform Provider
This simulates the behavior of terraform-provider-pyvider for PSPF bundling.
"""

import sys
import json
import os

def handle_terraform_rpc():
    """Handle Terraform RPC protocol (simplified demo)"""
    print("1|5|tcp|127.0.0.1:1234|grpc|")
    sys.stdout.flush()
    return 0

def show_info():
    """Show provider information"""
    info = {
        "name": "terraform-provider-pyvider",
        "version": "0.0.2",
        "protocol": "5",
        "description": "PSPF-bundled Terraform provider (demo)",
        "build": {
            "builder": os.environ.get("PSPF_BUILDER", "unknown"),
            "format": "PSPF/2025"
        }
    }
    print(json.dumps(info, indent=2))
    return 0

def main():
    """Main entry point mimicking terraform-provider behavior"""
    args = sys.argv[1:]
    
    # When Terraform calls the provider with no args, it expects RPC info
    if not args:
        return handle_terraform_rpc()
    
    # Handle basic commands
    if args[0] == "--help":
        print("terraform-provider-pyvider (PSPF Demo)")
        print("Usage:")
        print("  terraform-provider-pyvider          # Start RPC server (called by Terraform)")
        print("  terraform-provider-pyvider info     # Show provider information")
        print("  terraform-provider-pyvider version  # Show version")
        return 0
    
    if args[0] == "info":
        return show_info()
    
    if args[0] == "version":
        print("terraform-provider-pyvider v0.0.2 (PSPF Demo)")
        return 0
    
    # For any other args, assume Terraform is calling us
    return handle_terraform_rpc()

if __name__ == "__main__":
    sys.exit(main())