"""Tests for the subprocess utility function."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from flavor.packaging.util import run_subprocess
from flavor.exceptions import BuildError


class TestRunSubprocess:
    """Test suite for the run_subprocess utility function."""
    
    def test_successful_command(self):
        """Test that a successful command returns stdout."""
        result = run_subprocess(["echo", "hello world"])
        assert result == "hello world"
    
    def test_command_with_cwd(self, tmp_path):
        """Test that cwd parameter is respected."""
        # Create a test directory
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Run pwd command in the test directory
        result = run_subprocess(["pwd"], cwd=test_dir)
        assert str(test_dir) in result
    
    def test_failed_command_raises_build_error(self):
        """Test that a failed command raises BuildError."""
        with pytest.raises(BuildError) as exc_info:
            run_subprocess(["ls", "/nonexistent/directory/that/does/not/exist"])
        
        assert "Command failed" in str(exc_info.value)
        assert "ls /nonexistent/directory/that/does/not/exist" in str(exc_info.value)
    
    def test_environment_variable_set(self):
        """Test that NO_COVERAGE environment variable is set."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output",
                stderr=""
            )
            
            run_subprocess(["echo", "test"])
            
            # Verify subprocess.run was called with modified environment
            call_args = mock_run.call_args
            env = call_args.kwargs["env"]
            assert "NO_COVERAGE" in env
            assert env["NO_COVERAGE"] == "1"
    
    def test_command_output_is_stripped(self):
        """Test that command output is stripped of whitespace."""
        result = run_subprocess(["echo", "  spaced output  "])
        assert result == "spaced output"
    
    def test_stderr_included_in_error(self):
        """Test that stderr is included in the BuildError message."""
        with pytest.raises(BuildError) as exc_info:
            # Use a command that will definitely fail with stderr output
            run_subprocess(["python3", "-c", "import sys; sys.stderr.write('error message'); sys.exit(1)"])
        
        assert "error message" in str(exc_info.value)
    
    def test_empty_command_list(self):
        """Test handling of empty command list."""
        with pytest.raises(Exception):  # subprocess.run will raise an exception for empty command
            run_subprocess([])
    
    def test_path_as_cwd(self, tmp_path):
        """Test that Path objects work as cwd parameter."""
        test_path = Path(tmp_path)
        result = run_subprocess(["pwd"], cwd=test_path)
        assert str(test_path) in result
    
    def test_string_as_cwd(self, tmp_path):
        """Test that string paths work as cwd parameter."""
        test_path = str(tmp_path)
        result = run_subprocess(["pwd"], cwd=test_path)
        assert test_path in result