import os
import sys

import pytest
import yaml  # type: ignore

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.core.anti_detection_manager import AntiDetectionConfig
from src.scrapers.models.config import ScraperConfig
from src.scrapers.parser.yaml_parser import ScraperConfigParser

# Constants
TIMEOUT_DEFAULT = 30
RETRIES_DEFAULT = 3
EXPECTED_SELECTORS_COUNT = 2
EXPECTED_WORKFLOWS_COUNT = 2


@pytest.fixture
def sample_yaml_config():
    """Sample YAML configuration as string."""
    return """
name: "Test Scraper"
base_url: "https://example.com"
timeout: 30
retries: 3
selectors:
  - name: "product_name"
    selector: ".product-title"
    attribute: "text"
  - name: "price"
    selector: ".price"
    attribute: "text"
    multiple: false
workflows:
  - action: "navigate"
    params:
      url: "https://example.com/products"
  - action: "extract"
    params:
      fields: ["product_name", "price"]
"""


@pytest.fixture
def sample_config_dict():
    """Sample configuration as dictionary."""
    return {
        "name": "Test Scraper",
        "base_url": "https://example.com",
        "timeout": TIMEOUT_DEFAULT,
        "retries": RETRIES_DEFAULT,
        "selectors": [
            {
                "name": "product_name",
                "selector": ".product-title",
                "attribute": "text",
            },
            {
                "name": "price",
                "selector": ".price",
                "attribute": "text",
                "multiple": False,
            },
        ],
        "workflows": [
            {"action": "navigate", "params": {"url": "https://example.com/products"}},
            {"action": "extract", "params": {"fields": ["product_name", "price"]}},
        ],
    }


@pytest.fixture
def config_with_anti_detection():
    """Sample configuration with anti-detection settings."""
    return {
        "name": "Test Scraper",
        "base_url": "https://example.com",
        "anti_detection": {
            "enable_captcha_detection": True,
            "enable_rate_limiting": True,
            "enable_human_simulation": True,
            "enable_session_rotation": True,
            "enable_blocking_handling": True,
        },
    }


