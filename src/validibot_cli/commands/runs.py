"""
Validation run commands.
"""

from typing import Annotated

import typer
from rich.console import Console

from validibot_cli.client import APIError, AuthenticationError, get_client
from validibot_cli.commands.validate import _display_run_result

app = typer.Typer(no_args_is_help=True)
err_console = Console(stderr=True)


@app.command(name="show")
def show(
    run_id: Annotated[str, typer.Argument(help="Validation run ID")],
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
    """Show a validation run status and results."""
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
            if e.detail:
                err_console.print(str(e.detail), style="dim", markup=False, highlight=False)
        raise typer.Exit(1) from None
    except Exception as e:
        err_console.print(f"Error: {e}", style="red", markup=False)
        raise typer.Exit(1) from None

    if json_output:
        import json

        typer.echo(json.dumps(run_data.model_dump(mode="json"), indent=2))
    else:
        _display_run_result(run_data, verbose=verbose)
