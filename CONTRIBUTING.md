# Contributing

Thanks for your interest in contributing to `validibot-cli`.

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

## Reporting bugs

- Include your OS, Python version, and `validibot --version`.
- If the output contains an API key or token, redact it before sharing.

