"""Tests for plugin registry and capability management."""

import pytest
from src.common.plugin_registry import (
    PluginRegistry,
    Capability,
    PluginRegistrationError,
)


class TestCapability:
    def test_capability_creation(self):
        cap = Capability("test.cap", "1.0.0", "test_handler")
        assert cap.name == "test.cap"
        assert cap.version == "1.0.0"
        assert cap.handler == "test_handler"
    
    def test_capability_to_dict(self):
        cap = Capability("test.cap", "1.0.0", "test_handler", {"key": "value"})
        data = cap.to_dict()
        assert data["name"] == "test.cap"
        assert data["version"] == "1.0.0"
        assert data["handler"] == "test_handler"
        assert data["metadata"] == {"key": "value"}


class TestPluginRegistry:
    def setup_method(self):
        self.registry = PluginRegistry()
    
    def test_register_plugin_success(self):
        """Test successful plugin registration."""
        caps = [
            Capability("cap1", "1.0", "handler1"),
            Capability("cap2", "1.0", "handler2"),
        ]
        self.registry.register_plugin("plugin1", "Test Plugin", "1.0.0", caps)
        
        assert self.registry.has_capability("cap1")
        assert self.registry.has_capability("cap2")
        assert len(self.registry.list_capabilities()) == 2
    
    def test_register_duplicate_capability(self):
        """Regression test: duplicate capability names should be rejected."""
        caps1 = [Capability("shared.cap", "1.0", "handler1")]
        self.registry.register_plugin("plugin1", "Plugin 1", "1.0.0", caps1)
        
        caps2 = [Capability("shared.cap", "2.0", "handler2")]
        with pytest.raises(PluginRegistrationError, match="already registered"):
            self.registry.register_plugin("plugin2", "Plugin 2", "1.0.0", caps2)
    
    def test_register_duplicate_within_same_plugin(self):
        """Test that duplicate capabilities within the same plugin are rejected."""
        caps = [
            Capability("dup.cap", "1.0", "handler1"),
            Capability("dup.cap", "2.0", "handler2"),  # Duplicate name
        ]
        # The second capability should be caught as duplicate of the first
        with pytest.raises(PluginRegistrationError, match="Duplicate capability name"):
            self.registry.register_plugin("plugin1", "Plugin 1", "1.0.0", caps)
    
    def test_get_capability(self):
        """Test retrieving a capability."""
        cap = Capability("test.cap", "1.0", "test_handler", {"meta": "data"})
        self.registry.register_plugin("plugin1", "Test", "1.0", [cap])
        
        retrieved = self.registry.get_capability("test.cap")
        assert retrieved is not None
        assert retrieved.name == "test.cap"
        assert retrieved.handler == "test_handler"
    
    def test_get_nonexistent_capability(self):
        """Test retrieving a non-existent capability."""
        assert self.registry.get_capability("nonexistent") is None
    
    def test_has_capability(self):
        """Test checking capability existence."""
        assert not self.registry.has_capability("test.cap")
        
        self.registry.register_plugin("plugin1", "Test", "1.0", [Capability("test.cap", "1.0", "handler")])
        assert self.registry.has_capability("test.cap")
    
    def test_get_plugin_for_capability(self):
        """Test finding which plugin provides a capability."""
        self.registry.register_plugin(
            "plugin1",
            "Test Plugin",
            "1.0",
            [Capability("test.cap", "1.0", "handler")]
        )
        
        plugin_id = self.registry.get_plugin_for_capability("test.cap")
        assert plugin_id == "plugin1"
    
    def test_unregister_plugin(self):
        """Test unregistering a plugin."""
        caps = [Capability("cap1", "1.0", "h1"), Capability("cap2", "1.0", "h2")]
        self.registry.register_plugin("plugin1", "Test", "1.0", caps)
        
        assert self.registry.has_capability("cap1")
        assert self.registry.unregister_plugin("plugin1")
        assert not self.registry.has_capability("cap1")
        assert not self.registry.has_capability("cap2")
    
    def test_unregister_nonexistent_plugin(self):
        """Test unregistering a plugin that doesn't exist."""
        assert not self.registry.unregister_plugin("nonexistent")
    
    def test_list_capabilities(self):
        """Test listing all capabilities."""
        self.registry.register_plugin("p1", "P1", "1.0", [Capability("cap1", "1.0", "h1")])
        self.registry.register_plugin("p2", "P2", "1.0", [Capability("cap2", "1.0", "h2")])
        
        caps = self.registry.list_capabilities()
        assert "cap1" in caps
        assert "cap2" in caps
        assert len(caps) == 2
    
    def test_list_plugins(self):
        """Test listing all plugins."""
        self.registry.register_plugin("p1", "Plugin 1", "1.0", [Capability("c1", "1.0", "h1")])
        self.registry.register_plugin("p2", "Plugin 2", "2.0", [Capability("c2", "1.0", "h2")])
        
        plugins = self.registry.list_plugins()
        assert len(plugins) == 2
        plugin_ids = [p["id"] for p in plugins]
        assert "p1" in plugin_ids
        assert "p2" in plugin_ids
    
    def test_resolve_capability(self):
        """Test resolving a capability to its handler."""
        cap = Capability("test.cap", "1.0", "test_handler", {"key": "value"})
        self.registry.register_plugin("plugin1", "Test", "1.0", [cap])
        
        resolved = self.registry.resolve_capability("test.cap")
        assert resolved is not None
        assert resolved["plugin_id"] == "plugin1"
        assert resolved["capability"]["name"] == "test.cap"
        assert resolved["capability"]["handler"] == "test_handler"
    
    def test_resolve_nonexistent_capability(self):
        """Test resolving a non-existent capability."""
        assert self.registry.resolve_capability("nonexistent") is None
    
    def test_clear(self):
        """Test clearing all registrations."""
        self.registry.register_plugin("p1", "P1", "1.0", [Capability("c1", "1.0", "h1")])
        self.registry.register_plugin("p2", "P2", "1.0", [Capability("c2", "1.0", "h2")])
        
        assert len(self.registry.list_capabilities()) == 2
        self.registry.clear()
        assert len(self.registry.list_capabilities()) == 0
        assert len(self.registry.list_plugins()) == 0


