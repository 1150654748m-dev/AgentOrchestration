"""Tests for API middleware components."""

import base64
import json
import time
import pytest
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import PlainTextResponse

from src.api.middleware import AuthMiddleware, parse_token_nbf


def create_test_app():
    """Create a test app with auth middleware."""
    async def homepage(request):
        return PlainTextResponse("Hello, World!")
    
    routes = [Route("/api/v2/agents", homepage)]
    app = Starlette(routes=routes)
    app.add_middleware(AuthMiddleware)
    return app


class TestParseTokenNbf:
    def test_parse_token_with_nbf(self):
        """Test parsing token with nbf claim."""
        payload = {"nbf": 1234567890, "sub": "user123"}
        token = f"header.{base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')}.signature"
        assert parse_token_nbf(token) == 1234567890

    def test_parse_token_with_not_before(self):
        """Test parsing token with not_before claim."""
        payload = {"not_before": 1234567890, "sub": "user123"}
        token = f"header.{base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')}.signature"
        assert parse_token_nbf(token) == 1234567890

    def test_parse_token_without_nbf(self):
        """Test parsing token without nbf claim."""
        payload = {"sub": "user123"}
        token = f"header.{base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')}.signature"
        assert parse_token_nbf(token) is None

    def test_parse_invalid_token(self):
        """Test parsing invalid token."""
        assert parse_token_nbf("invalid-token") is None


class TestAuthMiddlewareNbf:
    def test_valid_token_with_future_nbf_rejected(self):
        """Test that tokens with future nbf are rejected (#4264)."""
        app = create_test_app()
        client = TestClient(app)
        
        # Create token with nbf 1 hour in the future
        future_nbf = time.time() + 3600
        payload = {"nbf": future_nbf, "sub": "user123"}
        token = f"header.{base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')}.signature"
        
        response = client.get("/api/v2/agents", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert "not valid yet" in response.text.lower()

    def test_valid_token_with_past_nbf_accepted(self):
        """Test that tokens with past nbf are accepted."""
        app = create_test_app()
        client = TestClient(app)
        
        # Create token with nbf 1 hour in the past
        past_nbf = time.time() - 3600
        payload = {"nbf": past_nbf, "sub": "user123"}
        token = f"header.{base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')}.signature"
        
        response = client.get("/api/v2/agents", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_valid_token_without_nbf_accepted(self):
        """Test that tokens without nbf are accepted."""
        app = create_test_app()
        client = TestClient(app)
        
        payload = {"sub": "user123"}
        token = f"header.{base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')}.signature"
        
        response = client.get("/api/v2/agents", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_missing_auth_header_rejected(self):
        """Test that requests without auth header are rejected."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/api/v2/agents")
        assert response.status_code == 401

    def test_invalid_auth_format_rejected(self):
        """Test that requests with invalid auth format are rejected."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/api/v2/agents", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert response.status_code == 401

    def test_token_endpoint_excluded(self):
        """Test that token endpoint is excluded from auth check."""
        async def token_endpoint(request):
            return PlainTextResponse("Token")
        
        routes = [Route("/api/v2/auth/token", token_endpoint)]
        app = Starlette(routes=routes)
        app.add_middleware(AuthMiddleware)
        client = TestClient(app)
        
        response = client.get("/api/v2/auth/token")
        assert response.status_code == 200
