# hermes-dash

A terminal-native monitoring cockpit. Plugin-based data sources, real-time updates, no browser required.

## The Plugin Model

hermes-dash is built on one idea: any data source that can provide structured metrics becomes a dashboard panel.

Your services speak different protocols. SSH for system metrics. HTTP for API status. Database connections for query performance. Custom APIs for business KPIs. hermes-dash plugins normalize them all into one live view.

```
    Your Services
    ┌─────┬────────┬───────────┬────────┐
    │ SSH │  HTTP  │ Database  │ Custom │
    └──┬──┴────┬───┴─────┬─────┴───┬────┘
       │       │         │         │
       └───────┴────┬────┴─────────┘
                    │
            ┌───────▼────────┐
            │ Plugin Engine  │
            │  acquire()     │
            │  parse()       │
            │  push()        │
            └───────┬────────┘
                    │
            ┌───────▼────────┐
            │  Terminal TUI  │
            │ Real-time view │
            └────────────────┘
```

## Getting Started

### Installation

```bash
git clone https://github.com/dlorp/hermes-dash.git
cd hermes-dash
pip install -e .
```

Or with Docker:

```bash
docker compose up -d
```

### Quick Start

```bash
# Run demo with mock data
hermes-dash --demo

# Create config and run
mkdir -p ~/.config/hermes-dash
cat > ~/.config/hermes-dash/config.yaml << 'EOF'
plugins:
  - name: localhost
    type: ssh-agent
    host: localhost
    metrics: [cpu, memory, disk]

layout:
  rows:
    - panels:
        - title: System
          source: localhost
          chart: sparkline
EOF

hermes-dash
```

## Documentation

### Setup
- [Installation](INSTALLATION.md) - Docker, pipx, from source
- [Configuration](CONFIGURATION.md) - Plugin setup, YAML config
- [Usage](Usage.md) - Commands, keyboard shortcuts

### Reference
- [Architecture](ARCHITECTURE.md) - How the plugin engine works
- [Widgets](WIDGETS.md) - Panel types and layout
- [Tools](TOOLS.md) - Standalone utilities

### Development
- [Development Guide](DEVELOPMENT.md) - Writing plugins, contributing

## What It Looks Like

```
┌─ Server Health ──────────────┐┌─ API Latency ────────────────┐
│ CPU  ████████████████████ 45%││        ╭────╮                │
│ Mem  ██████████████░░░░░░ 62%││  200ms │    │    ╭──╮        │
│ Disk ████████░░░░░░░░░░░░ 28%││        │    ╭───╯  ╰──╮      │
└──────────────────────────────┘└──────────────────────────────┘
┌─ Database ───────────────────────────────────────────────────┐
│ connections │████████████████████████████████████████│  42   │
│ slow queries│██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   3   │
│ repl lag    │█░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│  12ms │
└──────────────────────────────────────────────────────────────┘
```

Terminal-native. Real-time updates. Keyboard driven.

## License

[PolyForm Noncommercial 1.0.0](../LICENSE) - free for personal and non-commercial use
