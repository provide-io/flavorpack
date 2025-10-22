"""Test ingredients/manager.py - List and get operations."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from flavor.ingredients.manager import IngredientInfo, IngredientManager


@pytest.mark.unit
class TestListIngredients:
    """Test listing ingredients."""

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> IngredientManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return IngredientManager()

    def test_list_ingredients_empty(self) -> None:
        """Test listing ingredients when directory is empty."""
        manager = self.setup_manager()
        manager.ingredients_bin = Mock(spec=Path)
        manager.ingredients_bin.exists.return_value = True
        manager.ingredients_bin.iterdir.return_value = []

        # Mock the Path(__file__).parent / "bin" embedded path
        with patch("flavor.ingredients.manager.Path") as mock_path_class:
            mock_file_path = Mock(spec=Path)
            mock_parent = Mock(spec=Path)
            mock_embedded_bin = Mock(spec=Path)

            mock_file_path.parent = mock_parent
            mock_parent.__truediv__ = Mock(return_value=mock_embedded_bin)
            mock_embedded_bin.exists.return_value = False

            mock_path_class.return_value = mock_file_path

            ingredients = manager.list_ingredients()

        assert ingredients == {"launchers": [], "builders": []}

    def test_list_ingredients_with_files(self) -> None:
        """Test listing ingredients with actual files."""
        manager = self.setup_manager()

        # Create mock files
        mock_launcher = Mock(spec=Path)
        mock_launcher.is_file.return_value = True
        mock_launcher.name = "flavor-go-launcher-linux_amd64"

        mock_builder = Mock(spec=Path)
        mock_builder.is_file.return_value = True
        mock_builder.name = "flavor-rs-builder-linux_amd64"

        manager.ingredients_bin = Mock(spec=Path)
        manager.ingredients_bin.exists.return_value = True
        manager.ingredients_bin.iterdir.return_value = [mock_launcher, mock_builder]

        # Mock _get_ingredient_info to return valid info
        manager._get_ingredient_info = Mock(side_effect=lambda p: IngredientInfo(
            name=p.name,
            path=p,
            type="launcher" if "launcher" in p.name else "builder",
            language="go" if "go" in p.name else "rust",
            size=1024,
        ))

        # Mock embedded bin to not exist
        with patch("flavor.ingredients.manager.Path") as mock_path_class:
            mock_embedded = Mock(spec=Path)
            mock_embedded.exists.return_value = False
            mock_path_class.return_value = mock_embedded

            ingredients = manager.list_ingredients()

        assert len(ingredients["launchers"]) == 1
        assert len(ingredients["builders"]) == 1
        assert ingredients["launchers"][0].name == "flavor-go-launcher-linux_amd64"
        assert ingredients["builders"][0].name == "flavor-rs-builder-linux_amd64"

    def test_list_ingredients_platform_filter(self) -> None:
        """Test listing ingredients with platform filter."""
        manager = self.setup_manager()

        # Create mock files for different platforms
        mock_compatible = Mock(spec=Path)
        mock_compatible.is_file.return_value = True
        mock_compatible.name = "flavor-go-launcher-linux_amd64"

        mock_incompatible = Mock(spec=Path)
        mock_incompatible.is_file.return_value = True
        mock_incompatible.name = "flavor-go-launcher-darwin_arm64"

        manager.ingredients_bin = Mock(spec=Path)
        manager.ingredients_bin.exists.return_value = True
        manager.ingredients_bin.iterdir.return_value = [mock_compatible, mock_incompatible]

        manager._get_ingredient_info = Mock(side_effect=lambda p: IngredientInfo(
            name=p.name,
            path=p,
            type="launcher",
            language="go",
            size=1024,
        ))

        # Mock embedded bin to not exist
        with patch("flavor.ingredients.manager.Path") as mock_path_class:
            mock_embedded = Mock(spec=Path)
            mock_embedded.exists.return_value = False
            mock_path_class.return_value = mock_embedded

            ingredients = manager.list_ingredients(platform_filter=True)

        # Only linux_amd64 should be included
        assert len(ingredients["launchers"]) == 1
        assert ingredients["launchers"][0].name == "flavor-go-launcher-linux_amd64"

    def test_list_ingredients_with_embedded(self) -> None:
        """Test listing ingredients includes embedded ingredients."""
        manager = self.setup_manager()

        # No ingredients in build directory
        manager.ingredients_bin = Mock(spec=Path)
        manager.ingredients_bin.exists.return_value = True
        manager.ingredients_bin.iterdir.return_value = []

        # Mock embedded launcher
        mock_embedded_launcher = Mock(spec=Path)
        mock_embedded_launcher.is_file.return_value = True
        mock_embedded_launcher.name = "flavor-go-launcher-linux_amd64"

        with patch("flavor.ingredients.manager.Path") as mock_path_class:
            mock_embedded_bin = Mock(spec=Path)
            mock_embedded_bin.exists.return_value = True
            mock_embedded_bin.exists.return_value = True
            mock_embedded_bin.iterdir.return_value = [mock_embedded_launcher]

            mock_file_path.parent = Mock()
            mock_file_path.parent.__truediv__ = Mock(return_value=mock_embedded_bin)
            mock_path_class.return_value = mock_file_path

            manager._get_ingredient_info = Mock(return_value=IngredientInfo(
                name="flavor-go-launcher-linux_amd64",
                path=mock_embedded_launcher,
                type="launcher",
                language="go",
                size=1024,
            ))

            ingredients = manager.list_ingredients()

        assert len(ingredients["launchers"]) == 1
        assert ingredients["launchers"][0].name == "flavor-go-launcher-linux_amd64"

    def test_list_ingredients_deduplicates_embedded(self) -> None:
        """Test embedded ingredients don't duplicate dev-built ones."""
        manager = self.setup_manager()

        # Mock dev-built launcher
        mock_dev_launcher = Mock(spec=Path)
        mock_dev_launcher.is_file.return_value = True
        mock_dev_launcher.name = "flavor-go-launcher-linux_amd64"

        manager.ingredients_bin = Mock(spec=Path)
        manager.ingredients_bin.exists.return_value = True
        manager.ingredients_bin.iterdir.return_value = [mock_dev_launcher]

        # Mock embedded launcher with same name
        mock_embedded_launcher = Mock(spec=Path)
        mock_embedded_launcher.is_file.return_value = True
        mock_embedded_launcher.name = "flavor-go-launcher-linux_amd64"

        call_count = [0]

        def get_info_side_effect(path: Path) -> IngredientInfo:
            call_count[0] += 1
            return IngredientInfo(
                name=path.name,
                path=path,
                type="launcher",
                language="go",
                size=1024,
            )

        manager._get_ingredient_info = Mock(side_effect=get_info_side_effect)

        with patch("flavor.ingredients.manager.Path") as mock_path_class:
            mock_embedded_bin = Mock(spec=Path)
            mock_embedded_bin.exists.return_value = True
            mock_embedded_bin.exists.return_value = True
            mock_embedded_bin.iterdir.return_value = [mock_embedded_launcher]

            mock_file_path.parent = Mock()
            mock_file_path.parent.__truediv__ = Mock(return_value=mock_embedded_bin)
            mock_path_class.return_value = mock_file_path

            ingredients = manager.list_ingredients()

        # Should only have one launcher (dev-built takes precedence)
        assert len(ingredients["launchers"]) == 1
        assert call_count[0] == 2  # Called for both, but only one added

    def test_list_ingredients_ignores_invalid_files(self) -> None:
        """Test listing ignores files that don't parse as valid ingredients."""
        manager = self.setup_manager()

        mock_invalid = Mock(spec=Path)
        mock_invalid.is_file.return_value = True
        mock_invalid.name = "random-file.txt"

        manager.ingredients_bin = Mock(spec=Path)
        manager.ingredients_bin.exists.return_value = True
        manager.ingredients_bin.iterdir.return_value = [mock_invalid]

        # _get_ingredient_info returns None for invalid files
        manager._get_ingredient_info = Mock(return_value=None)

        with patch("flavor.ingredients.manager.Path") as mock_path_class:
            mock_embedded = Mock(spec=Path)
            mock_embedded.exists.return_value = False
            mock_path_class.return_value = mock_embedded

            ingredients = manager.list_ingredients()

        assert ingredients == {"launchers": [], "builders": []}

    def test_list_ingredients_nonexistent_directory(self) -> None:
        """Test listing ingredients when directory doesn't exist."""
        manager = self.setup_manager()
        manager.ingredients_bin = Mock(spec=Path)
        manager.ingredients_bin.exists.return_value = False

        with patch("flavor.ingredients.manager.Path") as mock_path_class:
            mock_embedded = Mock(spec=Path)
            mock_embedded.exists.return_value = False
            mock_path_class.return_value = mock_embedded

            ingredients = manager.list_ingredients()

        assert ingredients == {"launchers": [], "builders": []}


