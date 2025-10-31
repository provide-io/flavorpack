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


class SignalTester:
    def __init__(self) -> None:
        self.signals_received = []
        self.original_handlers = {}

    def signal_handler(self, signum, frame) -> None:
        """Handle signals and record them"""
        signal_name = signal.Signals(signum).name
        self.signals_received.append((signal_name, time.time()))
        click.echo(f"\n📨 Received {signal_name}")

        if signum == signal.SIGINT:
            click.echo("  Gracefully shutting down...")
            # Simulate cleanup
            time.sleep(0.5)
            sys.exit(0)

    def install_handlers(self) -> None:
        """Install signal handlers"""
        for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP]:
            try:
                self.original_handlers[sig] = signal.signal(sig, self.signal_handler)
            except Exception as e:
                click.echo(f"  ⚠️ Could not install handler for {signal.Signals(sig).name}: {e}")

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
        click.echo(f"💤 Sleeping for {sleep} seconds...")
        try:
            time.sleep(sleep)
            sys.exit(exit_code)
        except KeyboardInterrupt:
            click.echo("\n⚠️ Sleep interrupted by signal", file=sys.stderr)
            sys.exit(130)  # Standard exit code for SIGINT

    click.secho("=" * 60, fg="cyan")
    click.secho("🛑 SIGNAL HANDLING TEST", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")

    tester = SignalTester()

    # Check current signal handlers
    click.secho("\n📊 Current Signal Handlers:", fg="yellow")
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP]:
        try:
            handler = signal.getsignal(sig)
            handler_name = (
                "DEFAULT" if handler == signal.SIG_DFL else "IGNORE" if handler == signal.SIG_IGN else "CUSTOM"
            )
            click.echo(f"  {signal.Signals(sig).name}: {handler_name}")
        except (ValueError, AttributeError):
            pass

    if test_mode:
        # Automated test mode
        click.echo(f"  Timeout: {timeout} seconds")

        # Install handlers
        click.secho("\n📝 Installing Signal Handlers:", fg="blue")
        tester.install_handlers()

        # Send signal to self after delay
        def send_signal_delayed() -> None:
            time.sleep(2)
            click.echo("\n🚀 Sending SIGTERM to self...")
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(1)
            click.echo("🚀 Sending SIGINT to self...")
            os.kill(os.getpid(), signal.SIGINT)

        thread = threading.Thread(target=send_signal_delayed)
        thread.daemon = True
        thread.start()

        # Wait for signals
        click.echo("\n⏳ Waiting for signals...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(0.1)
            if len(tester.signals_received) >= 2:
                break

        # Report results
        click.secho("\n📋 Test Results:", fg="cyan")
        if tester.signals_received:
            for sig_name, sig_time in tester.signals_received:
                click.echo(f"    • {sig_name} at {sig_time:.2f}")
        else:
            click.secho("  ❌ No signals received", fg="red")

        # Restore handlers
        tester.restore_handlers()

    else:
        # Interactive mode
        click.secho("\n📝 Interactive Signal Test", fg="green")
        click.echo("Installing signal handlers...")

        tester.install_handlers()

        click.secho("\n📌 Instructions:", fg="yellow")
        click.echo("  1. Press Ctrl+C to send SIGINT")
        click.echo("  2. From another terminal: kill -TERM <pid>")
        click.echo("  3. From another terminal: kill -HUP <pid>")
        click.echo(f"\n  PID: {os.getpid()}")
        click.echo(f"  Press Ctrl+C or wait {timeout} seconds to exit\n")

        # Wait for signals
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                remaining = timeout - (time.time() - start_time)
                sys.stdout.write(f"\r⏳ Waiting for signals... {remaining:.1f}s remaining")
                sys.stdout.flush()
                time.sleep(0.1)
            click.echo("\n\n⏰ Timeout reached")
        except KeyboardInterrupt:
            pass

        # Show results
        click.secho("\n\n📋 Signals Received:", fg="cyan")
        if tester.signals_received:
            for sig_name, sig_time in tester.signals_received:
                click.echo(f"  • {sig_name}")
        else:
            click.echo("  None")

        # Restore handlers
        tester.restore_handlers()

    # Test launcher capabilities
    click.secho("\n🚀 Launcher Signal Capabilities:", fg="magenta")

    launcher_name = (
        "rust"
        if "FLAVOR_COMMAND_NAME" not in os.environ or os.environ.get("FLAVOR_COMMAND_NAME") == sys.argv[0]
        else "go"
    )

    if launcher_name == "rust":
        click.echo("    • Forwards SIGTERM/SIGINT to child process")
        click.echo("    • Graceful shutdown with 10-second timeout")
        click.echo("    • Process cleanup on exit")
    else:
        click.secho("  ⚠️ Go launcher: Limited signal support", fg="yellow")
        click.echo("    • Basic signal handling")
        click.echo("    • May not forward all signals properly")


# 🌶️📦🔚
