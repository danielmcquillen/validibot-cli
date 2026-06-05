"""Tests for the HTTP client."""

import json
from pathlib import Path
from unittest.mock import Mock, call, patch

import httpx
import pytest
import typer

from validibot_cli.client import APIError, AuthenticationError, ValidibotClient
from validibot_cli.commands.validate import _parse_meta_options
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

    def test_list_user_orgs_follows_pagination(self):
        """Paginated org responses should be fetched until `next` is null."""
        client = ValidibotClient(token="test-token", api_url="https://api.example.com")

        responses = [
            {
                "results": [{"slug": "org-one", "name": "Org One"}],
                "next": "https://api.example.com/api/v1/orgs/?page=2",
            },
            {
                "results": [{"slug": "org-two", "name": "Org Two"}],
                "next": None,
            },
        ]

        with patch.object(ValidibotClient, "get", side_effect=responses) as mock_get:
            orgs = client.list_user_orgs()

        assert [org.slug for org in orgs] == ["org-one", "org-two"]
        assert mock_get.call_args_list == [
            call("/api/v1/orgs/"),
            call("https://api.example.com/api/v1/orgs/?page=2"),
        ]

    def test_list_workflows_follows_pagination(self):
        """Paginated workflow responses should include every page."""
        client = ValidibotClient(token="test-token", api_url="https://api.example.com")

        responses = [
            {
                "results": [{"id": "1", "slug": "wf-one", "name": "Workflow One"}],
                "next": "https://api.example.com/api/v1/orgs/demo/workflows/?page=2",
            },
            {
                "results": [{"id": "2", "slug": "wf-two", "name": "Workflow Two"}],
                "next": None,
            },
        ]

        with patch.object(ValidibotClient, "get", side_effect=responses) as mock_get:
            workflows = client.list_workflows("demo")

        assert [workflow.slug for workflow in workflows] == ["wf-one", "wf-two"]
        assert mock_get.call_args_list == [
            call("/api/v1/orgs/demo/workflows/"),
            call("https://api.example.com/api/v1/orgs/demo/workflows/?page=2"),
        ]

    def test_get_rejects_absolute_url_to_different_host(self):
        """Absolute URLs must stay on the configured API origin."""
        client = ValidibotClient(token="test-token", api_url="https://api.example.com")

        with pytest.raises(APIError, match="different host"):
            client.get("https://evil.example.com/api/v1/orgs/")


class TestStartValidationSubmissionFields:
    """start_validation must forward submission metadata + short_description.

    These fields back the ``submission.metadata.<key>`` and
    ``submission.short_description`` assertion namespace (ADR-2026-06-03b). The
    CLI is a trusted-setter path: it sends them as multipart form fields, and
    the API persists them ungated. We assert the request-building, mocking the
    upload so the tests stay fast and offline.
    """

    def test_metadata_and_short_description_become_form_fields(self):
        """--meta and --short-description are placed into the upload form data.

        metadata is JSON-encoded (the API coerces the string back to a dict on
        the multipart path); short_description is sent verbatim.
        """
        client = ValidibotClient(token="t", api_url="https://api.example.com")
        with (
            patch.object(
                ValidibotClient,
                "upload_file",
                return_value={},
            ) as mock_upload,
            patch("validibot_cli.client.ValidationRun"),
        ):
            client.start_validation(
                workflow_id="wf",
                file_path=Path("model.idf"),
                org="my-org",
                metadata={"deliverable": "handover"},
                short_description="Final handover package",
            )
        extra = mock_upload.call_args.kwargs["extra_data"]
        assert json.loads(extra["metadata"]) == {"deliverable": "handover"}
        assert extra["short_description"] == "Final handover package"

    def test_omitted_fields_are_not_sent(self):
        """With no metadata/short_description, no empty fields are sent.

        Omitting the fields entirely (rather than sending empty values) keeps
        the request clean and lets server-side defaults apply.
        """
        client = ValidibotClient(token="t", api_url="https://api.example.com")
        with (
            patch.object(
                ValidibotClient,
                "upload_file",
                return_value={},
            ) as mock_upload,
            patch("validibot_cli.client.ValidationRun"),
        ):
            client.start_validation(
                workflow_id="wf",
                file_path=Path("model.idf"),
                org="my-org",
            )
        # No name/metadata/short_description → extra_data is None.
        assert mock_upload.call_args.kwargs["extra_data"] is None


class TestParseMetaOptions:
    """Tests for the --meta key=value parser used by the run command."""

    def test_parses_multiple_pairs(self):
        """Repeated key=value pairs collapse into a single dict."""
        assert _parse_meta_options(["a=1", "b=2"]) == {"a": "1", "b": "2"}

    def test_value_may_contain_equals(self):
        """Only the first '=' splits, so values may contain '='.

        Matters for values like base64 or query strings that embed '='.
        """
        assert _parse_meta_options(["token=ab=cd"]) == {"token": "ab=cd"}

    def test_none_returns_none(self):
        """No --meta options means the field is omitted (None), not an empty map."""
        assert _parse_meta_options(None) is None

    def test_malformed_pair_exits(self):
        """A pair without '=' fails fast with a non-zero exit, not a server error."""
        with pytest.raises(typer.Exit):
            _parse_meta_options(["no_equals_here"])

    def test_empty_key_exits(self):
        """An empty key (e.g. '=value') is rejected — keys must be meaningful."""
        with pytest.raises(typer.Exit):
            _parse_meta_options(["=value"])
