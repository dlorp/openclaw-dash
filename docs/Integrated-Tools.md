# Integrated Tools

openclaw-dash bundles standalone utilities for repository management, security auditing, and development workflows.

See [TOOLS.md](TOOLS.md) for full reference.

## Overview

| Tool | Purpose |
|------|---------|
| `audit` | Security vulnerability scanning |
| `changelog` | Generate changelogs from git |
| `dep-shepherd` | Dependency management |
| `pr-create` | Create structured pull requests |
| `pr-describe` | Analyze pull requests |
| `pr-tracker` | Track PRs across repositories |
| `repo-scanner` | Scan for TODOs and patterns |
| `smart-todo` | Intelligent TODO detection |
| `status` | Quick repository status |
| `version-bump` | Semantic version management |

## Usage

As CLI commands:

```bash
openclaw-dash audit /path/to/repo
openclaw-dash changelog /path/to/repo
openclaw-dash status /path/to/repo
```

As standalone modules:

```bash
python -m openclaw_dash.tools.audit /path/to/repo
python -m openclaw_dash.tools.changelog /path/to/repo
```

## Plugin Architecture

Tools follow the same plugin pattern as data sources. Each tool is a module in `src/openclaw_dash/tools/` that implements a standard interface.

This means:
- Tools are independently testable
- New tools can be added without modifying core code
- Tools work standalone or integrate with the dashboard

See [Development Guide](DEVELOPMENT.md) for writing tool plugins.
