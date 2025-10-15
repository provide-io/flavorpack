#!/usr/bin/env python3
"""Pipe data processing - stdin/stderr handling with various transformations"""

import base64
import hashlib
import json
from pathlib import Path
import sys

import click


@click.group("pipe")
def pipe_command() -> None:
    """🔧 Process piped input/output"""
    pass


@pipe_command.command("stdin")
@click.option("--format", type=click.Choice(["raw", "json", "base64", "hex"]), default="raw")
@click.option("--output", type=click.Choice(["stdout", "stderr", "file"]), default="stdout")
@click.option("--file", type=click.Path(path_type=Path), help="Output file path")
@click.option(
    "--transform",
    type=click.Choice(["upper", "lower", "reverse", "hash", "none"]),
    default="none",
)
@click.option("--buffer-size", type=int, default=8192, help="Buffer size for reading")
def process_stdin(format, output, file, transform, buffer_size) -> None:
    """Process data from stdin with various transformations"""

    # Read from stdin
    if sys.stdin.isatty():
        click.echo("No input detected. Pipe data to this command.", err=True)
        sys.exit(1)

    # Read in chunks for large inputs
    chunks = []
    while True:
        chunk = sys.stdin.buffer.read(buffer_size)
        if not chunk:
            break
        chunks.append(chunk)

    data = b"".join(chunks)

    # Parse input based on format
    if format == "json":
        try:
            data = json.loads(data.decode("utf-8"))
            data = json.dumps(data).encode("utf-8")  # Re-encode for processing
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            click.echo(f"Invalid JSON input: {e}", err=True)
            sys.exit(1)
    elif format == "base64":
        try:
            data = base64.b64decode(data)
        except Exception as e:
            click.echo(f"Invalid base64 input: {e}", err=True)
            sys.exit(1)
    elif format == "hex":
        try:
            data = bytes.fromhex(data.decode("utf-8").strip())
        except Exception as e:
            click.echo(f"Invalid hex input: {e}", err=True)
            sys.exit(1)

    # Apply transformation
    if transform == "upper":
        data = data.upper()
    elif transform == "lower":
        data = data.lower()
    elif transform == "reverse":
        data = data[::-1]
    elif transform == "hash":
        data = hashlib.sha256(data).hexdigest().encode("utf-8")

    # Output the result
    if output == "stdout":
        sys.stdout.buffer.write(data)
        sys.stdout.flush()
    elif output == "stderr":
        sys.stderr.buffer.write(data)
        sys.stderr.flush()
    elif output == "file":
        if not file:
            click.echo("File path required for file output", err=True)
            sys.exit(1)
        Path(file).write_bytes(data)
        click.echo(f"Wrote {len(data)} bytes to {file}", err=True)


