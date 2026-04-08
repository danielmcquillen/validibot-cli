# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2026-04-08

- Add note about file-based fallback
- Ask user for preference on file-based fallback

## [0.2.1] - 2026-03-23

### Added

- Pre-commit hooks with TruffleHog secret scanning, detect-private-key, and Ruff linting
- Dependabot configuration for GitHub Actions and Python dependency updates
- Hardened .gitignore to exclude key material and credential files
- pip-audit dependency auditing in CI
- Sigstore attestations for PyPI publish (provenance verification)

### Changed

- Publish workflow: switched from pip+build to uv build, pinned uv version and all GitHub Actions to commit SHAs
- Improved docstrings and comments in validate and workflow commands

### Fixed

- Enforced HTTPS for stored server URLs, not just `VALIDIBOT_API_URL`
- Invalid environment-backed configuration now surfaces as clean CLI errors instead of Python tracebacks
- `config set-server` now honors `VALIDIBOT_ALLOW_INSECURE_API_URL=1` consistently with its help text
- Ambiguous workflow detection now works for structured API error responses
- Removed dead `validate status` subcommand; status references now point to `runs show`
- Workflow and organization listing now follows paginated API responses
- Pagination links are constrained to the configured API host before being followed

## [0.2.0] - 2026-01-29

### Changed (BREAKING)

- **Self-hosted only**: Removed default server URL (validibot.com). Users must now configure a server before use.
- Server URL must be set via `validibot config set-server <url>` or `VALIDIBOT_API_URL` environment variable.

### Added

- New `validibot config` command group:
  - `set-server <url>` - Configure server URL (required before login)
  - `get-server` - Show current server URL and source
  - `clear-server` - Clear stored server URL
- Server URL resolution order: env var → stored config → error

### Changed

- README rewritten for self-hosted deployment model
- CI/CD examples updated to include `VALIDIBOT_API_URL`
- All commands now check for server configuration before proceeding

## [0.1.5] - 2026-01-07

### Fixed

- Fix default org bug where Organization model required `id` field not present in API response

## [0.1.4] - 2026-01-07

### Added

- Default organization support:
  - After successful auth, fetches user's orgs
  - If 1 org: auto-sets as default
  - If multiple orgs: prompts user to select (or skip)
  - Shows default org in success panel
- `VALIDIBOT_ORG` environment variable support
- Org precedence order: `--org` flag → `VALIDIBOT_ORG` env var → stored default → error

### Changed

- `whoami` command now shows current default org
- All commands use default org when `--org` not provided

## [0.1.3] - 2026-01-06

### Changed

- Internal update to match new API on validibot.com
- Workflow can now be referenced by slug or public ID

## [0.1.2] - 2025-12-22

### Changed

- README updates

## [0.1.1] - 2025-12-22

### Added

- Initial release
- Authentication commands (login, logout, whoami, auth status)
- Workflow listing and management commands
- Validation run commands with wait/no-wait options
- Secure credential storage via system keyring
- Workflow disambiguation by organization, project, and version
- CI/CD integration support with meaningful exit codes
- JSON output option for scripting
- Verbose mode for detailed step-by-step output
- Environment variable configuration support
