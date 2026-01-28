"""
Configuration management for Validibot CLI.

Configuration is loaded from (in order of precedence):
1. Environment variables (VALIDIBOT_API_URL, VALIDIBOT_TOKEN, etc.)
2. Defaults

Note: The CLI intentionally does not auto-load a `.env` file from the current working
directory to avoid accidentally using credentials in untrusted repos.
"""

from pathlib import Path
from urllib.parse import urlparse

from platformdirs import user_config_dir, user_data_dir
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Application name for platformdirs
APP_NAME = "validibot"
APP_AUTHOR = "validibot"

_LOCAL_API_HOSTS = {"localhost", "127.0.0.1", "::1"}


def normalize_api_url(api_url: str) -> str:
    """Normalize an API base URL to `scheme://host[:port]` (no path/query/fragment)."""
    url = (api_url or "").strip()
    if not url:
        raise ValueError("API URL cannot be empty.")

    # Allow users to pass `validibot.com` without a scheme.
    if "://" not in url:
        url = f"https://{url}"

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError(
            "Invalid API URL. Expected something like `https://validibot.com`."
        )

    if parsed.username or parsed.password:
        raise ValueError("API URL must not include a username or password.")

    host = parsed.hostname.lower()
    host_for_netloc = f"[{host}]" if ":" in host else host
    netloc = (
        f"{host_for_netloc}:{parsed.port}"
        if parsed.port is not None
        else host_for_netloc
    )

    return f"{scheme}://{netloc}"


def get_config_dir() -> Path:
    """Get the configuration directory path.

    Uses platform-appropriate locations:
    - Linux: ~/.config/validibot (XDG_CONFIG_HOME)
    - macOS: ~/Library/Application Support/validibot
    - Windows: C:/Users/<user>/AppData/Local/validibot
    """
    return Path(user_config_dir(APP_NAME, APP_AUTHOR))


def get_data_dir() -> Path:
    """Get the data directory path for persistent storage.

    Uses platform-appropriate locations:
    - Linux: ~/.local/share/validibot (XDG_DATA_HOME)
    - macOS: ~/Library/Application Support/validibot
    - Windows: C:/Users/<user>/AppData/Local/validibot
    """
    return Path(user_data_dir(APP_NAME, APP_AUTHOR))


def ensure_config_dir() -> Path:
    """Ensure config directory exists and return its path."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def ensure_data_dir() -> Path:
    """Ensure data directory exists and return its path."""
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class Settings(BaseSettings):
    """CLI configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="VALIDIBOT_",
        extra="ignore",
    )

    # API configuration - no default; must be configured via set-server or env var
    api_url: str | None = Field(
        default=None,
        description="Base URL for the Validibot API",
    )

    # Authentication
    token: str | None = Field(
        default=None,
        description="API key for authentication (prefer keyring storage)",
    )

    allow_insecure_api_url: bool = Field(
        default=False,
        description="Allow non-HTTPS API URL (dangerous; use only for local development)",
    )

    # Output preferences
    output_format: str = Field(
        default="text",
        description="Default output format: text, json, or table",
    )

    # Timeouts
    timeout: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="Request timeout in seconds",
    )
    poll_interval: int = Field(
        default=5,
        ge=1,
        le=300,
        description="Polling interval for validation status (seconds)",
    )

    @field_validator("api_url")
    @classmethod
    def _normalize_api_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalize_api_url(v)

    @model_validator(mode="after")
    def _enforce_https_api_url(self) -> "Settings":
        if self.api_url is None:
            return self
        parsed = urlparse(self.api_url)
        host = parsed.hostname or ""
        if (
            parsed.scheme != "https"
            and not self.allow_insecure_api_url
            and host not in _LOCAL_API_HOSTS
        ):
            raise ValueError(
                "Refusing to use a non-HTTPS VALIDIBOT_API_URL. "
                "Set VALIDIBOT_ALLOW_INSECURE_API_URL=1 to override."
            )
        return self


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


class ServerNotConfiguredError(Exception):
    """Raised when no server URL has been configured."""

    pass


def get_api_url() -> str:
    """Get the configured API URL.

    Checks in order:
    1. VALIDIBOT_API_URL environment variable
    2. Stored server URL from 'validibot config set-server'

    Raises:
        ServerNotConfiguredError: If no server URL is configured.
    """
    import os

    # Environment variable takes precedence (handled by Settings)
    env_url = os.environ.get("VALIDIBOT_API_URL")
    if env_url:
        settings = get_settings()
        if settings.api_url:
            return settings.api_url
        # Normalize the env var directly if Settings didn't process it
        return normalize_api_url(env_url)

    # Check for stored server URL (lazy import to avoid circular dependency)
    from validibot_cli.auth import get_stored_server_url

    stored_url = get_stored_server_url()
    if stored_url:
        return stored_url

    # No server configured
    raise ServerNotConfiguredError(
        "No server configured. Run 'validibot config set-server <url>' first."
    )


def get_timeout() -> int:
    """Get the configured timeout."""
    return get_settings().timeout
