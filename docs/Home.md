# OpenClaw Dashboard

Welcome to the **openclaw-dash** documentation! 🎛️

A TUI dashboard for monitoring your [OpenClaw](https://github.com/openclaw/openclaw) ecosystem at a glance.

![Dashboard Screenshot](images/dashboard.svg)

## Quick Links

### Getting Started
- **[Installation](INSTALLATION.md)** — Install via pip, pipx, or from source
- **[Configuration](CONFIGURATION.md)** — Customize themes, refresh rates, panels
- **[Usage](Usage.md)** — Commands, keyboard shortcuts, and CLI options

### Reference
- **[Widgets Reference](WIDGETS.md)** — Every panel explained with examples
- **[Integrated Tools](Integrated-Tools.md)** — Bundled automation tools
- **[Architecture](ARCHITECTURE.md)** — Codebase structure and design

### Contributing
- **[Development Guide](DEVELOPMENT.md)** — Add widgets, run tests, contribute
- **[Contributing Guidelines](../CONTRIBUTING.md)** — How to contribute

## Features at a Glance

| Feature | Description |
|---------|-------------|
| **Gateway Status** | Health, context usage, uptime |
| **Metric Boxes** | Compact KPI bar (status, cost, errors, streak) |
| **Sessions** | Active sessions with context burn rate |
| **Cron Jobs** | Scheduled tasks and their status |
| **Agents** | Sub-agent coordination view |
| **Alerts** | Color-coded severity alerts |
| **Channels** | Messaging channel status |
| **Repos** | Repository health (PRs, CI, TODOs) |
| **Activity** | Recent actions timeline |
| **Metrics** | Cost tracking, performance stats, GitHub streak |
| **Security** | Config scanning, dependency vulnerabilities |
| **Resources** | CPU, memory, disk, network I/O |
| **Logs** | Real-time gateway log viewer |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh all panels |
| `t` | Cycle theme (dark/light/hacker) |
| `h` / `?` | Help panel |
| `Ctrl+P` | Command palette |
| `f` | Jump mode (focus any panel) |
| `Tab` | Next panel |
| `Enter` | Toggle panel collapse |
| `x` | Toggle resources panel |

See [Usage](Usage.md) for the complete list.

## Requirements

- **Python 3.10+** (3.11 or 3.12 recommended)
- **OpenClaw gateway** (optional but recommended)
- **gh CLI** (for GitHub integration features)

## Quick Install

```bash
pip install openclaw-dash
openclaw-dash
```

See [Installation](INSTALLATION.md) for detailed setup instructions.

## License

[PolyForm NonCommercial 1.0.0](../LICENSE) — free for personal and non-commercial use
