#!/usr/bin/env python3
"""
Simple test program to demonstrate PSPF 2025 packaging.
"""
import sys
import os

def main():
    print("Hello from PSPF 2025!")
    print(f"Python version: {sys.version}")
    print(f"Arguments: {sys.argv[1:]}")
    print(f"Working directory: {os.getcwd()}")
    
    # Check environment variables
    if "PSPF_VERSION" in os.environ:
        print(f"PSPF Version: {os.environ['PSPF_VERSION']}")
    
    # Process arguments
    if len(sys.argv) > 1:
        print("\nProcessing arguments:")
        for i, arg in enumerate(sys.argv[1:], 1):
            print(f"  Arg {i}: {arg}")
        
        # Echo back the first argument if provided
        if sys.argv[1] == "echo":
            if len(sys.argv) > 2:
                print(f"\nEcho: {' '.join(sys.argv[2:])}")
            else:
                print("\nEcho: (no message provided)")
    else:
        print("\nNo arguments provided. Try:")
        print(f"  {sys.argv[0]} echo Hello World")

if __name__ == "__main__":
    main()