"""
Configuration loader for the Search Keyword Performance Analyzer.
Reads settings from config/config.yaml and provides them to all modules.
"""

import logging
import os
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default path to config file (relative to project root)
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "config.yaml"
)


class ConfigLoadError(Exception):
    """Raised when the configuration file cannot be loaded or parsed."""
    pass


class Config:
    """
    Singleton configuration class that loads and provides access
    to all application settings from config.yaml.
    """

    _instance = None
    _config = {}

    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load(config_path or DEFAULT_CONFIG_PATH)
        return cls._instance

    def _load(self, config_path: str) -> None:
        """Load configuration from YAML file."""
        logger.info("Loading configuration from: %s", config_path)

        if not os.path.exists(config_path):
            logger.error("Config file not found at path: %s", config_path)
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)

            if not self._config or not isinstance(self._config, dict):
                raise ConfigLoadError(f"Config file is empty or invalid: {config_path}")

            logger.info("Configuration loaded successfully. Sections: %s",
                        list(self._config.keys()))

        except yaml.YAMLError as e:
            logger.error("Failed to parse YAML config file: %s — %s", config_path, e)
            raise ConfigLoadError(f"Invalid YAML in config file: {config_path}") from e

    def _get(self, *keys, default: Any = None) -> Any:
        """
        Safely traverse nested config keys.
        Example: self._get("input", "columns", "ip", default="ip")
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        return value if value is not None else default

    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
        cls._config = {}

    # --- Search Engines ---
    @property
    def search_engines(self) -> dict:
        return self._get("search_engines", default={})

    # --- Events ---
    @property
    def purchase_event(self) -> str:
        return str(self._get("events", "purchase", default="1"))

    # --- Input Settings ---
    @property
    def input_delimiter(self) -> str:
        return self._get("input", "delimiter", default="\t")

    @property
    def input_encoding(self) -> str:
        return self._get("input", "encoding", default="utf-8")

    @property
    def column_ip(self) -> str:
        return self._get("input", "columns", "ip", default="ip")

    @property
    def column_referrer(self) -> str:
        return self._get("input", "columns", "referrer", default="referrer")

    @property
    def column_event_list(self) -> str:
        return self._get("input", "columns", "event_list", default="event_list")

    @property
    def column_product_list(self) -> str:
        return self._get("input", "columns", "product_list", default="product_list")

    # --- Product List Parsing ---
    @property
    def product_delimiter(self) -> str:
        return self._get("product_list", "product_delimiter", default=",")

    @property
    def field_delimiter(self) -> str:
        return self._get("product_list", "field_delimiter", default=";")

    @property
    def revenue_field_index(self) -> int:
        return self._get("product_list", "revenue_field_index", default=3)

    # --- Output Settings ---
    @property
    def output_directory(self) -> str:
        return self._get("output", "directory", default="output")

    @property
    def output_filename_template(self) -> str:
        return self._get("output", "filename_template", default="{date}_SearchKeywordPerformance.tab")

    @property
    def output_date_format(self) -> str:
        return self._get("output", "date_format", default="%Y-%m-%d")

    @property
    def output_delimiter(self) -> str:
        return self._get("output", "delimiter", default="\t")

    @property
    def output_headers(self) -> list:
        return self._get("output", "headers", default=["Search Engine Domain", "Search Keyword", "Revenue"])

    # --- AWS Settings ---
    @property
    def aws_region(self) -> str:
        return self._get("aws", "region", default="us-east-1")

    @property
    def s3_input_prefix(self) -> str:
        return self._get("aws", "s3", "input_prefix", default="input/")

    @property
    def s3_output_prefix(self) -> str:
        return self._get("aws", "s3", "output_prefix", default="output/")
