# Tools

Standalone utilities bundled with hermes-dash. These work independently of the dashboard TUI.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `hermes-dash audit` | Security vulnerability scanning |
| `hermes-dash changelog` | Generate changelog from git |
| `hermes-dash dep-shepherd` | Dependency management |
| `hermes-dash pr-create` | Create structured pull requests |
| `hermes-dash pr-describe` | Analyze existing pull requests |
| `hermes-dash pr-tracker` | Track PRs across repos |
| `hermes-dash repo-scanner` | Scan for TODOs and patterns |
| `hermes-dash smart-todo` | Intelligent TODO detection |
| `hermes-dash status` | Quick repo status |
| `hermes-dash version-bump` | Semantic version management |

## audit

Security scanning for Python projects.

```bash
hermes-dash audit /path/to/repo
hermes-dash audit /path/to/repo --json
hermes-dash audit /path/to/repo --fix
```

Checks:
- Dependency vulnerabilities (pip-audit)
- Hardcoded secrets and API keys
- Dangerous patterns (eval, exec, shell=True)
- Insecure configurations (debug mode, CORS, TLS)

## changelog

Generate CHANGELOG.md from git history.

```bash
hermes-dash changelog /path/to/repo
hermes-dash changelog /path/to/repo --since v1.0.0
hermes-dash changelog /path/to/repo --format conventional
```

Parses conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `chore:` - Maintenance
- `docs:` - Documentation
- `refactor:` - Code changes
- `test:` - Test changes

## dep-shepherd

Dependency management.

```bash
hermes-dash dep-shepherd check /path/to/repo
hermes-dash dep-shepherd update /path/to/repo
hermes-dash dep-shepherd audit /path/to/repo
```

Features:
- Outdated dependency detection
- Vulnerability scanning
- Update suggestions
- Lock file generation

## pr-create

Create pull requests with structured descriptions.

```bash
hermes-dash pr-create --title "feat: add plugin"
hermes-dash pr-create --from feature-branch --to main
hermes-dash pr-create --reviewers user1,user2
```

Auto-generates description from commits when `--body` is omitted.

## pr-describe

Analyze existing pull requests.

```bash
hermes-dash pr-describe 42
hermes-dash pr-describe 42 --format markdown
hermes-dash pr-describe 42 --summary-only
```

Outputs:
- Change summary (files, lines)
- Risk assessment
- Testing recommendations
- Review checklist

## pr-tracker

Track PR status across multiple repositories.

```bash
hermes-dash pr-tracker --repos owner/repo1,owner/repo2
hermes-dash pr-tracker --status open
hermes-dash pr-tracker --assigned me
```

Aggregates status into a single view. Requires gh CLI.

## repo-scanner

Scan repositories for patterns.

```bash
hermes-dash repo-scanner /path/to/repo
hermes-dash repo-scanner /path/to/repo --pattern "FIXME|HACK"
hermes-dash repo-scanner /path/to/repo --json
```

Finds:
- TODO, FIXME, HACK, XXX comments
- Custom patterns
- Can filter docstrings

## smart-todo-scanner

Intelligent TODO detection with context.

```bash
hermes-dash smart-todo /path/to/repo
hermes-dash smart-todo /path/to/repo --priority high
```

Goes beyond pattern matching:
- Analyzes surrounding code context
- Assigns priority by impact
- Groups related TODOs
- Suggests resolution approaches

## status

Quick repository status.

```bash
hermes-dash status /path/to/repo
hermes-dash status /path/to/repo --json
hermes-dash status /path/to/repo --brief
```

Shows:
- Branch status (ahead/behind)
- Uncommitted changes
- Recent activity
- CI status (if gh CLI available)

## version-bump

Semantic version management.

```bash
hermes-dash version-bump patch    # 1.0.0 -> 1.0.1
hermes-dash version-bump minor    # 1.0.0 -> 1.1.0
hermes-dash version-bump major    # 1.0.0 -> 2.0.0
hermes-dash version-bump 1.2.3    # Explicit version
```

Updates version in:
- pyproject.toml
- setup.py
- __init__.py

## Standalone Usage

All tools can run as standalone modules:

```bash
python -m hermes_dash.tools.audit /path/to/repo
python -m hermes_dash.tools.changelog /path/to/repo
```

This is useful for CI/CD pipelines or when you want specific tool functionality without the full dashboard.

## Configuration

Tools read optional config from `~/.config/hermes-dash/tools.yaml`:

```yaml
tools:
  audit:
    severity_threshold: medium
    ignore_patterns:
      - "test_*"
  
  changelog:
    default_format: conventional
    include_authors: true
```
