"""Test ingredients/manager.py - Ingredient management system."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from flavor.ingredients.manager import IngredientInfo, IngredientManager


@pytest.mark.unit
class TestIngredientManagerInit:
    """Test IngredientManager initialization."""

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def test_initialization(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> None:
        """Test manager initialization sets up paths and directories."""
        mock_platform.return_value = "linux_amd64"

        manager = IngredientManager()

        # Check paths are set correctly
        assert manager.flavor_root.name == "flavorpack"
        assert manager.ingredients_dir.name == "dist"
        assert manager.ingredients_bin.name == "bin"
        assert manager.current_platform == "linux_amd64"

        # Check directories were created
        assert mock_ensure_dir.call_count == 2

        # Check binary loader was initialized
        mock_binary_loader.assert_called_once()

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def test_xdg_cache_path(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> None:
        """Test XDG cache path detection."""
        mock_platform.return_value = "darwin_arm64"

        with patch.dict("os.environ", {"XDG_CACHE_HOME": "/custom/cache"}):
            manager = IngredientManager()

        assert "/custom/cache" in str(manager.installed_ingredients_bin)
        assert "flavor/ingredients/bin" in str(manager.installed_ingredients_bin)


@pytest.mark.unit
class TestPlatformCompatibility:
    """Test platform compatibility checking."""

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> IngredientManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return IngredientManager()

    def test_platform_compatible_exact_match(self) -> None:
        """Test exact platform match is compatible."""
        manager = self.setup_manager()
        assert manager._is_platform_compatible("flavor-go-launcher-linux_amd64")

    def test_platform_incompatible_different_platform(self) -> None:
        """Test different platform is incompatible."""
        manager = self.setup_manager()
        assert not manager._is_platform_compatible("flavor-go-launcher-darwin_arm64")

    def test_platform_compatible_no_platform_info(self) -> None:
        """Test files without platform info are assumed compatible."""
        manager = self.setup_manager()
        assert manager._is_platform_compatible("generic-launcher")

    def test_platform_compatible_partial_match(self) -> None:
        """Test platform substring match."""
        manager = self.setup_manager()
        assert manager._is_platform_compatible("tool-linux_amd64-v1.0")


@pytest.mark.unit
class TestIngredientParsing:
    """Test ingredient identity parsing."""

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> IngredientManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return IngredientManager()

    def test_parse_go_launcher(self) -> None:
        """Test parsing Go launcher identity."""
        manager = self.setup_manager()
        ingredient_type, language = manager._parse_ingredient_identity("flavor-go-launcher-linux_amd64")
        assert ingredient_type == "launcher"
        assert language == "go"

    def test_parse_rust_builder(self) -> None:
        """Test parsing Rust builder identity."""
        manager = self.setup_manager()
        ingredient_type, language = manager._parse_ingredient_identity("flavor-rs-builder-darwin_arm64")
        assert ingredient_type == "builder"
        assert language == "rust"

    def test_parse_go_builder(self) -> None:
        """Test parsing Go builder identity."""
        manager = self.setup_manager()
        ingredient_type, language = manager._parse_ingredient_identity("flavor-go-builder")
        assert ingredient_type == "builder"
        assert language == "go"

    def test_parse_rust_launcher(self) -> None:
        """Test parsing Rust launcher identity."""
        manager = self.setup_manager()
        ingredient_type, language = manager._parse_ingredient_identity("flavor-rs-launcher")
        assert ingredient_type == "launcher"
        assert language == "rust"

    def test_parse_unknown_format(self) -> None:
        """Test parsing unknown format returns None."""
        manager = self.setup_manager()
        ingredient_type, language = manager._parse_ingredient_identity("random-file.txt")
        assert ingredient_type is None
        assert language is None

    def test_parse_missing_type(self) -> None:
        """Test parsing with missing type."""
        manager = self.setup_manager()
        ingredient_type, language = manager._parse_ingredient_identity("flavor-go-tool")
        assert ingredient_type is None
        assert language == "go"

    def test_parse_missing_language(self) -> None:
        """Test parsing with missing language."""
        manager = self.setup_manager()
        ingredient_type, language = manager._parse_ingredient_identity("generic-launcher")
        assert ingredient_type == "launcher"
        assert language is None


@pytest.mark.unit
class TestFileOperations:
    """Test file size and checksum operations."""

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> IngredientManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return IngredientManager()

    def test_get_file_size_success(self) -> None:
        """Test getting file size successfully."""
        manager = self.setup_manager()
        mock_path = Mock(spec=Path)
        mock_stat = Mock()
        mock_stat.st_size = 12345
        mock_path.stat.return_value = mock_stat

        size = manager._get_file_size(mock_path)
        assert size == 12345

    def test_get_file_size_os_error(self) -> None:
        """Test getting file size with OS error."""
        manager = self.setup_manager()
        mock_path = Mock(spec=Path)
        mock_path.stat.side_effect = OSError("Permission denied")

        size = manager._get_file_size(mock_path)
        assert size is None

    def test_get_file_size_not_found(self) -> None:
        """Test getting file size with file not found."""
        manager = self.setup_manager()
        mock_path = Mock(spec=Path)
        mock_path.stat.side_effect = FileNotFoundError("File not found")

        size = manager._get_file_size(mock_path)
        assert size is None

    def test_calculate_checksum_normal_file(self) -> None:
        """Test calculating checksum for normal file."""
        manager = self.setup_manager()
        mock_path = Mock(spec=Path)
        mock_path.read_bytes.return_value = b"test content"

        checksum = manager._calculate_checksum(mock_path, 1024)
        assert checksum is not None
        assert len(checksum) == 16  # First 16 chars of SHA256

    def test_calculate_checksum_large_file(self) -> None:
        """Test large files skip checksum calculation."""
        manager = self.setup_manager()
        mock_path = Mock(spec=Path)

        checksum = manager._calculate_checksum(mock_path, 100 * 1024 * 1024 + 1)
        assert checksum is None

    def test_calculate_checksum_os_error(self) -> None:
        """Test checksum calculation with OS error."""
        manager = self.setup_manager()
        mock_path = Mock(spec=Path)
        mock_path.read_bytes.side_effect = OSError("Read error")

        checksum = manager._calculate_checksum(mock_path, 1024)
        assert checksum is None

    def test_calculate_checksum_memory_error(self) -> None:
        """Test checksum calculation with memory error."""
        manager = self.setup_manager()
        mock_path = Mock(spec=Path)
        mock_path.read_bytes.side_effect = MemoryError("Out of memory")

        checksum = manager._calculate_checksum(mock_path, 1024)
        assert checksum is None


@pytest.mark.unit
class TestVersionExtraction:
    """Test version extraction from binaries."""

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> IngredientManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return IngredientManager()

    @patch("flavor.ingredients.manager.run")
    def test_extract_version_success(self, mock_run: MagicMock) -> None:
        """Test successful version extraction."""
        manager = self.setup_manager()
        mock_path = Mock(spec=Path)
        # Configure __str__ to return a string, not a Mock
        type(mock_path).__str__ = Mock(return_value="/path/to/binary")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "version 1.2.3\n"
        mock_run.return_value = mock_result

        version = manager._extract_version(mock_path)
        assert version == "1.2.3"

    @patch("flavor.ingredients.manager.run")
    def test_extract_version_failure(self, mock_run: MagicMock) -> None:
        """Test version extraction failure."""
        manager = self.setup_manager()
        mock_path = Mock(spec=Path)
        # Configure __str__ to return a string, not a Mock
        type(mock_path).__str__ = Mock(return_value="/path/to/binary")

        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        version = manager._extract_version(mock_path)
        assert version is None

    @patch("flavor.ingredients.manager.run")
    def test_extract_version_os_error(self, mock_run: MagicMock) -> None:
        """Test version extraction with OS error."""
        manager = self.setup_manager()
        mock_path = Mock(spec=Path)
        mock_run.side_effect = OSError("Execution failed")

        version = manager._extract_version(mock_path)
        assert version is None

    def test_parse_version_output_semantic(self) -> None:
        """Test parsing semantic version from output."""
        manager = self.setup_manager()
        version = manager._parse_version_output("flavor-launcher version 1.2.3")
        assert version == "1.2.3"

    def test_parse_version_output_no_match(self) -> None:
        """Test parsing version with no semantic version."""
        manager = self.setup_manager()
        version = manager._parse_version_output("version abc")
        assert version == "version abc"

    def test_parse_version_output_truncated(self) -> None:
        """Test parsing very long version output (truncated to 20 chars)."""
        manager = self.setup_manager()
        long_output = "very long version string that exceeds twenty characters"
        version = manager._parse_version_output(long_output)
        assert len(version) == 20
        assert version == long_output[:20]


@pytest.mark.unit
class TestBuildSourceDetermination:
    """Test build source determination."""

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> IngredientManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return IngredientManager()

    def test_determine_go_source_exists(self) -> None:
        """Test determining Go build source when directory exists."""
        manager = self.setup_manager()
        manager.go_src_dir = Mock(spec=Path)
        manager.go_src_dir.exists.return_value = True

        source = manager._determine_build_source("go")
        assert source == manager.go_src_dir

    def test_determine_rust_source_exists(self) -> None:
        """Test determining Rust build source when directory exists."""
        manager = self.setup_manager()
        manager.rust_src_dir = Mock(spec=Path)
        manager.rust_src_dir.exists.return_value = True

        source = manager._determine_build_source("rust")
        assert source == manager.rust_src_dir

    def test_determine_source_not_exists(self) -> None:
        """Test determining build source when directory doesn't exist."""
        manager = self.setup_manager()
        manager.go_src_dir = Mock(spec=Path)
        manager.go_src_dir.exists.return_value = False

        source = manager._determine_build_source("go")
        assert source is None

    def test_determine_source_unknown_language(self) -> None:
        """Test determining build source for unknown language."""
        manager = self.setup_manager()

        source = manager._determine_build_source("python")
        assert source is None


@pytest.mark.unit
class TestIngredientInfo:
    """Test IngredientInfo dataclass."""

    def test_ingredient_info_creation(self) -> None:
        """Test creating IngredientInfo object."""
        info = IngredientInfo(
            name="flavor-go-launcher",
            path=Path("/path/to/launcher"),
            type="launcher",
            language="go",
            size=12345,
            checksum="abcd1234",
            version="1.2.3",
            built_from=Path("/src/go"),
        )

        assert info.name == "flavor-go-launcher"
        assert info.type == "launcher"
        assert info.language == "go"
        assert info.size == 12345
        assert info.checksum == "abcd1234"
        assert info.version == "1.2.3"

    def test_ingredient_info_defaults(self) -> None:
        """Test IngredientInfo with default values."""
        info = IngredientInfo(
            name="test",
            path=Path("/test"),
            type="launcher",
            language="go",
            size=100,
        )

        assert info.checksum is None
        assert info.version is None
        assert info.built_from is None
