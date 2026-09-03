#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Helper functions for the packaging orchestrator build pipeline."""

import gzip
import os
from pathlib import Path
import tarfile
from typing import Any

from provide.foundation import logger
from provide.foundation.errors import ProcessError
from provide.foundation.file.formats import write_json
from provide.foundation.platform import is_windows
from provide.foundation.process import run
from provide.foundation.serialization import json_dumps

from flavor.config.defaults import (
    ENV_BUILDER_BIN,
    ENV_LAUNCHER_BIN,
    ENV_LAUNCHER_CLI,
    ENV_LAUNCHER_LOG_LEVEL,
)
from flavor.exceptions import BuildError
from flavor.packaging.defaults import DEFAULT_ENV_ISOLATION_UNSET, WINDOWS_SYSTEM_PASS


def get_cli_executable_name(package_name: str, build_config: dict[str, Any], windows: bool) -> str:
    """Get the CLI executable name from build config or fallback to package name.

    Args:
        package_name: The package name
        build_config: Build configuration containing cli_scripts
        windows: Whether we're on Windows

    Returns:
        The executable name with appropriate extension
    """
    cli_scripts = build_config.get("cli_scripts", {})
    if cli_scripts:
        # Use the first defined CLI script
        first_script = next(iter(cli_scripts.keys()))
        return f"{first_script}.exe" if windows else first_script
    else:
        # Fallback for JSON manifests or packages without scripts
        return f"{package_name}.exe" if windows else package_name


def get_cli_module_for_windows(package_name: str, build_config: dict[str, Any]) -> str:
    """Get the Python module to use for 'python -m <module>' invocation on Windows.

    On Windows the runtime command is 'python.exe -m <module>' rather than running
    a Scripts/*.exe distlib trampoline (which embeds a stale path after workenv move).
    The module must be derived from the entry point (e.g. 'taster.cli:main' → 'taster.cli'),
    NOT from the script name ('taster'), which would require a taster/__main__.py.

    Args:
        package_name: The package name (fallback)
        build_config: Build configuration containing cli_scripts

    Returns:
        The Python module path suitable for 'python -m <module>'
    """
    cli_scripts = build_config.get("cli_scripts", {})
    if cli_scripts:
        first_script_name = next(iter(cli_scripts.keys()))
        entry_point = cli_scripts[first_script_name]
        if ":" in entry_point:
            return str(entry_point.split(":")[0])
        return str(entry_point)
    return package_name


def create_slot_tarballs(temp_dir: Path, artifacts: dict[str, Path]) -> dict[str, Path]:
    """Create tarball files for each slot.

    Args:
        temp_dir: Temporary directory for build
        artifacts: Dictionary of prepared artifacts

    Returns:
        Dictionary mapping slot names to tarball paths
    """
    windows = is_windows()
    uv_exe = "uv.exe" if windows else "uv"

    slots = {}

    # UV binary: pre-compress with gzip so external builders (Go/Rust) store
    # data that matches operations="gzip" — both builders stream source bytes
    # directly without applying compression themselves.
    uv_raw = artifacts["payload_dir"] / "bin" / uv_exe
    uv_gz = temp_dir / f"{uv_exe}.gz"
    with uv_raw.open("rb") as src, gzip.open(uv_gz, "wb") as dst:
        dst.write(src.read())
    slots["uv"] = uv_gz

    python_tarball = artifacts.get("python_tgz")
    if not python_tarball:
        raise BuildError("Python runtime tarball not found")
    slots["python"] = python_tarball  # already .tar.gz, matches operations="tgz"

    # Wheels: build a .tar.gz so stored bytes match operations="tgz"
    wheels_tgz = temp_dir / "wheels.tar.gz"
    with tarfile.open(wheels_tgz, "w:gz") as tar:
        wheels_dir = artifacts["payload_dir"] / "wheels"
        for wheel in wheels_dir.glob("*.whl"):
            tar.add(wheel, arcname=f"wheels/{wheel.name}")
    slots["wheels"] = wheels_tgz

    return slots


