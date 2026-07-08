# openclaw-dash

[![Version](https://img.shields.io/badge/version-0.4.0-ff9500)](https://github.com/dlorp/openclaw-dash/releases)
[![License](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-ff9500)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-ff9500)](https://www.python.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/dlorp/openclaw-dash/ci.yml?label=CI&color=ff9500)](https://github.com/dlorp/openclaw-dash/actions)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-ff9500)](https://github.com/dlorp/openclaw-dash)

openclaw-dash is a terminal-based monitoring dashboard. It collects metrics from multiple data sources (servers, APIs, databases, custom endpoints) and displays them in a single real-time TUI panel. Think Grafana, but lightweight and terminal-native.

## What It Does

You have multiple services running across different hosts and protocols. openclaw-dash unifies them into one dashboard:

- **Server health** via SSH (CPU, memory, disk, network)
- **API status** via HTTP polling (latency, uptime, error rates)
- **Database health** via direct connections (pool usage, slow queries)
- **Custom metrics** via any HTTP endpoint (business data, internal APIs)

Each data source is a plugin. Write one Python class, get a dashboard panel. Three methods: acquire data, parse it, push it to the display.

## Quick Start

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
openclaw-dash
```

No config needed for the demo:

```bash
openclaw-dash --demo
```

## Configuration

Create `~/.config/openclaw-dash/config.yaml`:

```yaml
plugins:
  - name: web-server
    type: ssh-agent
    host: 192.168.1.100
    metrics: [cpu, memory, disk]

  - name: api
    type: http-api
    url: https://api.example.com/health
    interval: 15s

  - name: database
    type: db-health
    connection: postgresql://localhost:5432/mydb
```

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

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh all panels |
| `t` | Cycle theme |
| `f` | Jump to any panel |
| `s` | Settings |
| `Ctrl+P` | Command palette |

See [Usage](docs/Usage.md) for the full list.

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
