"""Tests for security boundaries: HTTPS enforcement, graceful error handling,
and structured API error preservation.

These tests cover the security and robustness hardening across the CLI.
Each test class targets a specific finding from the security review.
"""

import os
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

import validibot_cli.config as config_module
from validibot_cli.client import (
    AmbiguousWorkflowError,
    APIError,
    ValidibotClient,
    _check_ambiguous_workflow_error,
)
from validibot_cli.config import ServerNotConfiguredError, enforce_https
from validibot_cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Reset the global settings cache between tests."""
    config_module._settings = None
    yield
    config_module._settings = None


# ── HTTPS enforcement ──────────────────────────────────────────────────
# The CLI must reject non-HTTPS URLs on both the env-var path and the
# stored-config path, unless the URL targets localhost or the user
# explicitly opts in with --allow-insecure / VALIDIBOT_ALLOW_INSECURE_API_URL.


class TestHttpsEnforcement:
    """Tests that the HTTPS guard applies consistently to all config paths."""

    def test_enforce_https_rejects_http_remote(self):
        """Non-localhost HTTP URLs must be rejected by default."""
        with pytest.raises(ValueError, match="Refusing to use a non-HTTPS"):
            enforce_https("http://example.com")

    def test_enforce_https_allows_https(self):
        """HTTPS URLs must always be accepted."""
        enforce_https("https://example.com")  # should not raise

    def test_enforce_https_allows_localhost_http(self):
        """HTTP to localhost is acceptable for local development."""
        enforce_https("http://localhost:8000")
        enforce_https("http://127.0.0.1:8000")

    def test_enforce_https_allows_insecure_override(self):
        """The allow_insecure flag should bypass the HTTPS check."""
        enforce_https("http://example.com", allow_insecure=True)  # should not raise

    def test_set_server_rejects_http_remote(self, tmp_path):
        """validibot config set-server must reject http:// for non-localhost."""
        with patch("validibot_cli.commands.config.save_server_url"):
            result = runner.invoke(app, ["config", "set-server", "http://example.com"])
        assert result.exit_code == 1
        assert "non-HTTPS" in result.output

    def test_set_server_accepts_http_with_allow_insecure(self, tmp_path):
        """validibot config set-server --allow-insecure should accept http://."""
        with patch("validibot_cli.commands.config.save_server_url"):
            result = runner.invoke(
                app,
                ["config", "set-server", "http://example.com", "--allow-insecure"],
            )
        assert result.exit_code == 0

    def test_set_server_accepts_http_with_env_override(self, tmp_path):
        """config set-server should honor VALIDIBOT_ALLOW_INSECURE_API_URL=1."""
        with patch("validibot_cli.commands.config.save_server_url"):
            result = runner.invoke(
                app,
                ["config", "set-server", "http://example.com"],
                env={"VALIDIBOT_ALLOW_INSECURE_API_URL": "1"},
            )
        assert result.exit_code == 0

    def test_set_server_accepts_https(self, tmp_path):
        """validibot config set-server should accept https:// URLs."""
        with patch("validibot_cli.commands.config.save_server_url"):
            result = runner.invoke(
                app, ["config", "set-server", "https://validibot.example.com"]
            )
        assert result.exit_code == 0

    def test_get_api_url_enforces_https_on_stored_config(self):
        """get_api_url() must enforce HTTPS when reading from stored config.

        Previously, env-var URLs went through Settings validation but stored
        URLs were returned as-is, allowing http:// to bypass the guard.
        """
        from validibot_cli.config import get_api_url

        with patch.dict(os.environ, {}, clear=False):
            # Remove VALIDIBOT_API_URL if set
            env = {k: v for k, v in os.environ.items() if k != "VALIDIBOT_API_URL"}
            with patch.dict(os.environ, env, clear=True):
                with patch(
                    "validibot_cli.auth.get_stored_server_url",
                    return_value="http://example.com",
                ):
                    with pytest.raises(ValueError, match="non-HTTPS"):
                        get_api_url()


# ── Graceful error handling on unconfigured server ─────────────────────
# When no server is configured, auth helpers should return None/False
# rather than crashing with a traceback.  The CLI commands should show
# a clean error message pointing the user to `config set-server`.


