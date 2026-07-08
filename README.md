# openclaw-dash

[![Version](https://img.shields.io/badge/version-0.4.0-ff9500)](https://github.com/dlorp/openclaw-dash/releases)
[![License](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-ff9500)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-ff9500)](https://www.python.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/dlorp/openclaw-dash/ci.yml?label=CI&color=ff9500)](https://github.com/dlorp/openclaw-dash/actions)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-ff9500)](https://github.com/dlorp/openclaw-dash)

```
    ___    ____  ___   ________       ____    ___    _  _______  ______
   /   |  / __ \/   | / ____/ /      / __ \  /   |  / |/ / __ \/_  __/
  / /| | / / / / /| |/ /   / /      / / / / / /| | /   / / / / / /
 / ___ |/ /_/ / ___ / /___/ /___   / /_/ / / ___ |/   / /_/ / / /
/_/  |_/_____/_/  |_\____/_____/  /_____/ /_/  |_/_/|_/_____/ /_/
```

A terminal-native monitoring cockpit. Plugin architecture for any data source. Real-time TUI, no browser required.

## The Pitch

Grafana is heavy. Terminal dashboards are thin. This sits in the gap.

You have services scattered across SSH hosts, HTTP endpoints, databases, and internal APIs. Each speaks its own protocol. openclaw-dash plugins normalize them into one live view - sparklines, gauges, time-series, all in your terminal.

The plugin system is the point. Write one class, get a panel. Three methods: acquire, parse, push.

## Quick Start

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
openclaw-dash --demo
```

The demo runs mock data. No config needed. Press `q` to quit, `t` to cycle themes.

## Configure

Create `~/.config/openclaw-dash/config.yaml`:

```yaml
plugins:
  - name: server
    type: ssh-agent
    host: prod-01.example.com
    metrics: [cpu, memory, disk]

  - name: api
    type: http-api
    url: https://api.example.com/health
    interval: 30s

  - name: postgres
    type: db-health
    connection: postgresql://localhost:5432/app

layout:
  rows:
    - panels:
        - title: Server Health
          source: server
          chart: sparkline
          height: 3
        - title: API Latency
          source: api
          chart: gauge
          height: 3
    - panels:
        - title: Database
          source: postgres
          chart: time-series
          height: 5

theme:
  name: phosphor    # dark | light | phosphor
```

Run: `openclaw-dash`

## Documentation

- [Installation](docs/INSTALLATION.md) - Docker, pipx, from source
- [Configuration](docs/CONFIGURATION.md) - Plugin types, layout, themes
- [Usage](docs/Usage.md) - Commands, keys, settings
- [Architecture](docs/ARCHITECTURE.md) - Plugin engine, data flow
- [Widgets](docs/WIDGETS.md) - Panel types reference
- [Development](docs/DEVELOPMENT.md) - Writing plugins
- [Tools](docs/TOOLS.md) - Audit, changelog, repo scanner utilities

## Stack

Python 3.10+, [Textual](https://textual.textualize.io/) for the TUI, [Rich](https://rich.readthedocs.io/) for terminal rendering. Plugin engine is pure Python.

## Contributing

```bash
pip install -e ".[dev]"
pytest
```

New plugins welcome. See [Development Guide](docs/DEVELOPMENT.md).

## License

PolyForm Noncommercial 1.0.0. See [LICENSE](LICENSE).
