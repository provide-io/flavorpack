#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Pipe data processing utilities for stdin/stderr transformations."""

from __future__ import annotations

import base64
from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path
import random
import sys

import click
from provide.foundation.console import perr


@click.group("pipe")
def pipe_command() -> None:
    """Namespace for data-piping helpers."""


@pipe_command.command("stdin")
@click.option("--format", "input_format", type=click.Choice(["raw", "json", "base64", "hex"]), default="raw")
@click.option("--output", "destination", type=click.Choice(["stdout", "stderr", "file"]), default="stdout")
@click.option("--file", "file_path", type=click.Path(path_type=Path), help="Output file path")
@click.option(
    "--transform",
    type=click.Choice(["upper", "lower", "reverse", "hash", "none"]),
    default="none",
)
@click.option("--buffer-size", type=int, default=8192, help="Buffer size for reading")
def process_stdin(
    input_format: str,
    destination: str,
    file_path: Path | None,
    transform: str,
    buffer_size: int,
) -> None:
    """Process data from stdin with optional decoding and transformations."""
    if sys.stdin.isatty():
        raise click.ClickException("No input detected. Pipe data to this command.")

    data = _read_stdin(buffer_size)
    decoded = _decode_input(data, input_format)
    transformed = _apply_transform(decoded, transform)
    _emit_output(transformed, destination, file_path)


@pipe_command.command("stress")
@click.option("--size", type=int, default=1024 * 1024, help="Size of data to generate (bytes)")
@click.option(
    "--pattern",
    type=click.Choice(["random", "zeros", "ones", "pattern"]),
    default="random",
)
@click.option("--chunk-size", type=int, default=8192, help="Chunk size for output")
def stress_test(size: int, pattern: str, chunk_size: int) -> None:
    """Generate stress test data to stdout."""
    remaining = size
    while remaining > 0:
        chunk_len = min(chunk_size, remaining)
        chunk = _generate_pattern(pattern, chunk_len)
        sys.stdout.buffer.write(chunk)
        remaining -= chunk_len
    sys.stdout.flush()


@pipe_command.command("fuzz")
@click.option("--seed", type=int, help="Random seed for reproducibility")
@click.option("--mutations", type=int, default=100, help="Number of mutations")
def fuzz_input(seed: int | None, mutations: int) -> None:
    """Fuzz test input data with random mutations."""
    if seed is not None:
        random.seed(seed)

    payload = bytearray(sys.stdin.buffer.read())
    if not payload:
        raise click.ClickException("No input to fuzz.")

    for _ in range(mutations):
        _mutate_payload(payload)

    sys.stdout.buffer.write(payload)
    sys.stdout.flush()


@pipe_command.command("validate")
@click.option("--schema", type=click.Choice(["json", "pspf", "manifest"]), default="json")
@click.option("--strict", is_flag=True, help="Strict validation mode")
def validate_input(schema: str, strict: bool) -> None:
    """Validate piped input against schemas."""
    data = sys.stdin.buffer.read()
    if schema == "json":
        _validate_json(data)
    elif schema == "pspf":
        _validate_pspf(data, strict)
    else:
        _validate_manifest(data)


@pipe_command.command("corrupt")
@click.option("--probability", type=float, default=0.01, help="Corruption probability (0-1)")
@click.option(
    "--type",
    "corruption_type",
    type=click.Choice(["bit", "byte", "chunk"]),
    default="bit",
)
def corrupt_data(probability: float, corruption_type: str) -> None:
    """Randomly corrupt piped data for testing."""
    payload = bytearray(sys.stdin.buffer.read())
    CORRUPTORS[corruption_type](payload, probability)
    sys.stdout.buffer.write(payload)
    sys.stdout.flush()


def _read_stdin(buffer_size: int) -> bytes:
    """Read stdin in chunks."""
    chunks: list[bytes] = []
    while True:
        chunk = sys.stdin.buffer.read(buffer_size)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def _decode_input(data: bytes, fmt: str) -> bytes:
    """Decode input according to user preference."""
    if fmt == "json":
        try:
            parsed = json.loads(data.decode("utf-8"))
            return json.dumps(parsed).encode("utf-8")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise click.ClickException(f"Invalid JSON input: {exc}") from exc
    if fmt == "base64":
        try:
            return base64.b64decode(data)
        except Exception as exc:
            raise click.ClickException(f"Invalid base64 input: {exc}") from exc
    if fmt == "hex":
        try:
            return bytes.fromhex(data.decode("utf-8").strip())
        except Exception as exc:
            raise click.ClickException(f"Invalid hex input: {exc}") from exc
    return data