class TestUnconfiguredServerHandling:
    """Tests that the CLI handles 'no server configured' gracefully."""

    def test_is_authenticated_returns_false_without_server(self):
        """is_authenticated() should return False, not crash, when no server exists."""
        from validibot_cli.auth import is_authenticated

        with patch(
            "validibot_cli.auth.get_api_url",
            side_effect=ServerNotConfiguredError("No server"),
        ):
            with patch("validibot_cli.auth.get_settings") as mock_settings:
                mock_settings.return_value.token = None
                assert is_authenticated() is False

    def test_get_stored_token_returns_none_without_server(self):
        """get_stored_token() should return None when no server is configured."""
        from validibot_cli.auth import get_stored_token

        with patch(
            "validibot_cli.auth.get_api_url",
            side_effect=ServerNotConfiguredError("No server"),
        ):
            with patch("validibot_cli.auth.get_settings") as mock_settings:
                mock_settings.return_value.token = None
                assert get_stored_token() is None

    def test_get_default_org_returns_none_without_server(self):
        """get_default_org() should return None when no server is configured."""
        from validibot_cli.auth import get_default_org

        with patch(
            "validibot_cli.auth.get_api_url",
            side_effect=ServerNotConfiguredError("No server"),
        ):
            with patch.dict(os.environ, {}, clear=False):
                env = {k: v for k, v in os.environ.items() if k != "VALIDIBOT_ORG"}
                with patch.dict(os.environ, env, clear=True):
                    assert get_default_org() is None

    def test_delete_token_returns_false_without_server(self):
        """delete_token() should return False when no server is configured."""
        from validibot_cli.auth import delete_token

        with patch(
            "validibot_cli.auth.get_api_url",
            side_effect=ServerNotConfiguredError("No server"),
        ):
            assert delete_token() is False

    def test_logout_does_not_crash_without_server(self):
        """validibot logout should show a clean message, not a traceback."""
        with patch(
            "validibot_cli.auth.get_api_url",
            side_effect=ServerNotConfiguredError("No server"),
        ):
            with patch("validibot_cli.auth.get_settings") as mock_settings:
                mock_settings.return_value.token = None
                result = runner.invoke(app, ["logout"])
        # Should exit cleanly (not crash)
        assert result.exit_code == 0
        assert "not currently logged in" in result.output.lower()

    def test_workflows_list_shows_clean_error_without_server(self):
        """validibot workflows list should show a clean error, not a traceback."""
        with patch(
            "validibot_cli.auth.get_api_url",
            side_effect=ServerNotConfiguredError("No server"),
        ):
            with patch("validibot_cli.auth.get_settings") as mock_settings:
                mock_settings.return_value.token = None
                result = runner.invoke(app, ["workflows", "list", "--org", "test"])
        assert result.exit_code == 1
        assert "No server configured" in result.output


class TestInvalidEnvConfigurationHandling:
    """Tests that invalid env-backed settings surface clean CLI errors."""

    def test_login_shows_clean_error_for_invalid_env_url(self):
        result = runner.invoke(
            app,
            ["login", "--token", "abc", "--no-verify"],
            env={
                "VALIDIBOT_API_URL": "http://example.com",
                "VALIDIBOT_NO_KEYRING": "1",
            },
        )
        assert result.exit_code == 1
        assert "Traceback" not in result.output
        assert "non-HTTPS" in result.output

    def test_config_get_server_shows_clean_error_for_invalid_env_url(self):
        result = runner.invoke(
            app,
            ["config", "get-server"],
            env={"VALIDIBOT_API_URL": "http://example.com"},
        )
        assert result.exit_code == 1
        assert "Traceback" not in result.output
        assert "non-HTTPS" in result.output


# ── Ambiguous workflow error preservation ──────────────────────────────
# When the server returns a 400 with {detail: ..., matches: [...]},
# the CLI must raise AmbiguousWorkflowError with the matches list intact.
# Previously, _handle_response stripped the response down to just `detail`,
# so `_check_ambiguous_workflow_error` could never find `matches`.


class TestAmbiguousWorkflowError:
    """Tests that structured 400 error payloads are preserved for inspection."""

    def test_check_ambiguous_workflow_error_with_response_data(self):
        """_check_ambiguous_workflow_error should find matches in response_data."""
        error = APIError(
            "API error (HTTP 400)",
            status_code=400,
            detail="Multiple workflows match 'my-workflow'",
            response_data={
                "detail": "Multiple workflows match 'my-workflow'",
                "matches": [
                    {"slug": "my-workflow", "version": "1"},
                    {"slug": "my-workflow", "version": "2"},
                ],
            },
        )
        with pytest.raises(AmbiguousWorkflowError) as exc_info:
            _check_ambiguous_workflow_error(error)

        expected_match_count = 2
        assert len(exc_info.value.matches) == expected_match_count

    def test_check_ambiguous_error_no_matches_does_not_raise(self):
        """A 400 without matches should not raise AmbiguousWorkflowError."""
        error = APIError(
            "API error (HTTP 400)",
            status_code=400,
            detail="Some other error",
            response_data={"detail": "Some other error"},
        )
        # Should not raise
        _check_ambiguous_workflow_error(error)

    def test_check_ambiguous_error_non_400_does_not_raise(self):
        """Only 400 status codes should be checked for ambiguity."""
        error = APIError(
            "API error (HTTP 500)",
            status_code=500,
            detail="Server error",
            response_data={"detail": "Server error", "matches": []},
        )
        # Should not raise even though response_data has matches
        _check_ambiguous_workflow_error(error)

    def test_handle_response_preserves_response_data(self):
        """_handle_response should preserve the full JSON body in response_data."""
        client = ValidibotClient(token="test-token", api_url="https://api.example.com")

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "detail": "Multiple workflows match",
            "matches": [{"slug": "w", "version": "1"}],
        }
        mock_response.text = ""

        with pytest.raises(APIError) as exc_info:
            client._handle_response(mock_response)

        assert exc_info.value.response_data is not None
        assert "matches" in exc_info.value.response_data


