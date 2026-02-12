<div align="center">

# Validibot CLI

**Command-line interface for the Validibot data validation platform**

[![Build Status](https://github.com/danielmcquillen/validibot-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/danielmcquillen/validibot-cli/actions)
[![PyPI version](https://badge.fury.io/py/validibot-cli.svg)](https://pypi.org/project/validibot-cli/)
[![Python versions](https://img.shields.io/pypi/pyversions/validibot-cli.svg)](https://pypi.org/project/validibot-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Installation](#installation) •
[Quick Start](#quick-start) •
[Commands](#commands) •
[CI/CD Integration](#cicd-integration) •
[Documentation](https://docs.validibot.com/cli)

</div>

---

> [!NOTE]
> This CLI is part of the [Validibot](https://github.com/danielmcquillen/validibot) open-source data validation platform. It connects to self-hosted Validibot servers to run validations from the command line or CI/CD pipelines.

---

## Part of the Validibot Project

| Repository | Description |
|------------|-------------|
| **[validibot](https://github.com/danielmcquillen/validibot)** | Core platform — web UI, REST API, workflow engine |
| **[validibot-cli](https://github.com/danielmcquillen/validibot-cli)** (this repo) | Command-line interface |
| **[validibot-validators](https://github.com/danielmcquillen/validibot-validators)** | Advanced validator containers (EnergyPlus, FMI) |
| **[validibot-shared](https://github.com/danielmcquillen/validibot-shared)** | Shared Pydantic models for data interchange |

---

## What is Validibot CLI?

Validibot CLI provides command-line access to your Validibot server for automated data validation. Use it to:

- **Run validations** from terminals, scripts, or CI/CD pipelines
- **Integrate validation** into your development workflow
- **Automate quality checks** for building energy models, simulations, and structured data

The CLI communicates with your Validibot server's REST API, so you need a running Validibot instance to use it.

## Features

- **Self-hosted support** — connect to your own Validibot server
- **Workflow support** — reference workflows by ID or human-readable slug
- **Organization filtering** — disambiguate workflows across orgs and projects
- **Secure credential storage** — uses system keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- **CI/CD friendly** — meaningful exit codes and JSON output for scripting

## Disclaimer

> [!NOTE]
> This CLI connects to your Validibot server and transmits files for validation. You are solely responsible for the security of your server, the confidentiality of your data, and any costs associated with your infrastructure. API keys should be kept secret — see [Credential storage](#authentication) for details. See the [LICENSE](LICENSE) for full warranty disclaimer.

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
- A running [Validibot](https://github.com/danielmcquillen/validibot) server

## Quick Start

### 1. Configure Your Server

Point the CLI at your Validibot server:

```bash
validibot config set-server https://validibot.your-company.com
```

### 2. Authenticate

Get your API key from your Validibot server's web interface (Settings → API Key), then:

```bash
validibot login
# Enter your API key when prompted (input is hidden)
```

Your API key is stored securely in your system keyring.

### 3. List Available Workflows

```bash
validibot workflows list
```

This displays a table of workflows you have access to, including their IDs, names, and status.

### 4. Run a Validation

```bash
# By workflow ID
validibot validate model.idf --workflow 123

# By workflow slug
validibot validate model.idf --workflow energyplus-schema-check
```

The CLI uploads your file, runs the validation workflow, and displays results when complete.

## Commands

### Server Configuration

```bash
validibot config set-server <url>   # Set server URL (required before login)
validibot config get-server         # Show current server URL
validibot config clear-server       # Clear stored server URL
```

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
4. Fetches your organizations and sets a default:
   - If you belong to one org, it becomes your default automatically
   - If you belong to multiple orgs, you'll be prompted to select one
5. Displays your account info to confirm success

**Credential storage:**

| Platform | Storage |
|----------|---------|
| macOS | Keychain |
| Windows | Credential Manager |
| Linux | Secret Service (GNOME Keyring, KWallet) |

If the system keyring is unavailable, credentials fall back to `~/.config/validibot/credentials.json` with restrictive file permissions.

### Workflows

```bash
validibot workflows list                        # List all available workflows
validibot workflows list --json                 # Output as JSON
validibot workflows show <workflow-id-or-slug>  # Show workflow details
```

### Validation Runs

```bash
validibot runs show <run-id>        # Show run status and results
validibot runs show <run-id> --json # Output as JSON
```

### Running Validations

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

Workflows can be specified by **ID** (numeric) or **slug** (human-readable string):

```bash
# By numeric ID
validibot validate model.idf -w 123

# By slug
validibot validate model.idf -w energyplus-schema-check
```

When using slugs, if multiple workflows share the same slug across different organizations, you'll need to disambiguate:

```bash
# Specify organization
validibot validate model.idf -w my-workflow --org acme-corp

# Specify organization and project
validibot validate model.idf -w my-workflow --org acme-corp --project building-a

# Specify a particular version
validibot validate model.idf -w my-workflow --org acme-corp --version 2
```

#### Output Options

```bash
# Verbose output (shows individual step results)
validibot validate model.idf -w <workflow> --verbose

# JSON output (for scripting/CI)
validibot validate model.idf -w <workflow> --json

# Custom timeout (default: 600 seconds)
validibot validate model.idf -w <workflow> --timeout 300

# Name your validation run
validibot validate model.idf -w <workflow> --name "nightly-build-check"
```

#### Option Reference

| Option | Short | Description |
|--------|-------|-------------|
| `--workflow` | `-w` | Workflow ID or slug (required) |
| `--org` | `-o` | Organization slug |
| `--project` | `-p` | Project slug for filtering |
| `--version` | | Workflow version |
| `--name` | `-n` | Name for this validation run |
| `--wait/--no-wait` | | Wait for completion (default: wait) |
| `--timeout` | `-t` | Max wait time in seconds (default: 600) |
| `--verbose` | `-v` | Show detailed step-by-step output |
| `--json` | `-j` | Output results as JSON |

## Configuration

### Server URL Resolution

The CLI determines which server to connect to in this order:

1. `VALIDIBOT_API_URL` environment variable
2. Stored server URL from `validibot config set-server`
3. Error if neither is set

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VALIDIBOT_API_URL` | Server URL | — |
| `VALIDIBOT_TOKEN` | API key (alternative to `validibot login`) | — |
| `VALIDIBOT_ORG` | Default organization slug | — |
| `VALIDIBOT_TIMEOUT` | Request timeout in seconds | `300` |
| `VALIDIBOT_POLL_INTERVAL` | Status polling interval in seconds | `5` |
| `VALIDIBOT_NO_KEYRING` | Disable keyring, use file storage | `false` |
| `VALIDIBOT_ALLOW_INSECURE_API_URL` | Allow non-HTTPS API URL (dangerous) | `false` |

### Organization Resolution

When `--org` is not explicitly provided, the CLI resolves the organization in this order:

1. `--org` flag (if provided)
2. `VALIDIBOT_ORG` environment variable
3. Default org saved during `validibot login`
4. Error with a helpful message

## Exit Codes

The `validate` command returns meaningful exit codes for CI/CD integration:

| Code | Meaning |
|------|---------|
| `0` | Validation passed |
| `1` | Validation failed (`FAIL`) or CLI/API error |
| `2` | Validation error (`ERROR`/`TIMED_OUT`/`CANCELED`) |
| `3` | Timed out waiting for completion (run still in progress) |
| `130` | Interrupted (Ctrl+C) |

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
          VALIDIBOT_API_URL: ${{ vars.VALIDIBOT_API_URL }}
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
    VALIDIBOT_API_URL: $VALIDIBOT_API_URL
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
    VALIDIBOT_API_URL: $(VALIDIBOT_API_URL)
    VALIDIBOT_TOKEN: $(VALIDIBOT_TOKEN)
```

## Development

```bash
# Clone the repository
git clone https://github.com/danielmcquillen/validibot-cli.git
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

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

[Validibot Platform](https://github.com/danielmcquillen/validibot) •
[Documentation](https://docs.validibot.com/cli) •
[Report Issues](https://github.com/danielmcquillen/validibot-cli/issues)

</div>
