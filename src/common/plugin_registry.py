"""Plugin Registry — Manages plugin registration and capability names."""

import logging
from typing import Dict, List, Optional, Set
from threading import Lock

logger = logging.getLogger(__name__)


class PluginRegistrationError(Exception):
    """Raised when plugin registration fails."""
    pass


class Capability:
    """Represents a plugin capability."""
    
    def __init__(self, name: str, version: str, handler: str, metadata: Optional[Dict] = None):
        self.name = name
        self.version = version
        self.handler = handler
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "handler": self.handler,
            "metadata": self.metadata,
        }


class PluginRegistry:
    """
    Registry for managing plugins and their capabilities.
    
    Ensures unique capability names across all registered plugins.
    """
    
    def __init__(self):
        self._plugins: Dict[str, Dict] = {}
        self._capabilities: Dict[str, Capability] = {}
        self._capability_to_plugin: Dict[str, str] = {}
        self._lock = Lock()
    
    def register_plugin(
        self,
        plugin_id: str,
        name: str,
        version: str,
        capabilities: List[Capability],
    ) -> None:
        """
        Register a plugin with its capabilities.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Human-readable plugin name
            version: Plugin version
            capabilities: List of capabilities provided by this plugin
            
        Raises:
            PluginRegistrationError: If a capability name is already registered
        """
        with self._lock:
            # Check for duplicate capability names within the same plugin
            seen_names = set()
            for cap in capabilities:
                if cap.name in seen_names:
                    error_msg = (
                        f"Duplicate capability name '{cap.name}' within plugin '{plugin_id}'. "
                        f"Each capability must have a unique name."
                    )
                    logger.error(error_msg)
                    raise PluginRegistrationError(error_msg)
                seen_names.add(cap.name)
            
            # Check for duplicate capability names in global registry
            for cap in capabilities:
                if cap.name in self._capabilities:
                    existing_plugin = self._capability_to_plugin[cap.name]
                    error_msg = (
                        f"Capability '{cap.name}' is already registered "
                        f"by plugin '{existing_plugin}'. "
                        f"Cannot register duplicate capability from plugin '{plugin_id}'."
                    )
                    logger.error(error_msg)
                    raise PluginRegistrationError(error_msg)
            
            # Register the plugin
            self._plugins[plugin_id] = {
                "id": plugin_id,
                "name": name,
                "version": version,
                "capabilities": [cap.name for cap in capabilities],
            }
            
            # Register capabilities
            for cap in capabilities:
                self._capabilities[cap.name] = cap
                self._capability_to_plugin[cap.name] = plugin_id
                logger.info(
                    f"Registered capability '{cap.name}' from plugin '{plugin_id}'"
                )
            
            logger.info(f"Successfully registered plugin '{plugin_id}' with {len(capabilities)} capabilities")
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        Unregister a plugin and remove its capabilities.
        
        Args:
            plugin_id: The plugin to unregister
            
        Returns:
            True if plugin was found and removed, False otherwise
        """
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            
            plugin = self._plugins.pop(plugin_id)
            
            # Remove capabilities
            for cap_name in plugin["capabilities"]:
                if cap_name in self._capabilities:
                    del self._capabilities[cap_name]
                    del self._capability_to_plugin[cap_name]
                    logger.info(f"Unregistered capability '{cap_name}'")
            
            logger.info(f"Unregistered plugin '{plugin_id}'")
            return True
    
    def get_capability(self, name: str) -> Optional[Capability]:
        """Get a capability by name."""
        with self._lock:
            return self._capabilities.get(name)
    
    def has_capability(self, name: str) -> bool:
        """Check if a capability exists."""
        with self._lock:
            return name in self._capabilities
    
    def get_plugin_for_capability(self, name: str) -> Optional[str]:
        """Get the plugin ID that provides a given capability."""
        with self._lock:
            return self._capability_to_plugin.get(name)
    
    def list_capabilities(self) -> List[str]:
        """List all registered capability names."""
        with self._lock:
            return list(self._capabilities.keys())
    
    def list_plugins(self) -> List[Dict]:
        """List all registered plugins."""
        with self._lock:
            return list(self._plugins.values())
    
    def resolve_capability(self, name: str) -> Optional[Dict]:
        """
        Resolve a capability to its handler information.
        
        Args:
            name: Capability name to resolve
            
        Returns:
            Dict with capability info or None if not found
        """
        with self._lock:
            cap = self._capabilities.get(name)
            if not cap:
                return None
            
            plugin_id = self._capability_to_plugin.get(name)
            return {
                "capability": cap.to_dict(),
                "plugin_id": plugin_id,
            }
    
    def clear(self) -> None:
        """Clear all registered plugins and capabilities (useful for testing)."""
        with self._lock:
            self._plugins.clear()
            self._capabilities.clear()
            self._capability_to_plugin.clear()
            logger.info("Cleared all plugin registrations")


# Global instance for application-wide use
plugin_registry = PluginRegistry()
