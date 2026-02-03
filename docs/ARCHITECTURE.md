# Architecture Overview

This document describes the architecture and design decisions of openclaw-dash.

## High-Level Design

```
┌────────────────────────────────────────────────────────────────────┐
│                         TUI Application                            │
│                          (app.py)                                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     Textual Framework                         │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │  │
│  │  │   Widgets   │ │   Themes    │ │   Commands  │             │  │
│  │  │ (widgets/)  │ │ (themes.py) │ │(commands.py)│             │  │
│  │  └──────┬──────┘ └─────────────┘ └─────────────┘             │  │
│  │         │                                                     │  │
│  │         ▼                                                     │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │                    Collectors                            │ │  │
│  │  │  gateway.py | sessions.py | repos.py | alerts.py | ...   │ │  │
│  │  └──────────────────────────┬──────────────────────────────┘ │  │
│  └─────────────────────────────┼────────────────────────────────┘  │
│                                │                                    │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                       External Sources                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ OpenClaw │ │  GitHub  │ │   File   │ │  System  │              │
│  │ Gateway  │ │    CLI   │ │  System  │ │  (psutil)│              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
└────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. CLI Entry Point (`cli.py`)

The main entry point for the application:

```bash
openclaw-dash              # Launch TUI
openclaw-dash --status     # Quick text status
openclaw-dash --json       # JSON output
openclaw-dash --demo       # Demo mode with mock data
```

Handles argument parsing and mode selection before launching the TUI.

### 2. Main Application (`app.py`)

The Textual `App` subclass that orchestrates the entire TUI:

- **Compose**: Builds the widget tree
- **Key bindings**: Handles keyboard shortcuts
- **Refresh loop**: Periodically updates all panels
- **Responsive layout**: Adapts to terminal size

Key responsibilities:
- Panel layout and navigation
- Theme switching
- Jump mode (press `f` then a letter)
- Command palette integration

### 3. Collectors (`collectors/`)

Data fetching modules that abstract external sources:

| Collector | Source | Data |
|-----------|--------|------|
| `gateway.py` | OpenClaw CLI | Gateway health, context usage |
| `sessions.py` | OpenClaw CLI | Active sessions, burn rates |
| `repos.py` | `gh` CLI, files | PRs, CI status, TODOs |
| `alerts.py` | Multiple | Aggregated alerts |
| `channels.py` | Config files | Messaging channel status |
| `cron.py` | OpenClaw config | Scheduled jobs |
| `resources.py` | `psutil` | CPU, memory, disk, network |
| `logs.py` | Log files | Gateway log entries |
| `agents.py` | OpenClaw CLI | Sub-agent status |
| `activity.py` | Workspace files | Recent activity |
| `billing.py` | Provider APIs | Real cost data |

**Design principle**: Collectors return dictionaries with either data or an `"error"` key:

```python
def collect() -> dict[str, Any]:
    try:
        data = fetch_data()
        return {"items": data, "count": len(data)}
    except Exception as e:
        return {"error": str(e)}
```

### 4. Widgets (`widgets/`)

Textual widgets that display collector data:

| Widget | Display |
|--------|---------|
| `MetricBoxesBar` | Compact KPI header |
| `SessionsPanel` | Sessions with progress bars |
| `AlertsPanel` | Color-coded alert list |
| `ResourcesPanel` | System resource meters |
| `SecurityPanel` | Security audit results |
| `LogsPanel` | Scrollable log viewer |
| `HelpScreen` | Modal help overlay |

**Design principle**: Widgets fetch data in `refresh_data()` method:

```python
class MyPanel(Static):
    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="content")

    def refresh_data(self) -> None:
        data = my_collector.collect()
        content = self.query_one("#content", Static)
        content.update(format_data(data))