@pipe_command.command("stress")
@click.option("--size", type=int, default=1024 * 1024, help="Size of data to generate (bytes)")
@click.option(
    "--pattern",
    type=click.Choice(["random", "zeros", "ones", "pattern"]),
    default="random",
)
@click.option("--chunk-size", type=int, default=8192, help="Chunk size for output")
def stress_test(size, pattern, chunk_size) -> None:
    """Generate stress test data to stdout"""
    import os

    remaining = size
    while remaining > 0:
        chunk_len = min(chunk_size, remaining)

        if pattern == "random":
            chunk = os.urandom(chunk_len)
        elif pattern == "zeros":
            chunk = b"\x00" * chunk_len
        elif pattern == "ones":
            chunk = b"\xff" * chunk_len
        elif pattern == "pattern":
            # Repeating pattern
            base = b"STRESS_TEST_PATTERN_"
            chunk = (base * (chunk_len // len(base) + 1))[:chunk_len]

        sys.stdout.buffer.write(chunk)
        remaining -= chunk_len

    sys.stdout.flush()


@pipe_command.command("fuzz")
@click.option("--seed", type=int, help="Random seed for reproducibility")
@click.option("--mutations", type=int, default=100, help="Number of mutations")
def fuzz_input(seed, mutations) -> None:
    """Fuzz test input data with random mutations"""
    import random

    if seed:
        random.seed(seed)

    # Read input
    data = sys.stdin.buffer.read()
    if not data:
        click.echo("No input to fuzz", err=True)
        sys.exit(1)

    data = bytearray(data)

    # Apply random mutations
    for _ in range(mutations):
        mutation_type = random.choice(["flip", "insert", "delete", "replace"])

        if len(data) == 0:
            continue

        pos = random.randint(0, len(data) - 1)

        if mutation_type == "flip":
            # Flip random bit
            data[pos] ^= 1 << random.randint(0, 7)
        elif mutation_type == "insert" and len(data) < 1024 * 1024:  # Limit growth
            # Insert random byte
            data.insert(pos, random.randint(0, 255))
        elif mutation_type == "delete" and len(data) > 1:
            # Delete byte
            del data[pos]
        elif mutation_type == "replace":
            # Replace with random byte
            data[pos] = random.randint(0, 255)

    sys.stdout.buffer.write(bytes(data))
    sys.stdout.flush()


@pipe_command.command("validate")
@click.option("--schema", type=click.Choice(["json", "pspf", "manifest"]), default="json")
@click.option("--strict", is_flag=True, help="Strict validation mode")
def validate_input(schema, strict) -> None:
    """Validate piped input against schemas"""

    data = sys.stdin.buffer.read()

    if schema == "json":
        try:
            parsed = json.loads(data.decode("utf-8"))
            # Output pretty-printed valid JSON
            print(json.dumps(parsed, indent=2))
            click.echo("✅ Valid JSON", err=True)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            click.echo(f"❌ Invalid JSON: {e}", err=True)
            sys.exit(1)

    elif schema == "pspf":
        # Check for PSPF magic bytes
        if len(data) < 4:
            click.echo("❌ File too small to be PSPF", err=True)
            sys.exit(1)

        # Check magic wand at end
        if data[-4:] == "🪄".encode():
            click.echo("✅ Valid PSPF magic", err=True)
        else:
            click.echo("❌ Invalid PSPF magic", err=True)
            if not strict:
                click.echo("  (Use --strict to fail on validation errors)", err=True)
            else:
                sys.exit(1)

    elif schema == "manifest":
        try:
            manifest = json.loads(data.decode("utf-8"))
            required = ["name", "version", "slots"]
            missing = [k for k in required if k not in manifest]

            if missing:
                click.echo(f"❌ Missing required fields: {missing}", err=True)
                sys.exit(1)

            click.echo("✅ Valid manifest structure", err=True)

        except Exception as e:
            click.echo(f"❌ Invalid manifest: {e}", err=True)
            sys.exit(1)


@pipe_command.command("corrupt")
@click.option("--probability", type=float, default=0.01, help="Corruption probability (0-1)")
@click.option(
    "--type",
    "corruption_type",
    type=click.Choice(["bit", "byte", "chunk"]),
    default="bit",
)
def corrupt_data(probability, corruption_type) -> None:
    """Randomly corrupt piped data for testing"""
    import random

    data = bytearray(sys.stdin.buffer.read())

    if corruption_type == "bit":
        # Flip random bits
        for i in range(len(data)):
            for bit in range(8):
                if random.random() < probability:
                    data[i] ^= 1 << bit

    elif corruption_type == "byte":
        # Corrupt entire bytes
        for i in range(len(data)):
            if random.random() < probability:
                data[i] = random.randint(0, 255)

    elif corruption_type == "chunk":
        # Corrupt chunks of data
        chunk_size = max(1, len(data) // 100)
        for i in range(0, len(data), chunk_size):
            if random.random() < probability:
                for j in range(min(chunk_size, len(data) - i)):
                    data[i + j] = random.randint(0, 255)

    sys.stdout.buffer.write(bytes(data))
    sys.stdout.flush()
