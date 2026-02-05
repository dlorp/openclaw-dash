# Integrated Tools

> **See [TOOLS.md](TOOLS.md) for comprehensive documentation** including CLI options, configuration, and API usage.

openclaw-dash bundles several automation tools that work standalone or as part of the dashboard.

## Quick Reference

| Tool | Description | Quick Start |
|------|-------------|-------------|
| `pr-describe` | Auto-generate PR descriptions | `pr-describe --title` |
| `pr-create` | Create PRs with generated content | `pr-create --dry-run` |
| `version-bump` | Semantic versioning from commits | `version-bump --dry-run` |
| `repo-scanner` | Repository health metrics | `repo-scanner --format json` |
| `smart-todo-scanner` | Context-aware TODO categorization | `smart-todo-scanner --no-docstrings` |
| `dep-shepherd` | Dependency audit and updates | `dep-shepherd --report` |
| `audit` | Security scanning | `audit --verbose` |

## Installation

All tools are included with openclaw-dash:

```bash
pip install openclaw-dash
```

For full functionality, also install:

```bash
pip install pip-audit safety  # Python security scanning
gh auth login                  # GitHub CLI for PR operations
```

## Usage

Tools can be invoked:

1. **Via CLI** — Run directly from terminal
2. **Via Dashboard** — Integrated into TUI panels
3. **Via Python API** — Import and use programmatically

See **[TOOLS.md](TOOLS.md)** for detailed documentation.
