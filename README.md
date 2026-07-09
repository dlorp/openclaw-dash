# hermes-dash

[![Version](https://img.shields.io/badge/version-0.5.0-ff9500)](https://github.com/dlorp/hermes-dash/releases)
[![License](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-ff9500)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-ff9500)](https://www.python.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/dlorp/hermes-dash/ci.yml?label=CI&color=ff9500)](https://github.com/dlorp/hermes-dash/actions)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-ff9500)](https://github.com/dlorp/hermes-dash)

TUI dashboard for [Hermes Agent](https://github.com/dlorp/hermes-dash) monitoring. Real-time visibility into your agent pipeline, knowledge vault, sessions, cron jobs, and system health — all from the terminal.

## What It Does

hermes-dash monitors the full Hermes Agent stack:

- **Gateway** — connection status, context usage, uptime
- **Sessions** — active sessions, token usage, model per session
- **Agents** — agent status, pipeline health, running tasks
- **Knowledge Vault** — 3700+ entries, domain count, research queue depth, pipeline status
- **Cron Jobs** — scheduled tasks, last run, success/failure
- **Repositories** — git status, branch info, CI state across HDLS projects
- **Activity** — recent commits, PRs, releases across monitored repos
- **System** — CPU, memory, disk, network (when not in bare mode)

## The Vault Differentiator

Nobody else has a 3700+ entry knowledge graph with 9 autonomous agents feeding it. hermes-dash surfaces that:

- **Entry count** — total markdown entries in the knowledge vault
- **Domain count** — active knowledge domains
- **Research queue depth** — pending vs resolved research items
- **Pipeline status** — ready / running / blocked tasks across the agent fleet

## Quick Start

```bash
git clone https://github.com/dlorp/hermes-dash.git
cd hermes-dash
pip install -e .
hermes-dash
```

No config needed for the demo:

```bash
hermes-dash --demo
```

## Bare Mode

For new HDLS deployments or minimal installs, use `--bare`:

```bash
hermes-dash --bare
```

Bare mode strips the dashboard to core HDLS panels only:

- Gateway, Sessions, Agents, Repos, Activity, Cron, Knowledge Vault

Disabled in bare mode: Alerts, Metrics, Security, Logs, Resources, Channels, Metric Boxes, MQTT sinks.

## Configuration

Config lives at `~/.config/hermes-dash/config.toml`:

```toml
[theme]
name = "phosphor"

[display]
show_resources = true
show_notifications = true

[models]
custom_paths = ["/opt/models"]
```

## CLI Commands

```bash
hermes-dash                    # Launch TUI
hermes-dash --demo             # Demo mode (no gateway needed)
hermes-dash --bare             # Minimal HDLS-only panels
hermes-dash --skip-gateway     # Skip gateway checks
hermes-dash --status           # Quick text status
hermes-dash --json             # JSON output
hermes-dash security           # Security audit
hermes-dash models             # List available models
hermes-dash collectors         # Collector health stats
hermes-dash export             # Export dashboard data
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh all panels |
| `t` | Cycle theme |
| `f` | Jump to any panel |
| `s` | Settings |
| `Ctrl+P` | Command palette |
| `/` or `i` | Focus input pane |

See [Usage](docs/Usage.md) for the full list.

## Documentation

| Document | Description |
|----------|-------------|
| [Installation](docs/INSTALLATION.md) | Docker, source install, pipx |
| [Configuration](docs/CONFIGURATION.md) | Plugin setup, layout, themes |
| [Usage](docs/Usage.md) | Commands and keyboard shortcuts |
| [Architecture](docs/ARCHITECTURE.md) | How the plugin engine works |
| [Widgets](docs/WIDGETS.md) | Panel types and options |
| [Development](docs/DEVELOPMENT.md) | Writing new plugins |
| [Tools](docs/TOOLS.md) | Standalone CLI utilities |

## Tech Stack

Python 3.10+, [Textual](https://textual.textualize.io/) for the TUI framework, [Rich](https://rich.readthedocs.io/) for terminal rendering. No browser, no JavaScript, no external services.

## Contributing

```bash
pip install -e ".[dev]"
pytest
```

See [Development Guide](docs/DEVELOPMENT.md) for how to write plugins.

## License

PolyForm Noncommercial 1.0.0. See [LICENSE](LICENSE).
