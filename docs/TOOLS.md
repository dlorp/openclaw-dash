# Tools Reference

openclaw-dash bundles standalone utilities for repo management, security auditing, and PR workflows. These tools work independently of the dashboard.

## Quick Reference

| Tool | Command | Description |
|------|---------|-------------|
| Audit | `openclaw-dash audit` | Security vulnerability scanning |
| Changelog | `openclaw-dash changelog` | Generate changelogs from git |
| Dep Shepherd | `openclaw-dash dep-shepherd` | Dependency management |
| PR Create | `openclaw-dash pr-create` | Structured PR creation |
| PR Describe | `openclaw-dash pr-describe` | PR analysis and description |
| PR Tracker | `openclaw-dash pr-tracker` | Cross-repo PR tracking |
| Repo Scanner | `openclaw-dash repo-scanner` | Pattern and TODO scanning |
| Smart TODO | `openclaw-dash smart-todo-scanner` | Contextual TODO detection |
| Status | `openclaw-dash status` | Quick repo status report |
| Version Bump | `openclaw-dash version-bump` | Semantic version management |

## audit

Security vulnerability scanning for Python projects.

```bash
openclaw-dash audit /path/to/repo
openclaw-dash audit /path/to/repo --json
openclaw-dash audit /path/to/repo --fix
```

Checks:
- Dependency vulnerabilities (pip-audit integration)
- Hardcoded secrets and API keys
- Dangerous code patterns (eval, exec, shell=True)
- Insecure configurations (debug mode, CORS, TLS)

## changelog

Generate CHANGELOG.md from git commit history.

```bash
openclaw-dash changelog /path/to/repo
openclaw-dash changelog /path/to/repo --since v1.0.0
openclaw-dash changelog /path/to/repo --format conventional
```

Parses conventional commits (feat:, fix:, chore:, etc.) and groups by type.

## dep-shepherd

Dependency management and vulnerability scanning.

```bash
openclaw-dash dep-shepherd check /path/to/repo
openclaw-dash dep-shepherd update /path/to/repo
openclaw-dash dep-shepherd audit /path/to/repo
```

Features:
- Outdated dependency detection
- Vulnerability scanning via pip-audit
- Automated update suggestions
- Lock file generation

## pr-create

Create pull requests with structured descriptions.

```bash
openclaw-dash pr-create --title "feat: add plugin system" --body "Description here"
openclaw-dash pr-create --from feature-branch --to main
openclaw-dash pr-create --reviewers user1,user2
```

Auto-generates PR description from commit history when `--body` is omitted.

## pr-describe

Analyze and describe existing pull requests.

```bash
openclaw-dash pr-describe 42
openclaw-dash pr-describe 42 --format markdown
openclaw-dash pr-describe 42 --summary-only
```

Outputs:
- Change summary (files changed, lines added/removed)
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

Aggregates PR status from multiple repos into a single view.

## repo-scanner

Scan repositories for TODOs, issues, and code patterns.

```bash
openclaw-dash repo-scanner /path/to/repo
openclaw-dash repo-scanner /path/to/repo --pattern "FIXME|HACK|XXX"
openclaw-dash repo-scanner /path/to/repo --skip-docstrings
```

Features:
- TODO/FIXME/HACK detection
- Custom pattern matching
- Docstring filtering
- Structured output (JSON, markdown)

## smart-todo-scanner

Intelligent TODO detection with context analysis.

```bash
openclaw-dash smart-todo-scanner /path/to/repo
openclaw-dash smart-todo-scanner /path/to/repo --priority high
```

Goes beyond simple pattern matching:
- Analyzes surrounding code context
- Assigns priority based on impact
- Groups related TODOs
- Suggests resolution approaches

## status

Quick status report for repositories.

```bash
openclaw-dash status /path/to/repo
openclaw-dash status /path/to/repo --json
openclaw-dash status /path/to/repo --brief
```

Shows:
- Branch status (ahead/behind remote)
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

Updates version in pyproject.toml, setup.py, and __init__.py.
