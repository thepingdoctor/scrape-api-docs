"""Unit tests for configuration management module."""

import pytest
import tempfile
import os
from pathlib import Path

from scrape_api_docs.config import Config
from scrape_api_docs.exceptions import ConfigurationException


class TestConfig:
    """Test suite for Config class."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = Config()

        assert config.get('scraper.max_pages') == 100
        assert config.get('scraper.timeout') == 10
        assert config.get('rate_limiting.requests_per_second') == 2.0
        assert config.get('robots.enabled') is True
        assert config.get('logging.level') == 'INFO'

    def test_get_nested_value(self):
        """Test getting nested configuration values."""
        config = Config()

        value = config.get('rate_limiting.requests_per_second')
        assert value == 2.0

    def test_get_with_default(self):
        """Test getting non-existent value with default."""
        config = Config()

        value = config.get('nonexistent.key', default=42)
        assert value == 42

    def test_set_value(self):
        """Test setting configuration values."""
        config = Config()

        config.set('scraper.max_pages', 200)
        assert config.get('scraper.max_pages') == 200

    def test_set_nested_value(self):
        """Test setting nested configuration values."""
        config = Config()

        config.set('custom.nested.value', 'test')
        assert config.get('custom.nested.value') == 'test'

    def test_load_from_yaml(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
scraper:
  max_pages: 500
  timeout: 20

rate_limiting:
  requests_per_second: 5.0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = Config.load(f.name)

                assert config.get('scraper.max_pages') == 500
                assert config.get('scraper.timeout') == 20
                assert config.get('rate_limiting.requests_per_second') == 5.0
            finally:
                os.unlink(f.name)

    def test_load_nonexistent_file(self):
        """Test loading from non-existent file uses defaults."""
        config = Config.load('/nonexistent/path/config.yaml')

        # Should still have defaults
        assert config.get('scraper.max_pages') == 100

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises exception."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content:")
            f.flush()

            try:
                with pytest.raises(ConfigurationException):
                    Config.load(f.name)
            finally:
                os.unlink(f.name)

    def test_environment_variable_override(self):
        """Test environment variable overrides."""
        os.environ['SCRAPER_MAX_PAGES'] = '300'
        os.environ['LOG_LEVEL'] = 'DEBUG'

        try:
            config = Config.load()

            assert config.get('scraper.max_pages') == 300
            assert config.get('logging.level') == 'DEBUG'
        finally:
            del os.environ['SCRAPER_MAX_PAGES']
            del os.environ['LOG_LEVEL']

    def test_type_conversion_int(self):
        """Test automatic type conversion for integers."""
        config = Config()

        config.set('scraper.max_pages', '500')  # String
        assert config.get('scraper.max_pages') == 500  # Converted to int
        assert isinstance(config.get('scraper.max_pages'), int)

    def test_type_conversion_float(self):
        """Test automatic type conversion for floats."""
        config = Config()

        config.set('rate_limiting.requests_per_second', '3.5')
        assert config.get('rate_limiting.requests_per_second') == 3.5
        assert isinstance(config.get('rate_limiting.requests_per_second'), float)

    def test_type_conversion_bool(self):
        """Test automatic type conversion for booleans."""
        config = Config()

        config.set('robots.enabled', 'true')
        assert config.get('robots.enabled') is True

        config.set('robots.enabled', 'false')
        assert config.get('robots.enabled') is False

        config.set('robots.enabled', '1')
        assert config.get('robots.enabled') is True

        config.set('robots.enabled', '0')
        assert config.get('robots.enabled') is False

    def test_validate_success(self):
        """Test configuration validation passes for valid config."""
        config = Config()
        config.validate()  # Should not raise

    def test_validate_invalid_max_pages(self):
        """Test validation fails for invalid max_pages."""
        config = Config()
        config.set('scraper.max_pages', -1)

        with pytest.raises(ConfigurationException) as exc_info:
            config.validate()

        assert 'max_pages' in str(exc_info.value)

    def test_validate_invalid_timeout(self):
        """Test validation fails for invalid timeout."""
        config = Config()
        config.set('scraper.timeout', 0)

        with pytest.raises(ConfigurationException):
            config.validate()

    def test_validate_invalid_rate_limit(self):
        """Test validation fails for invalid rate limit."""
        config = Config()
        config.set('rate_limiting.requests_per_second', -2.0)

        with pytest.raises(ConfigurationException):
            config.validate()

    def test_validate_invalid_log_level(self):
        """Test validation fails for invalid log level."""
        config = Config()
        config.set('logging.level', 'INVALID')

        with pytest.raises(ConfigurationException):
            config.validate()

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config = Config()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert 'scraper' in config_dict
        assert 'rate_limiting' in config_dict
        assert config_dict['scraper']['max_pages'] == 100

    def test_deep_merge(self):
        """Test deep merging of configurations."""
        base = {'a': {'b': 1, 'c': 2}, 'd': 3}
        override = {'a': {'b': 10}, 'e': 4}

        config = Config()
        result = config._deep_merge(base, override)

        assert result['a']['b'] == 10  # Overridden
        assert result['a']['c'] == 2   # Preserved
        assert result['d'] == 3        # Preserved
        assert result['e'] == 4        # Added

    def test_repr(self):
        """Test string representation."""
        config = Config()
        repr_str = repr(config)

        assert 'Config' in repr_str
        assert 'sections' in repr_str