class TestPluginRegistryEdgeCases:
    """Edge case tests for plugin registry."""
    
    def setup_method(self):
        self.registry = PluginRegistry()
    
    def test_capability_name_after_plugin_unregistered(self):
        """Test that capability can be re-registered after plugin is removed."""
        caps = [Capability("reusable.cap", "1.0", "handler")]
        self.registry.register_plugin("plugin1", "Test", "1.0", caps)
        
        # Unregister first plugin
        self.registry.unregister_plugin("plugin1")
        
        # Should be able to register the same capability name again
        caps2 = [Capability("reusable.cap", "2.0", "new_handler")]
        self.registry.register_plugin("plugin2", "Test 2", "2.0", caps2)
        
        cap = self.registry.get_capability("reusable.cap")
        assert cap.version == "2.0"
        assert cap.handler == "new_handler"
    
    def test_multiple_plugins_different_capabilities(self):
        """Test multiple plugins with different capabilities."""
        self.registry.register_plugin(
            "plugin1",
            "Plugin 1",
            "1.0",
            [Capability("cap.a", "1.0", "h1"), Capability("cap.b", "1.0", "h2")]
        )
        self.registry.register_plugin(
            "plugin2",
            "Plugin 2",
            "1.0",
            [Capability("cap.c", "1.0", "h3"), Capability("cap.d", "1.0", "h4")]
        )
        
        assert len(self.registry.list_capabilities()) == 4
        assert self.registry.get_plugin_for_capability("cap.a") == "plugin1"
        assert self.registry.get_plugin_for_capability("cap.c") == "plugin2"
    
    def test_capability_metadata_preserved(self):
        """Test that capability metadata is preserved."""
        metadata = {"author": "test", "description": "Test capability"}
        cap = Capability("meta.cap", "1.0", "handler", metadata)
        self.registry.register_plugin("plugin1", "Test", "1.0", [cap])
        
        retrieved = self.registry.get_capability("meta.cap")
        assert retrieved.metadata == metadata


class TestIntegration:
    """Integration tests for plugin registry."""
    
    def test_end_to_end_plugin_lifecycle(self):
        """Test complete plugin lifecycle: register, resolve, unregister."""
        registry = PluginRegistry()
        
        # Register a plugin with capabilities
        caps = [
            Capability("data.process", "1.0", "process_handler"),
            Capability("data.validate", "1.0", "validate_handler"),
        ]
        registry.register_plugin("data-plugin", "Data Processing", "1.0.0", caps)
        
        # Verify capabilities are registered
        assert registry.has_capability("data.process")
        assert registry.has_capability("data.validate")
        
        # Resolve capabilities
        process_cap = registry.resolve_capability("data.process")
        assert process_cap["plugin_id"] == "data-plugin"
        assert process_cap["capability"]["handler"] == "process_handler"
        
        # Unregister plugin
        registry.unregister_plugin("data-plugin")
        
        # Verify capabilities are removed
        assert not registry.has_capability("data.process")
        assert not registry.has_capability("data.validate")
    
    def test_duplicate_prevention_integrity(self):
        """Regression test: ensure duplicate prevention maintains registry integrity."""
        registry = PluginRegistry()
        
        # Register first plugin
        registry.register_plugin(
            "plugin1",
            "Plugin 1",
            "1.0",
            [Capability("unique.cap", "1.0", "handler1")]
        )
        
        # Try to register second plugin with duplicate capability
        try:
            registry.register_plugin(
                "plugin2",
                "Plugin 2",
                "1.0",
                [Capability("unique.cap", "2.0", "handler2")]
            )
            assert False, "Should have raised PluginRegistrationError"
        except PluginRegistrationError:
            pass
        
        # Verify first plugin's capability is still intact
        assert registry.has_capability("unique.cap")
        cap = registry.get_capability("unique.cap")
        assert cap.version == "1.0"
        assert cap.handler == "handler1"
        assert registry.get_plugin_for_capability("unique.cap") == "plugin1"