def _apply_transform(data: bytes, transform: str) -> bytes:
    """Apply simple transformations to the byte stream."""
    match transform:
        case "upper":
            return data.upper()
        case "lower":
            return data.lower()
        case "reverse":
            return data[::-1]
        case "hash":
            return hashlib.sha256(data).hexdigest().encode("utf-8")
        case _:
            return data


def _emit_output(data: bytes, destination: str, file_path: Path | None) -> None:
    """Write transformed data to the requested destination."""
    if destination == "stdout":
        sys.stdout.buffer.write(data)
        sys.stdout.flush()
        return
    if destination == "stderr":
        sys.stderr.buffer.write(data)
        sys.stderr.flush()
        return
    if not file_path:
        raise click.ClickException("File path required for file output.")
    file_path.write_bytes(data)
    perr(f"Wrote {len(data)} bytes to {file_path}")


def _generate_pattern(pattern: str, length: int) -> bytes:
    """Generate bytes for the stress command."""
    if pattern == "random":
        return os.urandom(length)
    if pattern == "zeros":
        return b"\x00" * length
    if pattern == "ones":
        return b"\xff" * length
    base = b"STRESS_TEST_PATTERN_"
    return (base * (length // len(base) + 1))[:length]


def _mutate_payload(payload: bytearray) -> None:
    """Apply a random mutation to the payload."""
    if not payload:
        return
    mutation = random.choice(["flip", "insert", "delete", "replace"])
    pos = random.randint(0, len(payload) - 1)

    if mutation == "flip":
        payload[pos] ^= 1 << random.randint(0, 7)
    elif mutation == "insert" and len(payload) < 1024 * 1024:
        payload.insert(pos, random.randint(0, 255))
    elif mutation == "delete" and len(payload) > 1:
        del payload[pos]
    else:
        payload[pos] = random.randint(0, 255)


def _validate_json(data: bytes) -> None:
    """Validate JSON input."""
    try:
        parsed = json.loads(data.decode("utf-8"))
        print(json.dumps(parsed, indent=2))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise click.ClickException(f"Invalid JSON: {exc}") from exc


def _validate_pspf(data: bytes, strict: bool) -> None:
    """Validate basic PSPF structure."""
    if len(data) < 4:
        raise click.ClickException("File too small to be PSPF.")
    if b"PSPF" not in data[:16]:
        perr("❌ Invalid PSPF magic")
        if strict:
            raise click.ClickException("Strict mode enabled; failing validation.")


def _validate_manifest(data: bytes) -> None:
    """Validate manifest JSON structure."""
    try:
        manifest = json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise click.ClickException(f"Invalid manifest: {exc}") from exc

    required = {"name", "version", "slots"}
    missing = required - manifest.keys()
    if missing:
        raise click.ClickException(f"Missing required fields: {sorted(missing)}")


def _corrupt_bit(payload: bytearray, probability: float) -> None:
    for i in range(len(payload)):
        for bit in range(8):
            if random.random() < probability:
                payload[i] ^= 1 << bit


def _corrupt_byte(payload: bytearray, probability: float) -> None:
    for i in range(len(payload)):
        if random.random() < probability:
            payload[i] = random.randint(0, 255)


def _corrupt_chunk(payload: bytearray, probability: float) -> None:
    chunk_size = max(1, len(payload) // 100 or 1)
    for start in range(0, len(payload), chunk_size):
        if random.random() < probability:
            end = min(start + chunk_size, len(payload))
            for idx in range(start, end):
                payload[idx] = random.randint(0, 255)


CORRUPTORS: dict[str, Callable[[bytearray, float], None]] = {
    "bit": _corrupt_bit,
    "byte": _corrupt_byte,
    "chunk": _corrupt_chunk,
}


# 🌶️📦🔚
