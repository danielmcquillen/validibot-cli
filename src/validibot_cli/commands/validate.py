"""
Validation commands.

Commands for running validations and checking results.
"""

import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from validibot_cli.client import (
    AmbiguousWorkflowError,
    APIError,
    AuthenticationError,
    ValidibotClient,
    get_client,
)
from validibot_cli.config import get_settings
from validibot_cli.models import (
    FindingSeverity,
    ValidationRun,
)

app = typer.Typer()
console = Console()
err_console = Console(stderr=True)


def _format_status(status: str) -> str:
    """Format a validation status for display."""
    status_colors = {
        "PENDING": "[yellow]PENDING[/yellow]",
        "RUNNING": "[blue]RUNNING[/blue]",
        "COMPLETED": "[dim]COMPLETED[/dim]",
        "PASSED": "[green]PASSED[/green]",
        "FAILED": "[red]FAILED[/red]",
        "SKIPPED": "[dim]SKIPPED[/dim]",
    }
    return status_colors.get(status.upper(), status)


def _format_result(result: str) -> str:
    """Format a validation result for display."""
    result_colors = {
        "PASS": "[green]PASS[/green]",
        "FAIL": "[red]FAIL[/red]",
        "ERROR": "[red]ERROR[/red]",
        "CANCELED": "[dim]CANCELED[/dim]",
        "TIMED_OUT": "[yellow]TIMED_OUT[/yellow]",
        "UNKNOWN": "[yellow]UNKNOWN[/yellow]",
    }
    return result_colors.get(result.upper() if result else "", result or "N/A")


def _format_severity(severity: FindingSeverity) -> str:
    """Format a finding severity for display."""
    severity_formats = {
        FindingSeverity.ERROR: "[red]ERROR[/red]",
        FindingSeverity.WARNING: "[yellow]WARN[/yellow]",
        FindingSeverity.INFO: "[blue]INFO[/blue]",
    }
    return severity_formats.get(severity, severity.value)


