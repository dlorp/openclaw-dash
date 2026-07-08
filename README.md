# openclaw-dash

![Version](https://img.shields.io/badge/version-0.4.0-blue)
[![License](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/dlorp/openclaw-dash/ci.yml?label=CI)](https://github.com/dlorp/openclaw-dash/actions)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)](https://github.com/dlorp/openclaw-dash)

A lightweight, customizable, real-time monitoring cockpit for open source projects, personal services, and small business systems. See all your key indicators in one view.

## Why openclaw-dash?

Most monitoring tools are either heavy (Grafana, Datadog) or too minimal to be useful. openclaw-dash sits in the middle: plugin-based data sources, real-time updates, YAML config, and a clean TUI interface that runs in your terminal. No browser required, no logs to grep.

**Use it for:**
- Server health (CPU, memory, disk, network)
- Service status (HTTP endpoints, database connections, API health)
- Business metrics (registrations, conversions, order flow)
- Infrastructure monitoring across multiple hosts

## Quick Start

### Docker

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
docker compose up -d
```

### From Source

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
openclaw-dash
```

### Minimal Config

Create a `config.yaml`:

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

openclaw-dash uses a plugin-based data source architecture. Any service that can provide standardized data can become a data source.

**Built-in plugins:**

| Plugin | Description |
|--------|-------------|
| `ssh-agent` | Collect CPU, memory, disk I/O via SSH |
| `http-api` | Poll HTTP endpoints for status codes and latency |
| `db-health` | Check database connections, slow queries, pool usage |
| `business-api` | Pull custom metrics from internal APIs |

**Write your own:** Implement the data source interface (acquire, parse, push) and drop it in the plugins directory. No core changes needed.

## Real-Time Updates

Data streams to the dashboard via WebSocket or Server-Sent Events. No page refreshes. Each plugin defines its own update frequency. The dashboard renders charts using ECharts or Chart.js, depending on your layout config.

## Layout Configuration

Panel layout is defined in YAML. Specify which plugins feed which panels, chart types, and refresh intervals:

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

## Architecture

```
┌─────────────┐     WebSocket/SSE     ┌──────────────┐
│   Frontend  │◄──────────────────────│    Backend    │
│  (React/    │                       │  (Node.js/   │
│   Vue.js)   │                       │    Go)       │
└─────────────┘                       └──────┬───────┘
                                             │
                                    ┌────────▼────────┐
                                    │  Plugin Engine   │
                                    │  (data sources)  │
                                    └────────┬────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                         ┌────▼───┐    ┌─────▼────┐   ┌────▼───┐
                         │ SSH    │    │ HTTP API │   │  DB    │
                         │ Agent  │    │  Plugin  │   │ Health │
                         └────────┘    └──────────┘   └────────┘
```

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

## License

PolyForm Noncommercial 1.0.0. See [LICENSE](LICENSE) for details.
