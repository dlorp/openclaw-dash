# Usage

## Basic Commands

```bash
openclaw-dash              # Launch TUI dashboard
openclaw-dash --status     # Quick text status
openclaw-dash --json       # JSON output for scripting
```

## Security Commands

```bash
openclaw-dash security              # Run security audit
openclaw-dash security --deep       # Full vulnerability scan
openclaw-dash security --fix        # Auto-fix issues
```

## Metrics

```bash
openclaw-dash metrics               # View metrics
```

## Automation

```bash
openclaw-dash auto merge            # Auto-merge approved PRs
openclaw-dash auto cleanup          # Clean stale branches
```

## TUI Dashboard

When you run `openclaw-dash` without arguments, the full TUI dashboard launches.

### Panels

- **Gateway** — Shows OpenClaw gateway status (online/offline), context usage percentage, and uptime
- **Current Task** — Displays what your agent is currently working on
- **Repos** — Repository health at a glance with PR counts and status indicators
- **Activity** — Recent actions with timestamps
- **Sessions** — Active agent sessions and their context burn rate
- **Cron** — Scheduled tasks and their status/next run time
- **Alerts** — Color-coded alerts from various sources
- **Channels** — Connected messaging channels (Discord, Slack, etc.)
- **System Resources** — CPU, memory, disk, network (toggleable with `x`)

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh all panels |
| `t` | Cycle theme (dark/light/hacker) |
| `h` / `?` | Help panel |
| `Ctrl+P` | Command palette |
| `j` / `k` | Scroll down/up |
| `G` / `Home` | Jump to end/top |
| `Tab` / `Shift+Tab` | Next/previous panel |
| `f` / `/` | Enter jump mode |
| `Enter` | Toggle panel collapse |
| `Ctrl+[` / `Ctrl+]` | Collapse/expand all |
| `x` | Toggle resources panel |
| `g` `s` `m` `a` `c` `p` `l` | Focus specific panels |

## JSON Output

For scripting and automation, use `--json` to get machine-readable output:

```bash
openclaw-dash --json | jq '.gateway.status'
```

---

See also: [Integrated Tools](Integrated-Tools.md)
