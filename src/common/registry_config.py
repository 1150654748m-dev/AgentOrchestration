"""Registry configuration loader with strict field validation."""

import json
from typing import Any, Dict, List, Optional, Set


class RegistryConfigError(Exception):
    """Raised when registry configuration is invalid."""
    pass


class RegistryConfig:
    """Registry configuration loader that rejects unknown fields."""
    
    # Define allowed fields for registry configuration
    ALLOWED_FIELDS: Set[str] = {
        "name",
        "endpoint",
        "auth",
        "timeout",
        "retry_policy",
        "cache_ttl",
        "enabled",
    }
    
    # Define allowed nested fields
    ALLOWED_AUTH_FIELDS: Set[str] = {
        "type",
        "token",
        "username",
        "password",
        "api_key",
    }
    
    ALLOWED_RETRY_FIELDS: Set[str] = {
        "max_attempts",
        "backoff_factor",
        "retry_on",
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self._data: Dict[str, Any] = {}
        self._cache: Dict[str, Any] = {}
        if config_path:
            self.load(config_path)
    
    def load(self, path: str) -> None:
        """Load and validate registry configuration from file."""
        with open(path) as f:
            raw_data = json.load(f)
        
        # Validate and reject unknown fields
        self._validate_config(raw_data)
        self._data = raw_data
        # Invalidate cache when config is reloaded
        self._cache.clear()
    
    def _validate_config(self, data: Dict[str, Any], path: str = "") -> None:
        """Recursively validate configuration fields."""
        if not isinstance(data, dict):
            return
        
        # Determine allowed fields based on current path
        if path == "":
            allowed = self.ALLOWED_FIELDS
        elif path == "auth":
            allowed = self.ALLOWED_AUTH_FIELDS
        elif path == "retry_policy":
            allowed = self.ALLOWED_RETRY_FIELDS
        else:
            # For other nested objects, allow any fields (flexibility)
            allowed = None
        
        if allowed is not None:
            unknown_fields = set(data.keys()) - allowed
            if unknown_fields:
                raise RegistryConfigError(
                    f"Unknown registry configuration fields: {unknown_fields}. "
                    f"Allowed fields at '{path or 'root'}': {allowed}"
                )
        
        # Recursively validate nested objects
        for key, value in data.items():
            if isinstance(value, dict):
                new_path = f"{path}.{key}" if path else key
                self._validate_config(value, new_path)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with caching."""
        if key in self._cache:
            return self._cache[key]
        
        parts = key.split(".")
        current = self._data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default
        
        self._cache[key] = current
        return current
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value with validation."""
        # Validate the key is allowed
        root_key = key.split(".")[0]
        if root_key not in self.ALLOWED_FIELDS:
            raise RegistryConfigError(
                f"Cannot set unknown field '{key}'. Allowed: {self.ALLOWED_FIELDS}"
            )
        
        parts = key.split(".")
        current = self._data
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
        
        # Invalidate cache entry
        if key in self._cache:
            del self._cache[key]
    
    def to_dict(self) -> Dict:
        """Return configuration as dictionary."""
        return self._data.copy()
    
    def invalidate_cache(self) -> None:
        """Invalidate all cached entries."""
        self._cache.clear()
