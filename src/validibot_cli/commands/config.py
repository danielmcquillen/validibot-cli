"""
Configuration commands.

Commands for managing CLI configuration like server URL.
"""

import typer
from rich.console import Console
from rich.markup import escape

from validibot_cli.auth import (
    delete_server_url,
    get_stored_server_url,
    save_server_url,
)
from validibot_cli.config import (
    ServerNotConfiguredError,
    get_api_url,
    normalize_api_url,
)

app = typer.Typer(no_args_is_help=True)
console = Console()
err_console = Console(stderr=True)


@app.command("set-server")
def set_server(
    url: str = typer.Argument(
        ...,
        help="Server URL (e.g., https://validibot.mycompany.com)",
    ),
) -> None:
    """
    Set the Validibot server URL.

    Use this for self-hosted Validibot installations.

    Example:
        validibot config set-server https://validibot.mycompany.com
    """
    try:
        normalized = normalize_api_url(url)
    except ValueError as e:
        err_console.print(f"Error: {e}", style="red", markup=False)
        raise typer.Exit(1) from None

    try:
        save_server_url(normalized)
    except Exception as e:
        err_console.print(f"Error saving server URL: {e}", style="red", markup=False)
        raise typer.Exit(1) from None

    console.print(f"Server URL set to: {escape(normalized)}", style="green")
    console.print(
        "Run 'validibot login' to authenticate with this server.",
        style="dim",
        markup=False,
    )


@app.command("get-server")
def get_server() -> None:
    """
    Show the current Validibot server URL.

    Displays the effective server URL, indicating its source
    (environment variable or stored config).
    """
    import os

    env_url = os.environ.get("VALIDIBOT_API_URL")
    stored_url = get_stored_server_url()

    try:
        effective_url = get_api_url()
    except ServerNotConfiguredError:
        err_console.print("No server configured.", style="yellow", markup=False)
        err_console.print(
            "Run 'validibot config set-server <url>' to configure.",
            style="dim",
            markup=False,
        )
        raise typer.Exit(1) from None

    if env_url:
        source = "environment variable (VALIDIBOT_API_URL)"
    elif stored_url:
        source = "stored config"
    else:
        source = "unknown"

    console.print(f"Server: {escape(effective_url)}")
    console.print(f"Source: {source}", style="dim", markup=False)


@app.command("clear-server")
def clear_server() -> None:
    """
    Clear the stored server URL.

    After clearing, you'll need to run 'validibot config set-server'
    again or set VALIDIBOT_API_URL.
    """
    deleted = delete_server_url()
    if deleted:
        console.print("Server URL cleared.", style="green", markup=False)
    else:
        console.print("No server URL was stored.", style="yellow", markup=False)
