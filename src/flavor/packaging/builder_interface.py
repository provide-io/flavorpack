#
# flavor/packaging/builder_interface.py
#
"""
Proof of concept for architectural change:
- Python packager handles ALL Python-specific packaging
- Go/Rust tools become pure "flavor builders" that assemble binaries
"""

import json
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Optional

from pyvider.telemetry import logger


class FlavorBuilder:
    """
    Interface for flavor builders (Go/Rust) that assemble self-extracting binaries.
    
    The builder is language-agnostic and simply assembles pre-prepared components:
    - launcher binary
    - UV binary (optional)
    - Python distribution archive (optional)
    - metadata archive
    - payload archive
    - signature
    - public key
    """
    
    def __init__(self, builder_type: str = "go"):
        """
        Initialize the flavor builder.
        
        Args:
            builder_type: Either "go" or "rust" to select the builder implementation
        """
        self.builder_type = builder_type
        self.builder_executable = self._get_builder_executable()
    
    def _get_builder_executable(self) -> str:
        """Get the path to the flavor builder executable."""
        from ..compiler import ensure_go_binary, ensure_rust_binary
        
        if self.builder_type == "go":
            return ensure_go_binary("flavor-go")
        elif self.builder_type == "rust":
            return ensure_rust_binary("flavor-rust")
        else:
            raise ValueError(f"Unknown builder type: {self.builder_type}")
    
    def build_flavor(
        self,
        output_path: Path,
        launcher_path: Path,
        payload_tgz: Path,
        metadata_tgz: Path,
        signature: bytes,
        public_key_path: Path,
        private_key_path: Path,
        uv_binary_path: Optional[Path] = None,
        python_tgz: Optional[Path] = None,
    ) -> None:
        """
        Build a flavor package from pre-prepared components.
        
        This is a pure assembly operation - all Python-specific work
        (wheels, dependencies, etc.) should already be done.
        
        Args:
            output_path: Where to write the final flavor binary
            launcher_path: Path to the launcher executable
            payload_tgz: Pre-built payload archive
            metadata_tgz: Pre-built metadata archive
            signature: Pre-computed signature bytes
            public_key_path: Path to public key file
            private_key_path: Path to private key file (for builder compatibility)
            uv_binary_path: Optional UV binary to include
            python_tgz: Optional Python distribution archive
        """
        with tempfile.TemporaryDirectory(prefix="flavor_build_") as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write signature to file for builder
            signature_path = temp_path / "signature.bin"
            signature_path.write_bytes(signature)
            
            # Create symlinks/copies for builder expectations
            work_payload = temp_path / "payload.tgz"
            work_metadata = temp_path / "metadata.tgz"
            work_payload.symlink_to(payload_tgz.absolute())
            work_metadata.symlink_to(metadata_tgz.absolute())
            
            if uv_binary_path and uv_binary_path.exists():
                work_uv = temp_path / "uv"
                work_uv.symlink_to(uv_binary_path.absolute())
            
            if python_tgz and python_tgz.exists():
                work_python = temp_path / "python.tgz"
                work_python.symlink_to(python_tgz.absolute())
            
            # Call the builder with minimal flags - it's just assembling
            cmd = [
                str(self.builder_executable),
                "build",
                "--out", str(output_path),
                "--payload-dir", str(temp_path),  # Builder expects this for legacy reasons
                "--package-key", str(private_key_path),
                "--public-key", str(public_key_path),
                "--launcher-bin", str(launcher_path),
            ]
            
            logger.info(f"Calling {self.builder_type} builder to assemble flavor binary")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_path)
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"Builder failed: {result.stderr}\nCommand: {' '.join(cmd)}"
                )
            
            logger.info(f"Successfully built flavor package: {output_path}")


