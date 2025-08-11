#!/usr/bin/env python3
"""
Simple Terraform Provider - PSPF Example
=========================================

A minimal terraform provider demonstrating PSPF packaging.
This provider creates and manages simple text files.
"""
import sys
import json
import logging
import os
from pathlib import Path
from provider import SimpleProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('simple-provider')

def main():
    """Main entry point for the terraform provider."""
    try:
        # Create provider instance
        provider = SimpleProvider()
        
        # Handle command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command in ['--help', '-h', 'help']:
                provider.show_help()
                return 0
            elif command in ['--version', '-v', 'version']:
                provider.show_version()
                return 0
            elif command == '--schema':
                # Output schema for terraform
                schema = provider.get_schema()
                print(json.dumps(schema, indent=2))
                return 0
            elif command == '--test':
                # Self-test mode
                return provider.self_test()
            else:
                logger.error(f"Unknown command: {command}")
                provider.show_help()
                return 1
        
        # Default: run as terraform provider (serve mode)
        logger.info("Starting Simple Provider in serve mode...")
        return provider.serve()
        
    except KeyboardInterrupt:
        logger.info("Provider interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Provider failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

# 📦🍜📄🪄
