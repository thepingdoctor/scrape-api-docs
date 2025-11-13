"""
Configuration Management
========================

This module provides configuration management with support for:
- YAML configuration files
- Environment variables
- Default values and validation
- Type checking and conversion

Usage:
    from scrape_api_docs.config import Config

    config = Config.load('config/default.yaml')
    max_pages = config.get('scraper.max_pages', default=100)
"""

import os
import yaml
from pathlib import Path
from typing import Any, Optional, Dict
import logging
from .exceptions import ConfigurationException

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager with YAML and environment variable support.

    Provides hierarchical configuration with:
    1. Default values (lowest priority)
    2. YAML configuration files
    3. Environment variables (highest priority)
    """

    # Default configuration
    DEFAULTS = {
        'scraper': {
            'max_pages': 100,
            'timeout': 10,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'max_content_size': 100 * 1024 * 1024,  # 100MB
            'politeness_delay': 1.0,
        },
        'rate_limiting': {
            'enabled': True,
            'requests_per_second': 2.0,
            'burst_size': 4,
            'max_retries': 3,
            'backoff_factor': 2.0,
        },
        'robots': {
            'enabled': True,
            'respect_crawl_delay': True,
            'user_agent': 'scrape-api-docs/0.1.0',
        },
        'security': {
            'validate_urls': True,
            'block_private_ips': True,
            'sanitize_filenames': True,
        },
        'logging': {
            'level': 'INFO',
            'file': None,
            'json_format': False,
            'max_bytes': 10 * 1024 * 1024,  # 10MB
            'backup_count': 5,
        },
        'output': {
            'directory': '.',
            'format': 'markdown',
            'encoding': 'utf-8',
        }
    }

    # Environment variable mapping
    # Maps config keys to environment variable names
    ENV_VARS = {
        'scraper.max_pages': 'SCRAPER_MAX_PAGES',
        'scraper.timeout': 'SCRAPER_TIMEOUT',
        'scraper.user_agent': 'SCRAPER_USER_AGENT',
        'rate_limiting.requests_per_second': 'RATE_LIMIT_RPS',
        'robots.enabled': 'ROBOTS_ENABLED',
        'logging.level': 'LOG_LEVEL',
        'logging.file': 'LOG_FILE',
    }

    def __init__(self, config_data: dict = None):
        """
        Initialize configuration.

        Args:
            config_data: Configuration dictionary (merged with defaults)
        """
        self._config = self._deep_merge(self.DEFAULTS.copy(), config_data or {})

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> 'Config':
        """
        Load configuration from file.

        Args:
            config_file: Path to YAML config file (optional)

        Returns:
            Config instance

        Raises:
            ConfigurationException: If config file is invalid
        """
        config_data = {}

        # Load from file if provided
        if config_file:
            config_path = Path(config_file)
            if not config_path.exists():
                logger.warning(f"Config file not found: {config_file}, using defaults")
            else:
                try:
                    with open(config_path, 'r') as f:
                        file_config = yaml.safe_load(f)
                        if file_config:
                            config_data = file_config
                        logger.info(f"Loaded configuration from {config_file}")
                except yaml.YAMLError as e:
                    raise ConfigurationException(
                        f"Invalid YAML in config file: {config_file}",
                        details={'error': str(e)}
                    )
                except Exception as e:
                    raise ConfigurationException(
                        f"Error loading config file: {config_file}",
                        details={'error': str(e)}
                    )

        # Create config instance
        config = cls(config_data)

        # Override with environment variables
        config._load_env_vars()

        return config

    def _load_env_vars(self):
        """Load configuration from environment variables."""
        for config_key, env_var in self.ENV_VARS.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Set the value (will be type-converted)
                self.set(config_key, env_value)
                logger.debug(f"Loaded {config_key} from environment variable {env_var}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., 'scraper.max_pages')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., 'scraper.max_pages')
            value: Value to set
        """
        keys = key.split('.')
        config = self._config

        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set value with type conversion
        final_key = keys[-1]
        config[final_key] = self._convert_type(value, self.get(key))

    def _convert_type(self, value: Any, reference: Any) -> Any:
        """
        Convert value to match reference type.

        Args:
            value: Value to convert
            reference: Reference value for type inference

        Returns:
            Converted value
        """
        if reference is None:
            return value

        target_type = type(reference)

        # Handle string to bool conversion
        if target_type == bool:
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)

        # Handle numeric conversions
        if target_type in (int, float):
            try:
                return target_type(value)
            except (ValueError, TypeError):
                logger.warning(
                    f"Could not convert '{value}' to {target_type.__name__}, "
                    f"using default"
                )
                return reference

        return value

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result and
                isinstance(result[key], dict) and
                isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def to_dict(self) -> dict:
        """
        Get configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        return self._config.copy()

    def validate(self):
        """
        Validate configuration.

        Raises:
            ConfigurationException: If configuration is invalid
        """
        # Validate max_pages
        max_pages = self.get('scraper.max_pages')
        if not isinstance(max_pages, int) or max_pages < 1:
            raise ConfigurationException(
                "scraper.max_pages must be a positive integer",
                details={'value': max_pages}
            )

        # Validate timeout
        timeout = self.get('scraper.timeout')
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ConfigurationException(
                "scraper.timeout must be a positive number",
                details={'value': timeout}
            )

        # Validate rate limiting
        rps = self.get('rate_limiting.requests_per_second')
        if not isinstance(rps, (int, float)) or rps <= 0:
            raise ConfigurationException(
                "rate_limiting.requests_per_second must be a positive number",
                details={'value': rps}
            )

        # Validate logging level
        log_level = self.get('logging.level')
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level.upper() not in valid_levels:
            raise ConfigurationException(
                f"logging.level must be one of {valid_levels}",
                details={'value': log_level}
            )

        logger.info("Configuration validation passed")

    def __repr__(self):
        """String representation."""
        return f"Config({len(self._config)} sections)"
