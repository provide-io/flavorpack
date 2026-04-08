#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ci.workflow_lib.common import (
    append_step_summary,
    ensure_executable,
    run_logged_command,
    write_github_env,
    write_github_output,
)
from ci.workflow_lib.matrices import (
    build_flavor_test_matrix,
    build_helper_matrix,
    build_taster_test_matrix,
    hash_file,
    hash_matching_files,
)
from ci.workflow_lib.pipelines import (
    detect_launcher_source,
    install_platform_helpers,
    organize_taster_flavor_artifacts,
    render_flavor_summary,
    render_taster_summary,
    resolve_flavor_build_assets,
    resolve_taster_build_inputs,
    resolve_workflow_run,
    run_taster_scenario,
    setup_test_workenv,
    verify_wheel_structure,
    write_taster_result,
)
from ci.workflow_lib.release import (
    create_release_tag,
    render_release_notes,
    render_release_summary,
    stage_release_directory,
    verify_release_wheels,
    write_release_checksums,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Helpers for thin CI workflow scripts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("helper-cache-keys")
    helper_matrix = subparsers.add_parser("helper-matrix")
    helper_matrix.add_argument("platforms", nargs="?", default="")
    helper_matrix.add_argument("--act", action="store_true")
    subparsers.add_parser("flavor-test-matrix")
    subparsers.add_parser("taster-test-matrix")

    for command in ("release-checksums", "release-notes", "stage-release", "verify-release-wheels"):
        subparsers.add_parser(command)
    subparsers.choices["release-checksums"].add_argument("release_dir")
    subparsers.choices["release-notes"].add_argument("release_dir")
    subparsers.choices["release-notes"].add_argument("version")
    subparsers.choices["release-notes"].add_argument("repository")
    subparsers.choices["stage-release"].add_argument("artifacts_dir")
    subparsers.choices["stage-release"].add_argument("release_dir")
    subparsers.choices["verify-release-wheels"].add_argument("dist_dir")

    create_tag = subparsers.add_parser("create-release-tag")
    create_tag.add_argument("version")
    create_tag.add_argument("version_tag")
    create_tag.add_argument("repository")

    release_summary = subparsers.add_parser("release-summary")
    for name in (
        "version",
        "version_tag",
        "repository",
        "helper_run_id",
        "flavor_run_id",
        "collect_wheels_result",
        "collect_packages_result",
        "generate_assets_result",
        "create_release_result",
        "publish_testpypi_result",
        "publish_pypi_result",
    ):
        release_summary.add_argument(f"--{name.replace('_', '-')}", required=True)
    release_summary.add_argument("--prerelease", action="store_true")
    release_summary.add_argument("--dry-run", action="store_true")

    organize_flavor = subparsers.add_parser("organize-flavor-artifacts")
    organize_flavor.add_argument("input_dir")
    organize_flavor.add_argument("output_dir")

    resolve_run = subparsers.add_parser("resolve-workflow-run")
    resolve_run.add_argument("--workflow", required=True)
    resolve_run.add_argument("--input-run", default="")

    install_helpers = subparsers.add_parser("install-platform-helpers")
    install_helpers.add_argument("--source-dir", required=True)
    install_helpers.add_argument("--dest-dir", required=True)
    install_helpers.add_argument("--platform", required=True)
    install_helpers.add_argument("--version")

    verify_exec = subparsers.add_parser("verify-executable")
    verify_exec.add_argument("path")

    taster_result = subparsers.add_parser("write-taster-result")
    taster_result.add_argument("output_path")
    taster_result.add_argument("--platform", required=True)
    taster_result.add_argument("--runner", required=True)
    taster_result.add_argument("--status", required=True)
    taster_result.add_argument("--taster-path", required=True)
    taster_result.add_argument("--helper-version", required=True)

    resolve_taster = subparsers.add_parser("resolve-taster-build")
    resolve_taster.add_argument("--flavor-dir", required=True)
    resolve_taster.add_argument("--helpers-dir", required=True)
    resolve_taster.add_argument("--platform", required=True)
    resolve_taster.add_argument("--version", required=True)

    setup_workenv = subparsers.add_parser("setup-test-workenv")
    setup_workenv.add_argument("--dev", action="store_true")
    setup_workenv.add_argument("--sibling", default="")

    verify_wheel = subparsers.add_parser("verify-wheel-structure")
    verify_wheel.add_argument("dist_dir")

    resolve_flavor = subparsers.add_parser("resolve-flavor-build")
    resolve_flavor.add_argument("--helpers-dir", required=True)
    resolve_flavor.add_argument("--wheel-dir", required=True)
    resolve_flavor.add_argument("--platform", required=True)
    resolve_flavor.add_argument("--version", required=True)

    flavor_summary = subparsers.add_parser("flavor-summary")
    for name in (
        "test_results_dir",
        "wheel_dir",
        "flavor_dir",
        "helper_version",
        "test_flavor_psp_result",
        "repository",
        "run_id",
    ):
        flavor_summary.add_argument(f"--{name.replace('_', '-')}", required=True)

    taster_summary = subparsers.add_parser("taster-summary")
    for name in ("results_dir", "helper_version", "repository", "run_id"):
        taster_summary.add_argument(f"--{name.replace('_', '-')}", required=True)

    taster_scenario = subparsers.add_parser("taster-scenario")
    taster_scenario.add_argument("scenario")
    taster_scenario.add_argument("--launcher", default="")
    taster_scenario.add_argument("--output", default="taster-bundled.psp")
    taster_scenario.add_argument("--platform", default="")
    taster_scenario.add_argument("--launcher-ext", default="")
    taster_scenario.add_argument("--include-info", action="store_true")
    return parser.parse_args()


def _dispatch_outputs(args: argparse.Namespace) -> None:
    if args.command == "helper-cache-keys":
        write_github_output(
            go_key_base=f"go-helpers-{hash_matching_files(Path('src/flavor-go'), ('.go',))}",
            rust_key_base=f"rust-helpers-{hash_matching_files(Path('src/flavor-rs'), ('.rs',))}",
            tastesh_key_base=f"tastesh-{hash_file(Path('ci/build-dash.sh'))}",
        )
        return
    if args.command == "helper-matrix":
        write_github_output(
            matrix=json.dumps(build_helper_matrix(args.platforms, args.act), separators=(",", ":"))
        )
        return
    if args.command == "flavor-test-matrix":
        write_github_output(matrix=json.dumps(build_flavor_test_matrix(), separators=(",", ":")))
        return
    if args.command == "taster-test-matrix":
        write_github_output(matrix=json.dumps(build_taster_test_matrix(), separators=(",", ":")))
        return
    if args.command == "resolve-workflow-run":
        write_github_output(run_id=resolve_workflow_run(args.input_run, args.workflow))
        return
    if args.command == "resolve-taster-build":
        write_github_output(
            **resolve_taster_build_inputs(
                Path(args.flavor_dir), Path(args.helpers_dir), args.platform, args.version
            )
        )
        return
    if args.command == "resolve-flavor-build":
        write_github_output(
            **resolve_flavor_build_assets(
                Path(args.helpers_dir), Path(args.wheel_dir), args.platform, args.version
            )
        )
        return
    raise ValueError(f"Unhandled output command: {args.command}")


def _dispatch_release(args: argparse.Namespace) -> None:
    if args.command == "release-checksums":
        write_release_checksums(Path(args.release_dir))
    elif args.command == "release-notes":
        (Path(args.release_dir) / "release-notes.md").write_text(
            render_release_notes(args.version, args.repository), encoding="utf-8"
        )
    elif args.command == "stage-release":
        print(
            json.dumps(
                stage_release_directory(Path(args.artifacts_dir), Path(args.release_dir)), sort_keys=True
            )
        )
    elif args.command == "create-release-tag":
        create_release_tag(args.version, args.version_tag, args.repository)
    elif args.command == "verify-release-wheels":
        verify_release_wheels(Path(args.dist_dir))
    elif args.command == "release-summary":
        append_step_summary(render_release_summary(args))
    else:
        raise ValueError(f"Unhandled release command: {args.command}")


def _dispatch_pipeline(args: argparse.Namespace) -> None:
    if args.command == "organize-flavor-artifacts":
        organize_taster_flavor_artifacts(Path(args.input_dir), Path(args.output_dir))
        return
    if args.command in {
        "install-platform-helpers",
        "verify-executable",
        "write-taster-result",
        "setup-test-workenv",
        "verify-wheel-structure",
    }:
        _dispatch_pipeline_actions(args)
        return
    if args.command in {"flavor-summary", "taster-summary", "taster-scenario"}:
        _dispatch_pipeline_reporting(args)
        return
    raise ValueError(f"Unhandled pipeline command: {args.command}")


def _dispatch_pipeline_actions(args: argparse.Namespace) -> None:
    if args.command == "install-platform-helpers":
        print(
            "\n".join(
                install_platform_helpers(
                    Path(args.source_dir), Path(args.dest_dir), args.version, args.platform
                )
            )
        )
    elif args.command == "verify-executable":
        ensure_executable(Path(args.path))
        run_logged_command([args.path, "--version"])
    elif args.command == "write-taster-result":
        write_taster_result(
            Path(args.output_path),
            args.platform,
            args.runner,
            args.status,
            args.taster_path,
            args.helper_version,
        )
    elif args.command == "setup-test-workenv":
        setup_test_workenv(args.dev, args.sibling)
    elif args.command == "verify-wheel-structure":
        verify_wheel_structure(Path(args.dist_dir))
    else:
        raise ValueError(f"Unhandled pipeline action command: {args.command}")


def _dispatch_pipeline_reporting(args: argparse.Namespace) -> None:
    if args.command == "flavor-summary":
        append_step_summary(
            render_flavor_summary(
                Path(args.test_results_dir),
                Path(args.wheel_dir),
                Path(args.flavor_dir),
                args.helper_version,
                args.test_flavor_psp_result,
                args.repository,
                args.run_id,
            )
        )
    elif args.command == "taster-summary":
        append_step_summary(
            render_taster_summary(Path(args.results_dir), args.helper_version, args.repository, args.run_id)
        )
    elif args.command == "taster-scenario":
        if args.scenario == "launcher-location":
            info = detect_launcher_source()
            write_github_env(LAUNCHER_SOURCE=info["source"])
            print(info["flavor_location"])
        else:
            run_taster_scenario(
                args.scenario, args.launcher, args.output, args.platform, args.launcher_ext, args.include_info
            )
    else:
        raise ValueError(f"Unhandled pipeline reporting command: {args.command}")


def main() -> int:
    args = parse_args()
    if args.command in {
        "helper-cache-keys",
        "helper-matrix",
        "flavor-test-matrix",
        "taster-test-matrix",
        "resolve-workflow-run",
        "resolve-taster-build",
        "resolve-flavor-build",
    }:
        _dispatch_outputs(args)
    elif args.command in {
        "release-checksums",
        "release-notes",
        "stage-release",
        "create-release-tag",
        "verify-release-wheels",
        "release-summary",
    }:
        _dispatch_release(args)
    else:
        _dispatch_pipeline(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
