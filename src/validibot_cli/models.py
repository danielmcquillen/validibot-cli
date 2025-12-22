"""
Pydantic models for Validibot API responses.

These models provide type-safe representations of API data with validation.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field


def _coerce_to_str(v: int | str | None) -> str | None:
    """Coerce integer IDs to strings for consistent handling."""
    if v is None:
        return None
    return str(v)


# Type alias for ID fields that may come as int or str from API
StrId = Annotated[str, BeforeValidator(_coerce_to_str)]
OptionalStrId = Annotated[str | None, BeforeValidator(_coerce_to_str)]


class ValidationStatus(str, Enum):
    """Run status returned by the Validibot API."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    TIMED_OUT = "TIMED_OUT"


class ValidationState(str, Enum):
    """Simplified lifecycle state for a validation run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"


class ValidationResult(str, Enum):
    """Stable conclusion of a validation run."""

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    CANCELED = "CANCELED"
    TIMED_OUT = "TIMED_OUT"
    UNKNOWN = "UNKNOWN"


class StepStatus(str, Enum):
    """Status of a single validation step."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class FindingSeverity(str, Enum):
    """Severity level of a validation finding."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class Issue(BaseModel):
    """A single validation issue (error, warning, or info)."""

    id: OptionalStrId = None
    severity: FindingSeverity = FindingSeverity.ERROR
    message: str
    path: str = ""
    code: str = ""
    assertion_id: OptionalStrId = None

class User(BaseModel):
    """Authenticated user information."""

    email: str
    name: str = ""
    username: str = ""


class WorkflowStep(BaseModel):
    """A step within a workflow."""

    id: OptionalStrId = None
    name: str
    validator_type: str = ""
    order: int = 0


class Workflow(BaseModel):
    """A validation workflow."""

    id: StrId
    slug: str = ""
    name: str
    description: str = ""
    version: int | None = None
    is_active: bool = True
    steps: list[WorkflowStep] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StepRun(BaseModel):
    """Result of a single step within a validation run."""

    # API returns step_id, not id
    step_id: OptionalStrId = None
    name: str = ""
    status: StepStatus = StepStatus.PENDING
    error: str = ""
    # API returns issues, not findings
    issues: list[Issue] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Count of ERROR severity issues."""
        return sum(1 for i in self.issues if i.severity == FindingSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of WARNING severity issues."""
        return sum(1 for i in self.issues if i.severity == FindingSeverity.WARNING)

    @property
    def info_count(self) -> int:
        """Count of INFO severity issues."""
        return sum(1 for i in self.issues if i.severity == FindingSeverity.INFO)


class ValidationRun(BaseModel):
    """A validation run instance."""

    id: StrId
    workflow: OptionalStrId = None
    workflow_slug: str = ""
    submission: OptionalStrId = None
    source: str = ""
    org: str = ""
    state: ValidationState
    result: ValidationResult
    status: ValidationStatus = ValidationStatus.PENDING
    error: str = ""
    error_category: str = ""
    user_friendly_error: str = ""
    duration_ms: int = 0
    # API returns 'steps', not 'step_runs'
    steps: list[StepRun] = Field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None

    @property
    def is_complete(self) -> bool:
        """Check if the run has finished (successfully or not)."""
        return self.state == ValidationState.COMPLETED

    @property
    def is_success(self) -> bool:
        """Check if the run completed successfully."""
        return self.result == ValidationResult.PASS


class PaginatedResponse(BaseModel):
    """Paginated API response wrapper."""

    count: int = 0
    next: str | None = None
    previous: str | None = None
    results: list[dict[str, object]] = Field(default_factory=list)
