"""Tests for Pydantic API response models."""

from validibot_cli.models import (
    FindingSeverity,
    StepStatus,
    ValidationResult,
    ValidationRun,
    ValidationState,
    ValidationStatus,
)


def test_validation_run_parses_state_and_result():
    """Parse API responses that include `state` and `result` fields."""
    payload = {
        "id": "run-123",
        "workflow": 42,
        "workflow_slug": "example-workflow",
        "submission": 99,
        "source": "API",
        "org": "example-org",
        "status": "FAILED",
        "state": "COMPLETED",
        "result": "FAIL",
        "error_category": "VALIDATION_FAILED",
        "user_friendly_error": "The validation found issues with your file.",
        "error": "Raw error text (optional).",
        "duration_ms": 1200,
        "steps": [
            {
                "step_id": 1,
                "name": "Schema Validation",
                "status": "FAILED",
                "issues": [
                    {
                        "severity": "ERROR",
                        "message": "Missing required field",
                        "path": "payload.name",
                        "code": "REQUIRED",
                        "assertion_id": 123,
                    },
                ],
            },
        ],
    }

    run = ValidationRun.model_validate(payload)
    assert run.id == "run-123"
    assert run.status == ValidationStatus.FAILED
    assert run.state == ValidationState.COMPLETED
    assert run.result == ValidationResult.FAIL
    assert run.is_complete is True
    assert run.is_success is False

    assert len(run.steps) == 1
    step = run.steps[0]
    assert step.status == StepStatus.FAILED
    assert step.error_count == 1
    assert step.warning_count == 0
    assert step.info_count == 0
    assert step.issues[0].severity == FindingSeverity.ERROR