def _runtime_command(package_name: str, build_config: dict[str, Any], windows: bool) -> str:
    """The command the launcher runs once the package is installed.

    Windows invokes python.exe -m <module> rather than the Scripts/*.exe distlib
    launcher: pip embeds the temporary python.exe path inside that launcher at
    install time, and the Rust launcher moves the tree to its final work
    environment afterwards, so the embedded path is stale. The entry-point
    module is used rather than the script name, since `python -m taster` needs
    taster/__main__.py, which may not exist.
    """
    if windows:
        return f"{{workenv}}/python.exe -m {get_cli_module_for_windows(package_name, build_config)}"
    return f"{{workenv}}/bin/{get_cli_executable_name(package_name, build_config, windows)}"


def _workenv_layout() -> dict[str, Any]:
    """The directories a package gets, and the variables pointing at them.

    Every path a program would otherwise take from the host -- temp, cache,
    config, home -- is redirected inside the work environment, so a package
    leaves nothing behind and picks nothing up.
    """
    return {
        "directories": [
            {"path": "{workenv}/tmp", "mode": "0700"},
            {"path": "{workenv}/var", "mode": "0755"},
            {"path": "{workenv}/var/log", "mode": "0755"},
            {"path": "{workenv}/var/cache", "mode": "0755"},
            {"path": "{workenv}/var/run", "mode": "0755"},
            {"path": "{workenv}/etc", "mode": "0755"},
            {"path": "{workenv}/home", "mode": "0700"},
            {"path": "{workenv}/state", "mode": "0755"},
        ],
        "env": {
            "TMPDIR": "{workenv}/tmp",
            "TEMP": "{workenv}/tmp",
            "TMP": "{workenv}/tmp",
            "XDG_RUNTIME_DIR": "{workenv}/var/run",
            "XDG_CACHE_HOME": "{workenv}/var/cache",
            "XDG_DATA_HOME": "{workenv}/share",
            "XDG_STATE_HOME": "{workenv}/state",
            "XDG_CONFIG_HOME": "{workenv}/etc",
            "HOME": "{workenv}/home",
        },
    }


def _setup_commands(windows: bool, python_path: str) -> list[dict[str, Any]]:
    """Install the bundled wheels, then record that the install happened.

    The marker file is what the launcher's cache check reads to decide whether
    this work environment is already built.
    """
    install = (
        "{workenv}/python.exe -m pip install --no-deps"
        if windows
        else f"{{workenv}}/bin/uv --no-config pip install --python {python_path} --no-deps"
    )
    return [
        {
            "type": "enumerate_and_execute",
            "command": install,
            "enumerate": {"path": "{workenv}/wheels", "pattern": "*.whl"},
        },
        {
            "type": "write_file",
            "path": "{workenv}/metadata/installed",
            "content": "{package_name}-{version}",
        },
    ]


def _package_slots(slots: dict[str, Path], bin_dir: str, uv_exe: str) -> list[dict[str, Any]]:
    """The three slots a Python package ships: its installer, runtime, payload."""
    return [
        {
            "id": "uv",
            "source": str(slots["uv"]),
            "operations": "gzip",
            "purpose": "tool",
            "lifecycle": "cache",
            # For gzip encoding, this is treated as a full file path.
            "target": f"{bin_dir}/{uv_exe}",
            "type": "file",
            "permissions": "0700",  # Owner-only executable permissions
        },
        {
            "id": "python",
            "source": str(slots["python"]),
            "operations": "tgz",
            "purpose": "runtime",
            "lifecycle": "cache",
            "target": "{workenv}",
        },
        {
            "id": "wheels",
            "source": str(slots["wheels"]),
            "operations": "tgz",
            "purpose": "payload",
            "lifecycle": "init",
            "target": "wheels",
        },
    ]


def _merge_preserving_order(defaults: list[str], extra: list[str]) -> list[str]:
    """Defaults first, then anything new, with no duplicates."""
    seen = set(defaults)
    return defaults + [item for item in extra if item not in seen]


