# Validibot CLI

[![CI](https://github.com/danielmcquillen/validibot-cli/workflows/CI/badge.svg)](https://github.com/danielmcquillen/validibot-cli/actions)
[![PyPI version](https://badge.fury.io/py/validibot-cli.svg)](https://pypi.org/project/validibot-cli/)
[![Python versions](https://img.shields.io/pypi/pyversions/validibot-cli.svg)](https://pypi.org/project/validibot-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A command-line interface for [Validibot](https://validibot.com) - your automated data validation assistant.

What's Validibot CLI? Validibot CLI is a small library that provides a command line access to Validibot.
What's Validibot? So happy you asked! Read more here >> [https://validibot.com ](https://validibot.com)

## Features

- **Run validations** from the command line or CI/CD pipelines
- **Workflow support** - reference workflows by ID or human-readable slug
- **Organization filtering** - disambiguate workflows across orgs and projects
- **Secure credential storage** - uses system keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- **CI/CD friendly** - meaningful exit codes and JSON output for scripting

## Installation

```bash
# Using pip
pip install validibot-cli

# Using uv (recommended)
uv tool install validibot-cli

# Using pipx
pipx install validibot-cli
```

### Requirements

- Python 3.10 or later

## Quick Start

### 1. Authenticate

Get your API key from the [Validibot web app](https://validibot.com/app/users/api-key/), then:

```bash
validibot login
# Enter your API key when prompted (input is hidden)
```

Your API key is stored securely in your system keyring.

### 2. List Available Workflows

```bash
validibot workflows list
```

This displays a table of workflows you have access to, including their IDs, names, and status.

### 3. Run a Validation

```bash
# By workflow ID
validibot validate model.idf --workflow 123

# By workflow slug
validibot validate model.idf --workflow energyplus-schema-check
```

The CLI uploads your file, runs the validation workflow, and displays results when complete.

## Commands

### Authentication

```bash
validibot login              # Authenticate with your API key
validibot logout             # Remove stored credentials
validibot whoami             # Show current user info (verifies API key)
validibot auth status        # Check if authenticated (no API call)
```

**Login flow:**

1. Prompts for your API key (input is hidden for security)
2. Validates the key against the Validibot API
3. Stores the key securely in your system keyring
4. Displays your account info to confirm success

**Credential storage:**

The CLI uses your system's secure credential storage:

- **macOS**: Keychain
- **Windows**: Credential Manager
- **Linux**: Secret Service (GNOME Keyring, KWallet, etc.)

If the system keyring is unavailable, credentials fall back to `~/.config/validibot/credentials.json` with restrictive file permissions (owner read/write only).
Tokens are stored per API host (based on `VALIDIBOT_API_URL`).

### Workflows

```bash
validibot workflows list          # List all available workflows
validibot workflows list --json   # Output as JSON
validibot workflows show <workflow-id-or-slug>  # Show details of a specific workflow
```

### Runs

```bash
validibot runs show <run-id>        # Show run status and results
validibot runs show <run-id> --json # Output as JSON
```

### Validation

#### Basic Usage

```bash
# Run a validation (waits for completion by default)
validibot validate model.idf -w <workflow-id-or-slug>

# Run without waiting (returns immediately with run ID)
validibot validate model.idf -w <workflow-id-or-slug> --no-wait

# Check status of a validation run
validibot runs show <run-id>
```

#### Workflow Selection

Workflows can be specified by **ID** (numeric) or **slug** (human-readable string).

```bash
# By numeric ID
validibot validate model.idf -w 123

# By slug
validibot validate model.idf -w energyplus-schema-check
```

When using slugs, if multiple workflows share the same slug across different organizations or versions, you'll need to disambiguate:

```bash
# Specify organization
validibot validate model.idf -w my-workflow --org acme-corp

# Specify organization and project
validibot validate model.idf -w my-workflow --org acme-corp --project building-a

# Specify a particular version
validibot validate model.idf -w my-workflow --org acme-corp --version 2
```

If the workflow slug is ambiguous, the CLI will display the matching workflows and prompt you to use filtering options.

#### Output Options

```bash
# Verbose output (shows individual step results)
validibot validate model.idf -w <workflow-id-or-slug> --verbose

# JSON output (for scripting/CI)
validibot validate model.idf -w <workflow-id-or-slug> --json

# Custom timeout (default: 600 seconds)
validibot validate model.idf -w <workflow-id-or-slug> --timeout 300

# Name your validation run
validibot validate model.idf -w <workflow-id-or-slug> --name "nightly-build-check"
```

#### Full Option Reference

| Option             | Short | Description                             |
| ------------------ | ----- | --------------------------------------- |
| `--workflow`       | `-w`  | Workflow ID or slug (required)          |
| `--org`            | `-o`  | Organization slug for disambiguation    |
| `--project`        | `-p`  | Project slug for filtering              |
| `--version`        |       | Workflow version for disambiguation     |
| `--name`           | `-n`  | Name for this validation run            |
| `--wait/--no-wait` |       | Wait for completion (default: wait)     |
| `--timeout`        | `-t`  | Max wait time in seconds (default: 600) |
| `--verbose`        | `-v`  | Show detailed step-by-step output       |
| `--json`           | `-j`  | Output results as JSON                  |

## Configuration

### Environment Variables

| Variable                           | Description                                | Default                 |
| ---------------------------------- | ------------------------------------------ | ----------------------- |
| `VALIDIBOT_API_URL`                | API base URL                               | `https://validibot.com` |
| `VALIDIBOT_TOKEN`                  | API key (alternative to `validibot login`) | -                       |
| `VALIDIBOT_TIMEOUT`                | Request timeout in seconds                 | `300`                   |
| `VALIDIBOT_POLL_INTERVAL`          | Status polling interval in seconds         | `5`                     |
| `VALIDIBOT_NO_KEYRING`             | Disable keyring, use file storage          | `false`                 |
| `VALIDIBOT_ALLOW_INSECURE_API_URL` | Allow non-HTTPS API base URL (dangerous)   | `false`                 |

### Using Environment Variables for CI/CD

Instead of running `validibot login`, you can set `VALIDIBOT_TOKEN` directly:

```bash
export VALIDIBOT_TOKEN="your-api-key"
validibot validate model.idf -w my-workflow
```

## Exit Codes

The `validate` command returns meaningful exit codes for CI/CD integration:

| Code  | Meaning                                                     |
| ----- | ----------------------------------------------------------- |
| `0`   | Validation passed                                           |
| `1`   | Validation failed (`FAIL`) or CLI/API error                 |
| `2`   | Validation error (`ERROR`/`TIMED_OUT`/`CANCELED`/`UNKNOWN`) |
| `3`   | Timed out waiting for completion (run still in progress)    |
| `130` | Interrupted (Ctrl+C)                                        |

## CI/CD Integration

### GitHub Actions

```yaml
name: Validate Building Model

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Validibot CLI
        run: pip install validibot-cli

      - name: Validate model
        env:
          VALIDIBOT_TOKEN: ${{ secrets.VALIDIBOT_TOKEN }}
        run: validibot validate model.idf -w ${{ vars.WORKFLOW_ID }}
```

### GitLab CI

```yaml
validate:
  image: python:3.12
  script:
    - pip install validibot-cli
    - validibot validate model.idf -w $WORKFLOW_ID
  variables:
    VALIDIBOT_TOKEN: $VALIDIBOT_TOKEN
```

### Azure Pipelines

```yaml
- task: UsePythonVersion@0
  inputs:
    versionSpec: "3.12"

- script: |
    pip install validibot-cli
    validibot validate model.idf -w $(WORKFLOW_ID)
  env:
    VALIDIBOT_TOKEN: $(VALIDIBOT_TOKEN)
```

## Development

```bash
# Clone the repository
git clone https://github.com/validibot/validibot-cli.git
cd validibot-cli

# Install with dev dependencies
uv sync --extra dev

# Run the CLI locally
uv run validibot --help

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=validibot_cli

# Lint and format
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/
```

## License

This CLI is open source under the MIT License - see [LICENSE](LICENSE) for details.

**Note:** This is an open-source client for the [Validibot](https://validibot.com) service. The Validibot platform itself is a commercial product with separate [terms of service](https://validibot.com/terms).
