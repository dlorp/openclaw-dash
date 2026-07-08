# Architecture Overview

openclaw-dash is a plugin-based monitoring cockpit. The architecture separates data acquisition (plugins), processing (collectors), and presentation (widgets).

## High-Level Design

```
┌────────────────────────────────────────────────────────────────┐
│                        TUI Application                          │
│                         (app.py)                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Textual Framework                      │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │  │
│  │  │   Widgets   │ │   Themes    │ │   Commands  │        │  │
│  │  │ (widgets/)  │ │ (themes.py) │ │(commands.py)│        │  │
│  │  └──────┬──────┘ └─────────────┘ └─────────────┘        │  │
│  │         │                                                │  │
│  │         ▼                                                │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │                   Collectors                         │ │  │
│  │  │  system.py | api.py | database.py | custom.py | ... │ │  │
│  │  └──────────────────────────┬──────────────────────────┘ │  │
│  └─────────────────────────────┼────────────────────────────┘  │
│                                │                                │
└────────────────────────────────┼────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                      Plugin Engine                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │   SSH    │ │  HTTP    │ │ Database │ │  Custom  │         │
│  │  Agent   │ │   API    │ │  Health  │ │   API    │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
└────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. CLI Entry Point (`cli.py`)

```bash
openclaw-dash              # Launch TUI
openclaw-dash --status     # Quick text status
openclaw-dash --json       # JSON output
openclaw-dash --demo       # Demo mode with mock data
```

### 2. Main Application (`app.py`)

The Textual `App` subclass that orchestrates the TUI:
- **Compose**: Builds the widget tree from config
- **Key bindings**: Keyboard shortcuts for navigation
- **Refresh loop**: Periodic updates from all plugins
- **Responsive layout**: Adapts to terminal size

### 3. Plugin Engine

The core differentiator. Plugins implement three functions:

```python
class DataSourcePlugin:
    def acquire(self) -> RawData:
        """Fetch raw data from the source."""
        pass

    def parse(self, raw: RawData) -> list[Metric]:
        """Convert raw data to structured metrics."""
        pass

    def push(self, metrics: list[Metric]) -> None:
        """Send metrics to the dashboard core."""
        pass
```

Any service that can implement these three functions becomes a plugin. The engine handles scheduling, error recovery, and metric normalization.

### 4. Collectors

Collectors sit between plugins and widgets. They:
- Poll plugins at configured intervals
- Buffer and batch metrics
- Handle connection failures gracefully
- Expose metrics via WebSocket/SSE to the frontend

### 5. Widgets

Widgets render metrics in the terminal. Supported types:
- **Sparkline**: Mini time-series in a single line
- **Time-series**: Full chart with axes
- **Gauge**: Single-value with threshold coloring
- **Bar**: Comparative values
- **Table**: Structured data
- **Heatmap**: Density visualization

### 6. Themes

Terminal color themes. Built-in: dark, light, phosphor (amber CRT aesthetic). Custom themes via YAML.

## Data Flow

```
Plugin.acquire() → RawData
       │
       ▼
Plugin.parse() → list[Metric]
       │
       ▼
Collector.push() → Buffer
       │
       ▼
WebSocket/SSE → Widget.render() → Terminal Display
```

## Design Principles

1. **Plugin-first**: Everything is a plugin. Adding a new data source means writing a plugin, not modifying core code.
2. **Terminal-native**: No browser required. Runs in any terminal with 256-color support.
3. **Lightweight**: Minimal dependencies. Single binary deployment possible.
4. **Real-time**: WebSocket/SSE for live updates. No page refreshes.
5. **Configurable**: YAML for layout, plugins, and themes. No code changes for common customizations.

## Directory Structure

```
openclaw-dash/
├── src/openclaw_dash/
│   ├── app.py              # Main TUI application
│   ├── cli.py              # CLI entry point
│   ├── commands.py         # Keyboard commands
│   ├── config.py           # Configuration loader
│   ├── themes.py           # Theme definitions
│   ├── collectors/         # Data collectors
│   ├── widgets/            # UI widgets
│   ├── tools/              # Standalone utilities
│   ├── services/           # Gateway client, services
│   ├── metrics/            # Metric definitions
│   └── security/           # Security audit tools
├── docs/                   # Documentation
├── tests/                  # Test suite
└── scripts/                # Build/deploy scripts
```
