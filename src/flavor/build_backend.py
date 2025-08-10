#
# flavor/build_backend.py
#

"""
PEP 517 build backend for Flavor providers.
"""

from pathlib import Path
import tempfile
import tomllib
from typing import Any, Never

from pyvider.telemetry import logger
from wheel.wheelfile import WheelFile

from .compiler import ensure_go_binary
from .exceptions import BuildError

# THE FIX: Use the correct class name 'PackagingOrchestrator'.
from .packaging.orchestrator import PackagingOrchestrator


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    logger.info(f"PEP 517 build_wheel called. Output wheel dir: {wheel_directory}")
    project_root = Path.cwd()
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        raise BuildError(f"pyproject.toml not found at {project_root}")

    with pyproject_path.open("rb") as f:
        pyproject_data = tomllib.load(f)

    project_conf = pyproject_data.get("project", {})
    tool_conf = pyproject_data.get("tool", {})
    if "flavor" not in tool_conf:
        raise BuildError("A [tool.flavor] section was not found in pyproject.toml.")
    flavor_conf = tool_conf["flavor"]

    package_name = project_conf.get("name")
    package_version = project_conf.get("version")
    if not package_name or not package_version:
        raise BuildError(
            "Missing 'name' or 'version' in [project] table of pyproject.toml"
        )

    pyproject_dir = pyproject_path.parent
    signing_conf = flavor_conf.get("signing", {})
    private_key_path = pyproject_dir / signing_conf.get(
        "private_key_path", "keys/provider-private.key"
    )
    public_key_path = pyproject_dir / signing_conf.get(
        "public_key_path", "keys/provider-public.key"
    )

    if not private_key_path.exists():
        raise BuildError(
            f"Private signing key not found at resolved path: {private_key_path}"
        )
    if not public_key_path.exists():
        raise BuildError(
            f"Public key for embedding not found at resolved path: {public_key_path}"
        )

    launcher_bin_path = ensure_go_binary("flavor-launcher")

    scripts = project_conf.get("scripts", {})
    if not scripts or len(scripts) != 1:
        raise BuildError(
            "A single [project.scripts] entry is required to name the final executable."
        )
    executable_name = next(iter(scripts.keys()))

    with tempfile.TemporaryDirectory(prefix="flavor_build_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        output_executable_path = temp_dir / executable_name

        build_conf = flavor_conf.get("build", {})
        entry_point = flavor_conf.get("entry_point")
        if not entry_point:
            raise BuildError(
                "Missing 'entry_point' in [tool.flavor] table of pyproject.toml"
            )

        provider_name = flavor_conf.get("provider_name")
        if not provider_name:
            raise BuildError(
                "Missing 'provider_name' in [tool.flavor] table of pyproject.toml"
            )

        orchestrator = PackagingOrchestrator(
            launcher_bin_path=str(launcher_bin_path),
            package_integrity_key_path=str(private_key_path),
            public_key_path=str(public_key_path),
            output_flavor_path=str(output_executable_path),
            build_config=build_conf,
            manifest_dir=pyproject_dir,
            provider_name=provider_name,
            entry_point=entry_point,
        )

        orchestrator.build_package()
        return _create_wheel_file(
            wheel_directory,
            package_name,
            package_version,
            project_conf,
            output_executable_path,
        )


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Editable installs are not supported for Flavor packages."""
    raise NotImplementedError(
        "Editable installs are not supported by this build backend."
    )


def _create_wheel_file(
    wheel_directory: str,
    package_name: str,
    package_version: str,
    project_conf: dict,
    executable_path: Path,
) -> str:
    normalized_name = package_name.replace("-", "_")
    wheel_name = f"{normalized_name}-{package_version}-py3-none-any.whl"
    final_wheel_path = Path(wheel_directory) / wheel_name
    dist_info_dirname = f"{normalized_name}-{package_version}.dist-info"

    with WheelFile(str(final_wheel_path), "w") as wf:
        script_name = next(iter(project_conf.get("scripts", {}).keys()))
        arcname = f"{normalized_name}-{package_version}.data/scripts/{script_name}"
        wf.write(str(executable_path), arcname=arcname)

        metadata_lines = [
            "Metadata-Version: 2.1",
            f"Name: {package_name}",
            f"Version: {package_version}",
        ]
        for dep in project_conf.get("dependencies", []):
            metadata_lines.append(f"Requires-Dist: {dep}")
        wf.writestr(f"{dist_info_dirname}/METADATA", "\n".join(metadata_lines) + "\n")

        wheel_md_lines = [
            "Wheel-Version: 1.0",
            "Generator: flavor",
            "Root-Is-Purelib: false",
            "Tag: py3-none-any",
        ]
        wf.writestr(f"{dist_info_dirname}/WHEEL", "\n".join(wheel_md_lines) + "\n")

    logger.info(f"Successfully built wheel: {final_wheel_path.name}")
    return final_wheel_path.name


def get_requires_for_build_wheel(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    return [
        "wheel",
    ]


def get_requires_for_build_editable(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    return []


def build_sdist(
    sdist_directory: str, config_settings: dict[str, Any] | None = None
) -> Never:
    raise NotImplementedError()


def get_requires_for_build_sdist(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    return []


# 🔨 🛠️ 🎁

# 📦🍜🔨🪄
