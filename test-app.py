#!/usr/bin/env python3
import sys
print(f"Hello from Python! Args: {sys.argv[1:]}")
with open("output.txt", "w") as f:
    f.write(f"Executed with args: {sys.argv[1:]}\n")
