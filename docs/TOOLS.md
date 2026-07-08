# Tools

Standalone utilities bundled with openclaw-dash. These work independently of the dashboard TUI.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `openclaw-dash audit` | Security vulnerability scanning |
| `openclaw-dash changelog` | Generate changelog from git |
| `openclaw-dash dep-shepherd` | Dependency management |
| `openclaw-dash pr-create` | Create structured pull requests |
| `openclaw-dash pr-describe` | Analyze existing pull requests |
| `openclaw-dash pr-tracker` | Track PRs across repos |
| `openclaw-dash repo-scanner` | Scan for TODOs and patterns |
| `openclaw-dash smart-todo` | Intelligent TODO detection |
| `openclaw-dash status` | Quick repo status |
| `openclaw-dash version-bump` | Semantic version management |

## audit

Security scanning for Python projects.

```bash
openclaw-dash audit /path/to/repo
openclaw-dash audit /path/to/repo --json
openclaw-dash audit /path/to/repo --fix
```

Checks:
- Dependency vulnerabilities (pip-audit)
- Hardcoded secrets and API keys
- Dangerous patterns (eval, exec, shell=True)
- Insecure configurations (debug mode, CORS, TLS)

## changelog

Generate CHANGELOG.md from git history.

```bash
openclaw-dash changelog /path/to/repo
openclaw-dash changelog /path/to/repo --since v1.0.0
openclaw-dash changelog /path/to/repo --format conventional
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
openclaw-dash dep-shepherd check /path/to/repo
openclaw-dash dep-shepherd update /path/to/repo
openclaw-dash dep-shepherd audit /path/to/repo
```

Features:
- Outdated dependency detection
- Vulnerability scanning
- Update suggestions
- Lock file generation

## pr-create

Create pull requests with structured descriptions.

```bash
openclaw-dash pr-create --title "feat: add plugin"
openclaw-dash pr-create --from feature-branch --to main
openclaw-dash pr-create --reviewers user1,user2
```

Auto-generates description from commits when `--body` is omitted.

## pr-describe

Analyze existing pull requests.

```bash
openclaw-dash pr-describe 42
openclaw-dash pr-describe 42 --format markdown
openclaw-dash pr-describe 42 --summary-only
```

Outputs:
- Change summary (files, lines)
- Risk assessment
- Testing recommendations
- Review checklist

## pr-tracker

Track PR status across multiple repositories.

```bash
openclaw-dash pr-tracker --repos owner/repo1,owner/repo2
openclaw-dash pr-tracker --status open
openclaw-dash pr-tracker --assigned me
```

Aggregates status into a single view. Requires gh CLI.

## repo-scanner

Scan repositories for patterns.

```bash
openclaw-dash repo-scanner /path/to/repo
openclaw-dash repo-scanner /path/to/repo --pattern "FIXME|HACK"
openclaw-dash repo-scanner /path/to/repo --json
```

Finds:
- TODO, FIXME, HACK, XXX comments
- Custom patterns
- Can filter docstrings

## smart-todo-scanner

Intelligent TODO detection with context.

```bash
openclaw-dash smart-todo /path/to/repo
openclaw-dash smart-todo /path/to/repo --priority high
```

Goes beyond pattern matching:
- Analyzes surrounding code context
- Assigns priority by impact
- Groups related TODOs
- Suggests resolution approaches

## status

Quick repository status.

```bash
openclaw-dash status /path/to/repo
openclaw-dash status /path/to/repo --json
openclaw-dash status /path/to/repo --brief
```

Shows:
- Branch status (ahead/behind)
- Uncommitted changes
- Recent activity
- CI status (if gh CLI available)

## version-bump

Semantic version management.

```bash
openclaw-dash version-bump patch    # 1.0.0 -> 1.0.1
openclaw-dash version-bump minor    # 1.0.0 -> 1.1.0
openclaw-dash version-bump major    # 1.0.0 -> 2.0.0
openclaw-dash version-bump 1.2.3    # Explicit version
```

Updates version in:
- pyproject.toml
- setup.py
- __init__.py

## Standalone Usage

All tools can run as standalone modules:

```bash
python -m openclaw_dash.tools.audit /path/to/repo
python -m openclaw_dash.tools.changelog /path/to/repo
```

This is useful for CI/CD pipelines or when you want specific tool functionality without the full dashboard.

## Configuration

Tools read optional config from `~/.config/openclaw-dash/tools.yaml`:

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
