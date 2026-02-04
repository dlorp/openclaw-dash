# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-06-15

### Added

- **pr-describe**: Add Why and How sections to PR descriptions for better context (#79)
- **pr-describe**: Implement structured commit format extraction for cleaner output (#77)
- **pr-describe**: Add `--squash` format for compact commit messages
- **pr-tracker**: Add `--ci` flag to show actual CI/GitHub Actions status (#80)
- **status**: New combined status command (`openclaw-dash status`) for quick overview (#83)
- **Structured output**: JSON output support for programmatic consumption (#78)
- **version-bump**: Add `--path` flag for monorepo support (#65)
- **smart-todo-scanner**: Add `--skip-docstrings` flag to exclude docstring TODOs (#86)
- **audit**: Add audit.py tool for security scanning

### Fixed

- **Timezone**: Use dynamic timezone detection instead of hardcoded AKST
- **pr-describe**: Improve multi-action title phrasing for clarity (#81)
- **smart-todo-scanner**: Prevent hanging on large directories (#75)
- **audit**: Update imports to use config module (#74)
- **CLI**: Add 10-second timeout for gateway-dependent commands (#71)
- **auto deps**: Prevent hang by closing stdin on subprocesses (#70)
- **auto**: Fix datetime comparison in branch cleanup (#68)
- **repo-scanner**: Improve status logic and exclude vendored code (#67)
- **Error messaging**: Update to reflect local gateway architecture (#72)

### Changed

- **Performance**: Optimize smart-todo-scanner from O(n²) to O(n) complexity (#69)

### Documentation

- Add missing badges to README (license, python, CI, platform) (#73)
- Add version badge to README (#66)

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

[0.2.0]: https://github.com/dlorp/openclaw-dash/releases/tag/v0.2.0
[0.1.0]: https://github.com/dlorp/openclaw-dash/releases/tag/v0.1.0