```

### 5. Visual Primitives (`widgets/ascii_art.py`)

Reusable ASCII art components:

```python
from openclaw_dash.widgets.ascii_art import (
    progress_bar,      # ████████░░░░ 75%
    mini_bar,          # ███░░░
    status_indicator,  # ✓ Online
    sparkline,         # ▁▃▅▂▄█▃
    separator,         # ────────────
    trend_indicator,   # ↑ or ↓
)
```

### 6. Themes (`themes.py`)

Color themes using Textual's theme system:

```python
DARK_THEME = Theme(
    name="dark",
    primary="#50D8D7",
    secondary="#3B60E4",
    background="#1a1a1a",
    # ...
)
```

Three built-in themes:
- **Dark** — Default, easy on eyes
- **Light** — High contrast
- **Hacker** — Green terminal aesthetic

### 7. Configuration (`config.py`)

User preferences stored in `~/.config/openclaw-dash/config.toml`:

```toml
theme = "dark"
refresh_interval = 30
show_resources = true
show_notifications = true
collapsed_panels = []
```

Config is loaded on startup and saved on changes.

### 8. Commands (`commands.py`)

Command palette provider for `Ctrl+P`:

```python
class DashboardCommands(Provider):
    async def search(self, query: str) -> Hits:
        # Return matching commands
        yield Hit("Refresh All", self.refresh_all)
        yield Hit("Export JSON", self.export_json)
```

## Data Flow

### Startup

```
main() → parse_args() → load_config() → App().run()
                                            │
                                            ▼
                                       compose()
                                            │
                                            ▼
                                    Initial refresh_data()
```

### Refresh Cycle

```
Timer tick (30s) or manual 'r' key
           │
           ▼
    _auto_refresh()
           │
           ├─→ gateway.collect() → GatewayPanel.refresh_data()
           ├─→ sessions.collect() → SessionsPanel.refresh_data()
           ├─→ repos.collect() → ReposPanel.refresh_data()
           └─→ ... (all panels)
```

### Error Handling

Collectors catch exceptions and return error dicts. Widgets display errors gracefully:

```
collect() raises Exception
         │
         ▼
return {"error": str(e)}
         │
         ▼
Widget shows: "✗ Error: {message}"
```

## Module Dependencies

```
cli.py
  └── app.py
        ├── config.py
        ├── themes.py
        ├── commands.py
        ├── widgets/
        │     ├── __init__.py (exports all widgets)
        │     ├── ascii_art.py (no deps)
        │     ├── sessions.py → collectors/sessions.py
        │     ├── alerts.py → collectors/alerts.py
        │     └── ...
        └── collectors/
              ├── gateway.py → openclaw_cli.py
              ├── sessions.py → openclaw_cli.py
              └── ...
```

**Circular imports**: Avoided by lazy imports within functions.

## Demo Mode

`--demo` flag enables mock data for testing/screenshots:

```python
from openclaw_dash.demo import is_demo_mode, mock_gateway_status

def collect() -> dict[str, Any]:
    if is_demo_mode():
        return mock_gateway_status()
    # ... real data collection
```

## Extension Points

### Adding a New Widget

1. Create `widgets/my_widget.py`
2. Create `collectors/my_collector.py`
3. Import in `app.py` and add to compose
4. Add to `PANEL_ORDER` for navigation
5. Add refresh call in `_auto_refresh()`
6. Export in `widgets/__init__.py`

See [Development Guide](DEVELOPMENT.md) for detailed steps.

### Adding a New Theme

1. Define `Theme` in `themes.py`
2. Add to `THEMES` list
3. Theme cycles with `t` key

### Adding a Command

1. Add method to `DashboardCommands` in `commands.py`
2. Yield `Hit` in `search()` method

## Performance Considerations

- **Refresh interval**: Default 30s, configurable
- **Lazy loading**: Collectors only run when needed
- **Caching**: `@lru_cache` for expensive operations
- **Error isolation**: One failed collector doesn't crash others
- **Responsive hiding**: Less-critical panels hide on narrow terminals

## Security Model

- **No network servers**: Dashboard is local-only
- **Read-only by default**: Collectors only read data
- **Sensitive data**: Masked in display, optional in export
- **Config files**: User-owned, standard XDG paths
