# Integrated Tools

openclaw-dash bundles standalone utilities that complement the monitoring cockpit. These tools work independently or as part of the dashboard.

See [TOOLS.md](TOOLS.md) for comprehensive reference.

## Quick Overview

| Tool | Purpose |
|------|---------|
| `audit` | Security audit for repos and configs |
| `changelog` | Generate CHANGELOG.md from git history |
| `dep-shepherd` | Dependency management and vulnerability scanning |
| `pr-create` | Create pull requests with structured descriptions |
| `pr-describe` | Analyze and describe existing pull requests |
| `pr-tracker` | Track PR status across repositories |
| `repo-scanner` | Scan repos for TODOs, issues, and patterns |
| `smart-todo-scanner` | Intelligent TODO detection with context |
| `status` | Quick status report for repos |
| `version-bump` | Semantic version management |

## Usage

All tools are available as CLI commands:

```bash
openclaw-dash audit /path/to/repo
openclaw-dash changelog /path/to/repo
openclaw-dash pr-describe 42
```

Or as standalone scripts:

```bash
python -m openclaw_dash.tools.audit /path/to/repo
```

## Writing Tool Plugins

Tools follow the same plugin architecture as data sources. See [DEVELOPMENT.md](DEVELOPMENT.md) for the plugin interface.
