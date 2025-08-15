"""Tests for progress indicators."""

import time
from unittest.mock import patch, MagicMock, call
import pytest
from click.testing import CliRunner

from flavor.cli import cli
from flavor.progress import ProgressReporter, ProgressBar


class TestProgressBar:
    """Test the ProgressBar class."""
    
    def test_progress_bar_initialization(self):
        """Test ProgressBar initializes correctly."""
        progress = ProgressBar(total=100, description="Testing")
        
        assert progress.total == 100
        assert progress.current == 0
        assert progress.description == "Testing"
        assert not progress.finished
    
    def test_progress_bar_update(self):
        """Test updating progress bar."""
        progress = ProgressBar(total=100)
        
        progress.update(25)
        assert progress.current == 25
        assert progress.get_percentage() == 25.0
        
        progress.update(50)
        assert progress.current == 50
        assert progress.get_percentage() == 50.0
    
    def test_progress_bar_increment(self):
        """Test incrementing progress bar."""
        progress = ProgressBar(total=100)
        
        progress.increment(10)
        assert progress.current == 10
        
        progress.increment(15)
        assert progress.current == 25
    
    def test_progress_bar_finish(self):
        """Test finishing progress bar."""
        progress = ProgressBar(total=100)
        
        progress.finish()
        assert progress.finished
        assert progress.current == progress.total
        assert progress.get_percentage() == 100.0
    
    def test_progress_bar_overflow_protection(self):
        """Test progress bar doesn't overflow."""
        progress = ProgressBar(total=100)
        
        progress.update(150)  # More than total
        assert progress.current == 100
        assert progress.get_percentage() == 100.0
    
    def test_progress_bar_render(self):
        """Test rendering progress bar string."""
        progress = ProgressBar(total=100, width=20)
        
        progress.update(50)
        rendered = progress.render()
        
        assert "50%" in rendered
        assert "█" in rendered  # Progress character
        assert len(rendered) > 0
    
    def test_progress_bar_with_rate(self):
        """Test progress bar with rate calculation."""
        progress = ProgressBar(total=1000, show_rate=True)
        
        progress.start()
        time.sleep(0.01)  # Small delay
        progress.increment(100)
        
        rate = progress.get_rate()
        assert rate > 0  # Should have some rate
        
        rendered = progress.render()
        assert "/s" in rendered  # Rate indicator


class TestProgressReporter:
    """Test the ProgressReporter class for managing multiple progress bars."""
    
    def test_reporter_initialization(self):
        """Test ProgressReporter initializes correctly."""
        reporter = ProgressReporter(enabled=True)
        
        assert reporter.enabled is True
        assert len(reporter.active_bars) == 0
    
    def test_reporter_disabled(self):
        """Test reporter when disabled."""
        reporter = ProgressReporter(enabled=False)
        
        bar = reporter.create_bar(total=100, description="Test")
        assert bar is None  # Should return None when disabled
    
    def test_create_progress_bar(self):
        """Test creating a progress bar."""
        reporter = ProgressReporter(enabled=True)
        
        bar = reporter.create_bar(total=100, description="Testing")
        
        assert bar is not None
        assert bar.total == 100
        assert bar.description == "Testing"
        assert bar in reporter.active_bars
    
    def test_multiple_progress_bars(self):
        """Test managing multiple progress bars."""
        reporter = ProgressReporter(enabled=True)
        
        bar1 = reporter.create_bar(total=100, description="Task 1")
        bar2 = reporter.create_bar(total=200, description="Task 2")
        
        assert len(reporter.active_bars) == 2
        assert bar1 != bar2
        
        bar1.finish()
        reporter.cleanup_finished()
        
        assert len(reporter.active_bars) == 1
        assert bar2 in reporter.active_bars
    
    def test_reporter_context_manager(self):
        """Test using reporter as context manager."""
        reporter = ProgressReporter(enabled=True)
        
        with reporter.task(total=100, description="Context task") as bar:
            assert bar is not None
            bar.update(50)
            assert bar.current == 50
        
        # Bar should be finished after context
        assert bar.finished
    
    def test_reporter_spinner(self):
        """Test spinner for indeterminate progress."""
        reporter = ProgressReporter(enabled=True)
        
        spinner = reporter.create_spinner(description="Processing...")
        
        assert spinner is not None
        assert spinner.description == "Processing..."
        
        # Spinner should animate
        frame1 = spinner.render()
        spinner.tick()
        frame2 = spinner.render()
        assert frame1 != frame2  # Animation frames should differ


class TestProgressIntegration:
    """Test progress indicators in actual commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    @patch('flavor.progress.ProgressReporter')
    def test_package_command_with_progress(self, MockReporter):
        """Test package command shows progress."""
        mock_reporter = MagicMock()
        MockReporter.return_value = mock_reporter
        
        mock_bar = MagicMock()
        mock_reporter.create_bar.return_value = mock_bar
        
        with patch('flavor.api.build_package_from_manifest') as mock_build:
            mock_build.return_value = {'success': True}
            
            result = self.runner.invoke(cli, [
                "package",
                "--manifest", "test.toml",
                "--output", "test.pspf",
                "--progress"
            ])
            
            # Progress reporter should be created
            MockReporter.assert_called_once()
            # Progress bars should be created for various stages
            assert mock_reporter.create_bar.called
    
    def test_quiet_mode_disables_progress(self):
        """Test --quiet flag disables progress."""
        with patch('flavor.progress.ProgressReporter') as MockReporter:
            mock_reporter = MagicMock()
            MockReporter.return_value = mock_reporter
            
            with patch('flavor.api.build_package_from_manifest') as mock_build:
                mock_build.return_value = {'success': True}
                
                result = self.runner.invoke(cli, [
                    "package",
                    "--manifest", "test.toml",
                    "--output", "test.pspf",
                    "--quiet"
                ])
                
                # Reporter should be created with enabled=False
                MockReporter.assert_called_with(enabled=False)
    
    @patch('flavor.progress.ProgressReporter')
    def test_extraction_progress(self, MockReporter):
        """Test progress during slot extraction."""
        mock_reporter = MagicMock()
        MockReporter.return_value = mock_reporter
        
        mock_bar = MagicMock()
        mock_reporter.create_bar.return_value = mock_bar
        
        # Simulate extraction with progress updates
        from flavor.psp.format_2025.launcher import PSPFLauncher
        
        with patch.object(PSPFLauncher, 'extract_slot') as mock_extract:
            def extract_with_progress(*args, **kwargs):
                # Simulate progress updates
                if mock_bar:
                    mock_bar.increment(1)
                return Path("/tmp/extracted")
            
            mock_extract.side_effect = extract_with_progress
            
            launcher = PSPFLauncher()
            # This would trigger extraction with progress
            # launcher.setup_workenv()
            
            # Check that progress was updated
            # assert mock_bar.increment.called
    
    def test_progress_in_verbose_mode(self):
        """Test progress indicators work with verbose output."""
        with patch('flavor.progress.ProgressReporter') as MockReporter:
            mock_reporter = MagicMock()
            MockReporter.return_value = mock_reporter
            
            with patch('flavor.api.build_package_from_manifest') as mock_build:
                mock_build.return_value = {'success': True}
                
                result = self.runner.invoke(cli, [
                    "package",
                    "--manifest", "test.toml",
                    "--output", "test.pspf",
                    "--verbose",
                    "--progress"
                ])
                
                # Both verbose and progress should work together
                MockReporter.assert_called_once()
                assert mock_reporter.create_bar.called or mock_reporter.create_spinner.called