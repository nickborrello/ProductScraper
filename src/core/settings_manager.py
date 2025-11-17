"""
Settings Manager for ProductScraper
Handles application configuration using QSettings for cross-platform storage.
"""

import os
from typing import Dict, Any, Optional
from PyQt6.QtCore import QSettings, QStandardPaths


class SettingsManager:
    """Manages application settings using QSettings for persistent storage."""

    # Default settings
    DEFAULTS = {
        # Scraper Credentials
        "petfood_username": "",
        "petfood_password": "",
        "phillips_username": "",
        "phillips_password": "",
        "orgill_username": "",
        "orgill_password": "",
        # ShopSite API Credentials
        "shopsite_client_id": "",
        "shopsite_secret_key": "",
        "shopsite_authorization_code": "",
        "shopsite_auth_url": "https://yourstore.shopsite.com/xml/",
        "shopsite_username": "",
        "shopsite_password": "",
        "shopsite_base_url": "",
        "shopsite_store_id": "",
        # Cloud Settings
        "google_cloud_project_id": "",
        "apify_api_token": "",
        "apify_base_url": "https://api.apify.com/v2",
        # AI/ML Settings
        "openrouter_api_key": "",
        "ollama_model": "llama3.2",
        "classification_method": "llm",  # 'llm' (OpenRouter), 'local_llm' (Ollama), 'fuzzy' (legacy)
        # Application Settings
        "debug_mode": False,
        "database_path": "data/databases/products.db",
        "selenium_headless": True,
        "selenium_timeout": 30,
        "scraper_system": "new",  # 'new' (modular YAML), 'legacy' (archived)
        # UI Settings
        "auto_scroll_logs": True,
        "theme": "dark",  # 'dark' or 'light'
    }

    def __init__(self):
        """Initialize settings manager with QSettings."""
        # Use organization and application name for settings storage
        self.settings = QSettings("BayStatePet", "ProductScraper")

        # Load from settings.json if it exists (for initial setup)
        self._load_from_json()

        # Load environment variables if they exist (for backward compatibility)
        self._load_from_env()

    def _load_from_json(self):
        """Load settings from settings.json file for initial setup."""
        try:
            import json
            from pathlib import Path
            settings_file = Path(__file__).parent.parent.parent / "settings.json"
            if settings_file.exists():
                with open(settings_file, "r") as f:
                    json_settings = json.load(f)
                
                # Load values from JSON (always override with JSON values for consistency)
                for key, value in json_settings.items():
                    if key in self.DEFAULTS:
                        self.set(key, value)
        except Exception as e:
            # Silently ignore JSON loading errors
            pass

    def _load_from_env(self):
        """Load settings from environment variables for backward compatibility."""
        env_mappings = {
            "petfood_username": "PETFOOD_USERNAME",
            "petfood_password": "PETFOOD_PASSWORD",
            "phillips_username": "PHILLIPS_USERNAME",
            "phillips_password": "PHILLIPS_PASSWORD",
            "orgill_username": "ORGILL_USERNAME",
            "orgill_password": "ORGILL_PASSWORD",
            "shopsite_client_id": "SHOPSITE_CLIENT_ID",
            "shopsite_secret_key": "SHOPSITE_SECRET_KEY",
            "shopsite_authorization_code": "SHOPSITE_AUTHORIZATION_CODE",
            "shopsite_auth_url": "SHOPSITE_AUTH_URL",
            "shopsite_username": "SHOPSITE_USERNAME",
            "shopsite_password": "SHOPSITE_PASSWORD",
            "shopsite_base_url": "SHOPSITE_BASE_URL",
            "shopsite_store_id": "SHOPSITE_STORE_ID",
            "google_cloud_project_id": "GOOGLE_CLOUD_PROJECT_ID",
            "openrouter_api_key": "OPENROUTER_API_KEY",
        }

        for setting_key, env_key in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value and not self.get(setting_key):
                self.set(setting_key, env_value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        if default is None:
            default = self.DEFAULTS.get(key, "")

        value = self.settings.value(key, default)

        # Convert string booleans
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Convert string numbers
        if isinstance(value, str) and value.isdigit():
            return int(value)

        return value

    def set(self, key: str, value: Any):
        """Set a setting value."""
        self.settings.setValue(key, value)
        self.settings.sync()

    def get_all(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        all_settings = {}
        for key in self.DEFAULTS.keys():
            all_settings[key] = self.get(key)
        return all_settings

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        for key, value in self.DEFAULTS.items():
            self.set(key, value)

    def export_settings(self) -> Dict[str, Any]:
        """Export settings for backup/sharing (excludes sensitive data)."""
        all_settings = self.get_all()
        # Remove sensitive data from export
        sensitive_keys = [
            "petfood_password",
            "phillips_password",
            "orgill_password",
            "shopsite_secret_key",
            "shopsite_authorization_code",
            "shopsite_password",
        ]
        for key in sensitive_keys:
            if key in all_settings:
                all_settings[key] = "***REDACTED***"
        return all_settings

    def import_settings(self, settings_dict: Dict[str, Any]):
        """Import settings from a dictionary."""
        for key, value in settings_dict.items():
            if key in self.DEFAULTS and value != "***REDACTED***":
                self.set(key, value)

    # Convenience methods for commonly accessed settings
    @property
    def petfood_credentials(self) -> tuple[str, str]:
        """Get PetFood credentials as (username, password)."""
        return self.get("petfood_username"), self.get("petfood_password")

    @property
    def phillips_credentials(self) -> tuple[str, str]:
        """Get Phillips credentials as (username, password)."""
        return self.get("phillips_username"), self.get("phillips_password")

    @property
    def orgill_credentials(self) -> tuple[str, str]:
        """Get Orgill credentials as (username, password)."""
        return self.get("orgill_username"), self.get("orgill_password")

    @property
    def shopsite_credentials(self) -> Dict[str, str]:
        """Get ShopSite credentials as dictionary."""
        return {
            "client_id": self.get("shopsite_client_id"),
            "secret_key": self.get("shopsite_secret_key"),
            "auth_code": self.get("shopsite_authorization_code"),
            "auth_url": self.get("shopsite_auth_url"),
            "username": self.get("shopsite_username"),
            "password": self.get("shopsite_password"),
            "base_url": self.get("shopsite_base_url"),
            "store_id": self.get("shopsite_store_id"),
        }

    @property
    def database_path(self) -> str:
        """Get the database path."""
        path = self.get("database_path")
        if not os.path.isabs(path):
            # Convert relative path to absolute based on project root
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            path = os.path.join(project_root, path)
        return path

    @property
    def debug_mode(self) -> bool:
        """Get debug mode setting."""
        return self.get("debug_mode")

    @property
    def selenium_settings(self) -> Dict[str, Any]:
        """Get Selenium settings."""
        return {
            "headless": self.get("selenium_headless"),
            "timeout": self.get("selenium_timeout"),
        }


# Global settings instance
settings = SettingsManager()
