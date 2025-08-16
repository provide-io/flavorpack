#!/usr/bin/env python3
"""Tree-shaking for Python dependencies - removes unused code."""

import ast
import os
from pathlib import Path
from typing import Set, Dict, List, Tuple
import importlib.util
import sys


class PythonTreeShaker:
    """Analyzes Python code and removes unused dependencies."""
    
    def __init__(self, entry_point: str, project_root: Path):
        """Initialize tree shaker.
        
        Args:
            entry_point: Main module entry point (e.g., "myapp.cli:main")
            project_root: Root directory of the project
        """
        self.entry_point = entry_point
        self.project_root = project_root
        self.used_imports: Set[str] = set()
        self.used_symbols: Dict[str, Set[str]] = {}  # module -> symbols
        self.analyzed_files: Set[Path] = set()
        
    def analyze(self) -> Dict[str, Set[str]]:
        """Analyze code to find all used imports.
        
        Returns:
            Dictionary mapping module names to used symbols
        """
        # Parse entry point
        module_name, func_name = self.entry_point.split(":")
        
        # Start with the entry module
        self._analyze_module(module_name)
        
        return self.used_symbols
    
    def _analyze_module(self, module_name: str) -> None:
        """Recursively analyze a module and its imports.
        
        Args:
            module_name: Name of module to analyze
        """
        if module_name in self.used_imports:
            return  # Already analyzed
            
        self.used_imports.add(module_name)
        
        # Find the module file
        module_path = self._find_module_path(module_name)
        if not module_path or module_path in self.analyzed_files:
            return
            
        self.analyzed_files.add(module_path)
        
        # Parse the Python file
        try:
            with open(module_path, "r") as f:
                tree = ast.parse(f.read(), filename=str(module_path))
        except (SyntaxError, FileNotFoundError):
            return
            
        # Find all imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._record_import(alias.name, None)
                    
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Record specific symbols imported
                    symbols = []
                    for alias in node.names:
                        if alias.name == "*":
                            symbols = None  # Import all
                            break
                        symbols.append(alias.name)
                    
                    self._record_import(node.module, symbols)
                    
                    # Recursively analyze imported modules
                    if node.level == 0:  # Absolute import
                        self._analyze_module(node.module)
                    else:  # Relative import
                        base_module = ".".join(module_name.split(".")[:-node.level])
                        if node.module:
                            full_module = f"{base_module}.{node.module}"
                        else:
                            full_module = base_module
                        self._analyze_module(full_module)
    
    def _record_import(self, module: str, symbols: List[str] | None) -> None:
        """Record that a module and symbols are used.
        
        Args:
            module: Module name
            symbols: List of symbols or None for all
        """
        if module not in self.used_symbols:
            self.used_symbols[module] = set()
            
        if symbols is None:
            self.used_symbols[module] = {"*"}  # All symbols
        else:
            for symbol in symbols:
                self.used_symbols[module].add(symbol)
    
    def _find_module_path(self, module_name: str) -> Path | None:
        """Find the file path for a module.
        
        Args:
            module_name: Dotted module name
            
        Returns:
            Path to module file or None
        """
        # First try relative to project root
        module_path = module_name.replace(".", "/")
        
        # Check for package __init__.py
        init_path = self.project_root / module_path / "__init__.py"
        if init_path.exists():
            return init_path
            
        # Check for module.py
        py_path = self.project_root / f"{module_path}.py"
        if py_path.exists():
            return py_path
            
        # Try to find using importlib
        try:
            spec = importlib.util.find_spec(module_name)
            if spec and spec.origin:
                return Path(spec.origin)
        except (ImportError, ValueError):
            pass
            
        return None
    
    def optimize_wheel(self, wheel_path: Path, output_path: Path) -> Dict[str, int]:
        """Optimize a wheel by removing unused code.
        
        Args:
            wheel_path: Path to input wheel
            output_path: Path for optimized wheel
            
        Returns:
            Statistics about optimization
        """
        import zipfile
        import tempfile
        
        stats = {
            "original_size": wheel_path.stat().st_size,
            "files_removed": 0,
            "files_kept": 0
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract wheel
            with zipfile.ZipFile(wheel_path, "r") as zf:
                zf.extractall(temp_path)
            
            # Find all Python files
            py_files = list(temp_path.rglob("*.py"))
            
            for py_file in py_files:
                # Determine module name from file path
                relative_path = py_file.relative_to(temp_path)
                module_parts = []
                
                for part in relative_path.parts[:-1]:
                    if not part.endswith(".dist-info"):
                        module_parts.append(part)
                
                if py_file.stem != "__init__":
                    module_parts.append(py_file.stem)
                    
                module_name = ".".join(module_parts)
                
                # Check if this module is used
                if module_name in self.used_symbols:
                    # Keep the file, but potentially strip unused symbols
                    stats["files_kept"] += 1
                    
                    # Advanced: We could parse and modify the file here
                    # to remove unused functions/classes
                    
                elif any(module_name.startswith(used + ".") for used in self.used_symbols):
                    # This is a submodule of a used module
                    stats["files_kept"] += 1
                    
                else:
                    # Remove unused module
                    py_file.unlink()
                    stats["files_removed"] += 1
                    
                    # Also remove .pyc if exists
                    pyc_file = py_file.with_suffix(".pyc")
                    if pyc_file.exists():
                        pyc_file.unlink()
            
            # Repackage wheel
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in temp_path.rglob("*"):
                    if file_path.is_file():
                        arc_name = file_path.relative_to(temp_path)
                        zf.write(file_path, arc_name)
        
        stats["optimized_size"] = output_path.stat().st_size
        stats["size_reduction"] = stats["original_size"] - stats["optimized_size"]
        stats["reduction_percent"] = (stats["size_reduction"] / stats["original_size"]) * 100
        
        return stats


def tree_shake_dependencies(
    entry_point: str,
    project_root: Path,
    wheels_dir: Path,
    output_dir: Path
) -> Dict[str, Dict[str, int]]:
    """Tree-shake all wheels in a directory.
    
    Args:
        entry_point: Main entry point
        project_root: Project root directory  
        wheels_dir: Directory containing wheels
        output_dir: Directory for optimized wheels
        
    Returns:
        Optimization statistics per wheel
    """
    shaker = PythonTreeShaker(entry_point, project_root)
    
    # Analyze code to find used imports
    used_symbols = shaker.analyze()
    
    print(f"Found {len(used_symbols)} used modules")
    
    # Optimize each wheel
    output_dir.mkdir(exist_ok=True)
    all_stats = {}
    
    for wheel_path in wheels_dir.glob("*.whl"):
        output_path = output_dir / wheel_path.name
        
        print(f"Optimizing {wheel_path.name}...")
        stats = shaker.optimize_wheel(wheel_path, output_path)
        all_stats[wheel_path.name] = stats
        
        if stats["size_reduction"] > 0:
            print(f"  Reduced by {stats['size_reduction'] / 1024:.1f} KB "
                  f"({stats['reduction_percent']:.1f}%)")
            print(f"  Removed {stats['files_removed']} unused files")
    
    return all_stats


# Example usage:
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: tree_shaker.py <entry_point> <project_root>")
        sys.exit(1)
    
    entry = sys.argv[1]  # e.g., "myapp.cli:main"
    root = Path(sys.argv[2])
    
    shaker = PythonTreeShaker(entry, root)
    used = shaker.analyze()
    
    print("Used modules and symbols:")
    for module, symbols in sorted(used.items()):
        if symbols == {"*"}:
            print(f"  {module}: *")
        else:
            print(f"  {module}: {', '.join(sorted(symbols))}")