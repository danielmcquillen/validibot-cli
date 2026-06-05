# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-06-06

### Security

- Strip terminal control/escape bytes (ANSI/OSC sequences, carriage returns)
  from all server-controlled strings before display. Rich's `escape()` /
  `markup=False` only neutralize Rich's own `[tag]` markup, not raw terminal
  control sequences, so a malicious or compromised server could previously
  recolor output to spoof a result, move the cursor, rewrite the window title,
  or overwrite a line. Added `validibot_cli.safe_output` and applied it to
  error details, finding messages, and workflow names/versions across the
  `validate`, `runs`, and `workflows` commands.
- Create the config directory (`~/.config/validibot`, which holds
  `credentials.json`) with `0700` permissions, and open the token temp-file
  with `O_NOFOLLOW`, hardening the credential store against other local users
  and symlink/predictable-temp races.
- Route `post`/`upload_file` requests through the same host-pinning guard
  (`_resolve_url`) as `get`, so a request target can never be sent to a
  different host than the configured API.

### Changed

- Refreshed `uv.lock` to pull patched transitive dependencies (idna 3.18,
  python-dotenv 1.2.2, jaraco-context 6.1.2, pygments 2.20.0, certifi
  2026.5.20), clearing several advisories that were pinned in the old lock.
- The lockfile is now committed, and CI verifies it stays in sync with
  `pyproject.toml` and audits the locked dependency set for known
  vulnerabilities (so a CVE pinned in the lock is caught even when a clean
  install would resolve to a fixed version).

## [0.3.0] - 2026-06-06

### Added

- `validibot validate` now accepts `--meta key=value` (repeatable) and
  `--short-description`, carrying submission metadata and a run description from
  the CLI. These back the `submission.metadata.*` and
  `submission.short_description` assertion namespace (ADR-2026-06-03b), so a
  `submission.*` rule fires regardless of launch path — matching the REST API,
  which already accepts these. The CLI is a trusted-setter path: values are sent
  as multipart form fields and persisted ungated. Metadata is parsed from
  `key=value` pairs (only the first `=` splits) into a JSON field; malformed
  pairs fail fast with a clear message.

### Fixed

- README: corrected a stale repo name (`validibot-validators` →
  `validibot-validator-backends`).

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
