#!/usr/bin/env python3
"""Safe optimization strategies that actually work."""

from pathlib import Path
import shutil
import zipfile


class SafeOptimizer:
    """Safe optimizations that won't break your code."""

    def remove_cache_files(self, wheel_path: Path) -> int:
        """Remove __pycache__ and .pyc files - always safe."""
        saved = 0
        with (
            zipfile.ZipFile(wheel_path, "r") as zin,
            zipfile.ZipFile(
                wheel_path.with_suffix(".tmp"),
                "w",
                zipfile.ZIP_DEFLATED,
                compresslevel=9,
            ) as zout,
        ):
            for item in zin.infolist():
                if "__pycache__" not in item.filename and not item.filename.endswith(
                    ".pyc"
                ):
                    zout.writestr(item, zin.read(item.filename))
                else:
                    saved += item.file_size

        # Replace original
        wheel_path.with_suffix(".tmp").replace(wheel_path)
        return saved

    def remove_test_files(self, wheel_path: Path) -> int:
        """Remove test directories - usually safe."""
        saved = 0
        test_patterns = ["tests/", "test/", "testing/", "*_test.py", "test_*.py"]

        with (
            zipfile.ZipFile(wheel_path, "r") as zin,
            zipfile.ZipFile(
                wheel_path.with_suffix(".tmp"),
                "w",
                zipfile.ZIP_DEFLATED,
                compresslevel=9,
            ) as zout,
        ):
            for item in zin.infolist():
                skip = any(pattern in item.filename for pattern in test_patterns)
                if not skip:
                    zout.writestr(item, zin.read(item.filename))
                else:
                    saved += item.file_size

        wheel_path.with_suffix(".tmp").replace(wheel_path)
        return saved

    def remove_docs(self, wheel_path: Path) -> int:
        """Remove documentation - safe for runtime."""
        saved = 0

        with (
            zipfile.ZipFile(wheel_path, "r") as zin,
            zipfile.ZipFile(
                wheel_path.with_suffix(".tmp"),
                "w",
                zipfile.ZIP_DEFLATED,
                compresslevel=9,
            ) as zout,
        ):
            for item in zin.infolist():
                skip = any(
                    item.filename.endswith(ext) for ext in [".md", ".rst", ".txt"]
                )
                skip = skip or any(
                    d in item.filename for d in ["docs/", "doc/", "examples/"]
                )
                if not skip or item.filename == "LICENSE.txt":  # Keep license
                    zout.writestr(item, zin.read(item.filename))
                else:
                    saved += item.file_size

        wheel_path.with_suffix(".tmp").replace(wheel_path)
        return saved

    def strip_type_hints(self, wheel_path: Path) -> int:
        """Remove .pyi stub files - safe if not using mypy at runtime."""
        saved = 0
        with (
            zipfile.ZipFile(wheel_path, "r") as zin,
            zipfile.ZipFile(
                wheel_path.with_suffix(".tmp"),
                "w",
                zipfile.ZIP_DEFLATED,
                compresslevel=9,
            ) as zout,
        ):
            for item in zin.infolist():
                if (
                    not item.filename.endswith(".pyi")
                    and "py.typed" not in item.filename
                ):
                    zout.writestr(item, zin.read(item.filename))
                else:
                    saved += item.file_size

        wheel_path.with_suffix(".tmp").replace(wheel_path)
        return saved


class DependencyAnalyzer:
    """Analyze but DON'T remove - just report."""

    def analyze_imports(self, project_path: Path) -> dict[str, set[str]]:
        """Analyze imports to INFORM decisions, not automate them."""
        import ast

        imports: dict[str, set[str]] = {}

        for py_file in project_path.rglob("*.py"):
            try:
                with py_file.open() as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.setdefault(alias.name.split(".")[0], set()).add(
                                str(py_file)
                            )
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.setdefault(node.module.split(".")[0], set()).add(
                                str(py_file)
                            )
            except (SyntaxError, FileNotFoundError, UnicodeDecodeError):
                pass  # Skip unparseable files

        return imports

    def suggest_removals(
        self, required_packages: set[str], installed_packages: set[str]
    ) -> set[str]:
        """SUGGEST what might be removable - human must decide."""
        suggestions = installed_packages - required_packages

        # Never suggest removing these (commonly lazy-loaded)
        always_keep = {
            "pip",
            "setuptools",
            "wheel",
            "certifi",
            "urllib3",
            "charset-normalizer",
            "idna",
            "six",
            "typing-extensions",
        }

        return suggestions - always_keep


# The ONLY safe "tree-shaking": explicit whitelist
class ExplicitWhitelist:
    """The only truly safe approach - explicit control."""

    def __init__(self, whitelist: set[str]) -> None:
        """
        Args:
            whitelist: Set of package names to keep
        """
        self.whitelist = whitelist

    def filter_wheels(self, wheels_dir: Path, output_dir: Path) -> None:
        """Only include explicitly whitelisted packages."""
        output_dir.mkdir(exist_ok=True)

        for wheel in wheels_dir.glob("*.whl"):
            # Parse wheel name: package-version-py...
            package_name = wheel.name.split("-")[0].replace("_", "-").lower()

            if package_name in self.whitelist:
                shutil.copy2(wheel, output_dir)
                print(f"✓ Kept: {wheel.name}")
            else:
                print(f"✗ Skipped: {wheel.name}")


# Example safe usage:
if __name__ == "__main__":
    # Safe optimizations
    optimizer = SafeOptimizer()

    # These are ALWAYS safe
    wheel = Path("some_package.whl")
    saved = optimizer.remove_cache_files(wheel)
    saved += optimizer.remove_test_files(wheel)
    saved += optimizer.remove_docs(wheel)
    print(f"Safely saved {saved / 1024:.1f} KB")

    # Analysis for human review
    analyzer = DependencyAnalyzer()
    imports = analyzer.analyze_imports(Path())
    print(f"\nYour code imports: {', '.join(imports.keys())}")
    print("Review this list and decide what to keep")

    # Explicit whitelist - the safest approach
    whitelist = ExplicitWhitelist({"click", "requests", "pyyaml"})
    whitelist.filter_wheels(Path("wheels"), Path("filtered_wheels"))
