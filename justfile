# Validibot CLI development commands

# Default recipe - show available commands
default:
    @just --list

# Run tests
test:
    uv run pytest

# Run tests with coverage
test-cov:
    uv run pytest --cov=validibot_cli

# Lint and format
lint:
    uv run ruff check .
    uv run ruff format --check .

# Format code
fmt:
    uv run ruff format .
    uv run ruff check --fix .

# Type check
typecheck:
    uv run mypy src/

# Run all checks (lint, typecheck, test)
check: lint typecheck test

# Run the CLI locally
run *ARGS:
    uv run validibot {{ARGS}}

# Release a new version (tag + GitHub release → PyPI publish)
# Usage: just release 0.1.5
release VERSION:
    #!/usr/bin/env bash
    set -euo pipefail

    # Validate version format
    if [[ ! "{{VERSION}}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "Error: Version must be in format X.Y.Z (e.g., 0.1.5)"
        exit 1
    fi

    # Check for uncommitted changes
    if [[ -n $(git status --porcelain) ]]; then
        echo "Error: You have uncommitted changes. Commit or stash them first."
        exit 1
    fi

    # Check we're on main branch
    BRANCH=$(git branch --show-current)
    if [[ "$BRANCH" != "main" ]]; then
        echo "Warning: You're on branch '$BRANCH', not 'main'. Continue? [y/N]"
        read -r REPLY
        if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # Check version in pyproject.toml matches
    TOML_VERSION=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
    if [[ "$TOML_VERSION" != "{{VERSION}}" ]]; then
        echo "Error: Version in pyproject.toml ($TOML_VERSION) doesn't match {{VERSION}}"
        echo "Update pyproject.toml first, then commit."
        exit 1
    fi

    echo "Releasing v{{VERSION}}..."

    # Create and push tag
    git tag "v{{VERSION}}"
    git push origin "v{{VERSION}}"

    # Create GitHub release (triggers PyPI publish via Actions)
    gh release create "v{{VERSION}}" \
        --title "v{{VERSION}}" \
        --notes "See [CHANGELOG.md](CHANGELOG.md) for details."

    echo ""
    echo "Release v{{VERSION}} created!"
    echo "GitHub Actions will publish to PyPI automatically."
    echo "Monitor: gh run list --limit 3"
