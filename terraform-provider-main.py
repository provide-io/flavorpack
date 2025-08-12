#!/usr/bin/env python3
"""
terraform-provider-pyvider
Main entry point for PSPF-bundled Terraform provider
"""

import sys
import os
import subprocess

def main():
    """Main entry point that delegates to appropriate component"""
    # Get the directory where this script is located (extracted by PSPF)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if we need to run the demo or server
    if len(sys.argv) > 1 and sys.argv[1] in ["info", "version", "--help"]:
        # Run the demo script for info commands
        demo_script = os.path.join(script_dir, "terraform-provider-demo.py")
        subprocess.run([sys.executable, demo_script] + sys.argv[1:])
    else:
        # Run the provider server for Terraform
        server_script = os.path.join(script_dir, "provider_server.py")
        subprocess.run([sys.executable, server_script] + sys.argv[1:])

if __name__ == "__main__":
    main()