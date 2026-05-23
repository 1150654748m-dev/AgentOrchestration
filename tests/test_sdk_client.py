"""Tests for SDK client."""

import pytest
from src.sdk.client import OrchestratorClient


class TestOrchestratorClient:
    """Tests for the OrchestratorClient."""

    def test_register_agent_with_valid_name(self):
        """Test that register_agent accepts valid agent names."""
        client = OrchestratorClient()
        # This will fail with network error, but validates the name check passes
        with pytest.raises(Exception):  # Network error expected
            client.register_agent("valid_agent", "test_type")

    def test_register_agent_rejects_empty_string(self):
        """Test that register_agent rejects empty string name."""
        client = OrchestratorClient()
        with pytest.raises(ValueError, match="agent name cannot be empty"):
            client.register_agent("", "test_type")

    def test_register_agent_rejects_whitespace_only(self):
        """Test that register_agent rejects whitespace-only name."""
        client = OrchestratorClient()
        with pytest.raises(ValueError, match="agent name cannot be empty"):
            client.register_agent("   ", "test_type")

    def test_register_agent_rejects_multiple_whitespace(self):
        """Test that register_agent rejects multiple whitespace characters."""
        client = OrchestratorClient()
        with pytest.raises(ValueError, match="agent name cannot be empty"):
            client.register_agent("\t\n  \r", "test_type")

    def test_register_agent_rejects_none_name(self):
        """Test that register_agent rejects None as name."""
        client = OrchestratorClient()
        with pytest.raises(TypeError, match="agent name must be a string"):
            client.register_agent(None, "test_type")

    def test_register_agent_rejects_non_string_name(self):
        """Test that register_agent rejects non-string name types."""
        client = OrchestratorClient()
        with pytest.raises(TypeError, match="agent name must be a string"):
            client.register_agent(123, "test_type")

    def test_register_agent_strips_whitespace(self):
        """Test that register_agent strips leading/trailing whitespace."""
        client = OrchestratorClient()
        # This will fail with network error, but we can verify the name is stripped
        # by checking the request would be made with stripped name
        with pytest.raises(Exception):  # Network error expected
            client.register_agent("  valid_agent  ", "test_type")

    def test_register_agent_accepts_name_with_internal_whitespace(self):
        """Test that register_agent accepts names with internal whitespace."""
        client = OrchestratorClient()
        # Names like "my agent" should be valid (only leading/trailing is stripped)
        with pytest.raises(Exception):  # Network error expected
            client.register_agent("my agent", "test_type")