@pytest.mark.unit
class TestGetIngredientInfo:
    """Test getting ingredient information."""

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> IngredientManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return IngredientManager()

    def test_get_ingredient_info_success(self) -> None:
        """Test getting ingredient info successfully."""
        manager = self.setup_manager()

        mock_path = Mock(spec=Path)
        mock_path.name = "flavor-go-launcher"

        manager.ingredients_bin = Mock(spec=Path)
        manager.ingredients_bin.__truediv__ = Mock(return_value=mock_path)
        mock_path.exists.return_value = True

        expected_info = IngredientInfo(
            name="flavor-go-launcher",
            path=mock_path,
            type="launcher",
            language="go",
            size=1024,
        )
        manager._get_ingredient_info = Mock(return_value=expected_info)

        info = manager.get_ingredient_info("flavor-go-launcher")
        assert info is not None
        assert info.name == "flavor-go-launcher"

    def test_get_ingredient_info_partial_name(self) -> None:
        """Test getting ingredient info by partial name."""
        manager = self.setup_manager()

        # Exact match doesn't exist
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = False
        manager.ingredients_bin = Mock(spec=Path)
        manager.ingredients_bin.__truediv__ = Mock(return_value=mock_path)

        # But list_ingredients finds a match
        mock_ingredient = IngredientInfo(
            name="flavor-go-launcher-linux_amd64",
            path=Path("/path/to/launcher"),
            type="launcher",
            language="go",
            size=1024,
        )
        manager.list_ingredients = Mock(return_value={
            "launchers": [mock_ingredient],
            "builders": [],
        })

        info = manager.get_ingredient_info("launcher")
        assert info is not None
        assert "launcher" in info.name

    def test_get_ingredient_info_not_found(self) -> None:
        """Test getting ingredient info when not found."""
        manager = self.setup_manager()

        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = False
        manager.ingredients_bin = Mock(spec=Path)
        manager.ingredients_bin.__truediv__ = Mock(return_value=mock_path)

        manager.list_ingredients = Mock(return_value={
            "launchers": [],
            "builders": [],
        })

        info = manager.get_ingredient_info("nonexistent")
        assert info is None


