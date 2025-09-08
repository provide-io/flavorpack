#
# flavor/packaging/python/example_integration.py
#
"""Example integration showing how to use all the new Python packaging managers.

This demonstrates the modular architecture with specialized managers:
- PyPaPipManager: Critical pip operations with manylinux support
- UVManager: Fast UV operations extending Foundation's ToolManager  
- WheelBuilder: Complex dependency resolution and wheel building
- PythonDistManager: Complete distribution creation and management
- ArchiveUtils: Deterministic tar.gz operations

This example shows how the main PythonPackager should be refactored.
"""

from pathlib import Path
import sys
import tempfile
from typing import Any

from provide.foundation.logger import logger

from flavor.packaging.python.pypapip_manager import PyPaPipManager
from flavor.packaging.python.uv_manager import UVManager
from flavor.packaging.python.wheel_builder import WheelBuilder
from flavor.packaging.python.dist_manager import PythonDistManager
from flavor.utils.archive_utils import ArchiveUtils


class ModernPythonPackager:
    """
    Modern Python packager demonstrating the new modular architecture.
    
    This is how PythonPackager should be refactored to use the specialized managers
    instead of having 1,239 lines of monolithic code.
    """
    
    def __init__(self, python_version: str = "3.11"):
        """
        Initialize with all specialized managers.
        
        Args:
            python_version: Target Python version
        """
        self.python_version = python_version
        
        # Initialize all specialized managers
        self.pypapip = PyPaPipManager(python_version=python_version)
        self.uv_manager = UVManager()
        self.wheel_builder = WheelBuilder(python_version=python_version)
        self.dist_manager = PythonDistManager(python_version=python_version)
        self.archive_utils = ArchiveUtils(deterministic=True)
        
        logger.info(f"🚀 Initialized ModernPythonPackager with Python {python_version}")
    
    def create_complete_package(
        self,
        project_dir: Path,
        output_dir: Path,
        requirements_file: Path | None = None,
        extra_packages: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a complete Python package using the new modular system.
        
        This demonstrates how the refactored PythonPackager should work:
        1. Use WheelBuilder for dependency resolution and wheel building
        2. Use PythonDistManager for complete distribution creation
        3. Use ArchiveUtils for deterministic archive creation
        4. Keep PyPaPipManager for critical pip operations
        
        Args:
            project_dir: Project source directory
            output_dir: Directory for package output
            requirements_file: Optional requirements file
            extra_packages: Additional packages to include
            
        Returns:
            Dictionary with package information and paths
        """
        logger.info(f"🏗️📦 Creating complete package: {project_dir.name}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Step 1: Create standalone distribution
            logger.info("📦🐍 Creating standalone Python distribution")
            dist_info = self.dist_manager.create_standalone_distribution(
                project_dir=project_dir,
                output_dir=temp_path / "dist_output",
                requirements_file=requirements_file,
                extra_packages=extra_packages,
                python_exe=Path(sys.executable),
            )
            
            # Step 2: Validate the distribution
            logger.info("🔍✅ Validating distribution")
            if not self.dist_manager.validate_distribution(dist_info):
                raise RuntimeError("Distribution validation failed")
            
            # Step 3: Create payload archive
            logger.info("📦🗜️ Creating payload archive")
            payload_archive = output_dir / f"{project_dir.name}-payload.tar.gz"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            self.archive_utils.create_tar_gz(
                source_path=dist_info["site_packages"],
                output_path=payload_archive,
                exclude_patterns=["**/__pycache__", "**/*.pyc", "**/tests"],
            )
            
            # Step 4: Create metadata
            logger.info("📋📝 Creating package metadata")
            metadata = {
                "project_name": project_dir.name,
                "python_version": self.python_version,
                "payload_archive": str(payload_archive),
                "distribution_size": dist_info["distribution_size"],
                "wheel_count": dist_info["total_wheels"],
            }
            
            metadata_file = output_dir / f"{project_dir.name}-metadata.json"
            import json
            metadata_file.write_text(json.dumps(metadata, indent=2))
            
            package_info = {
                "project_name": project_dir.name,
                "payload_archive": payload_archive,
                "metadata_file": metadata_file,
                "distribution_info": dist_info,
                "success": True,
            }
            
            logger.info("✅📦 Package creation completed successfully")
            return package_info
    
    def demonstrate_manager_capabilities(self) -> None:
        """
        Demonstrate the capabilities of each specialized manager.
        
        This shows how each manager has focused responsibilities and can be used
        independently or together for different packaging scenarios.
        """
        logger.info("🔍📋 Demonstrating manager capabilities")
        
        # PyPaPipManager: Critical pip operations with manylinux support
        logger.info("🎯 PyPaPipManager: Critical pip operations")
        logger.info("  - Debug-resistant naming (_get_pypapip_*)")
        logger.info("  - Manylinux2014 compatibility for Linux")
        logger.info("  - Proper dependency resolution that uv pip cannot handle")
        
        # UVManager: Fast operations extending Foundation
        logger.info("🚀 UVManager: Fast UV operations")
        logger.info("  - Extends Foundation's BaseToolManager")
        logger.info("  - Automatic UV installation and version management")
        logger.info("  - Fast venv creation and package compilation")
        
        # WheelBuilder: Complex dependency resolution
        logger.info("🔨 WheelBuilder: Sophisticated wheel building")
        logger.info("  - Combines UV speed with PyPA pip reliability")
        logger.info("  - Complex dependency resolution logic")
        logger.info("  - Cross-platform wheel selection")
        
        # PythonDistManager: Complete distribution handling
        logger.info("📦 PythonDistManager: Complete distribution management")
        logger.info("  - Virtual environment creation and management")
        logger.info("  - Package installation from wheels")
        logger.info("  - Site-packages optimization for packaging")
        
        # ArchiveUtils: Deterministic tar.gz operations
        logger.info("🗜️ ArchiveUtils: Advanced archive management")
        logger.info("  - Deterministic tar.gz creation")
        logger.info("  - Compression control and validation")
        logger.info("  - Proper metadata handling for PSPF")
        
        logger.info("✅ All managers working together provide a complete Python packaging solution")


def main():
    """Example usage of the modern packaging system."""
    packager = ModernPythonPackager(python_version="3.11")
    packager.demonstrate_manager_capabilities()


if __name__ == "__main__":
    main()