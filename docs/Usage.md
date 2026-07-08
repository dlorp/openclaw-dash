# Usage

## Basic Commands

```bash
openclaw-dash              # Launch TUI
openclaw-dash --status     # Text status report
openclaw-dash --json       # JSON output
openclaw-dash --demo       # Demo mode with mock data
openclaw-dash --config /path/to/config.yaml  # Custom config
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh all panels |
| `t` | Cycle theme (dark/light/phosphor) |
| `h` / `?` | Help panel |
| `Ctrl+P` | Command palette |
| `f` | Jump mode (focus any panel) |
| `Tab` | Next panel |
| `Shift+Tab` | Previous panel |
| `Enter` | Toggle panel collapse |
| `Ctrl+[` / `Ctrl+]` | Collapse/expand all panels |
| `x` | Toggle resources panel |
| `s` | Settings screen |

## Jump Mode

Press `f` to enter jump mode. Each panel gets a letter label. Press the letter to focus that panel. Press `Escape` to exit jump mode.

## Command Palette

Press `Ctrl+P` to open the command palette. Type to filter commands. Press `Enter` to execute.

Available commands:
- Refresh all panels
- Cycle theme
- Toggle panel collapse
- Export metrics to JSON
- Show/hide specific panels

## Themes

Three built-in themes:
- **dark**: Default dark theme
- **light**: Light background
- **phosphor**: Amber CRT aesthetic

Cycle themes with `t` or set in config:

```yaml
theme:
  name: phosphor
```

## Settings Screen

Press `s` to open the settings screen. Tabbed sections:
- **General**: Refresh interval, log level
- **Tools**: Plugin enable/disable
- **Appearance**: Theme, font size
- **Keybinds**: Custom keyboard shortcuts
- **Models**: Available data sources

## Status Mode

For scripting and automation:

```bash
# Quick status check
openclaw-dash --status

# JSON output for processing
openclaw-dash --json | jq '.plugins[] | select(.status == "error")'

# Check specific plugin
openclaw-dash --status --plugin web-server
```

## Demo Mode

Run without any plugins configured:

```bash
openclaw-dash --demo
```

Uses mock data to showcase the dashboard layout and features.
