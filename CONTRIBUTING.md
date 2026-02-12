# Contributing

Thanks for your interest in contributing to `validibot-cli`.

## License Agreement

By submitting a pull request, you agree that your contributions are licensed
under the [MIT License](LICENSE), the same license that covers this project.
You confirm that you have the right to grant this license for your contributions.

## Development setup

This project uses `uv` for dependency management.

```bash
uv sync --extra dev
```

## Running checks

```bash
# Tests
uv run pytest

# Linting/formatting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/
```

## Reporting Issues

- **Bugs and feature requests:** [GitHub Issues](https://github.com/danielmcquillen/validibot-cli/issues)
  - Include your OS, Python version, and `validibot --version`
  - If the output contains an API key or token, redact it before sharing
- **Security vulnerabilities:** See [SECURITY.md](SECURITY.md) — do not open a public issue

