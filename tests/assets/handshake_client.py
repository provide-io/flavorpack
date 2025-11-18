#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test handshake client used by Pretaster integration scenarios."""

import os
import socket
import sys
import time
from typing import NoReturn


def log_print(message: str) -> None:
    print(f"HANDSHAKE_CLIENT: {message}", file=sys.stderr)


def main() -> NoReturn:  # noqa: C901 - test script intentionally performs many sequential steps
    log_print("Python handshake client starting...")

    port_str = os.environ.get("PSP_HANDSHAKE_PORT")
    secret = os.environ.get("PSP_HANDSHAKE_SECRET")

    if not port_str or not secret:
        log_print("Error: Handshake port or secret not found in environment variables.")
        sys.exit(1)

    try:
        port = int(port_str)
    except ValueError:
        log_print(f"Error: Invalid handshake port value: {port_str}")
        sys.exit(1)

    log_print(f"Attempting to connect to Go launcher handshake server on 127.0.0.1:{port}")

    client_socket = None  # Initialize client_socket to None
    try:
        # Try to connect for a few seconds
        conn_attempts = 5
        conn_success = False
        for i in range(conn_attempts):
            try:
                client_socket = socket.create_connection(("127.0.0.1", port), timeout=2)
                conn_success = True
                break
            except ConnectionRefusedError:
                log_print(f"Connection refused (attempt {i + 1}/{conn_attempts}), retrying in 1s...")
                time.sleep(1)
            except TimeoutError:
                log_print(f"Connection timed out (attempt {i + 1}/{conn_attempts}), retrying in 1s...")
                time.sleep(1)

        if not conn_success:
            log_print(f"Error: Could not connect to handshake server after {conn_attempts} attempts.")
            sys.exit(1)

        log_print(f"Connected. Sending secret (len: {len(secret)}).")
        client_socket.sendall(secret.encode("utf-8"))  # Assuming secret is plain string

        log_print("Secret sent. Waiting for response from launcher...")
        # Wait for a single byte response
        response = client_socket.recv(1)
        log_print(f"Received response: {response!r}")

        if response == b"\x01":
            log_print("Handshake successful (all-clear received). Client will now proceed (simulated).")
            # In a real app, this is where the main application logic would start
            print(
                "HANDSHAKE_CLIENT_STDOUT: All clear, proceeding with dummy task.",
                file=sys.stdout,
            )
            sys.exit(0)
        elif response == b"\x00":
            log_print("Handshake failed (terminate signal received). Client exiting.")
            sys.exit(1)
        else:
            log_print(f"Handshake failed (unexpected response: {response!r}). Client exiting.")
            sys.exit(1)

    except Exception as e:
        log_print(f"An error occurred: {e}")
        sys.exit(1)
    finally:
        if client_socket:
            client_socket.close()
            log_print("Socket closed.")


if __name__ == "__main__":
    # Ensure appLogger (from Go) has a chance to start, small delay
    # This is a hack for testing; real Python app might not need this.
    # time.sleep(0.1)
    main()

# 🌶️📦🔚