def _runtime_env_config(build_config: dict[str, Any], windows: bool) -> dict[str, Any]:
    """Build the runtime env operations, isolating the package by default.

    Isolation is on unless the package sets ``isolated: false``. Without it a
    host virtualenv leaks into the package's Python and quietly changes which
    interpreter and site-packages it uses.

    Windows keeps its system variables either way: they are needed for DLL
    loading and process creation, so isolating them breaks the package rather
    than protecting it.
    """
    runtime_env_config = build_config.get("execution", {}).get("runtime", {}).get("env", {})
    isolated = runtime_env_config.get("isolated", True)  # Safe by default
    windows_pass = WINDOWS_SYSTEM_PASS if windows else []

    operations: dict[str, Any] = {
        "pass": _merge_preserving_order(list(windows_pass), runtime_env_config.get("pass", [])),
        "set": runtime_env_config.get("set", {}),
        "map": runtime_env_config.get("map", {}),
    }

    if isolated is False:
        logger.debug("🔓 Environment isolation disabled via isolated=false flag")
    else:
        logger.debug("🔒 Applying default environment isolation for Python/UV")
        user_unset = runtime_env_config.get("unset", [])
        merged_unset = _merge_preserving_order(list(DEFAULT_ENV_ISOLATION_UNSET), user_unset)
        if user_unset:
            logger.debug(f"Merging user unset vars {user_unset} with defaults")
            logger.debug(f"Final merged unset list: {merged_unset}")
        operations["unset"] = merged_unset
        logger.info(
            f"✅ Runtime environment configured with isolation: "
            f"unset={merged_unset[:3]}... ({len(merged_unset)} vars)"
        )

    # An operation with nothing in it is noise in the manifest.
    return {key: value for key, value in operations.items() if value}


def create_builder_manifest(
    package_name: str,
    version: str,
    build_config: dict[str, Any],
    slots: dict[str, Path],
    key_paths: dict[str, str | None],
) -> dict[str, Any]:
    """Create manifest for external builder."""
    windows = is_windows()
    uv_exe = "uv.exe" if windows else "uv"
    bin_dir = "Scripts" if windows else "bin"
    # cpython-build-standalone puts python.exe at the install root on Windows,
    # and in bin/ on Unix.
    python_path = "{workenv}/python.exe" if windows else "{workenv}/bin/python3"

    manifest: dict[str, Any] = {
        "package": {"name": package_name, "version": version},
        "execution": {"command": _runtime_command(package_name, build_config, windows)},
        "cache_validation": {
            "check_file": "{workenv}/metadata/installed",
            "expected_content": f"{package_name}-{version}",
        },
        "workenv": _workenv_layout(),
        "setup_commands": _setup_commands(windows, python_path),
        "slots": _package_slots(slots, bin_dir, uv_exe),
        "signature": {
            "private_key": key_paths.get("private"),
            "public_key": key_paths.get("public"),
        },
    }

    if runtime_env := _runtime_env_config(build_config, windows):
        manifest["runtime"] = {"env": runtime_env}

    return manifest


def write_manifest_file(manifest: dict[str, Any], temp_dir: Path) -> Path:
    """Write manifest to JSON file."""
    manifest_path = temp_dir / "manifest.json"
    write_json(manifest_path, manifest, indent=2)
    logger.info(f"Generated manifest at: {manifest_path}")
    if logger.is_debug_enabled():
        logger.debug(f"Manifest content: {json_dumps(manifest, indent=2)}")
    return manifest_path


def find_builder_executable(builder_bin: str | None) -> Path:
    """Find the builder executable to use."""
    if builder_bin:
        path = Path(builder_bin)
        if not path.exists():
            raise BuildError(f"Builder binary not found: {builder_bin}")
        logger.info(f"Using custom builder: {path}")
        return path

    env_bin = os.environ.get(ENV_BUILDER_BIN)
    if env_bin:
        path = Path(env_bin)
        if not path.exists():
            raise BuildError(f"Builder binary not found: {path.as_posix()}")
        logger.info(f"Using builder from {ENV_BUILDER_BIN}: {path}")
        return path

    from flavor.helpers.manager import HelperManager

    manager = HelperManager()
    try:
        return manager.get_helper("flavor-rs-builder")
    except FileNotFoundError:
        logger.warning("flavor-rs-builder not found, falling back to Go builder.")
        try:
            return manager.get_helper("flavor-go-builder")
        except FileNotFoundError as e:
            raise BuildError(
                "❌ No builder binaries found!\n"
                "\n"
                "   • cd helpers && ./build.sh     (build both Go and Rust builders)\n"
                "   • make build-helpers           (if using make)\n"
                "   • flavor helpers build         (if flavor CLI is available)\n"
                "\n"
                "💡 Or specify a custom builder with:\n"
                f"   • --builder-bin /path/to/builder   (command line)\n"
                f"   • {ENV_BUILDER_BIN}=/path/to/builder (environment variable)\n"
                "\n"
                f"🔍 Searched locations: {manager.helpers_bin.as_posix()}, {manager.installed_helpers_bin.as_posix()}"
            ) from e


