# Integrated Tools

openclaw-dash bundles several automation tools that work standalone or as part of the dashboard.

## Tool Overview

| Tool | Description |
|------|-------------|
| `repo-scanner` | Repository health metrics (TODOs, tests, PRs) |
| `pr-tracker` | PR status monitoring and merge detection |
| `smart-todo-scanner` | Context-aware TODO categorization |
| `dep-shepherd` | Dependency auditing and updates |
| `pr-describe` | Automated PR description generation |

## repo-scanner

Scans repositories for health metrics:
- TODO count and categorization
- Test coverage
- Open PR count
- CI status

## pr-tracker

Monitors pull requests across your repositories:
- Tracks PR state changes
- Detects merges and closures
- Alerts on review requests

## smart-todo-scanner

Goes beyond simple TODO counting:
- Categorizes by urgency (FIXME, TODO, HACK, XXX)
- Groups by file and module
- Tracks TODO age (when possible via git blame)

## dep-shepherd

Keeps dependencies healthy:
- Audits for known vulnerabilities
- Identifies outdated packages
- Suggests safe upgrade paths

## pr-describe

Generates PR descriptions automatically:
- Analyzes diff content
- Summarizes changes
- Follows conventional commit patterns

---

These tools can be invoked individually via the CLI or are used internally by the dashboard to populate panels.
