"""
Authentication commands.

Commands for logging in, logging out, and checking authentication status.
"""

from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from validibot_cli.auth import (
    delete_token,
    get_stored_token,
    get_token_storage_location,
    is_authenticated,
    save_token,
)
from validibot_cli.client import AuthenticationError, ValidibotClient, get_client
from validibot_cli.config import get_api_url

app = typer.Typer(no_args_is_help=True)
console = Console()
err_console = Console(stderr=True)


def _mask_key(key: str) -> str:
    """Mask an API key for display, showing only last 4 characters."""
    if len(key) <= 8:
        return "****"
    return f"****{key[-4:]}"


@app.command()
def login(
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            "-t",
            help="API key (will prompt if not provided)",
            hide_input=True,
        ),
    ] = None,
    verify: Annotated[
        bool,
        typer.Option(
            "--verify/--no-verify",
            help="Verify the API key works before saving",
        ),
    ] = True,
) -> None:
    """
    Authenticate with Validibot using an API key.

    Get your API key from the Validibot web app at:
    https://validibot.com/app/users/api-key/

    The key will be stored securely in your system keyring.
    """
    # Prompt for API key if not provided
    if token is None:
        console.print()
        api_key_url = f"{get_api_url()}/app/users/api-key/"
        console.print("Get your API key from:", style="dim")
        console.print(api_key_url, style="dim", markup=False)
        console.print()
        token = typer.prompt("API Key", hide_input=True)

    if not token or not token.strip():
        err_console.print("Error: API key cannot be empty", style="red", markup=False)
        raise typer.Exit(1)

    token = token.strip()

    # Verify the API key works
    if verify:
        err_console.print("Verifying API key...", style="dim", markup=False)
        try:
            client = ValidibotClient(token=token)
            user = client.get_current_user()
            email = user.email
            name = user.name
        except AuthenticationError:
            err_console.print(
                "Error: Invalid API key. Please check and try again.",
                style="red",
                markup=False,
            )
            raise typer.Exit(1) from None
        except Exception as e:
            err_console.print(
                f"Error: Could not verify API key: {e}",
                style="red",
                markup=False,
            )
            raise typer.Exit(1) from None

    # Save the API key
    try:
        save_token(token)
    except Exception as e:
        err_console.print(
            f"Error: Could not save API key: {e}",
            style="red",
            markup=False,
        )
        raise typer.Exit(1) from None

    # Success message
    console.print()
    if verify:
        display_name = name or email
        console.print(
            Panel(
                f"[green]Logged in as [bold]{escape(display_name)}[/bold][/green]\n\n"
                f"[dim]Email:[/dim] {escape(email)}\n"
                f"[dim]API Key:[/dim] {escape(_mask_key(token))}\n"
                f"[dim]Stored in:[/dim] {escape(get_token_storage_location())}",
                title="Authentication successful",
                border_style="green",
            )
        )
    else:
        console.print("[green]API key saved successfully.[/green]")


@app.command()
def logout() -> None:
    """
    Remove stored credentials.

    This will log you out of the CLI. You'll need to run 'validibot login'
    again to use commands that require authentication.
    """
    if not is_authenticated():
        err_console.print("You are not currently logged in.", style="yellow", markup=False)
        raise typer.Exit(0)

    deleted = delete_token()
    if deleted:
        console.print("[green]Logged out successfully.[/green]")
    else:
        err_console.print("No credentials found to remove.", style="yellow", markup=False)


@app.command()
def whoami() -> None:
    """
    Show the currently authenticated user.

    Displays your account information and verifies your API key is still valid.
    """
    if not is_authenticated():
        err_console.print("Not logged in.", style="yellow", markup=False)
        err_console.print("Run 'validibot login' to authenticate.", style="dim", markup=False)
        raise typer.Exit(1)

    try:
        client = get_client()
        user = client.get_current_user()
    except AuthenticationError as e:
        err_console.print(
            f"Authentication failed: {e.message}",
            style="red",
            markup=False,
        )
        err_console.print(
            "Your API key may have expired. Run 'validibot login' to re-authenticate.",
            style="dim",
            markup=False,
        )
        raise typer.Exit(1) from None
    except Exception as e:
        err_console.print(f"Error: {e}", style="red", markup=False)
        raise typer.Exit(1) from None

    # Display user info
    email = user.email
    name = user.name
    username = user.username

    token = get_stored_token()
    key_display = _mask_key(token) if token else "none"

    console.print()
    console.print(
        Panel(
            f"[bold]{escape(name or email)}[/bold]\n\n"
            + (f"[dim]Username:[/dim] {escape(username)}\n" if username else "")
            + f"[dim]Email:[/dim] {escape(email)}\n"
            f"[dim]API Key:[/dim] {escape(key_display)}\n"
            f"[dim]API:[/dim] {escape(get_api_url())}",
            title="Current User",
            border_style="blue",
        )
    )


@app.command()
def status() -> None:
    """
    Check authentication status without making an API call.
    """
    if is_authenticated():
        token = get_stored_token()
        key_display = _mask_key(token) if token else "none"
        console.print(
            f"Authenticated (API key: {key_display})",
            style="green",
            markup=False,
        )
        console.print(
            f"Storage: {get_token_storage_location()}",
            style="dim",
            markup=False,
        )
    else:
        err_console.print("Not authenticated", style="yellow", markup=False)
        err_console.print("Run 'validibot login' to authenticate.", style="dim", markup=False)