def find_launcher_executable(launcher_bin: str | None) -> Path:
    """Find the launcher executable to use."""
    if launcher_bin:
        path = Path(launcher_bin)
        if not path.exists():
            raise BuildError(f"Launcher binary not found: {launcher_bin}")
        return path

    env_bin = os.environ.get(ENV_LAUNCHER_BIN)
    if env_bin:
        path = Path(env_bin)
        if not path.exists():
            raise BuildError(f"Launcher binary from {ENV_LAUNCHER_BIN} not found: {env_bin}")
        return path

    from flavor.helpers.manager import HelperManager

    manager = HelperManager()
    try:
        return manager.get_helper("flavor-rs-launcher")
    except FileNotFoundError:
        logger.warning("flavor-rs-launcher not found, falling back to Go launcher.")
        try:
            return manager.get_helper("flavor-go-launcher")
        except FileNotFoundError as e:
            raise BuildError(
                "❌ No launcher binaries found!\n"
                "\n"
                "   • cd helpers && ./build.sh     (build both Go and Rust launchers)\n"
                "   • make build-helpers           (if using make)\n"
                "   • flavor helpers build         (if flavor CLI is available)\n"
                "\n"
                "💡 Or specify a custom launcher with:\n"
                f"   • --launcher-bin /path/to/launcher (command line)\n"
                f"   • {ENV_LAUNCHER_BIN}=/path/to/launcher (environment variable)\n"
                "\n"
                f"🔍 Searched locations: {manager.helpers_bin.as_posix()}, {manager.installed_helpers_bin.as_posix()}"
            ) from e


def _run_launcher_verify(package_path: Path) -> Any:
    """Run a package's own launcher against it in CLI mode."""
    return run(
        [package_path.as_posix(), "verify"],
        env={
            **os.environ,
            ENV_LAUNCHER_CLI: "1",
            # Launchers log at debug by default, which buries the one line that
            # says why the package was rejected under startup trace.
            ENV_LAUNCHER_LOG_LEVEL: "error",
        },
        check=False,
        capture_output=True,
        text=True,
    )


def _last_lines(output: str | None, count: int = 3) -> str:
    """Return the final non-empty lines of launcher output.

    The diagnosis is the last thing a launcher prints, and anything a stray
    logger emits first would otherwise be reported as the reason.
    """
    lines = [line.strip() for line in (output or "").splitlines() if line.strip()]
    return "\n   ".join(lines[-count:])


def verify_built_package(package_path: Path, *, launcher_name: str, host_platform: str) -> None:
    """Ask a freshly built package's own launcher to read it back.

    A PSPF package is a launcher with slots appended, so every build joins two
    independently versioned halves: the builder that writes the metadata and the
    launcher binary prepended to it. Nothing else makes them agree. When the
    builder stops writing a field the embedded launcher requires, the build still
    succeeds and the package fails at run time, wherever it has reached by then.

    Running the package's own launcher against it turns that into a build
    failure. It needs no compatibility matrix, because the launcher under test is
    the one being shipped, and it holds for fields nobody has thought of yet.

    Args:
        package_path: The package the builder just wrote.
        launcher_name: File name of the launcher embedded in it, which carries
            the platform it was built for.
        host_platform: Platform this build is running on.

    Raises:
        BuildError: The package is missing, or its launcher will not read it.
    """
    if not package_path.exists():
        raise BuildError(f"Build reported success but produced no file: {package_path}")

    # Running the package means running the launcher inside it, which only works
    # when that launcher is native. A foreign one is a deliberate --launcher-bin
    # choice, already warned about when the launcher is resolved.
    if host_platform not in launcher_name and "any" not in launcher_name:
        logger.warning(
            "⚠️🚀 Skipping launcher read-back: embedded launcher is not native",
            launcher=launcher_name,
            host=host_platform,
            package=package_path.name,
            consequence="a launcher that cannot read this package would not be caught here",
        )
        return

    logger.info("🔍🚀 Asking the embedded launcher to read the package back...")
    try:
        result = _run_launcher_verify(package_path)
    except ProcessError as exc:
        # The package could not be started at all -- a noexec mount, a lost exec
        # bit. That says nothing about the package, but it does mean this build
        # never confirmed the one thing it was supposed to, so it does not pass.
        raise BuildError(
            f"❌ Could not run {package_path.name} to check it.\n"
            "\n"
            "   The build cannot confirm the embedded launcher reads the package, "
            "so it stops rather than report a check it never made.\n"
            "\n"
            f"   {exc}\n"
            "\n"
            "💡 Usually the output directory is mounted noexec, or the package lost "
            "its execute bit."
        ) from exc

    if result.returncode == 0:
        logger.info("✅🚀 Embedded launcher reads the package it ships in")
        return

    said = _last_lines(result.stderr) or _last_lines(result.stdout)
    raise BuildError(
        f"❌ The launcher embedded in {package_path.name} cannot read the package it ships in.\n"
        "\n"
        "   Anyone running this package would get the same failure, so the build "
        "stops here instead.\n"
        "\n"
        f"   Launcher said: {said or f'exit status {result.returncode}, no output'}\n"
        "\n"
        "💡 This usually means the builder and the launcher are different versions:\n"
        f"   • rebuild the helpers so both halves match ({ENV_LAUNCHER_BIN} overrides which "
        "launcher is used)\n"
        "   • or the metadata changed in a way the launcher cannot parse"
    )


