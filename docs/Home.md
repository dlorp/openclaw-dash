# openclaw-dash

Welcome to the **openclaw-dash** documentation.

A lightweight, customizable monitoring cockpit for open source projects, personal services, and small business systems. Plugin-based data sources, real-time updates, terminal-native.

## The Plugin Architecture

openclaw-dash is built around one idea: **any data source that can provide standardized data becomes a dashboard panel.**

You have 10 services. Each exposes metrics differently — SSH for server health, HTTP endpoints for API status, database connections for query performance, custom APIs for business metrics. openclaw-dash plugins normalize them all into one real-time cockpit view.

```
┌─────────────────────────────────────────────┐
│              Your Services                   │
│  SSH  │  HTTP API  │  Database  │  Custom   │
└───────┴────────────┴───────────┴────────────┘
                    │
          ┌─────────▼──────────┐
          │   Plugin Engine    │
          │  (acquire/parse/   │
          │      push)         │
          └─────────┬──────────┘
                    │
          ┌─────────▼──────────┐
          │   Real-Time TUI    │
          │  (WebSocket/SSE)   │
          └────────────────────┘
```

## Quick Links

### Getting Started
- **[Installation](INSTALLATION.md)** — Docker or from source
- **[Configuration](CONFIGURATION.md)** — Plugin setup, YAML config
- **[Usage](Usage.md)** — Commands, keyboard shortcuts

### Plugin Development
- **[Architecture](ARCHITECTURE.md)** — How the plugin engine works
- **[Widgets Reference](WIDGETS.md)** — Panel types and layout

### Reference
- **[Tools](TOOLS.md)** — Standalone utilities (audit, changelog, repo scanner)
- **[Development Guide](DEVELOPMENT.md)** — Contributing, writing plugins

## Quick Install

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
openclaw-dash
```

Or with Docker:

```bash
docker compose up -d
```

## License

[PolyForm NonCommercial 1.0.0](../LICENSE) — free for personal and non-commercial use