def _display_run_result(run: ValidationRun, verbose: bool = False) -> None:
    """Display a validation run result."""
    status = run.state.value
    result = run.result.value
    run_id = run.id

    if not run.is_complete:
        border_style = "blue"
        title = f"Validation {status.capitalize()}"
    # Determine panel color based on result
    elif result == "PASS":
        border_style = "green"
        title = "Validation Passed"
    elif result == "FAIL":
        border_style = "red"
        title = "Validation Failed"
    elif result == "ERROR":
        border_style = "red"
        title = "Validation Error"
    elif result == "TIMED_OUT":
        border_style = "yellow"
        title = "Validation Timed Out"
    elif result == "CANCELED":
        border_style = "dim"
        title = "Validation Canceled"
    else:
        border_style = "blue"
        title = "Validation Completed"

    # Calculate total findings across all steps
    total_errors = sum(sr.error_count for sr in run.steps)
    total_warnings = sum(sr.warning_count for sr in run.steps)
    total_info = sum(sr.info_count for sr in run.steps)
    total_findings = total_errors + total_warnings + total_info

    # Build summary content
    lines = [
        f"[dim]Run ID:[/dim] {escape(str(run_id))}",
        f"[dim]Status:[/dim] {_format_status(status)}",
    ]

    if run.is_complete:
        lines.append(f"[dim]Result:[/dim] {_format_result(result)}")

    # Add error info if present (sanitize server-provided content)
    if run.error_category:
        lines.append(f"[dim]Error category:[/dim] {escape(run.error_category)}")
    if run.user_friendly_error:
        lines.append("")
        lines.append(f"[red]Error:[/red] {escape(run.user_friendly_error)}")
    elif run.error:
        lines.append("")
        lines.append(f"[red]Error:[/red] {escape(run.error)}")

    # Add timing info if available
    if run.duration_ms:
        seconds = run.duration_ms / 1000
        if seconds < 60:
            lines.append(f"[dim]Duration:[/dim] {seconds:.1f}s")
        else:
            minutes = int(seconds // 60)
            secs = seconds % 60
            lines.append(f"[dim]Duration:[/dim] {minutes}m {secs:.0f}s")

    console.print()
    console.print(Panel("\n".join(lines), title=title, border_style=border_style))

    # Always show findings if there are any (this is the important part!)
    has_findings = any(sr.issues for sr in run.steps)
    if has_findings:
        # Build findings content for the panel
        findings_lines: list[str] = []

        if total_findings > 0:
            findings_lines.append("Summary:")
            if total_errors is not None:
                findings_lines.append(f"  [red]Error count:[/red] {total_errors}")
            if total_warnings is not None:
                findings_lines.append(f"  [yellow]Warning count:[/yellow] {total_warnings}")
            if total_info is not None:
                findings_lines.append(f"  [blue]Info count:[/blue] {total_info}")
            findings_lines.append("")

        step_number = 0
        for step_run in run.steps:
            if step_run.issues:
                step_number += 1
                step_name = step_run.name or "Validation Step"

                # Show step header with counts
                counts = []
                if step_run.error_count > 0:
                    counts.append(f"[red]{step_run.error_count} error(s)[/red]")
                if step_run.warning_count > 0:
                    counts.append(f"[yellow]{step_run.warning_count} warning(s)[/yellow]")
                if step_run.info_count > 0:
                    counts.append(f"[blue]{step_run.info_count} info[/blue]")

                count_str = ", ".join(counts) if counts else "no issues"
                if step_number > 1:
                    findings_lines.append("")  # Add spacing between steps
                findings_lines.append(
                    f"[bold]Step {step_number}: {escape(step_name)}[/bold] - {count_str}"
                )

                # Add each finding
                for finding in step_run.issues:
                    severity = _format_severity(finding.severity)
                    message = escape(finding.message)
                    path = escape(finding.path) if finding.path else ""

                    if path:
                        findings_lines.append(f"  {severity}  {path}  {message}")
                    else:
                        findings_lines.append(f"  {severity}  {message}")

        console.print()
        console.print(
            Panel(
                "\n".join(findings_lines),
                title="Findings",
                border_style="dim",
            )
        )

    # Show step summary if verbose and no findings displayed
    elif verbose and run.steps:
        console.print("\n[dim]Steps:[/dim]")
        for step_number, step_run in enumerate(run.steps, start=1):
            step_name = step_run.name or "Step"
            step_status = step_run.status.value
            console.print(
                f"  • Step {step_number}: {escape(step_name)}: {_format_status(step_status)}"
            )


def _wait_for_completion(
    client: ValidibotClient,
    run_id: str,
    poll_interval: int,
    timeout: int,
    show_progress: bool = True,
) -> ValidationRun:
    """Wait for a validation run to complete, showing progress."""
    start_time = time.time()

    if not show_progress:
        while True:
            run = client.get_validation_run(run_id)
            if run.is_complete:
                return run

            elapsed = time.time() - start_time
            if timeout and elapsed > timeout:
                err_console.print("Timeout waiting for validation.", style="yellow")
                err_console.print(f"Run ID: {run_id}", style="dim", markup=False)
                err_console.print(
                    f"Check status with: validibot runs show {run_id}",
                    style="dim",
                    markup=False,
                )
                return run

            time.sleep(poll_interval)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=err_console,
        transient=True,
    ) as progress:
        task = progress.add_task("Running validation...", total=None)

        while True:
            run = client.get_validation_run(run_id)
            status = run.status.value

            # Update progress description
            progress.update(task, description=f"Validation {status.lower()}...")

            # Check if complete
            if run.is_complete:
                return run

            # Check timeout
            elapsed = time.time() - start_time
            if timeout and elapsed > timeout:
                err_console.print("Timeout waiting for validation.", style="yellow")
                err_console.print(f"Run ID: {run_id}", style="dim", markup=False)
                err_console.print(
                    f"Check status with: validibot runs show {run_id}",
                    style="dim",
                    markup=False,
                )
                return run

            time.sleep(poll_interval)


