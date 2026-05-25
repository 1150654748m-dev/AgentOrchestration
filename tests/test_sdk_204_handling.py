"""Tests for SDK client 204 response handling."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from src.sdk.client import OrchestratorClient


class TestSDK204ResponseHandling:
    """Test suite for 204 No Content response handling."""

    def setup_method(self):
        """Set up test client."""
        self.client = OrchestratorClient(
            base_url="https://test.api.agent-orchestrator.io",
            api_key="test-api-key"
        )

    @patch('src.sdk.client.urlopen')
    def test_delete_agent_returns_204_empty_response(self, mock_urlopen):
        """Test that delete_agent handles 204 No Content correctly."""
        # Mock a 204 response with empty body
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.read.return_value = b''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.delete_agent("test-agent-id")

        # Should return empty dict, not crash on JSON decode
        assert result == {}
        assert "error" not in result

    @patch('src.sdk.client.urlopen')
    def test_stop_agent_returns_204_empty_response(self, mock_urlopen):
        """Test that stop_agent handles 204 No Content correctly."""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.read.return_value = b''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.stop_agent("test-agent-id")

        assert result == {}
        assert "error" not in result

    @patch('src.sdk.client.urlopen')
    def test_200_response_with_body_still_parses_json(self, mock_urlopen):
        """Test that normal 200 responses with body still work."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"id": "agent-123", "status": "running"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.get_agent("test-agent-id")

        assert result["id"] == "agent-123"
        assert result["status"] == "running"

    @patch('src.sdk.client.urlopen')
    def test_200_response_with_empty_body_returns_empty_dict(self, mock_urlopen):
        """Test that 200 with empty body returns empty dict safely."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client._request("GET", "/test")

        assert result == {}

    @patch('src.sdk.client.urlopen')
    def test_http_error_still_returns_error_dict(self, mock_urlopen):
        """Test that HTTP errors are still handled correctly."""
        from urllib.error import HTTPError
        
        mock_urlopen.side_effect = HTTPError(
            url="https://test.api.agent-orchestrator.io/api/v2/agents/test-id",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None
        )

        result = self.client.get_agent("nonexistent-agent")

        assert result["error"] == 404
        assert result["message"] == "Not Found"
