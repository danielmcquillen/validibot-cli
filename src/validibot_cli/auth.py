"""
Token storage and authentication utilities.

Tokens are stored securely using the system keyring (macOS Keychain,
Windows Credential Manager, Linux Secret Service). Falls back to
a file-based store if keyring is unavailable.
"""

import json
import os
import stat
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console

from validibot_cli.config import (
    ensure_config_dir,
    get_api_url,
    get_settings,
    normalize_api_url,
)

console = Console(stderr=True)

# Keyring service name
KEYRING_SERVICE = "validibot-cli"
KEYRING_USERNAME = "api-token"

# Fallback file for systems without keyring
TOKEN_FILE_NAME = "credentials.json"


def _get_token_file() -> Path:
    """Get the path to the fallback token file."""
    return ensure_config_dir() / TOKEN_FILE_NAME


def _use_keyring() -> bool:
    """Check if keyring is available and should be used."""
    # Allow disabling keyring via environment variable
    if os.environ.get("VALIDIBOT_NO_KEYRING", "").lower() in ("1", "true", "yes"):
        return False

    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring

        # Check if we have a working backend
        backend = keyring.get_keyring()
        return not isinstance(backend, FailKeyring)
    except Exception:
        return False


def _get_host_key(api_url: str | None = None) -> str:
    """Get the host[:port] identifier for a given api_url (used for token scoping)."""
    normalized = normalize_api_url(api_url or get_api_url())
    parsed = urlparse(normalized)
    host_key = (parsed.netloc or "").lower()
    if not host_key:
        raise ValueError("Invalid API URL.")
    return host_key


def _keyring_username(host_key: str) -> str:
    return f"{KEYRING_USERNAME}@{host_key}"


def _load_token_file(token_file: Path) -> dict[str, object]:
    if not token_file.exists():
        return {}
    try:
        with open(token_file, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_token_file(token_file: Path, data: dict[str, object]) -> None:
    tmp_file = token_file.with_name(f"{token_file.name}.tmp")
    fd = os.open(tmp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, token_file)
    finally:
        try:
            if tmp_file.exists():
                tmp_file.unlink()
        except Exception:
            pass

    # Ensure restrictive permissions even if create mode was ignored.
    try:
        os.chmod(token_file, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def save_token(token: str, api_url: str | None = None) -> None:
    """Save an API token securely.

    Uses system keyring if available, falls back to file storage.
    """
    host_key = _get_host_key(api_url)

    if _use_keyring():
        try:
            import keyring

            keyring.set_password(KEYRING_SERVICE, _keyring_username(host_key), token)
            return
        except Exception as e:
            console.print(
                f"Warning: Could not save to keyring: {e}",
                style="yellow",
                markup=False,
            )
            console.print("Falling back to file storage.", style="dim", markup=False)

    # Fallback to file storage
    token_file = _get_token_file()
    data = _load_token_file(token_file)

    tokens: dict[str, str] = {}
    raw_tokens = data.get("tokens")
    if isinstance(raw_tokens, dict):
        tokens = {str(k): str(v) for k, v in raw_tokens.items() if v is not None}

    tokens[host_key] = token
    _write_token_file(token_file, {"tokens": tokens})


def get_stored_token(api_url: str | None = None) -> str | None:
    """Retrieve a stored API token.

    Checks in order:
    1. Environment variable (VALIDIBOT_TOKEN)
    2. System keyring
    3. Fallback file
    """
    # Check environment variable first
    env_token = get_settings().token
    if env_token:
        return env_token

    host_key = _get_host_key(api_url)

    # Try keyring
    if _use_keyring():
        try:
            import keyring

            token = keyring.get_password(KEYRING_SERVICE, _keyring_username(host_key))
            if token:
                return token
        except Exception:
            pass

    # Try file fallback
    token_file = _get_token_file()
    if token_file.exists():
        try:
            with open(token_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                tokens = data.get("tokens")
                if isinstance(tokens, dict):
                    token = tokens.get(host_key)
                    if token:
                        return str(token)
        except Exception:
            pass

    return None


def delete_token(api_url: str | None = None) -> bool:
    """Delete the stored API token.

    Returns True if a token was deleted, False if none was stored.
    """
    host_key = _get_host_key(api_url)
    deleted = False

    # Try to delete from keyring
    if _use_keyring():
        try:
            import keyring

            keyring.delete_password(KEYRING_SERVICE, _keyring_username(host_key))
            deleted = True
        except Exception:
            pass

    # Also delete from file if it exists
    token_file = _get_token_file()
    if token_file.exists():
        try:
            data = _load_token_file(token_file)

            tokens = data.get("tokens") if isinstance(data, dict) else None
            updated_tokens = dict(tokens) if isinstance(tokens, dict) else {}
            file_changed = False

            if host_key in updated_tokens:
                updated_tokens.pop(host_key, None)
                file_changed = True

            if file_changed:
                if updated_tokens:
                    _write_token_file(token_file, {"tokens": updated_tokens})
                else:
                    token_file.unlink()
                deleted = True
        except Exception:
            pass

    return deleted


def is_authenticated() -> bool:
    """Check if we have stored credentials."""
    return get_stored_token() is not None


def get_token_storage_location() -> str:
    """Get a human-readable description of where tokens are stored."""
    if _use_keyring():
        try:
            import keyring

            backend = keyring.get_keyring()
            return f"system keyring ({type(backend).__name__})"
        except Exception:
            pass

    return str(_get_token_file())
