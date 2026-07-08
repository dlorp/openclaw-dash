# Architecture

openclaw-dash separates data acquisition (plugins), collection (buffers), and presentation (widgets). The TUI layer never talks directly to data sources.

## Overview

```
                    Data Flow
    ┌─────────────────────────────────────────────────────┐
    │                                                      │
    │   ┌──────────┐     ┌──────────┐     ┌──────────┐   │
    │   │  Plugin  │────▶│ Collector│────▶│  Widget  │   │
    │   │ (source) │     │ (buffer) │     │ (render) │   │
    │   └──────────┘     └──────────┘     └──────────┘   │
    │        │                │                │         │
    │   acquire()        batch/poll        textual      │
    │   parse()          reactive          render()      │
    │   push()                                            │
    │                                                      │
    └─────────────────────────────────────────────────────┘
```

## Components

### CLI (`cli.py`)

Entry point. Handles arguments, config loading, dispatches to TUI or command modes.

```bash
openclaw-dash              # Launch TUI
openclaw-dash --status     # Text output
openclaw-dash --json       # JSON for piping
openclaw-dash --demo       # Mock data mode
```

### Main App (`app.py`)

Textual `App` subclass. Orchestrates the widget tree, handles keyboard input, manages the refresh loop.

Key responsibilities:
- Compose widget tree from config
- Bind keyboard shortcuts
- Coordinate periodic updates
- Adapt layout to terminal resize

### Plugin Engine

Plugins implement three methods:

```python
class DataSourcePlugin:
    def acquire(self) -> RawData:
        """Fetch from source."""
        pass

    def parse(self, raw: RawData) -> list[Metric]:
        """Normalize to structured metrics."""
        pass

    def push(self, metrics: list[Metric]) -> None:
        """Send to collector."""
        pass
```

Any source that implements these becomes a plugin. The engine handles scheduling, error recovery, and metric normalization.

Built-in types:
- `ssh-agent` - System metrics over SSH
- `http-api` - Poll HTTP endpoints
- `db-health` - Database connection status
- `business-api` - Custom internal APIs

### Collectors

Sit between plugins and widgets:
- Poll plugins at configured intervals
- Buffer and batch metrics
- Handle connection failures gracefully
- Expose metrics via Textual reactive system

### Widgets

Render metrics in the terminal:

| Type | Lines | Use Case |
|------|-------|----------|
| sparkline | 1-3 | Quick health overview |
| time-series | 5+ | Trends, latency over time |
| gauge | 3 | Single values with thresholds |
| bar | 3-5 | Category comparison |
| table | variable | Structured data |
| heatmap | 5+ | Density patterns |

### Themes

Terminal color schemes. Built-in:
- `dark` - Default
- `light` - For bright terminals
- `phosphor` - Amber CRT aesthetic

Custom themes via YAML color definitions.

## Data Flow Detail

```
1. Plugin.acquire()
   └── Fetch raw data (SSH, HTTP, DB query)

2. Plugin.parse()
   └── Convert to list[Metric]
       Metric: name, value, unit, timestamp, tags

3. Collector.push()
   └── Buffer in circular buffer
       Configurable retention (default: 100 points)

4. Textual reactive update
   └── Widget observes buffer change

5. Widget.render()
   └── Rich renderables to terminal
```

## Design Decisions

**Plugin-first architecture**
Everything is a plugin. Adding a source means writing a plugin, not modifying core code. The interface is intentionally small: three methods.

**Terminal-native**
No browser. No WebSocket. No SSE. Runs in any terminal with 256-color support. Uses Textual's reactive system for live updates.

**Lightweight**
Minimal dependencies. No database required. Single-binary deployment possible with PyInstaller or similar.

**YAML configuration**
No code changes for common customizations. Plugin definitions, layout, and themes all in one file.

## Directory Structure

```
openclaw-dash/
├── src/openclaw_dash/
│   ├── app.py              # Main TUI application
│   ├── cli.py              # CLI entry point
│   ├── commands.py         # Keyboard commands
│   ├── config.py           # YAML config loader
│   ├── themes.py           # Color schemes
│   ├── collectors/         # Metric collectors
│   ├── widgets/            # UI widgets
│   ├── tools/              # Standalone utilities
│   ├── services/           # External service clients
│   ├── metrics/            # Metric type definitions
│   └── security/           # Security audit tools
├── docs/                   # Documentation
├── tests/                  # Test suite
└── scripts/                # Build/deploy scripts
```

## Plugin Lifecycle

```
Config Load
     │
     ▼
Plugin Registry
     │
     ▼
Plugin Init (with config dict)
     │
     ▼
Collector Thread Spawn
     │
     ├───▶ acquire() ──▶ parse() ──▶ push()
     │         │
     │         └── Retry on failure (exponential backoff)
     │
     └───▶ Buffer Update
                │
                ▼
           Textual Reactive
                │
                ▼
           Widget Re-render
```

## Error Handling

Plugins are expected to handle their own errors. Return empty data on failure; the collector will retry with backoff. Widgets show last-known-good data with a staleness indicator.

Connection failures, timeouts, and parse errors are logged at `WARNING` level. The dashboard stays up even if individual plugins fail.
