# openclaw-dash

![Version](https://img.shields.io/badge/version-0.4.0-blue)
[![License](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/dlorp/openclaw-dash/ci.yml?label=CI)](https://github.com/dlorp/openclaw-dash/actions)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)](https://github.com/dlorp/openclaw-dash)

A lightweight, customizable monitoring cockpit for open source projects, personal services, and small business systems. Plugin-based data sources, real-time terminal display, zero browser required.

## Why openclaw-dash?

Most monitoring tools are either heavy (Grafana, Datadog) or too minimal to be useful. openclaw-dash sits in the middle: plugin-based data sources, real-time updates, YAML config, and a clean TUI that runs in your terminal.

**The plugin architecture is the differentiator.** You have 10 services. Each exposes metrics differently — SSH for server health, HTTP endpoints for API status, database connections for query performance, custom APIs for business metrics. openclaw-dash plugins normalize them all into one real-time cockpit view.

## Quick Start

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
openclaw-dash
```

Try the demo without plugins: `openclaw-dash --demo`

## Config

Create `~/.config/openclaw-dash/config.yaml`:

```yaml
plugins:
  - name: system
    type: ssh-agent
    host: my-server
    metrics: [cpu, memory, disk]

  - name: api-health
    type: http-api
    url: https://myapi.com/health
    interval: 30s

  - name: db
    type: db-health
    connection: postgresql://localhost:5432/mydb
```

See [Configuration Guide](docs/CONFIGURATION.md) for all plugin types and layout options.

## Docs

- [Installation](docs/INSTALLATION.md) — Docker, from source, pipx
- [Configuration](docs/CONFIGURATION.md) — Plugins, layout, themes
- [Usage](docs/Usage.md) — Commands, keyboard shortcuts, settings
- [Architecture](docs/ARCHITECTURE.md) — Plugin engine, data flow, design
- [Widgets](docs/WIDGETS.md) — Panel types (sparkline, time-series, gauge, bar, table, heatmap)
- [Development](docs/DEVELOPMENT.md) — Writing plugins, contributing
- [Tools](docs/TOOLS.md) — Standalone utilities (audit, changelog, PR tools, repo scanner)

## Built With

Python 3.10+, [Textual](https://textual.textualize.io/) for the TUI, [Rich](https://rich.readthedocs.io/) for terminal rendering. Plugin engine is pure Python.

## Contributing

```bash
pip install -e ".[dev]"
pytest
```

New plugins welcome. See [Development Guide](docs/DEVELOPMENT.md).

## License

PolyForm Noncommercial 1.0.0. See [LICENSE](LICENSE).
