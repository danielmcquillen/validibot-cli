"""
Workflow commands.

Commands for listing and inspecting available workflows.
"""

from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from validibot_cli.auth import get_default_org
from validibot_cli.client import APIError, AuthenticationError, get_client


def _resolve_org(org: str | None) -> str:
    """Resolve the organization, using default if not provided."""
    if org:
        return org

    default_org = get_default_org()
    if default_org:
        return default_org

    err_console.print(
        "Error: --org is required (no default org set)",
        style="red",
        markup=False,
    )
    err_console.print(
        "Run 'validibot login' to set a default org, or use --org",
        style="dim",
        markup=False,
    )
    raise typer.Exit(1)

app = typer.Typer(no_args_is_help=True)
console = Console()
err_console = Console(stderr=True)

# Maximum length for description in table view
MAX_DESCRIPTION_LENGTH = 50


def _sanitize(text: str) -> str:
    """Sanitize user-provided text to prevent Rich markup injection.

    Escapes Rich markup tags like [bold], [link], etc. to prevent
    malicious content from manipulating terminal output.
    """
    return escape(text)


@app.command(name="list")
def list_workflows(
    org: Annotated[
        str | None,
        typer.Option(
            "--org",
            "-o",
            help="Organization slug (uses default if set)",
        ),
    ] = None,
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
    List available workflows in an organization.

    Shows all workflows you have access to in the specified org,
    including their IDs, slugs, and descriptions.

    [bold]Examples:[/bold]

        validibot workflows list --org my-org
        validibot workflows list -o my-org --json
    """
    # Resolve org (use default if not provided)
    resolved_org = _resolve_org(org)

    try:
        client = get_client()
        workflows = client.list_workflows(org=resolved_org)
    except AuthenticationError as e:
        err_console.print(e.message, style="red", markup=False)
        raise typer.Exit(1) from None
    except APIError as e:
        err_console.print(f"Error: {e.message}", style="red", markup=False)
        if e.detail:
            err_console.print(str(e.detail), style="dim", markup=False, highlight=False)
        raise typer.Exit(1) from None
    except Exception as e:
        err_console.print(f"Error: {e}", style="red", markup=False)
        raise typer.Exit(1) from None

    if not workflows:
        console.print("[yellow]No workflows found.[/yellow]")
        console.print("[dim]Create workflows in the Validibot web app.[/dim]")
        return

    if json_output:
        import json

        typer.echo(json.dumps([wf.model_dump(mode="json") for wf in workflows], indent=2))
        return

    # Display as table
    table = Table(title=f"Workflows in '{resolved_org}'", show_header=True)
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Ver", style="dim", no_wrap=True, justify="center")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Status", justify="center")

    for wf in workflows:
        status = "[green]Active[/green]" if wf.is_active else "[dim]Inactive[/dim]"
        # Sanitize user-provided content to prevent markup injection
        name = _sanitize(wf.name)
        slug = _sanitize(wf.slug) if wf.slug else "-"
        desc = _sanitize(wf.description)
        if len(desc) > MAX_DESCRIPTION_LENGTH:
            desc = desc[:MAX_DESCRIPTION_LENGTH] + "..."
        table.add_row(
            slug,
            str(wf.id),
            str(wf.version) if wf.version is not None else "-",
            name,
            desc,
            status,
        )

    console.print()
    console.print(table)
    console.print()
    console.print(f"[dim]Found {len(workflows)} workflow(s)[/dim]")
    console.print("[dim]Use slug or ID with 'validibot workflows show' or 'validibot validate run'[/dim]")


@app.command()
def show(
    workflow_id: Annotated[
        str,
        typer.Argument(help="Workflow ID or slug"),
    ],
    org: Annotated[
        str | None,
        typer.Option(
            "--org",
            "-o",
            help="Organization slug (uses default if set)",
        ),
    ] = None,
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
    Show details of a specific workflow.

    [bold]Examples:[/bold]

        validibot workflows show my-workflow --org my-org
        validibot workflows show 123 -o my-org --json
    """
    # Resolve org (use default if not provided)
    resolved_org = _resolve_org(org)

    try:
        client = get_client()
        workflow = client.get_workflow(workflow_id, org=resolved_org)
    except AuthenticationError as e:
        err_console.print(e.message, style="red", markup=False)
        raise typer.Exit(1) from None
    except APIError as e:
        if e.status_code == 404:
            err_console.print(
                f"Workflow not found: {workflow_id}",
                style="red",
                markup=False,
            )
        else:
            err_console.print(f"Error: {e.message}", style="red", markup=False)
            if e.detail:
                err_console.print(str(e.detail), style="dim", markup=False, highlight=False)
        raise typer.Exit(1) from None
    except Exception as e:
        err_console.print(f"Error: {e}", style="red", markup=False)
        raise typer.Exit(1) from None

    if json_output:
        import json

        typer.echo(json.dumps(workflow.model_dump(mode="json"), indent=2))
        return

    # Display workflow details (sanitize user-provided content)
    console.print()
    console.print(f"[bold]{_sanitize(workflow.name)}[/bold]")
    console.print()
    if workflow.slug:
        console.print(f"[dim]Slug:[/dim] {_sanitize(workflow.slug)}")
    console.print(f"[dim]ID:[/dim] {workflow.id}")
    if workflow.version is not None:
        console.print(f"[dim]Version:[/dim] {workflow.version}")
    if workflow.org_slug:
        console.print(f"[dim]Organization:[/dim] {_sanitize(workflow.org_slug)}")
    if workflow.description:
        console.print(f"[dim]Description:[/dim] {_sanitize(workflow.description)}")
    console.print(f"[dim]Active:[/dim] {'Yes' if workflow.is_active else 'No'}")

    # Show steps if available
    if workflow.steps:
        console.print()
        console.print("[dim]Steps:[/dim]")
        for i, step in enumerate(workflow.steps, 1):
            step_name = step.name or step.validator_type or "Unknown"
            console.print(f"  {i}. {_sanitize(step_name)}")

    console.print()