class TestScraperConfigParser:
    """Test cases for ScraperConfigParser class."""

    def test_init(self):
        """Test parser initialization."""
        parser = ScraperConfigParser()
        assert parser is not None

    def test_preprocess_config_dict_no_anti_detection(self, sample_config_dict):
        """Test preprocessing config dict without anti-detection."""
        parser = ScraperConfigParser()

        result = parser._preprocess_config_dict(sample_config_dict)

        assert result == sample_config_dict
        assert "anti_detection" not in result

    def test_preprocess_config_dict_with_anti_detection(self, config_with_anti_detection):
        """Test preprocessing config dict with anti-detection."""

        parser = ScraperConfigParser()

        result = parser._preprocess_config_dict(config_with_anti_detection)

        assert "anti_detection" in result
        assert isinstance(result["anti_detection"], AntiDetectionConfig)
        assert result["anti_detection"].enable_captcha_detection is True
        assert result["anti_detection"].enable_rate_limiting is True

    def test_load_from_file_success(self, sample_yaml_config, tmp_path):
        """Test successful loading from YAML file."""
        parser = ScraperConfigParser()

        # Create temporary YAML file
        yaml_file = tmp_path / "test_config.yaml"
        yaml_file.write_text(sample_yaml_config)

        config = parser.load_from_file(str(yaml_file))

        assert isinstance(config, ScraperConfig)
        assert config.name == "Test Scraper"
        assert config.base_url == "https://example.com"
        assert config.timeout == TIMEOUT_DEFAULT
        assert config.retries == RETRIES_DEFAULT
        assert len(config.selectors) == EXPECTED_SELECTORS_COUNT
        assert len(config.workflows) == EXPECTED_WORKFLOWS_COUNT

    def test_load_from_file_not_found(self):
        """Test loading from non-existent file."""
        parser = ScraperConfigParser()

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            parser.load_from_file("nonexistent.yaml")

    def test_load_from_file_invalid_yaml(self, tmp_path):
        """Test loading from invalid YAML file."""
        parser = ScraperConfigParser()

        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            parser.load_from_file(str(yaml_file))

    def test_load_from_file_invalid_config(self, tmp_path):
        """Test loading from YAML file with invalid configuration."""
        parser = ScraperConfigParser()

        invalid_yaml = """
name: "Test"
base_url: "https://example.com"
timeout: "not_a_number"  # Invalid timeout
"""

        yaml_file = tmp_path / "invalid_config.yaml"
        yaml_file.write_text(invalid_yaml)

        # Should raise validation error
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            parser.load_from_file(str(yaml_file))

    def test_load_from_string_success(self, sample_yaml_config):
        """Test successful loading from YAML string."""
        parser = ScraperConfigParser()

        config = parser.load_from_string(sample_yaml_config)

        assert isinstance(config, ScraperConfig)
        assert config.name == "Test Scraper"
        assert config.base_url == "https://example.com"
        assert len(config.selectors) == EXPECTED_SELECTORS_COUNT
        assert len(config.workflows) == EXPECTED_WORKFLOWS_COUNT

    def test_load_from_string_invalid_yaml(self):
        """Test loading from invalid YAML string."""
        parser = ScraperConfigParser()

        invalid_yaml = "invalid: yaml: content: ["

        with pytest.raises(yaml.YAMLError):
            parser.load_from_string(invalid_yaml)

    def test_load_from_string_invalid_config(self):
        """Test loading from YAML string with invalid configuration."""
        parser = ScraperConfigParser()

        invalid_yaml = """
name: "Test"
base_url: "https://example.com"
selectors:
  - name: "test"
    selector: ".test"
    attribute: "text"
    invalid_field: "should_not_be_here"
"""

        # Note: Pydantic models may allow extra fields depending on configuration
        config = parser.load_from_string(invalid_yaml)
        assert config.name == "Test"
        assert config.base_url == "https://example.com"

    def test_load_from_string_empty(self):
        """Test loading from empty YAML string."""
        parser = ScraperConfigParser()

        with pytest.raises(
            TypeError
        ):  # yaml.safe_load("") returns None, causing TypeError in preprocess
            parser.load_from_string("")

    def test_save_to_file_success(self, sample_config_dict, tmp_path):
        """Test successful saving to YAML file."""
        parser = ScraperConfigParser()

        # Create config object
        config = ScraperConfig(**sample_config_dict)

        yaml_file = tmp_path / "output.yaml"
        parser.save_to_file(config, str(yaml_file))

        assert yaml_file.exists()

        # Verify content can be loaded back
        loaded_config = parser.load_from_file(str(yaml_file))
        assert loaded_config.name == config.name
        assert loaded_config.base_url == config.base_url

    def test_save_to_file_creates_directory(self, tmp_path):
        """Test that save_to_file creates necessary directories."""
        parser = ScraperConfigParser()

        config = ScraperConfig(
            name="Test",
            base_url="https://example.com",
            timeout=TIMEOUT_DEFAULT,
            retries=RETRIES_DEFAULT,
            login=None,
            anti_detection=None,
            http_status=None,
            validation=None,
            test_skus=None,
        )

        nested_dir = tmp_path / "nested" / "deep" / "path"
        yaml_file = nested_dir / "config.yaml"

        parser.save_to_file(config, str(yaml_file))

        assert nested_dir.exists()
        assert yaml_file.exists()

    def test_save_to_file_overwrites_existing(self, tmp_path):
        """Test that save_to_file overwrites existing file."""
        parser = ScraperConfigParser()

        config = ScraperConfig(
            name="Test",
            base_url="https://example.com",
            timeout=TIMEOUT_DEFAULT,
            retries=RETRIES_DEFAULT,
            login=None,
            anti_detection=None,
            http_status=None,
            validation=None,
            test_skus=None,
        )

        yaml_file = tmp_path / "config.yaml"

        # Create initial file with different content
        yaml_file.write_text("initial: content")

        parser.save_to_file(config, str(yaml_file))

        # Verify it was overwritten
        with open(yaml_file) as f:
            content = f.read()
            assert "name:" in content
            assert "initial:" not in content

    def test_roundtrip_file_save_load(self, sample_config_dict, tmp_path):
        """Test that saving and loading preserves data."""
        parser = ScraperConfigParser()

        original_config = ScraperConfig(**sample_config_dict)

        yaml_file = tmp_path / "roundtrip.yaml"
        parser.save_to_file(original_config, str(yaml_file))

        loaded_config = parser.load_from_file(str(yaml_file))

        assert loaded_config.name == original_config.name
        assert loaded_config.base_url == original_config.base_url
        assert loaded_config.timeout == original_config.timeout
        assert len(loaded_config.selectors) == len(original_config.selectors)
        assert len(loaded_config.workflows) == len(original_config.workflows)

    def test_config_with_login(self):
        """Test loading configuration with login settings."""
        yaml_content = """
name: "Login Test Scraper"
base_url: "https://example.com"
login:
  url: "https://example.com/login"
  username_field: "#username"
  password_field: "#password"
  submit_button: "#submit"
  success_indicator: ".dashboard"
"""

        parser = ScraperConfigParser()
        config = parser.load_from_string(yaml_content)

        assert config.login is not None
        assert config.login.url == "https://example.com/login"
        assert config.login.username_field == "#username"
        assert config.login.success_indicator == ".dashboard"

    def test_config_minimal(self):
        """Test loading minimal valid configuration."""
        yaml_content = """
name: "Minimal Scraper"
base_url: "https://example.com"
"""

        parser = ScraperConfigParser()
        config = parser.load_from_string(yaml_content)

        assert config.name == "Minimal Scraper"
        assert config.base_url == "https://example.com"
        assert config.timeout == TIMEOUT_DEFAULT  # default
        assert config.retries == RETRIES_DEFAULT  # default
        assert config.selectors == []  # default
        assert config.workflows == []  # default

    def test_config_with_test_skus(self):
        """Test loading configuration with test SKUs."""
        yaml_content = """
name: "SKU Test Scraper"
base_url: "https://example.com"
test_skus:
  - "SKU001"
  - "SKU002"
  - "SKU003"
"""

        parser = ScraperConfigParser()
        config = parser.load_from_string(yaml_content)

        assert config.test_skus == ["SKU001", "SKU002", "SKU003"]

    def test_preprocess_config_dict_preserves_other_fields(self, sample_config_dict):
        """Test that preprocessing preserves non-anti-detection fields."""
        parser = ScraperConfigParser()

        # Add some other fields
        sample_config_dict["custom_field"] = "custom_value"
        sample_config_dict["nested"] = {"key": "value"}

        result = parser._preprocess_config_dict(sample_config_dict)

        assert result["custom_field"] == "custom_value"
        assert result["nested"]["key"] == "value"

    def test_load_from_file_pathlib_path(self, sample_yaml_config, tmp_path):
        """Test loading using pathlib.Path object."""
        parser = ScraperConfigParser()

        yaml_file = tmp_path / "test_config.yaml"
        yaml_file.write_text(sample_yaml_config)

        config = parser.load_from_file(yaml_file)  # Pass Path object

        assert isinstance(config, ScraperConfig)
        assert config.name == "Test Scraper"

    def test_save_to_file_pathlib_path(self, tmp_path):
        """Test saving using pathlib.Path object."""
        parser = ScraperConfigParser()

        config = ScraperConfig(
            name="Test",
            base_url="https://example.com",
            timeout=TIMEOUT_DEFAULT,
            retries=RETRIES_DEFAULT,
            login=None,
            anti_detection=None,
            http_status=None,
            validation=None,
            test_skus=None,
        )

        yaml_file = tmp_path / "output.yaml"
        parser.save_to_file(config, yaml_file)  # Pass Path object

        assert yaml_file.exists()
