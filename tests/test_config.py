"""Tests for configuration validation and normalization."""

import pytest

from validibot_cli.config import Settings, normalize_api_url


def test_normalize_api_url_adds_https_scheme():
    assert normalize_api_url("validibot.com") == "https://validibot.com"


def test_settings_rejects_http_non_localhost_by_default():
    with pytest.raises(ValueError, match="Refusing to use a non-HTTPS"):
        Settings(api_url="http://example.com")


def test_settings_allows_http_localhost_by_default():
    settings = Settings(api_url="http://localhost:8000")
    assert settings.api_url == "http://localhost:8000"


def test_settings_allows_http_non_localhost_with_override():
    settings = Settings(api_url="http://example.com", allow_insecure_api_url=True)
    assert settings.api_url == "http://example.com"

