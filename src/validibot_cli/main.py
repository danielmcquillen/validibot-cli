"""
Validibot CLI - Main entry point.

Usage:
    validibot login          # Authenticate with your API key
    validibot whoami         # Show current user info
    validibot validate       # Run a validation workflow
    validibot workflows      # List available workflows
"""

import typer
from rich.console import Console

from validibot_cli import __version__
from validibot_cli.commands import auth, runs, validate, workflows

# Create the main app with rich markup for better help formatting
app = typer.Typer(
    name="validibot",
    help="Validibot CLI - Automated data validation from the command line.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,  # Can enable later if users want shell completion
)

console = Console()

# Register command groups
app.add_typer(auth.app, name="auth", help="Authentication commands")
app.add_typer(workflows.app, name="workflows", help="Workflow commands")
app.add_typer(
    runs.app,
    name="runs",
    help="Inspect validation runs (in progress or completed)",
)

# Register top-level convenience commands
app.command(name="login", help="Authenticate with Validibot (alias for auth login)")(
    auth.login
)
app.command(name="whoami", help="Show current user info (alias for auth whoami)")(
    auth.whoami
)
app.command(name="logout", help="Remove stored credentials (alias for auth logout)")(
    auth.logout
)
app.command(name="validate", help="Start a validation run")(validate.run)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"validibot-cli version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """
    Validibot CLI - Automated data validation from the command line.

    [bold]Quick start:[/bold]

        validibot login              # Authenticate with your API key
        validibot validate file.idf  # Validate a file

    [bold]Getting help:[/bold]

        validibot --help             # Show this help
        validibot validate --help    # Help for a specific command

    [dim]Docs: https://docs.validibot.com/cli[/dim]
    """
    pass


if __name__ == "__main__":
    app()
