# Configuration Guide

openclaw-dash stores user preferences in a TOML config file and auto-discovers your OpenClaw environment.

## Config File Location

```
~/.config/openclaw-dash/config.toml
```

The file is created automatically when you first change a setting (theme, etc.).

## Configuration Options

### Full Example

```toml
# Theme: "dark", "light", or "hacker"
theme = "dark"

# Auto-refresh interval in seconds (minimum: 5)
refresh_interval = 30

# Show toast notifications for events
show_notifications = true

# Show the system resources panel (CPU, memory, disk, network)
show_resources = true

# Panels to start collapsed (by panel ID)
collapsed_panels = ["activity-panel", "channels-panel"]
```

### Options Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `theme` | string | `"dark"` | Color theme: `dark`, `light`, or `hacker` |
| `refresh_interval` | integer | `30` | Seconds between auto-refresh cycles |
| `show_notifications` | boolean | `true` | Show toast notifications |
| `show_resources` | boolean | `true` | Display system resources panel |
| `collapsed_panels` | array | `[]` | Panel IDs to start collapsed |

## Themes

Three built-in themes with OpenClaw brand colors:

### Dark (Default)
Best for most environments. Easy on the eyes with high contrast.

```toml
theme = "dark"
```

### Light
For bright environments or daytime use.

```toml
theme = "light"
```

### Hacker
Matrix-inspired green-on-black theme.

```toml
theme = "hacker"
```

**Cycle themes:** Press `t` in the dashboard to cycle through themes. Your choice is saved automatically.

### Theme Colors

The OpenClaw brand palette:

| Color | Hex | Usage |
|-------|-----|-------|
| Granite Gray | `#636764` | Borders, muted elements |
| Dark Orange | `#FB8B24` | Warnings, important actions |
| Titanium Yellow | `#F4E409` | Highlights, focus states |
| Medium Turquoise | `#50D8D7` | Success, online status |
| Royal Blue Light | `#3B60E4` | Primary, links |

## Panel Configuration

### Collapsing Panels

Collapse panels to save space. Press `Enter` on a focused panel to toggle, or configure defaults:

```toml
# Start these panels collapsed
collapsed_panels = [
    "activity-panel",
    "channels-panel",
    "cron-panel"
]
```

**Panel IDs:**
- `gateway-panel` — Gateway status
- `task-panel` — Current task
- `alerts-panel` — Active alerts
- `repos-panel` — Repository health
- `activity-panel` — Activity log
- `cron-panel` — Scheduled jobs
- `sessions-panel` — Active sessions
- `agents-panel` — Sub-agents
- `channels-panel` — Messaging channels
- `metrics-panel` — Cost and performance
- `security-panel` — Security audit
- `logs-panel` — Gateway logs
- `resources-panel` — System resources

### Hiding the Resources Panel

Toggle with `x` key, or configure:

```toml
show_resources = false
```

## Refresh Behavior

### Auto-Refresh

```toml
# Refresh every 30 seconds (default)
refresh_interval = 30

# More aggressive for active monitoring
refresh_interval = 10

# Conservative for lower resource use
refresh_interval = 60
```

### Watch Mode

Launch with `--watch` for aggressive 5-second refresh:

```bash
openclaw-dash --watch
```

### Manual Refresh

Press `r` to refresh all panels immediately.

## Auto-Discovery

The dashboard automatically finds:

| Resource | Default Location | Override |
|----------|------------------|----------|
| OpenClaw Gateway | `localhost:3000` | `OPENCLAW_GATEWAY_URL` env var |
| Repositories | `~/repos/` | — |
| Workspace | `~/.openclaw/workspace/` | `OPENCLAW_WORKSPACE` env var |
| Config | `~/.config/openclaw-dash/` | `--config` flag |

### Environment Variables

```bash
# Custom gateway URL
export OPENCLAW_GATEWAY_URL="http://localhost:4000"

# Custom workspace
export OPENCLAW_WORKSPACE="/path/to/workspace"
```

## Demo Mode

No OpenClaw gateway? The dashboard works standalone with simulated data for UI exploration:

```bash
# The dashboard auto-detects when gateway is offline
openclaw-dash
```

In demo mode:
- Gateway panel shows "OFFLINE"
- Metrics use placeholder data
- All UI features still work

## Programmatic Configuration

Use the config module in Python scripts:

```python
from openclaw_dash.config import load_config, Config

# Load existing config
config = load_config()
print(f"Current theme: {config.theme}")

# Modify and save
config.update(theme="hacker", refresh_interval=15)

# Create fresh config
new_config = Config(
    theme="light",
    refresh_interval=60,
    show_notifications=False
)
new_config.save()
```

## Responsive Layout

The dashboard adapts to terminal size:

| Width | Behavior |
|-------|----------|
| ≥100 cols | Full layout, all panels |
| <100 cols | Hide less-critical panels (channels, security, metrics) |
| <80 cols | Minimum supported, basic layout |

Resize your terminal to see the responsive behavior.

## Keyboard Shortcuts for Config

| Key | Action |
|-----|--------|
| `t` | Cycle theme (saves automatically) |
| `x` | Toggle resources panel (saves automatically) |
| `Enter` | Toggle focused panel collapse (saves automatically) |
| `Ctrl+[` | Collapse all panels |
| `Ctrl+]` | Expand all panels |

## Resetting Configuration

Delete the config file to reset to defaults:

```bash
rm ~/.config/openclaw-dash/config.toml
```

## Next Steps

- [Widgets](WIDGETS.md) — Detailed guide to each panel
- [Development](DEVELOPMENT.md) — Create custom themes and widgets
