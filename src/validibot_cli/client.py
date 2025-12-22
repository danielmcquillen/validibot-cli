"""
HTTP client for Validibot API.

Provides a clean interface for making authenticated API calls.
"""

from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from validibot_cli import __version__
from validibot_cli.auth import get_stored_token
from validibot_cli.config import get_api_url, get_timeout, normalize_api_url
from validibot_cli.models import User, ValidationRun, Workflow


class APIError(Exception):
    """Raised when an API request fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        detail: str | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    pass


class NotFoundError(APIError):
    """Raised when a resource is not found."""

    pass


class AmbiguousWorkflowError(APIError):
    """Raised when a workflow lookup matches multiple results."""

    def __init__(
        self,
        message: str,
        matches: list[dict[str, str]] | None = None,
    ):
        self.matches = matches or []
        super().__init__(message, status_code=400)


def _check_ambiguous_workflow_error(error: APIError) -> None:
    """
    Check if an APIError represents an ambiguous workflow lookup.

    Raises AmbiguousWorkflowError if the error contains workflow match info,
    otherwise does nothing (caller should re-raise the original error).
    """
    if error.status_code != 400 or not error.detail:
        return

    import json

    try:
        error_data = (
            json.loads(error.detail)
            if isinstance(error.detail, str)
            else error.detail
        )
        if isinstance(error_data, dict) and "matches" in error_data:
            raise AmbiguousWorkflowError(
                error_data.get("detail", str(error)),
                matches=error_data.get("matches", []),
            ) from error
    except json.JSONDecodeError:
        pass


class ValidibotClient:
    """HTTP client for the Validibot API."""

    def __init__(
        self,
        token: str | None = None,
        api_url: str | None = None,
        timeout: int | None = None,
    ):
        """Initialize the client.

        Args:
            token: API token. If not provided, will try to load from storage.
            api_url: Base API URL. Defaults to configured URL.
            timeout: Request timeout in seconds.
        """
        self.api_url = normalize_api_url(api_url or get_api_url())
        self.timeout = timeout or get_timeout()
        self._token = token

    @property
    def token(self) -> str | None:
        """Get the API token, loading from storage if needed."""
        if self._token is None:
            self._token = get_stored_token(api_url=self.api_url)
        return self._token

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "User-Agent": f"validibot-cli/{__version__}",
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle API response, raising appropriate errors."""
        if 300 <= response.status_code < 400:
            raise APIError(
                f"Unexpected redirect (HTTP {response.status_code}).",
                status_code=response.status_code,
                detail=response.headers.get("Location"),
            )

        if response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed. Run 'validibot login' to authenticate.",
                status_code=401,
            )

        if response.status_code == 403:
            raise AuthenticationError(
                "Access denied. You don't have permission for this action.",
                status_code=403,
            )

        if response.status_code == 404:
            raise NotFoundError(
                "Resource not found.",
                status_code=404,
            )

        if response.status_code >= 400:
            # Try to extract error detail from response
            detail = None
            try:
                data = response.json()
                detail = data.get("detail") or data.get("error") or str(data)
            except Exception:
                detail = response.text[:200] if response.text else None

            raise APIError(
                f"API error (HTTP {response.status_code})",
                status_code=response.status_code,
                detail=detail,
            )

        # Success - return JSON or None
        if response.status_code == 204:
            return None

        try:
            return response.json()
        except Exception:
            return response.text

    def get(self, path: str, **kwargs: Any) -> Any:
        """Make a GET request."""
        url = f"{self.api_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            try:
                response = client.get(url, headers=self._get_headers(), **kwargs)
            except httpx.TimeoutException as e:
                raise APIError("Request timed out.", detail=str(e)) from e
            except httpx.RequestError as e:
                raise APIError("Network error connecting to API.", detail=str(e)) from e
            return self._handle_response(response)

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Make a POST request."""
        url = f"{self.api_url}{path}"
        headers = self._get_headers()

        # Don't set Content-Type for multipart (httpx handles it)
        if json is not None:
            headers["Content-Type"] = "application/json"

        with httpx.Client(timeout=self.timeout) as client:
            try:
                response = client.post(
                    url,
                    headers=headers,
                    json=json,
                    data=data,
                    files=files,
                    **kwargs,
                )
            except httpx.TimeoutException as e:
                raise APIError("Request timed out.", detail=str(e)) from e
            except httpx.RequestError as e:
                raise APIError("Network error connecting to API.", detail=str(e)) from e
            return self._handle_response(response)

    def upload_file(
        self,
        path: str,
        file_path: Path,
        extra_data: dict[str, str] | None = None,
    ) -> Any:
        """Upload a file via multipart form."""
        url = f"{self.api_url}{path}"
        headers = self._get_headers()
        # Remove Content-Type - httpx will set multipart boundary
        headers.pop("Content-Type", None)

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f)}
            upload_data = extra_data or {}

            with httpx.Client(timeout=self.timeout) as client:
                try:
                    response = client.post(
                        url,
                        headers=headers,
                        files=files,
                        data=upload_data,
                    )
                except httpx.TimeoutException as e:
                    raise APIError("Request timed out.", detail=str(e)) from e
                except httpx.RequestError as e:
                    raise APIError(
                        "Network error connecting to API.",
                        detail=str(e),
                    ) from e
                return self._handle_response(response)

    # Convenience methods for common operations

    def get_current_user(self) -> User:
        """Get the current authenticated user.

        Uses the /auth/me/ endpoint which returns minimal user info
        (email, name) and validates the token.

        Returns:
            User model with email and name
        """
        data = self.get("/api/v1/auth/me/")
        return User.model_validate(data)

    def list_workflows(self) -> list[Workflow]:
        """List available workflows."""
        response = self.get("/api/v1/workflows/")
        # Handle paginated response
        if isinstance(response, dict) and "results" in response:
            items = response["results"]
        else:
            items = response
        return [Workflow.model_validate(w) for w in items]

    def get_workflow(
        self,
        workflow_id: str,
        org: str | None = None,
        version: str | None = None,
        project: str | None = None,
    ) -> Workflow:
        """Get a workflow by ID or slug.

        Args:
            workflow_id: Workflow ID (integer) or slug (string).
            org: Organization slug for disambiguation when using workflow slug.
            version: Workflow version for disambiguation.
            project: Project slug for filtering within an organization.

        Returns:
            The workflow details.

        Raises:
            AmbiguousWorkflowError: If multiple workflows match the slug.
            NotFoundError: If no workflow is found.
        """
        # Build query params for disambiguation/filtering
        params: dict[str, str] = {}
        if org:
            params["org"] = org
        if version:
            params["version"] = version
        if project:
            params["project"] = project

        # URL-encode the workflow_id to prevent path injection
        safe_workflow_id = quote(workflow_id, safe="")
        path = f"/api/v1/workflows/{safe_workflow_id}/"
        try:
            data = self.get(path, params=params if params else None)
        except APIError as e:
            _check_ambiguous_workflow_error(e)
            raise

        return Workflow.model_validate(data)

    def start_validation(
        self,
        workflow_id: str,
        file_path: Path,
        name: str | None = None,
        org: str | None = None,
        version: str | None = None,
        project: str | None = None,
    ) -> ValidationRun:
        """Start a validation run by uploading a file.

        Args:
            workflow_id: Workflow ID (integer) or slug (string).
            file_path: Path to the file to validate.
            name: Optional name for this validation run.
            org: Organization slug for disambiguation when using workflow slug.
            version: Workflow version for disambiguation.
            project: Project slug for filtering within an organization.

        Returns:
            The created validation run.

        Raises:
            AmbiguousWorkflowError: If multiple workflows match the slug.
        """
        # Build query params for disambiguation/filtering
        params: dict[str, str] = {}
        if org:
            params["org"] = org
        if version:
            params["version"] = version
        if project:
            params["project"] = project

        # URL-encode the workflow_id to prevent path injection
        safe_workflow_id = quote(workflow_id, safe="")
        path = f"/api/v1/workflows/{safe_workflow_id}/start/"
        if params:
            path = f"{path}?{urlencode(params)}"

        extra_data: dict[str, str] = {}
        if name:
            extra_data["name"] = name

        try:
            data = self.upload_file(
                path,
                file_path,
                extra_data=extra_data if extra_data else None,
            )
        except APIError as e:
            _check_ambiguous_workflow_error(e)
            raise

        return ValidationRun.model_validate(data)

    def get_validation_run(self, run_id: str) -> ValidationRun:
        """Get validation run status."""
        safe_run_id = quote(run_id, safe="")
        data = self.get(f"/api/v1/validation-runs/{safe_run_id}/")
        return ValidationRun.model_validate(data)


def get_client(token: str | None = None) -> ValidibotClient:
    """Get a configured API client."""
    return ValidibotClient(token=token)