@app.command(name="run")
def run(
    file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            readable=True,
            help="File to validate",
        ),
    ],
    workflow: Annotated[
        str,
        typer.Option(
            "--workflow",
            "-w",
            help="Workflow ID or slug to use for validation",
        ),
    ],
    org: Annotated[
        str | None,
        typer.Option(
            "--org",
            "-o",
            help="Organization slug (for disambiguating workflow slugs)",
        ),
    ] = None,
    project: Annotated[
        str | None,
        typer.Option(
            "--project",
            "-p",
            help="Project slug (for filtering workflows within an org)",
        ),
    ] = None,
    version: Annotated[
        str | None,
        typer.Option(
            "--version",
            help="Workflow version (for disambiguating workflow slugs)",
        ),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option(
            "--name",
            "-n",
            help="Optional name for this validation run",
        ),
    ] = None,
    wait: Annotated[
        bool,
        typer.Option(
            "--wait/--no-wait",
            help="Wait for validation to complete",
        ),
    ] = True,
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            "-t",
            help="Maximum time to wait (seconds)",
        ),
    ] = 600,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed output",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Output as JSON",
        ),
    ] = False,
) -> None:
    """
    Run a validation workflow on a file.

    Uploads the file to Validibot and runs the specified workflow.
    By default, waits for the validation to complete and shows results.

    You can specify the workflow by ID or slug. If using a slug and it matches
    multiple workflows, use --org, --project, and/or --version to filter.

    [bold]Examples:[/bold]

        validibot validate model.idf -w abc123
        validibot validate model.idf -w my-workflow --org my-org
        validibot validate model.idf -w my-workflow --org my-org --project my-project
        validibot validate model.idf -w my-workflow --org my-org --version 2
        validibot validate model.fmu --workflow def456 --no-wait
    """
    # Validate file exists and is readable
    if not file.is_file():
        err_console.print(f"Error: Not a file: {file}", style="red", markup=False)
        raise typer.Exit(1)

    try:
        client = get_client()
    except Exception as e:
        err_console.print(f"Error: {e}", style="red", markup=False)
        raise typer.Exit(1) from None

    # Start the validation
    err_console.print(f"Uploading {file.name}...", style="dim", markup=False)

    try:
        run_data = client.start_validation(
            workflow_id=workflow,
            file_path=file,
            name=name,
            org=org,
            project=project,
            version=version,
        )
    except AmbiguousWorkflowError as e:
        err_console.print(f"Error: {e.message}", style="red", markup=False)
        if e.matches:
            err_console.print("\nMatching workflows:", style="dim")
            for match in e.matches:
                match_org = match.get("org", "?")
                match_version = match.get("version", "?")
                err_console.print(
                    f"  • org={match_org}, version={match_version}",
                    markup=False,
                )
            err_console.print(
                "\nUse --org and/or --version to specify which workflow.",
                style="dim",
            )
        raise typer.Exit(1) from None
    except AuthenticationError as e:
        err_console.print(e.message, style="red", markup=False)
        raise typer.Exit(1) from None
    except APIError as e:
        err_console.print(
            f"Error starting validation: {e.message}",
            style="red",
            markup=False,
        )
        if e.detail:
            err_console.print(str(e.detail), style="dim", markup=False, highlight=False)
        raise typer.Exit(1) from None

    run_id = run_data.id
    err_console.print(f"Validation started (run: {run_id})", style="green", markup=False)

    # If not waiting, just show the run ID and exit
    if not wait:
        if json_output:
            import json

            typer.echo(json.dumps(run_data.model_dump(mode="json"), indent=2))
        else:
            console.print()
            console.print(f"Run ID: {run_id}", style="dim", markup=False)
            console.print(
                f"Check status with: validibot runs show {run_id}",
                style="dim",
                markup=False,
            )
        return

    # Wait for completion
    settings = get_settings()
    poll_interval = settings.poll_interval

    try:
        final_run = _wait_for_completion(
            client,
            run_id,
            poll_interval=poll_interval,
            timeout=timeout,
            show_progress=not json_output,
        )
    except KeyboardInterrupt:
        err_console.print(
            "\nInterrupted. Validation continues in background.",
            style="yellow",
        )
        err_console.print(f"Run ID: {run_id}", style="dim", markup=False)
        raise typer.Exit(130) from None
    except APIError as e:
        err_console.print(f"Error checking status: {e.message}", style="red", markup=False)
        raise typer.Exit(1) from None

    # Display result
    if json_output:
        import json

        typer.echo(json.dumps(final_run.model_dump(mode="json"), indent=2))
    else:
        _display_run_result(final_run, verbose=verbose)

    # Exit with appropriate code
    if not final_run.is_complete:
        raise typer.Exit(3)
    if final_run.is_success:
        raise typer.Exit(0)
    elif final_run.result.value == "FAIL":
        raise typer.Exit(1)
    elif final_run.result.value in ("ERROR", "TIMED_OUT", "CANCELED", "UNKNOWN"):
        raise typer.Exit(2)
    else:
        raise typer.Exit(2)


@app.command(name="status")
def status(
    run_id: Annotated[
        str,
        typer.Argument(help="Validation run ID"),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Output as JSON",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed output",
        ),
    ] = False,
) -> None:
    """
    Check the status of a validation run.
    """
    try:
        client = get_client()
        run_data = client.get_validation_run(run_id)
    except AuthenticationError as e:
        err_console.print(e.message, style="red", markup=False)
        raise typer.Exit(1) from None
    except APIError as e:
        if e.status_code == 404:
            err_console.print(f"Run not found: {run_id}", style="red", markup=False)
        else:
            err_console.print(f"Error: {e.message}", style="red", markup=False)
        raise typer.Exit(1) from None
    except Exception as e:
        err_console.print(f"Error: {e}", style="red", markup=False)
        raise typer.Exit(1) from None

    if json_output:
        import json

        typer.echo(json.dumps(run_data.model_dump(mode="json"), indent=2))
    else:
        _display_run_result(run_data, verbose=verbose)
