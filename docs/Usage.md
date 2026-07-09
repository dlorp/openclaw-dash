# Usage

Command reference and keyboard shortcuts for hermes-dash.

## Commands

```bash
hermes-dash                      # Launch TUI
hermes-dash --status             # Text status report
hermes-dash --json               # JSON output
hermes-dash --demo               # Demo mode with mock data
hermes-dash --config /path       # Custom config file
hermes-dash --list-plugins       # Show installed plugins
hermes-dash --version            # Version info
hermes-dash --config-check       # Validate config without running
```

## Keyboard Shortcuts

### Navigation

| Key | Action |
|-----|--------|
| `q` | Quit |
| `h` or `?` | Toggle help panel |
| `Tab` | Next panel |
| `Shift+Tab` | Previous panel |
| `f` | Jump mode (focus any panel by letter) |

### Actions

| Key | Action |
|-----|--------|
| `r` | Refresh all panels |
| `t` | Cycle theme (dark / light / phosphor) |
| `Enter` | Toggle panel collapse |
| `Ctrl+[` | Collapse all panels |
| `Ctrl+]` | Expand all panels |
| `x` | Toggle resources panel |
| `s` | Open settings screen |
| `Ctrl+P` | Command palette |

### Jump Mode

Press `f` to enter jump mode. Each panel gets a letter label:

```
[a] Server Health    [b] API Latency
[c] Database         [d] Signups
```

Press the letter to focus that panel. Press `Escape` to exit jump mode.

## Command Palette

Press `Ctrl+P` to open the command palette. Type to filter:

- Refresh all panels
- Cycle theme
- Toggle panel collapse
- Export metrics to JSON
- Show/hide specific panels

Press `Enter` to execute, `Escape` to close.

## Themes

Three built-in themes:

| Theme | Description |
|-------|-------------|
| `dark` | Default dark colors |
| `light` | Light background |
| `phosphor` | Amber CRT aesthetic |

Cycle with `t` or set in config:

```yaml
theme:
  name: phosphor
```

The phosphor theme uses amber (#ff9500) on near-black to mimic old CRT monitors.

## Settings Screen

Press `s` to open settings. Tab through sections:

- **General** - Refresh interval, log level
- **Plugins** - Enable/disable individual plugins
- **Appearance** - Theme selection
- **Keybinds** - View shortcuts (custom keybinds planned)
- **Data Sources** - View configured sources

Changes in the settings screen are temporary. Edit `config.yaml` for permanent changes.

## Status Mode

For scripting and automation:

```bash
# Quick status
hermes-dash --status

# JSON for processing
hermes-dash --json | jq '.plugins[] | select(.status == "error")'

# Specific plugin only
hermes-dash --status --plugin web-server
```

JSON output schema:

```json
{
  "timestamp": 1234567890,
  "plugins": [
    {
      "name": "web-server",
      "status": "ok",
      "metrics": [
        {"name": "cpu", "value": 45.2, "unit": "%"}
      ]
    }
  ]
}
```

## Demo Mode

Run without any configuration:

```bash
hermes-dash --demo
```

Uses mock data to demonstrate widgets and layout. Useful for:
- Testing terminal compatibility
- Exploring widget types
- Screenshots and demos

## Tips

**Small terminals:** Collapse panels with `Enter` or `Ctrl+[` to focus on specific metrics.

**Many plugins:** Use jump mode (`f`) to quickly navigate between panels.

**Scripting:** Combine `--json` with `jq` for custom alerting or logging.

**Performance:** If the UI feels sluggish, increase `refresh_interval` in config or disable unused plugins.