def create_python_builder_metadata(
    package_name: str, version: str, build_config: dict[str, Any]
) -> dict[str, Any]:
    """Create metadata for Python builder."""
    windows = is_windows()
    bin_dir = "Scripts" if windows else "bin"
    # On Windows, cpython-build-standalone places python.exe at the root of the install
    # dir (not inside Scripts/).  On Unix it lives in bin/.
    python_path = "{workenv}/python.exe" if windows else "{workenv}/bin/python3"
    package_exe = get_cli_executable_name(package_name, build_config, windows)
    # On Windows the runtime command uses python.exe -m <module> instead of the
    # Scripts/*.exe distlib launcher.  The Rust launcher runs setup commands in
    # the TEMP extraction directory and then moves the tree to the final workenv.
    # pip embeds the temp python.exe path inside the distlib launcher at install
    # time, so the launcher's embedded path is stale after the move.  Invoking
    # python.exe directly avoids the stale-path problem entirely.
    # Use the entry-point module (e.g. 'taster.cli') not the script name ('taster'),
    # since 'python -m taster' requires taster/__main__.py which may not exist.
    if windows:
        cli_module = get_cli_module_for_windows(package_name, build_config)
        runtime_command = f"{{workenv}}/python.exe -m {cli_module}"
    else:
        runtime_command = f"{{workenv}}/{bin_dir}/{package_exe}"

    metadata = {
        "package": {"name": package_name, "version": version},
        "execution": {
            "command": runtime_command,
            "env": {},
        },
        "workenv": {
            "directories": [
                {"path": "{workenv}/tmp", "mode": "0700"},
                {"path": "{workenv}/var", "mode": "0755"},
                {"path": "{workenv}/var/log", "mode": "0755"},
                {"path": "{workenv}/var/cache", "mode": "0755"},
                {"path": "{workenv}/var/run", "mode": "0755"},
                {"path": "{workenv}/etc", "mode": "0755"},
                {"path": "{workenv}/home", "mode": "0700"},
                {"path": "{workenv}/state", "mode": "0755"},
            ],
            "env": {
                "TMPDIR": "{workenv}/tmp",
                "TEMP": "{workenv}/tmp",
                "TMP": "{workenv}/tmp",
                "XDG_RUNTIME_DIR": "{workenv}/var/run",
                "XDG_CACHE_HOME": "{workenv}/var/cache",
                "XDG_DATA_HOME": "{workenv}/share",
                "XDG_STATE_HOME": "{workenv}/state",
                "XDG_CONFIG_HOME": "{workenv}/etc",
                "HOME": "{workenv}/home",
            },
        },
        "cache_validation": {
            "check_file": "{workenv}/metadata/installed",
            "expected_content": f"{package_name}-{version}",
        },
        "setup_commands": [
            {
                "type": "enumerate_and_execute",
                # On Windows use python -m pip: uv trampolines fail to canonicalize
                # their own path inside the PSP workenv.  pip's distlib launchers
                # embed the Python path at install time and don't canonicalize.
                # On Linux/macOS uv pip install works fine (shell-script entry points).
                "command": (
                    "{workenv}/python.exe -m pip install --no-deps"
                    if windows
                    else f"{{workenv}}/bin/uv --no-config pip install --python {python_path} --no-deps"
                ),
                "enumerate": {"path": "{workenv}/wheels", "pattern": "*.whl"},
            },
            {
                "type": "chmod",
                "path": f"{{workenv}}/{bin_dir}/*",
                "mode": "700",
                "description": f"Make all scripts in {bin_dir}/ executable",
            },
            {
                "type": "write_file",
                "path": "{workenv}/metadata/installed",
                "content": "{package_name}-{version}",
            },
        ],
    }

    # Default environment isolation for Python/UV to prevent host venv interference
    execution_config = build_config.get("execution", {})
    runtime_env_config = execution_config.get("runtime", {}).get("env", {})

    # Check for explicit opt-out via isolated flag
    isolated = runtime_env_config.get("isolated", True)  # Default to True (safe by default)

    # On Windows, always preserve system vars required for DLL loading and process
    # creation regardless of isolation mode.
    windows_pass = WINDOWS_SYSTEM_PASS if windows else []

    if isolated is False:
        logger.debug("🔓 Environment isolation disabled via isolated=false flag")
        # User has explicitly opted out of isolation - don't add runtime section
        # unless they provided other env config
        user_pass = runtime_env_config.get("pass", [])
        merged_pass = windows_pass + [v for v in user_pass if v not in set(windows_pass)]
        manifest_runtime_env = {
            key: value
            for key, value in {
                "pass": merged_pass,
                "set": runtime_env_config.get("set", {}),
                "map": runtime_env_config.get("map", {}),
            }.items()
            if value
        }
        if manifest_runtime_env:
            logger.debug(f"Adding user-specified runtime config (no isolation): {manifest_runtime_env}")
            metadata["runtime"] = {"env": manifest_runtime_env}
    else:
        # Apply default isolation (safe by default)
        logger.debug("🔒 Applying default environment isolation for Python/UV")

        # Merge user unset vars with defaults (defaults first, then user vars, preserve order)
        user_unset = runtime_env_config.get("unset", [])
        # Remove duplicates while preserving order: defaults first, then new user vars
        seen = set(DEFAULT_ENV_ISOLATION_UNSET)
        merged_unset = DEFAULT_ENV_ISOLATION_UNSET + [var for var in user_unset if var not in seen]

        if user_unset:
            logger.debug(f"Merging user unset vars {user_unset} with defaults")
            logger.debug(f"Final merged unset list: {merged_unset}")

        user_pass = runtime_env_config.get("pass", [])
        merged_pass = windows_pass + [v for v in user_pass if v not in set(windows_pass)]

        manifest_runtime_env = {
            key: value
            for key, value in {
                "unset": merged_unset,
                "pass": merged_pass,
                "set": runtime_env_config.get("set", {}),
                "map": runtime_env_config.get("map", {}),
            }.items()
            if value
        }

        if manifest_runtime_env:
            metadata["runtime"] = {"env": manifest_runtime_env}
            logger.info(
                f"✅ Runtime environment configured with isolation: unset={merged_unset[:3]}... ({len(merged_unset)} vars)"
            )

    return metadata


def create_python_slot_tarballs(temp_dir: Path, artifacts: dict[str, Path]) -> tuple[Path, Path, Path]:
    """Create slot tarballs for Python builder."""
    windows = is_windows()
    uv_exe = "uv.exe" if windows else "uv"

    # UV slot - single binary (builder will compress it)
    uv_path = artifacts["payload_dir"] / "bin" / uv_exe

    python_tarball = artifacts.get("python_tgz")
    if not python_tarball:
        raise BuildError("Python runtime tarball not found")

    wheels_tarball = temp_dir / "wheels.tar"
    with tarfile.open(wheels_tarball, "w") as tar:
        wheels_dir = artifacts["payload_dir"] / "wheels"
        for wheel in wheels_dir.glob("*.whl"):
            tar.add(wheel, arcname=f"wheels/{wheel.name}")

    return uv_path, python_tarball, wheels_tarball


# 🌶️📦🔚
