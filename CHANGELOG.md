# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.4] - 2026-01-07

### Updated

- After successful auth, fetches user's orgs
  - If 1 org: auto-sets as default
  - If multiple orgs: prompts user to select (or skip)
  - Shows default org in success panel
- Updated whoami command to show current default org
- Updated all commands to use default org when --org not provided
- Added VALIDIBOT_ORG env variable
- Org precedence order:
  - --org flag (explicit)
  - VALIDIBOT_ORG environment variable
  - Stored default org from login
  - Error with helpful message

## [0.1.3] - 2026-01-06

### Updated

- Internal update to match new API on validibot.com
- Workflow can now be referenced by slug _or_ public ID

## [0.1.2] - 2025-12-22

### Updated

- README.md

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
- Comprehensive README with examples and CI/CD integration guides