@pytest.mark.unit
class TestDelegationMethods:
    """Test methods that delegate to BinaryLoader."""

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> tuple[IngredientManager, MagicMock]:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        manager = IngredientManager()
        return manager, mock_binary_loader

    def test_build_ingredients_delegation(self) -> None:
        """Test build_ingredients delegates to binary loader."""
        manager, mock_binary_loader = self.setup_manager()
        mock_loader_instance = mock_binary_loader.return_value
        mock_loader_instance.build_ingredients.return_value = [Path("/path/to/built")]

        result = manager.build_ingredients("go", force=True)

        mock_loader_instance.build_ingredients.assert_called_once_with("go", True)
        assert result == [Path("/path/to/built")]

    def test_clean_ingredients_delegation(self) -> None:
        """Test clean_ingredients delegates to binary loader."""
        manager, mock_binary_loader = self.setup_manager()
        mock_loader_instance = mock_binary_loader.return_value
        mock_loader_instance.clean_ingredients.return_value = [Path("/path/to/cleaned")]

        result = manager.clean_ingredients("rust")

        mock_loader_instance.clean_ingredients.assert_called_once_with("rust")
        assert result == [Path("/path/to/cleaned")]

    def test_test_ingredients_delegation(self) -> None:
        """Test test_ingredients delegates to binary loader."""
        manager, mock_binary_loader = self.setup_manager()
        mock_loader_instance = mock_binary_loader.return_value
        mock_loader_instance.test_ingredients.return_value = {"passed": 5, "failed": 0}

        result = manager.test_ingredients("go")

        mock_loader_instance.test_ingredients.assert_called_once_with("go")
        assert result == {"passed": 5, "failed": 0}

    def test_get_ingredient_delegation(self) -> None:
        """Test get_ingredient delegates to binary loader."""
        manager, mock_binary_loader = self.setup_manager()
        mock_loader_instance = mock_binary_loader.return_value
        mock_loader_instance.get_ingredient.return_value = Path("/path/to/ingredient")

        result = manager.get_ingredient("flavor-go-launcher")

        mock_loader_instance.get_ingredient.assert_called_once_with("flavor-go-launcher")
        assert result == Path("/path/to/ingredient")


