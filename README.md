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

**Use it for:**
- Server health (CPU, memory, disk, network)
- Service status (HTTP endpoints, database connections, API health)
- Business metrics (registrations, conversions, order flow)
- Infrastructure monitoring across multiple hosts

## Quick Start

### From Source

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
openclaw-dash
```

### Demo Mode

No plugins configured? Try the demo:

```bash
openclaw-dash --demo
```

### Minimal Config

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

## Plugin System

openclaw-dash uses a plugin-based data source architecture. Any service that can provide standardized data can become a dashboard panel.

**Built-in plugins:**

| Plugin | Description |
|--------|-------------|
| `ssh-agent` | Collect CPU, memory, disk I/O via SSH |
| `http-api` | Poll HTTP endpoints for status codes and latency |
| `db-health` | Check database connections, slow queries, pool usage |
| `business-api` | Pull custom metrics from internal APIs |

**Write your own:** Implement the data source interface (acquire, parse, push) and drop it in the plugins directory. See [Development Guide](docs/DEVELOPMENT.md) for the plugin interface.

## Architecture

Built with Python 3.10+, [Textual](https://textual.textualize.io/) for the TUI framework, and [Rich](https://rich.readthedocs.io/) for terminal rendering. The plugin engine is pure Python — no external services required.

```
┌────────────────────────────────────────────────────────────────┐
│                        TUI Application                          │
│                    (Textual + Rich)                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Collectors                              │  │
│  │  system.py | api.py | database.py | custom.py | ...     │  │
│  └──────────────────────────┬───────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   Plugin Engine    │
                    │  (acquire/parse/   │
                    │      push)         │
                    └─────────┬──────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
       ┌────▼───┐      ┌─────▼────┐      ┌────▼───┐
       │  SSH   │      │  HTTP    │      │   DB   │
       │ Agent  │      │   API    │      │ Health │
       └────────┘      └──────────┘      └────────┘
```

## Layout Configuration

Panel layout is defined in YAML:

```yaml
layout:
  rows:
    - panels:
        - title: System Health
          source: system
          chart: sparkline
        - title: API Latency
          source: api-health
          chart: time-series
    - panels:
        - title: Database
          source: db
          chart: gauge
```

Supported chart types: `sparkline`, `time-series`, `gauge`, `bar`, `table`, `heatmap`.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh all panels |
| `t` | Cycle theme (dark/light/phosphor) |
| `f` | Jump mode (focus any panel) |
| `Ctrl+P` | Command palette |
| `s` | Settings |

## Contributing

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e ".[dev]"
pytest
```

Suggested areas for contribution:
- New data source plugins (Prometheus, MQTT, home automation)
- Additional chart types
- Alert rules and notification channels
- Dashboard export/import

See [Development Guide](docs/DEVELOPMENT.md) for plugin development.

## License

PolyForm Noncommercial 1.0.0. See [LICENSE](LICENSE) for details.
