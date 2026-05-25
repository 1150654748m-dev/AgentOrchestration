"""Tests for registry configuration validation."""

import json
import os
import tempfile

import pytest

from src.common.registry_config import RegistryConfig, RegistryConfigError


class TestRegistryConfigValidation:
    """Test suite for registry config field validation."""

    def test_rejects_unknown_top_level_fields(self):
        """Test that unknown top-level fields are rejected."""
        config = RegistryConfig()
        
        with pytest.raises(RegistryConfigError) as exc_info:
            config._validate_config({
                "name": "test-registry",
                "endpoint": "https://registry.example.com",
                "unknown_field": "value"
            })
        
        assert "unknown_field" in str(exc_info.value)
        assert "Unknown registry configuration fields" in str(exc_info.value)

    def test_rejects_unknown_auth_fields(self):
        """Test that unknown auth fields are rejected."""
        config = RegistryConfig()
        
        with pytest.raises(RegistryConfigError) as exc_info:
            config._validate_config({
                "name": "test-registry",
                "auth": {
                    "type": "token",
                    "token": "secret",
                    "malicious_field": "bad_value"
                }
            })
        
        assert "malicious_field" in str(exc_info.value)

    def test_rejects_unknown_retry_policy_fields(self):
        """Test that unknown retry_policy fields are rejected."""
        config = RegistryConfig()
        
        with pytest.raises(RegistryConfigError) as exc_info:
            config._validate_config({
                "name": "test-registry",
                "retry_policy": {
                    "max_attempts": 3,
                    "invalid_option": True
                }
            })
        
        assert "invalid_option" in str(exc_info.value)

    def test_accepts_valid_config(self):
        """Test that valid configuration is accepted."""
        config = RegistryConfig()
        
        # Should not raise
        config._validate_config({
            "name": "test-registry",
            "endpoint": "https://registry.example.com",
            "auth": {
                "type": "api_key",
                "api_key": "secret-key"
            },
            "timeout": 30,
            "retry_policy": {
                "max_attempts": 3,
                "backoff_factor": 1.5
            },
            "cache_ttl": 300,
            "enabled": True
        })

    def test_load_from_file_rejects_unknown_fields(self):
        """Test that loading from file rejects unknown fields."""
        config_data = {
            "name": "test-registry",
            "endpoint": "https://registry.example.com",
            "deprecated_field": "old_value"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = RegistryConfig()
            with pytest.raises(RegistryConfigError) as exc_info:
                config.load(temp_path)
            
            assert "deprecated_field" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_load_from_file_accepts_valid_config(self):
        """Test that loading valid config from file works."""
        config_data = {
            "name": "test-registry",
            "endpoint": "https://registry.example.com",
            "timeout": 30,
            "enabled": True
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = RegistryConfig()
            config.load(temp_path)
            
            assert config.get("name") == "test-registry"
            assert config.get("endpoint") == "https://registry.example.com"
            assert config.get("timeout") == 30
            assert config.get("enabled") == True
        finally:
            os.unlink(temp_path)

    def test_set_rejects_unknown_fields(self):
        """Test that set() rejects unknown fields."""
        config = RegistryConfig()
        config._data = {"name": "test"}  # Initialize with valid data
        
        with pytest.raises(RegistryConfigError) as exc_info:
            config.set("unknown_field", "value")
        
        assert "unknown_field" in str(exc_info.value)

    def test_set_accepts_valid_fields(self):
        """Test that set() accepts valid fields."""
        config = RegistryConfig()
        config._data = {"name": "test"}
        
        # Should not raise
        config.set("timeout", 60)
        assert config.get("timeout") == 60

    def test_cache_invalidation_on_reload(self):
        """Test that cache is invalidated when config is reloaded."""
        config_data = {
            "name": "test-registry",
            "timeout": 30
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = RegistryConfig()
            config.load(temp_path)
            
            # Populate cache
            assert config.get("timeout") == 30
            assert "timeout" in config._cache
            
            # Reload should clear cache
            config.load(temp_path)
            assert len(config._cache) == 0
        finally:
            os.unlink(temp_path)

    def test_multiple_unknown_fields_reported(self):
        """Test that all unknown fields are reported in error."""
        config = RegistryConfig()
        
        with pytest.raises(RegistryConfigError) as exc_info:
            config._validate_config({
                "name": "test",
                "bad_field1": "value1",
                "bad_field2": "value2"
            })
        
        error_msg = str(exc_info.value)
        assert "bad_field1" in error_msg
        assert "bad_field2" in error_msg