@pytest.mark.unit
class TestGetIngredientInfoHelper:
    """Test _get_ingredient_info helper method."""

    @patch("flavor.ingredients.manager.ensure_dir")
    @patch("flavor.ingredients.manager.get_platform_string")
    @patch("flavor.ingredients.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> IngredientManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return IngredientManager()

    def test_get_ingredient_info_complete(self) -> None:
        """Test _get_ingredient_info with all information."""
        manager = self.setup_manager()

        mock_path = Mock(spec=Path)
        mock_path.name = "flavor-go-launcher-linux_amd64"

        # Mock all helper methods
        manager._parse_ingredient_identity = Mock(return_value=("launcher", "go"))
        manager._get_file_size = Mock(return_value=12345)
        manager._calculate_checksum = Mock(return_value="abcd1234")
        manager._extract_version = Mock(return_value="1.2.3")
        manager._determine_build_source = Mock(return_value=Path("/src/go"))

        info = manager._get_ingredient_info(mock_path)

        assert info is not None
        assert info.name == "flavor-go-launcher-linux_amd64"
        assert info.type == "launcher"
        assert info.language == "go"
        assert info.size == 12345
        assert info.checksum == "abcd1234"
        assert info.version == "1.2.3"
        assert info.built_from == Path("/src/go")

    def test_get_ingredient_info_invalid_identity(self) -> None:
        """Test _get_ingredient_info with invalid identity."""
        manager = self.setup_manager()

        mock_path = Mock(spec=Path)
        mock_path.name = "random-file.txt"

        manager._parse_ingredient_identity = Mock(return_value=(None, None))

        info = manager._get_ingredient_info(mock_path)
        assert info is None

    def test_get_ingredient_info_no_size(self) -> None:
        """Test _get_ingredient_info when file size cannot be determined."""
        manager = self.setup_manager()

        mock_path = Mock(spec=Path)
        mock_path.name = "flavor-go-launcher"

        manager._parse_ingredient_identity = Mock(return_value=("launcher", "go"))
        manager._get_file_size = Mock(return_value=None)

        info = manager._get_ingredient_info(mock_path)
        assert info is None
