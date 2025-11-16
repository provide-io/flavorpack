#!/usr/bin/env python3
"""Progress reporting utilities for Flavor."""

from contextlib import contextmanager
import time
from typing import Any, ClassVar


class ProgressBar:
    """A simple progress bar implementation."""

    def __init__(
        self,
        total: int,
        description: str = "",
        width: int = 40,
        show_rate: bool = False,
    ) -> None:
        """Initialize progress bar.

        Args:
            total: Total number of items
            description: Description text
            width: Width of the progress bar
            show_rate: Whether to show processing rate
        """
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self.show_rate = show_rate
        self.finished = False
        self.start_time: float | None = None

    def start(self) -> None:
        """Start timing for rate calculation."""
        self.start_time = time.time()

    def update(self, value: int) -> None:
        """Update progress to specific value.

        Args:
            value: New progress value
        """
        self.current = min(value, self.total)
        if self.current >= self.total:
            self.finished = True

    def increment(self, amount: int = 1) -> None:
        """Increment progress by amount.

        Args:
            amount: Amount to increment
        """
        self.update(self.current + amount)

    def finish(self) -> None:
        """Mark progress as finished."""
        self.current = self.total
        self.finished = True

    def get_percentage(self) -> float:
        """Get current percentage.

        Returns:
            Percentage complete (0-100)
        """
        if self.total == 0:
            return 100.0 if self.finished else 0.0
        return (self.current / self.total) * 100

    def get_rate(self) -> float:
        """Get processing rate.

        Returns:
            Items per second
        """
        if self.start_time is None:
            return 0.0

        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0

        return self.current / elapsed

    def render(self) -> str:
        """Render progress bar as string.

        Returns:
            Rendered progress bar
        """
        percentage = self.get_percentage()
        filled = int(self.width * percentage / 100)
        bar = "█" * filled + "░" * (self.width - filled)

        output = f"{self.description}: [{bar}] {percentage:.0f}%"

        if self.show_rate and self.start_time:
            rate = self.get_rate()
            output += f" ({rate:.1f}/s)"

        return output


class Spinner:
    """A spinner for indeterminate progress."""

    FRAMES: ClassVar[list[str]] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, description: str = "") -> None:
        """Initialize spinner.

        Args:
            description: Description text
        """
        self.description = description
        self.frame_index = 0
        self.finished = False

    def tick(self) -> None:
        """Advance to next animation frame."""
        self.frame_index = (self.frame_index + 1) % len(self.FRAMES)

    def render(self) -> str:
        """Render current spinner frame.

        Returns:
            Rendered spinner string
        """
        if self.finished:
            return f"✓ {self.description}"

        frame = self.FRAMES[self.frame_index]
        return f"{frame} {self.description}"

    def finish(self) -> None:
        """Mark spinner as finished."""
        self.finished = True


class ProgressReporter:
    """Manages multiple progress bars and spinners."""

    def __init__(self, enabled: bool = True) -> None:
        """Initialize progress reporter.

        Args:
            enabled: Whether progress reporting is enabled
        """
        self.enabled = enabled
        self.active_bars: list[ProgressBar] = []
        self.active_spinners: list[Spinner] = []

    def create_bar(
        self, total: int, description: str = "", **kwargs: Any
    ) -> ProgressBar | None:
        """Create a new progress bar.

        Args:
            total: Total number of items
            description: Description text
            **kwargs: Additional ProgressBar arguments

        Returns:
            ProgressBar instance or None if disabled
        """
        if not self.enabled:
            return None

        bar = ProgressBar(total, description, **kwargs)
        self.active_bars.append(bar)
        return bar

    def create_spinner(self, description: str = "") -> Spinner | None:
        """Create a new spinner.

        Args:
            description: Description text

        Returns:
            Spinner instance or None if disabled
        """
        if not self.enabled:
            return None

        spinner = Spinner(description)
        self.active_spinners.append(spinner)
        return spinner

    def cleanup_finished(self) -> None:
        """Remove finished progress bars."""
        self.active_bars = [bar for bar in self.active_bars if not bar.finished]
        self.active_spinners = [s for s in self.active_spinners if not s.finished]

    @contextmanager
    def task(self, total: int, description: str = "", **kwargs: Any) -> Any:
        """Context manager for a task with progress.

        Args:
            total: Total number of items
            description: Description text
            **kwargs: Additional ProgressBar arguments

        Yields:
            ProgressBar instance or None
        """
        bar = self.create_bar(total, description, **kwargs)
        if bar:
            bar.start()

        try:
            yield bar
        finally:
            if bar:
                bar.finish()
                self.cleanup_finished()