# ── validate status command removal ────────────────────────────────────
# The `validate status` subcommand was never reachable because main.py
# mounts validate.run as a top-level command, not validate.app as a group.
# Help text and error messages now direct users to `validibot runs show`.


class TestValidateStatusRedirect:
    """Tests that user-facing messages point to runs show, not validate status."""

    def test_no_validate_status_references_in_source(self):
        """Source code should no longer reference the dead validate status command."""
        import importlib
        import inspect

        from validibot_cli.commands import validate

        importlib.reload(validate)
        source = inspect.getsource(validate)
        assert "validate status" not in source


# ── Terminal escape-sequence sanitization ──────────────────────────────
# API responses are attacker-influenced. Rich's escape()/markup=False only
# neutralize Rich's [tag] markup, NOT terminal ANSI/OSC control sequences. A
# hostile server could otherwise recolor output to spoof a "PASSED", move the
# cursor, rewrite the window title, or overwrite a line with \r. Server strings
# must therefore be stripped of control bytes before display.


class TestTerminalOutputSanitization:
    """The output sanitizer strips terminal control bytes from server text."""

    def test_strips_ansi_escape_sequences(self):
        """ESC-introduced ANSI sequences (color/cursor) are removed."""
        from validibot_cli.safe_output import strip_control_chars

        out = strip_control_chars("PASSED\x1b[31m FAILED\x1b[0m")
        assert "\x1b" not in out
        # ESC removed; the remaining bracket text is now inert literal characters.
        assert out == "PASSED[31m FAILED[0m"

    def test_strips_carriage_return_and_c1_csi(self):
        """\\r (line-overwrite spoofing) and the 8-bit C1 CSI are removed."""
        from validibot_cli.safe_output import strip_control_chars

        assert "\r" not in strip_control_chars("real\rspoofed")
        assert "\x9b" not in strip_control_chars("x\x9b31m")  # C1 CSI
        assert "\x07" not in strip_control_chars("bell\x07")  # BEL

    def test_preserves_newlines_and_tabs(self):
        """Legitimate whitespace in multi-line messages is kept."""
        from validibot_cli.safe_output import strip_control_chars

        assert strip_control_chars("line1\nline2\tcol") == "line1\nline2\tcol"

    def test_safe_markup_strips_control_and_escapes_rich(self):
        """safe_markup removes control bytes AND escapes Rich markup.

        Both layers must be defended: the ANSI layer (ESC) and Rich's own
        ``[tag]`` layer. A server string carrying both must come out inert.
        """
        from validibot_cli.safe_output import safe_markup

        out = safe_markup("\x1b[31m[bold]danger[/bold]")
        assert "\x1b" not in out  # ANSI control stripped
        # Rich markup is escaped (``[bold]`` -> ``\[bold]``), so Rich renders it
        # literally instead of interpreting it. The escaped backslash form is
        # the proof; note ``[bold]`` still appears as a substring of ``\[bold]``,
        # which is why we assert the escaped form rather than its absence.
        assert "\\[bold]" in out
        assert "\\[/bold]" in out

    def test_workflow_sanitize_applies_the_guard(self):
        """The workflows command's _sanitize routes through the shared guard."""
        from validibot_cli.commands.workflows import _sanitize

        # OSC title-set (\x1b]0;…\x07) + Rich markup: both must be neutralized.
        out = _sanitize("\x1b]0;pwned\x07name[red]x[/red]")
        assert "\x1b" not in out  # ESC (and thus the OSC sequence) stripped
        assert "\x07" not in out  # BEL terminator stripped
        assert "\\[red]" in out  # Rich markup escaped, not interpreted


# ── Credential storage hardening ────────────────────────────────────────
# credentials.json is 0600, but the directory holding it should also be
# owner-only so other local users can't list it and to blunt symlink/predictable
# -temp races during token writes.


class TestConfigDirPermissions:
    """ensure_config_dir creates an owner-only (0700) directory on POSIX."""

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits only")
    def test_config_dir_is_owner_only(self, tmp_path, monkeypatch):
        """The config directory must be created with 0700 permissions."""
        import stat

        target = tmp_path / "cfgroot" / "validibot"
        monkeypatch.setattr(config_module, "get_config_dir", lambda: target)

        created = config_module.ensure_config_dir()

        assert created == target
        assert created.is_dir()
        mode = stat.S_IMODE(created.stat().st_mode)
        assert mode == 0o700, f"expected 0o700, got {oct(mode)}"
