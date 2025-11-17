import yaml
from pathlib import Path
from typing import Union
from src.scrapers.models import ScraperConfig
from src.scrapers.schemas import validate_config_dict


class ScraperConfigParser:
    """Parser for YAML-based scraper configurations."""

    def __init__(self):
        pass

    def load_from_file(self, file_path: Union[str, Path]) -> ScraperConfig:
        """Load and parse a scraper configuration from a YAML file.

        Args:
            file_path: Path to the YAML configuration file

        Returns:
            Parsed ScraperConfig object

        Raises:
            FileNotFoundError: If the file doesn't exist
            yaml.YAMLError: If the YAML is malformed
            ValidationError: If the configuration doesn't match the schema
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)

        return validate_config_dict(config_dict)

    def load_from_string(self, yaml_string: str) -> ScraperConfig:
        """Load and parse a scraper configuration from a YAML string.

        Args:
            yaml_string: YAML configuration as string

        Returns:
            Parsed ScraperConfig object

        Raises:
            yaml.YAMLError: If the YAML is malformed
            ValidationError: If the configuration doesn't match the schema
        """
        config_dict = yaml.safe_load(yaml_string)
        return validate_config_dict(config_dict)

    def save_to_file(self, config: ScraperConfig, file_path: Union[str, Path]) -> None:
        """Save a ScraperConfig to a YAML file.

        Args:
            config: ScraperConfig object to save
            file_path: Path where to save the YAML file
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = config.model_dump()
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, sort_keys=False)