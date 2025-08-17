#!/usr/bin/env python3
"""Binary optimization utilities for Flavor."""

from pathlib import Path
from typing import Dict

from flavor.utils.subprocess import run_command


class BinaryOptimizer:
    """Optimizes binary files for size reduction."""
    
    def __init__(self):
        """Initialize binary optimizer."""
        pass
    
    def strip_binary(self, binary_path: Path) -> Dict:
        """Strip debug symbols from a binary.
        
        Args:
            binary_path: Path to binary file
        
        Returns:
            Result dictionary with success status and size reduction
        """
        if not binary_path.exists():
            return {"success": False, "error": "Binary not found"}
        
        original_size = binary_path.stat().st_size
        
        try:
            # Run strip command
            result = run_command(
                ["strip", str(binary_path)],
                capture_output=True,
                check=False,
                log_command=False,
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or "Strip command failed",
                    "original_size": original_size
                }
            
            new_size = binary_path.stat().st_size
            size_reduction = original_size - new_size
            
            return {
                "success": True,
                "original_size": original_size,
                "new_size": new_size,
                "size_reduction": size_reduction,
                "reduction_percent": (size_reduction / original_size) * 100 if original_size > 0 else 0
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "strip command not found",
                "original_size": original_size
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "original_size": original_size
            }
    
    def optimize(self, binary_path: Path, strip: bool = True) -> Dict:
        """Optimize a binary file.
        
        Args:
            binary_path: Path to binary file
            strip: Whether to strip debug symbols
        
        Returns:
            Optimization results
        """
        if not strip:
            return {
                "success": True,
                "total_reduction": 0,
                "operations": []
            }
        
        strip_result = self.strip_binary(binary_path)
        return {
            "success": strip_result["success"],
            "total_reduction": strip_result.get("size_reduction", 0),
            "operations": [{"type": "strip", **strip_result}]
        }