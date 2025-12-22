"""Tests for the HTTP client."""

from unittest.mock import Mock, patch

import httpx
import pytest

from validibot_cli.client import AuthenticationError, ValidibotClient
from validibot_cli.models import User


class TestValidibotClient:
    """Tests for ValidibotClient."""

    def test_get_current_user_calls_auth_me_endpoint(self):
        """Test that get_current_user calls /api/v1/auth/me/ and returns User model."""
        client = ValidibotClient(token="test-token", api_url="https://api.example.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "email": "test@example.com",
            "name": "Test User",
        }

        with patch.object(httpx.Client, "get", return_value=mock_response) as mock_get:
            with patch.object(
                httpx.Client, "__enter__", return_value=Mock(get=mock_get)
            ):
                with patch.object(httpx.Client, "__exit__", return_value=None):
                    result = client.get_current_user()

        assert isinstance(result, User)
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        mock_get.assert_called_once()
        # Verify the URL includes /auth/me/
        call_args = mock_get.call_args
        assert "/api/v1/auth/me/" in call_args[0][0]

    def test_get_current_user_uses_bearer_token(self):
        """Test that requests use Bearer authentication."""
        client = ValidibotClient(
            token="test-token-123", api_url="https://api.example.com"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "test@example.com", "name": ""}

        with patch.object(httpx.Client, "get", return_value=mock_response) as mock_get:
            with patch.object(
                httpx.Client, "__enter__", return_value=Mock(get=mock_get)
            ):
                with patch.object(httpx.Client, "__exit__", return_value=None):
                    client.get_current_user()

        call_kwargs = mock_get.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-token-123"

    def test_raises_auth_error_on_401(self):
        """Test that 401 response raises AuthenticationError."""
        client = ValidibotClient(token="bad-token", api_url="https://api.example.com")

        mock_response = Mock()
        mock_response.status_code = 401

        with patch.object(httpx.Client, "get", return_value=mock_response):
            with patch.object(
                httpx.Client,
                "__enter__",
                return_value=Mock(get=lambda *a, **k: mock_response),
            ):
                with patch.object(httpx.Client, "__exit__", return_value=None):
                    with pytest.raises(AuthenticationError):
                        client.get_current_user()

    def test_raises_auth_error_on_403(self):
        """Test that 403 response raises AuthenticationError."""
        client = ValidibotClient(token="bad-token", api_url="https://api.example.com")

        mock_response = Mock()
        mock_response.status_code = 403

        with patch.object(httpx.Client, "get", return_value=mock_response):
            with patch.object(
                httpx.Client,
                "__enter__",
                return_value=Mock(get=lambda *a, **k: mock_response),
            ):
                with patch.object(httpx.Client, "__exit__", return_value=None):
                    with pytest.raises(AuthenticationError):
                        client.get_current_user()
