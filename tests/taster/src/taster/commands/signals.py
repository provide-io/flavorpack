#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test signal handling (SIGTERM/SIGINT)"""

import os
import signal
import sys
import threading
import time

import click
from provide.foundation.console import perr, pout


class SignalTester:
    def __init__(self) -> None:
        self.signals_received = []
        self.original_handlers = {}

    def signal_handler(self, signum, frame) -> None:
        """Handle signals and record them"""
        signal_name = signal.Signals(signum).name
        self.signals_received.append((signal_name, time.time()))
        pout(f"\n📨 Received {signal_name}")

        if signum == signal.SIGINT:
            pout("  Gracefully shutting down...")
            # Simulate cleanup
            time.sleep(0.5)
            sys.exit(0)

    def install_handlers(self) -> None:
        """Install signal handlers"""
        for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP]:
            try:
                self.original_handlers[sig] = signal.signal(sig, self.signal_handler)
            except Exception as e:
                pout(f"  ⚠️ Could not install handler for {signal.Signals(sig).name}: {e}")

    def restore_handlers(self) -> None:
        """Restore original handlers"""
        for sig, handler in self.original_handlers.items():
            signal.signal(sig, handler)


@click.command("signals")
@click.option("--test-mode", is_flag=True, help="Run automated test")
@click.option("--timeout", default=10, help="Timeout for signal test")
@click.option("--sleep", type=float, help="Just sleep for N seconds (simpler than full test)")
@click.option("--exit-code", type=int, default=0, help="Exit code to use on signal/timeout")
def signals_command(test_mode, timeout, sleep, exit_code) -> None:
    """🛑 Test signal handling (SIGTERM/SIGINT)"""

    # Simple sleep mode
    if sleep is not None:
        pout(f"💤 Sleeping for {sleep} seconds...")
        try:
            time.sleep(sleep)
            sys.exit(exit_code)
        except KeyboardInterrupt:
            pout("\n⚠️ Sleep interrupted by signal", file=sys.stderr)
            sys.exit(130)  # Standard exit code for SIGINT

    pout("=" * 60, color="cyan")
    pout("🛑 SIGNAL HANDLING TEST", color="cyan", bold=True)
    pout("=" * 60, color="cyan")

    tester = SignalTester()

    # Check current signal handlers
    pout("\n📊 Current Signal Handlers:", color="yellow")
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP]:
        try:
            handler = signal.getsignal(sig)
            handler_name = (
                "DEFAULT" if handler == signal.SIG_DFL else "IGNORE" if handler == signal.SIG_IGN else "CUSTOM"
            )
            pout(f"  {signal.Signals(sig).name}: {handler_name}")
        except (ValueError, AttributeError):
            pass

    if test_mode:
        # Automated test mode
        pout(f"  Timeout: {timeout} seconds")

        # Install handlers
        pout("\n📝 Installing Signal Handlers:", color="blue")
        tester.install_handlers()

        # Send signal to self after delay
        def send_signal_delayed() -> None:
            time.sleep(2)
            pout("\n🚀 Sending SIGTERM to self...")
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(1)
            pout("🚀 Sending SIGINT to self...")
            os.kill(os.getpid(), signal.SIGINT)

        thread = threading.Thread(target=send_signal_delayed)
        thread.daemon = True
        thread.start()

        # Wait for signals
        pout("\n⏳ Waiting for signals...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(0.1)
            if len(tester.signals_received) >= 2:
                break

        # Report results
        pout("\n📋 Test Results:", color="cyan")
        if tester.signals_received:
            for sig_name, sig_time in tester.signals_received:
                pout(f"    • {sig_name} at {sig_time:.2f}")
        else:
            pout("  ❌ No signals received", color="red")

        # Restore handlers
        tester.restore_handlers()

    else:
        # Interactive mode
        pout("\n📝 Interactive Signal Test", color="green")
        pout("Installing signal handlers...")

        tester.install_handlers()

        pout("\n📌 Instructions:", color="yellow")
        pout("  1. Press Ctrl+C to send SIGINT")
        pout("  2. From another terminal: kill -TERM <pid>")
        pout("  3. From another terminal: kill -HUP <pid>")
        pout(f"\n  PID: {os.getpid()}")
        pout(f"  Press Ctrl+C or wait {timeout} seconds to exit\n")

        # Wait for signals
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                remaining = timeout - (time.time() - start_time)
                sys.stdout.write(f"\r⏳ Waiting for signals... {remaining:.1f}s remaining")
                sys.stdout.flush()
                time.sleep(0.1)
            pout("\n\n⏰ Timeout reached")
        except KeyboardInterrupt:
            pass

        # Show results
        pout("\n\n📋 Signals Received:", color="cyan")
        if tester.signals_received:
            for sig_name, sig_time in tester.signals_received:
                pout(f"  • {sig_name}")
        else:
            pout("  None")

        # Restore handlers
        tester.restore_handlers()

    # Test launcher capabilities
    pout("\n🚀 Launcher Signal Capabilities:", color="magenta")

    launcher_name = (
        "rust"
        if "FLAVOR_COMMAND_NAME" not in os.environ or os.environ.get("FLAVOR_COMMAND_NAME") == sys.argv[0]
        else "go"
    )

    if launcher_name == "rust":
        pout("    • Forwards SIGTERM/SIGINT to child process")
        pout("    • Graceful shutdown with 10-second timeout")
        pout("    • Process cleanup on exit")
    else:
        pout("  ⚠️ Go launcher: Limited signal support", color="yellow")
        pout("    • Basic signal handling")
        pout("    • May not forward all signals properly")


# 🌶️📦🔚