class PythonPackager:
    """
    Handles all Python-specific packaging logic.
    
    This class owns:
    - Creating wheels from source packages
    - Managing dependencies
    - Creating virtual environments
    - Generating metadata
    - Computing signatures
    
    The output is a set of artifacts that can be assembled by any flavor builder.
    """
    
    def __init__(
        self,
        manifest_dir: Path,
        package_name: str,
        entry_point: str,
        build_config: dict[str, Any],
        python_version: str = "3.13",
    ):
        self.manifest_dir = manifest_dir
        self.package_name = package_name
        self.entry_point = entry_point
        self.build_config = build_config
        self.python_version = python_version
    
    def prepare_artifacts(self, work_dir: Path) -> dict[str, Path]:
        """
        Prepare all artifacts needed for flavor assembly.
        
        Returns:
            Dictionary mapping artifact names to their paths:
            - payload_tgz: The main payload archive
            - metadata_tgz: Metadata archive
            - uv_binary: UV binary (if available)
            - python_tgz: Python distribution (placeholder for now)
        """
        artifacts = {}
        
        # Create payload structure
        payload_dir = work_dir / "payload"
        payload_dir.mkdir(mode=0o700)
        
        # Build wheels
        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir(mode=0o700)
        self._build_wheels(wheels_dir)
        
        # Add UV binary
        import shutil
        uv_path = shutil.which("uv")
        if uv_path:
            bin_dir = payload_dir / "bin"
            bin_dir.mkdir(mode=0o700, exist_ok=True)
            payload_uv = bin_dir / "uv"
            shutil.copy2(uv_path, str(payload_uv))
            payload_uv.chmod(0o755)
            artifacts["uv_binary"] = payload_uv
        
        # Create metadata
        metadata_dir = payload_dir / "metadata"
        metadata_dir.mkdir(mode=0o700)
        self._create_metadata(metadata_dir)
        
        # Create payload archive
        payload_tgz = work_dir / "payload.tgz"
        with tarfile.open(payload_tgz, "w:gz", compresslevel=9) as tar:
            tar.add(payload_dir, arcname=".")
        artifacts["payload_tgz"] = payload_tgz
        
        # Create metadata archive (separate for selective extraction)
        metadata_content = work_dir / "metadata_content"
        metadata_content.mkdir(mode=0o700)
        # For now empty, but could contain launcher-specific metadata
        metadata_tgz = work_dir / "metadata.tgz"
        with tarfile.open(metadata_tgz, "w:gz", compresslevel=9) as tar:
            tar.add(metadata_content, arcname=".")
        artifacts["metadata_tgz"] = metadata_tgz
        
        # Create Python distribution placeholder
        python_tgz = work_dir / "python.tgz"
        self._create_python_placeholder(python_tgz)
        artifacts["python_tgz"] = python_tgz
        
        return artifacts
    
    def _build_wheels(self, wheels_dir: Path) -> None:
        """Build wheels for the package and its dependencies."""
        # Create temporary build environment
        with tempfile.TemporaryDirectory() as build_env_dir:
            build_venv = Path(build_env_dir) / "venv"
            
            # Create venv and install pip
            subprocess.run(
                ["uv", "venv", str(build_venv), "--python", f"python{self.python_version}"],
                check=True
            )
            subprocess.run(
                ["uv", "pip", "install", "--python", str(build_venv / "bin" / "python"), "pip"],
                check=True
            )
            
            pip3 = build_venv / "bin" / "pip3"
            
            # Build wheels for dependencies
            for dep in self.build_config.get("dependencies", []):
                dep_path = self.manifest_dir / dep
                if dep_path.exists():
                    logger.info(f"Building wheel for dependency: {dep}")
                    subprocess.run(
                        [str(pip3), "wheel", "--wheel-dir", str(wheels_dir), "--no-deps", str(dep_path)],
                        check=True
                    )
            
            # Build main package wheel
            logger.info("Building wheel for main package")
            subprocess.run(
                [str(pip3), "wheel", "--wheel-dir", str(wheels_dir), "--no-deps", str(self.manifest_dir)],
                check=True
            )
            
            # Download transitive dependencies
            logger.info("Downloading dependency wheels")
            subprocess.run(
                [str(pip3), "wheel", "--wheel-dir", str(wheels_dir), str(self.manifest_dir)],
                check=True
            )
    
    def _create_metadata(self, metadata_dir: Path) -> None:
        """Create metadata files."""
        package_manifest = {
            "name": self.package_name,
            "version": self.build_config.get("version", "0.0.1"),
            "entry_point": self.entry_point,
            "python_version": self.python_version,
        }
        (metadata_dir / "package_manifest.json").write_text(
            json.dumps(package_manifest, indent=2)
        )
        
        config_data = {
            "entry_point": self.entry_point,
            "package_name": self.package_name,
        }
        (metadata_dir / "config.json").write_text(
            json.dumps(config_data, indent=2)
        )
    
    def _create_python_placeholder(self, python_tgz: Path) -> None:
        """Create a placeholder Python distribution archive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            python_dir = Path(temp_dir) / "python"
            python_dir.mkdir()
            (python_dir / "README.txt").write_text(
                f"Python {self.python_version} distribution placeholder\n"
                "In production, this would contain the full Python distribution."
            )
            with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
                tar.add(python_dir, arcname=".")
    
    def compute_signature(self, payload_tgz: Path, private_key_path: Path) -> bytes:
        """Compute signature for the payload."""
        import hashlib
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        
        # Hash the payload
        hasher = hashlib.sha256()
        with open(payload_tgz, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        payload_hash = hasher.digest()
        
        # Load private key and sign
        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        
        signature = private_key.sign(payload_hash, ec.ECDSA(hashes.SHA256()))
        return signature


def build_flavor_package(
    manifest_dir: Path,
    package_name: str,
    entry_point: str,
    build_config: dict[str, Any],
    output_path: Path,
    private_key_path: Path,
    public_key_path: Path,
    launcher_type: str = "go",
    builder_type: str = "go",
    python_version: str = "3.13",
) -> None:
    """
    High-level function to build a flavor package.
    
    This demonstrates the new architecture where:
    1. Python packager handles all Python-specific work
    2. Flavor builders just assemble the final binary
    
    Args:
        manifest_dir: Directory containing the Python package
        package_name: Name of the package
        entry_point: Entry point in format "module:function"
        build_config: Build configuration dict
        output_path: Where to write the final flavor binary
        private_key_path: Path to private key for signing
        public_key_path: Path to public key
        launcher_type: "go" or "rust" for the launcher
        builder_type: "go" or "rust" for the builder
        python_version: Python version to use
    """
    from ..compiler import ensure_go_binary, ensure_rust_binary
    
    with tempfile.TemporaryDirectory(prefix="flavor_pkg_") as work_dir:
        work_path = Path(work_dir)
        
        # Step 1: Python packager prepares all artifacts
        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name=package_name,
            entry_point=entry_point,
            build_config=build_config,
            python_version=python_version,
        )
        
        logger.info("Preparing Python artifacts...")
        artifacts = packager.prepare_artifacts(work_path)
        
        # Step 2: Compute signature
        logger.info("Computing payload signature...")
        signature = packager.compute_signature(artifacts["payload_tgz"], private_key_path)
        
        # Step 3: Get launcher binary
        if launcher_type == "go":
            launcher_path = Path(ensure_go_binary("flavor-launcher-go"))
        else:
            launcher_path = Path(ensure_rust_binary("flavor-launcher-rs"))
        
        # Step 4: Use flavor builder to assemble the final binary
        builder = FlavorBuilder(builder_type=builder_type)
        
        logger.info(f"Assembling flavor binary with {builder_type} builder...")
        builder.build_flavor(
            output_path=output_path,
            launcher_path=launcher_path,
            payload_tgz=artifacts["payload_tgz"],
            metadata_tgz=artifacts["metadata_tgz"],
            signature=signature,
            public_key_path=Path(public_key_path),
            private_key_path=Path(private_key_path),
            uv_binary_path=artifacts.get("uv_binary"),
            python_tgz=artifacts.get("python_tgz"),
        )
        
        logger.info(f"Successfully built flavor package: {output_path}")


# Example usage demonstrating the new architecture
if __name__ == "__main__":
    # This would be called from the `flavor package` command
    build_flavor_package(
        manifest_dir=Path("/path/to/python/package"),
        package_name="example_provider",
        entry_point="example_provider.main:main",
        build_config={"version": "1.0.0", "dependencies": []},
        output_path=Path("/tmp/example.flavor"),
        private_key_path=Path("/path/to/private.key"),
        public_key_path=Path("/path/to/public.key"),
        launcher_type="go",
        builder_type="go",
    )


# 🏗️ 🐍 🔧