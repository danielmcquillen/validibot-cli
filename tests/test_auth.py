"""Tests for authentication module."""

import os
from unittest.mock import patch

import pytest

from validibot_cli.auth import (
    delete_token,
    get_stored_token,
    save_token,
)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Use a temporary directory for config."""
    with patch("validibot_cli.auth.ensure_config_dir", return_value=tmp_path):
        with patch(
            "validibot_cli.auth._get_token_file",
            return_value=tmp_path / "credentials.json",
        ):
            with patch("validibot_cli.auth._use_keyring", return_value=False):
                yield tmp_path


@pytest.fixture
def no_env_token():
    """Ensure no token is set via environment."""
    with patch("validibot_cli.auth.get_settings") as mock_settings:
        mock_settings.return_value.token = None
        yield


class TestTokenStorage:
    """Tests for file-based token storage."""

    def test_save_and_retrieve_token(self, temp_config_dir, no_env_token):
        """Test saving and retrieving a token."""
        test_token = "test_token_12345"

        save_token(test_token, api_url="https://validibot.com")
        retrieved = get_stored_token(api_url="https://validibot.com")

        assert retrieved == test_token

    def test_delete_token(self, temp_config_dir, no_env_token):
        """Test deleting a stored token."""
        test_token = "test_token_12345"

        save_token(test_token, api_url="https://validibot.com")
        assert get_stored_token(api_url="https://validibot.com") == test_token

        deleted = delete_token(api_url="https://validibot.com")
        assert deleted is True
        assert get_stored_token(api_url="https://validibot.com") is None

    def test_delete_nonexistent_token(self, temp_config_dir, no_env_token):
        """Test deleting when no token exists."""
        deleted = delete_token(api_url="https://validibot.com")
        assert deleted is False

    def test_token_file_permissions(self, temp_config_dir, no_env_token):
        """Test that token file has restrictive permissions."""
        import stat

        test_token = "test_token_12345"
        save_token(test_token, api_url="https://validibot.com")

        token_file = temp_config_dir / "credentials.json"
        mode = token_file.stat().st_mode

        # Check that only owner can read/write (on Unix)
        if os.name != "nt":
            assert mode & stat.S_IRWXG == 0  # No group permissions
            assert mode & stat.S_IRWXO == 0  # No other permissions


class TestEnvironmentToken:
    """Tests for environment variable token."""

    def test_env_token_takes_precedence(self, temp_config_dir):
        """Test that environment variable token is used first."""
        # Save a token to file first
        with patch("validibot_cli.auth._use_keyring", return_value=False):
            save_token("file_token_xyz", api_url="https://validibot.com")

        # Now mock get_settings to return an env token - patch where it's used, not where it's defined
        with patch("validibot_cli.auth.get_settings") as mock_settings:
            mock_settings.return_value.token = "env_token_abc"

            # Environment token should be returned
            token = get_stored_token(api_url="https://validibot.com")
            assert token == "env_token_abc"
