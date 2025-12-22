"""Tests for the login command, including interactive prompts."""

from unittest.mock import patch

from typer.testing import CliRunner

from validibot_cli.main import app
from validibot_cli.models import User

runner = CliRunner()


def _mock_user() -> User:
    """Create a mock User for testing."""
    return User(email="test@example.com", name="Test User")


class TestLoginCommand:
    """Tests for the login command."""

    def test_login_with_token_flag(self, tmp_path):
        """Test login when token is provided via --token flag."""
        with patch("validibot_cli.commands.auth.save_token") as mock_save:
            with patch("validibot_cli.commands.auth.ValidibotClient") as mock_client:
                mock_client.return_value.get_current_user.return_value = _mock_user()
                with patch(
                    "validibot_cli.commands.auth.get_token_storage_location",
                    return_value="test-keyring",
                ):
                    result = runner.invoke(app, ["login", "--token", "my_token_123"])

        assert result.exit_code == 0
        assert "Authentication successful" in result.output
        mock_save.assert_called_once_with("my_token_123")

    def test_login_prompts_for_token_when_not_provided(self, tmp_path):
        """Test that login prompts for token when not provided via flag."""
        with patch("validibot_cli.commands.auth.save_token") as mock_save:
            with patch("validibot_cli.commands.auth.ValidibotClient") as mock_client:
                mock_client.return_value.get_current_user.return_value = _mock_user()
                with patch(
                    "validibot_cli.commands.auth.get_token_storage_location",
                    return_value="test-keyring",
                ):
                    # Simulate user typing a token when prompted
                    result = runner.invoke(app, ["login"], input="my_prompted_token\n")

        assert result.exit_code == 0
        assert "Authentication successful" in result.output
        mock_save.assert_called_once_with("my_prompted_token")

    def test_login_with_no_verify_skips_api_call(self, tmp_path):
        """Test that --no-verify skips the API verification."""
        with patch("validibot_cli.commands.auth.save_token") as mock_save:
            with patch("validibot_cli.commands.auth.ValidibotClient") as mock_client:
                result = runner.invoke(
                    app, ["login", "--token", "my_token_123", "--no-verify"]
                )

        assert result.exit_code == 0
        assert "API key saved successfully" in result.output
        mock_save.assert_called_once_with("my_token_123")
        # Client should not have been instantiated
        mock_client.assert_not_called()

    def test_login_empty_key_fails(self):
        """Test that empty API key produces an error."""
        result = runner.invoke(app, ["login"], input="\n\n")

        # Typer's prompt with hide_input aborts on empty input
        assert result.exit_code == 1
