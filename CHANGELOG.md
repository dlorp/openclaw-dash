# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-03

### Added

- **TUI Dashboard** — Full-featured terminal UI with Textual
  - Gateway status, sessions, cron jobs, and logs panels
  - Repository health and activity tracking
  - Alerts panel with color-coded severity
  - Agents panel for sub-agent coordination
  - Security audit panel
  - Metrics panel with cost tracking and GitHub streak
  - System resources panel (CPU, memory, disk, network)
- **UI Features**
  - Metric boxes bar showing KPIs at a glance
  - Collapsible panels with `Enter` or `Ctrl+[`/`Ctrl+]`
  - Jump mode (`f`) for quick panel navigation
  - Vim-style navigation (`j`/`k`/`G`/`Home`)
  - Command palette (`Ctrl+P`)
  - Theme cycling (dark/light/hacker)
  - Responsive layout adapting to terminal size
- **Bundled Tools**
  - `repo-scanner` — Repository health metrics (TODOs, tests, PRs)
  - `pr-tracker` — PR status monitoring and merge detection
  - `smart-todo-scanner` — Context-aware TODO categorization
  - `dep-shepherd` — Dependency auditing and updates
  - `pr-describe` — Automated PR description generation
  - `pr-create` — Streamlined PR creation
  - `audit` — Security scanning tool
  - `version-bump` — Semantic version management
  - `changelog` — Changelog generation helper
- **CLI Modes**
  - `openclaw-dash` — Launch TUI
  - `openclaw-dash --status` — Quick text status
  - `openclaw-dash --json` — JSON output for scripting
  - `openclaw-dash security` — Run security audits
  - `openclaw-dash auto merge/cleanup` — Automation commands
- **Documentation**
  - Comprehensive README with ASCII preview
  - Installation, configuration, widgets, and development guides
  - Contributing guidelines and code of conduct

### Fixed

- **pr-tracker**: Handle corrupted state files, invalid date formats, and malformed org names gracefully (#60)
- **smart-todo-scanner**: Complete rewrite with proper argparse, input validation, and improved detection logic (#61)
- **repo-scanner**: Add progress indicator, deprecation warnings, and general polish (#59)
- **pr-describe**: Fix `dataclass` import for Python 3.10 compatibility in CI (#62)
- **Security**: Remove `shell=True` command injection vulnerabilities (#57)

### Changed

- **pr-describe**: Add `--squash` format for compact commit messages suitable for squash merges
- Improved error handling and edge case coverage across all collectors (#56)
- Added collector caching, timing metrics, and error tracking (#55)
- Enhanced code quality with docstrings and type hints throughout (#54)

[0.1.0]: https://github.com/dlorp/openclaw-dash/releases/tag/v0.1.0
